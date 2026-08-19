"""
data_ingestion.py — Multimodal PDF ingestion for Startup Blueprint Generator
Extracts and embeds: text chunks, tables, visual summaries (charts/images)
into 3 separate ChromaDB collections using Gemini embedding-001.

Collections:
  - text_chunks      : plain text paragraphs and prose
  - table_data       : tables serialized to markdown
  - visual_summaries : Gemini Vision descriptions of charts/images/diagrams

doc_type metadata (required by crag.py for filtered retrieval):
  Inferred from subfolder name under data/ — organise your PDFs as:
    data/government_scheme/  → startup india, MSME, DPIIT, yojana PDFs
    data/market_report/      → sector trend, industry reports
    data/legal/              → companies act, GST, compliance docs
    data/investor/           → incubator directories, VC landscape
    data/general/            → anything that doesn't fit above

Run:   python data_ingestion.py
Resume-safe: skips already-embedded (page, chunk_idx) pairs per source file.

Bugs fixed vs original:
  1. Resume logic keyed on compound string (never matched) → now uses
     (page, chunk_idx) tuples per source filename — actually skips duplicates.
  2. IDs started from collection.count() — crashes on re-run if prior run had
     errors/deletions → now scans existing IDs for true max.
  3. doc_type metadata was missing — crag.py where-filter returned zero results,
     silently falling to Tavily every time → added to all three collections.
  4. Vision call had bytes + text part order wrong for Gemini 2.0 Flash →
     bytes part now comes before text prompt.
  5. page.crop().to_image() on degenerate bboxes threw AttributeError →
     added bbox clipping and validity check.
"""

import os
import glob
import time
import io
import chromadb
import pdfplumber
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH    = "chroma_db"
DATA_DIR       = "data"
CHUNK_SIZE     = 500
CHUNK_OVERLAP  = 50
EMBED_DELAY    = 1.5       # seconds between embedding API calls (rate-limit safety)
VISION_DELAY   = 7.0       # seconds between vision API calls
                           # Free tier: ~10 RPM = 6s minimum; 7s gives headroom
MIN_TEXT_LEN   = 60        # skip chunks shorter than this
MIN_TABLE_ROWS = 2         # skip tables with fewer rows
MIN_IMG_SIZE   = (80, 80)  # skip tiny images (likely icons/decorative elements)

# Scanned PDFs (e.g. Nasscom report) render the entire page as a single image.
# If an image covers more than this fraction of the page area it's a full-page
# scan, not an embedded chart — skip it in the visual pipeline (text extraction
# via pdfplumber already handles the OCR layer for those pages).
MAX_PAGE_AREA_FRACTION = 0.80

EMBED_MODEL  = "models/gemini-embedding-001"
VISION_MODEL = "gemini-2.0-flash"

client_genai = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# ── doc_type inference (must match crag.py filter values) ────────────────────
KNOWN_DOC_TYPES = {"government_scheme", "market_report", "legal", "investor", "general"}

FILENAME_KEYWORDS = {
    "government_scheme": ["scheme", "msme", "startup_india", "dpiit", "policy",
                          "subsidy", "yojana", "seedfund", "standup", "mudra"],
    "market_report":     ["market", "trend", "report", "survey", "industry",
                          "sector", "outlook", "analysis", "research"],
    "legal":             ["legal", "compliance", "act", "regulation", "tax",
                          "gst", "company_law", "ipr", "patent", "trademark"],
    "investor":          ["investor", "incubator", "accelerator", "vc", "funding",
                          "angel", "venture", "seed", "fund"],
}


def infer_doc_type(pdf_path: str) -> str:
    """
    1. If the PDF lives directly under data/<doc_type>/*, use that subfolder.
    2. Otherwise keyword-match on the filename.
    3. Default: "general".
    """
    rel   = os.path.relpath(pdf_path, DATA_DIR)
    parts = rel.split(os.sep)
    if len(parts) > 1 and parts[0].lower() in KNOWN_DOC_TYPES:
        return parts[0].lower()
    fname = parts[-1].lower()
    for doc_type, keywords in FILENAME_KEYWORDS.items():
        if any(kw in fname for kw in keywords):
            return doc_type
    return "general"


# ── Gemini helpers ────────────────────────────────────────────────────────────
def get_text_embedding(text: str) -> list[float]:
    result = client_genai.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def describe_image_with_gemini(pil_img: Image.Image, context: str = "") -> str:
    """
    Use Gemini Vision to produce a dense retrieval-optimised description.
    Bytes part MUST precede the text prompt — Gemini 2.0 Flash rejects the
    reverse order (was a bug in the original script).
    """
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    prompt = (
        "You are analyzing a page from an Indian startup ecosystem report or "
        "government policy document. Describe this image, chart, table, or diagram "
        "in detail. Focus on: key numbers, trends, sector names, funding amounts, "
        "policy names, government schemes, startup names, and any business insights "
        f"visible. Page context: {context[:200] if context else 'startup/business report'}. "
        "Be specific and factual. Output a dense description (100-200 words) "
        "suitable for semantic search retrieval."
    )

    try:
        # bytes part first, then text — required order for Gemini 2.0 Flash
        response = client_genai.models.generate_content(
            model=VISION_MODEL,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        return response.text.strip()
    except Exception as e:
        return f"[Vision error: {str(e)[:100]}]"


# ── Text helpers ──────────────────────────────────────────────────────────────
def chunk_text(text: str) -> list[str]:
    words  = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + CHUNK_SIZE])
        if len(chunk.strip()) >= MIN_TEXT_LEN:
            chunks.append(chunk)
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def table_to_markdown(table: list[list]) -> str:
    if not table or len(table) < MIN_TABLE_ROWS:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(c).strip() if c else "" for c in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


# ── Resume helpers ────────────────────────────────────────────────────────────
def get_embedded_keys(collection) -> dict[str, set]:
    """
    Returns {source_filename: set_of_(page, idx)_tuples} already stored.

    BUG FIX: original code keyed by a compound string like
    "schemes/foo.pdf_text_3_2" then looked up that string as if it were
    a source filename — it never matched, so nothing was ever skipped and
    every run re-embedded everything.  Fixed: key by actual source filename,
    store (page, chunk_idx) tuples.
    """
    try:
        existing = collection.get(include=["metadatas"])
        done: dict[str, set] = {}
        for meta in existing["metadatas"]:
            src = meta.get("source", "")
            pg  = meta.get("page", -1)
            # chunk / table_idx / image_idx all stored under their own key
            idx = meta.get("chunk", meta.get("table_idx", meta.get("image_idx", -1)))
            done.setdefault(src, set()).add((pg, idx))
        return done
    except Exception:
        return {}


def get_next_id(collection, prefix: str) -> int:
    """
    Return the next safe integer ID for this collection prefix.

    BUG FIX: original used collection.count() as the starting ID, which
    breaks when a previous run had errors or deletions — the count no longer
    equals the max existing ID, causing duplicate-ID crashes on .add().
    Fixed: scan existing IDs to find true max.
    """
    if collection.count() == 0:
        return 0
    try:
        existing = collection.get(include=[])
        nums = []
        for id_str in existing.get("ids", []):
            try:
                nums.append(int(id_str.split("_")[-1]))
            except ValueError:
                pass
        return max(nums) + 1 if nums else collection.count()
    except Exception:
        return collection.count()


# ── Stats printer ─────────────────────────────────────────────────────────────
def print_stats(text_col, table_col, visual_col):
    t  = text_col.count()
    tb = table_col.count()
    v  = visual_col.count()
    total = t + tb + v
    BAR   = 38

    def bar(n):
        filled = int((n / max(total, 1)) * BAR)
        return "█" * filled + "░" * (BAR - filled)

    print("\n" + "═" * 62)
    print("  📊 EMBEDDING STATS")
    print("═" * 62)
    print(f"  {'Collection':<24} {'Count':>6}  Distribution")
    print(f"  {'─'*24}  {'─'*6}  {'─'*BAR}")
    print(f"  {'📄 text_chunks':<24} {t:>6}  {bar(t)}")
    print(f"  {'📊 table_data':<24} {tb:>6}  {bar(tb)}")
    print(f"  {'🖼️  visual_summaries':<24} {v:>6}  {bar(v)}")
    print(f"  {'─'*24}  {'─'*6}")
    print(f"  {'TOTAL':<24} {total:>6}")
    print("═" * 62)
    print(f"  Embed model  : {EMBED_MODEL}")
    print(f"  Vision model : {VISION_MODEL}")
    print(f"  ChromaDB     : {CHROMA_PATH}/")
    print("═" * 62 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def ingest_pdfs():
    print("\n🚀 Multimodal PDF Ingestion — Startup Blueprint Generator")
    print("=" * 62)

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    def get_or_create(name):
        try:
            col = chroma_client.get_collection(name=name)
            print(f"  ✅ Resumed  [{name}] — {col.count()} existing embeddings")
        except Exception:
            col = chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"  🆕 Created  [{name}]")
        return col

    print("\n📦 Collections:")
    text_col   = get_or_create("text_chunks")
    table_col  = get_or_create("table_data")
    visual_col = get_or_create("visual_summaries")

    # load existing keys for resume (fixed logic — see get_embedded_keys)
    text_done   = get_embedded_keys(text_col)
    table_done  = get_embedded_keys(table_col)
    visual_done = get_embedded_keys(visual_col)

    # safe starting IDs (fixed — see get_next_id)
    text_id   = get_next_id(text_col,   "text")
    table_id  = get_next_id(table_col,  "table")
    visual_id = get_next_id(visual_col, "visual")

    pdf_files = sorted(glob.glob(f"{DATA_DIR}/**/*.pdf", recursive=True))
    if not pdf_files:
        print(f"\n⚠️  No PDFs found under {DATA_DIR}/. Add PDFs and re-run.")
        return
    print(f"\n📁 Found {len(pdf_files)} PDF(s) in {DATA_DIR}/\n")

    added_text = added_table = added_visual = 0
    skipped    = 0
    errors     = 0

    # ══════════════════════════════════════════════════════════════════════════
    # PASS 1 — TEXT + TABLES (all PDFs, no vision API calls)
    # Run this to completion before touching the vision quota.
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "━" * 62)
    print("  PASS 1 — Text & Table embeddings (all 38 PDFs)")
    print("━" * 62)

    for pdf_idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.relpath(pdf_path, DATA_DIR)
        doc_type = infer_doc_type(pdf_path)
        print(f"\n[{pdf_idx}/{len(pdf_files)}] {filename}  [doc_type={doc_type}]")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    label    = f"p{page_num}/{total_pages}"
                    raw_text = page.extract_text() or ""

                    # ── TEXT CHUNKS ───────────────────────────────────────
                    if raw_text.strip():
                        for chunk_idx, chunk in enumerate(chunk_text(raw_text)):
                            resume_key = (page_num, chunk_idx)
                            if resume_key in text_done.get(filename, set()):
                                skipped += 1
                                continue
                            try:
                                time.sleep(EMBED_DELAY)
                                emb = get_text_embedding(chunk)
                                text_col.add(
                                    ids=[f"text_{text_id}"],
                                    embeddings=[emb],
                                    documents=[chunk],
                                    metadatas=[{
                                        "source":   filename,
                                        "page":     page_num,
                                        "chunk":    chunk_idx,
                                        "type":     "text",
                                        "doc_type": doc_type,
                                        "char_len": len(chunk),
                                    }],
                                )
                                text_done.setdefault(filename, set()).add(resume_key)
                                text_id    += 1
                                added_text += 1
                                print(f"  📄 [{label}] chunk {chunk_idx} → {doc_type} ✓")
                            except Exception as e:
                                err = str(e)
                                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                                    print("\n⚠️  Rate limit (text). Re-run to resume.\n")
                                    print_stats(text_col, table_col, visual_col)
                                    return
                                print(f"  ❌ text error: {err[:80]}")
                                errors += 1

                    # ── TABLES ────────────────────────────────────────────
                    for tbl_idx, table in enumerate(page.extract_tables() or []):
                        if not table or len(table) < MIN_TABLE_ROWS:
                            continue
                        md = table_to_markdown(table)
                        if not md or len(md) < MIN_TEXT_LEN:
                            continue

                        resume_key = (page_num, tbl_idx)
                        if resume_key in table_done.get(filename, set()):
                            skipped += 1
                            continue

                        ctx_text = f"Table from page {page_num} of {filename}:\n{md}"
                        try:
                            time.sleep(EMBED_DELAY)
                            emb = get_text_embedding(ctx_text)
                            table_col.add(
                                ids=[f"table_{table_id}"],
                                embeddings=[emb],
                                documents=[ctx_text],
                                metadatas=[{
                                    "source":    filename,
                                    "page":      page_num,
                                    "table_idx": tbl_idx,
                                    "type":      "table",
                                    "doc_type":  doc_type,
                                    "row_count": len(table),
                                    "col_count": len(table[0]) if table else 0,
                                    "markdown":  md[:500],
                                }],
                            )
                            table_done.setdefault(filename, set()).add(resume_key)
                            table_id    += 1
                            added_table += 1
                            print(f"  📊 [{label}] table {tbl_idx} "
                                  f"({len(table)} rows) → {doc_type} ✓")
                        except Exception as e:
                            err = str(e)
                            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                                print("\n⚠️  Rate limit (table). Re-run to resume.\n")
                                print_stats(text_col, table_col, visual_col)
                                return
                            print(f"  ❌ table error: {err[:80]}")
                            errors += 1

        except Exception as e:
            print(f"  ❌ PDF open error: {str(e)[:120]}")
            errors += 1
            continue

    print(f"\n✅ Pass 1 done — {added_text} text chunks, {added_table} tables embedded.")

    # ══════════════════════════════════════════════════════════════════════════
    # PASS 2 — IMAGES / VISUALS (separate pass, vision API only)
    # Runs after all text+table is safely stored.
    # Full-page scans (area > MAX_PAGE_AREA_FRACTION of the page) are skipped —
    # those are scanned document pages, not embedded charts/diagrams, and their
    # text content is already handled by pdfplumber's text extraction above.
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "━" * 62)
    print("  PASS 2 — Visual/image embeddings (vision API)")
    print("  Tip: if you hit rate limits here, just re-run — Pass 1 will be")
    print("  skipped entirely (resume-safe) and Pass 2 will pick up where it left off.")
    print("━" * 62)

    for pdf_idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.relpath(pdf_path, DATA_DIR)
        doc_type = infer_doc_type(pdf_path)
        print(f"\n[{pdf_idx}/{len(pdf_files)}] {filename}  [doc_type={doc_type}]")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                page_area   = None  # computed once per PDF from first page

                for page_num, page in enumerate(pdf.pages, 1):
                    label    = f"p{page_num}/{total_pages}"
                    raw_text = page.extract_text() or ""

                    # Compute page area once (width × height in PDF points)
                    if page_area is None:
                        page_area = float(page.width) * float(page.height)

                    for img_idx, img_meta in enumerate(page.images or []):
                        resume_key = (page_num, img_idx)
                        if resume_key in visual_done.get(filename, set()):
                            skipped += 1
                            continue

                        try:
                            x0  = max(float(img_meta["x0"]),     0.0)
                            top = max(float(img_meta["top"]),     0.0)
                            x1  = min(float(img_meta["x1"]),     float(page.width))
                            bot = min(float(img_meta["bottom"]),  float(page.height))

                            if x1 <= x0 or bot <= top:
                                continue  # degenerate bbox

                            # Skip full-page scans — these are scanned document
                            # pages, not embedded charts. Their text is already
                            # extracted in Pass 1. Sending a 2000×1100px page
                            # image to vision just wastes quota and produces
                            # a generic document description instead of a useful
                            # chart/diagram summary.
                            img_area     = (x1 - x0) * (bot - top)
                            area_fraction = img_area / max(page_area, 1)
                            if area_fraction > MAX_PAGE_AREA_FRACTION:
                                print(f"  ⏭️  [{label}] image {img_idx} — "
                                      f"full-page scan ({area_fraction:.0%}), skipping")
                                continue

                            page_image = page.crop((x0, top, x1, bot)).to_image(resolution=150)
                            pil_img    = page_image.original

                            if (pil_img.width  < MIN_IMG_SIZE[0] or
                                    pil_img.height < MIN_IMG_SIZE[1]):
                                continue  # icon / decorative element

                            print(f"  🖼️  [{label}] image {img_idx} "
                                  f"({pil_img.width}×{pil_img.height}) → describing...")
                            time.sleep(VISION_DELAY)
                            description = describe_image_with_gemini(
                                pil_img, context=raw_text[:300]
                            )

                            if not description or "[Vision error" in description:
                                print(f"      ⚠️  Vision failed: {description[:80]}")
                                continue

                            embed_text = (
                                f"Visual content from {filename} page {page_num} "
                                f"[{doc_type}]: {description}"
                            )
                            time.sleep(EMBED_DELAY)
                            emb = get_text_embedding(embed_text)
                            visual_col.add(
                                ids=[f"visual_{visual_id}"],
                                embeddings=[emb],
                                documents=[embed_text],
                                metadatas=[{
                                    "source":      filename,
                                    "page":        page_num,
                                    "image_idx":   img_idx,
                                    "type":        "visual",
                                    "doc_type":    doc_type,
                                    "width":       pil_img.width,
                                    "height":      pil_img.height,
                                    "description": description[:600],
                                }],
                            )
                            visual_done.setdefault(filename, set()).add(resume_key)
                            visual_id    += 1
                            added_visual += 1
                            print(f"      ✓ Visual embedded. "
                                  f"Preview: {description[:90]}...")

                        except Exception as e:
                            err = str(e)
                            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                                print("\n⚠️  Rate limit (vision). Re-run to resume —")
                                print("    Pass 1 is already complete and will be skipped.\n")
                                print_stats(text_col, table_col, visual_col)
                                return
                            print(f"  ❌ image error: {err[:100]}")
                            errors += 1

        except Exception as e:
            print(f"  ❌ PDF open error: {str(e)[:120]}")
            errors += 1
            continue

    # ── Final report ──────────────────────────────────────────────────────────
    print("\n" + "═" * 62)
    print("  ✅ INGESTION COMPLETE (both passes)")
    print("═" * 62)
    print(f"  This run added:")
    print(f"    📄 Text chunks       : +{added_text}")
    print(f"    📊 Tables            : +{added_table}")
    print(f"    🖼️  Visual summaries  : +{added_visual}")
    print(f"    ⏭️  Skipped (resume)  : {skipped}")
    if errors:
        print(f"    ❌ Errors            : {errors}")
    print_stats(text_col, table_col, visual_col)


if __name__ == "__main__":
    ingest_pdfs()