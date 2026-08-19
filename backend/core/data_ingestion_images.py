"""
data_ingestion_images.py — Image-only ingestion pass for Startup Blueprint Generator

Run AFTER data_ingestion.py has completed Pass 1 (text + tables).
Adds visual summaries into the `visual_summaries` ChromaDB collection.

Why separate:
  - Free tier Gemini Vision quota exhausts fast; keeping it separate means
    a rate limit never blocks your text/table embeddings.
  - Resume-safe: tracks (page, img_idx) tuples already embedded, skips them.

Rate limit strategy:
  - Uses gemini-1.5-flash (higher free quota than 2.0-flash for vision).
  - Exponential backoff retry: on 429, waits 30s → 60s → 120s before giving up.
  - Full-page scan detection: images covering >80% of page area are skipped
    (they are scanned document pages, not charts — text already handled).
  - Deduplicates identical image bytes within a PDF using MD5 hash.

Run: python data_ingestion_images.py
"""

import os
import io
import glob
import time
import hashlib
import chromadb
import pdfplumber
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH          = "chroma_db"
DATA_DIR             = "data"
MIN_IMG_SIZE         = (100, 100)   # skip anything smaller (icons, decorations)
MAX_PAGE_AREA_FRAC   = 0.80         # skip full-page scans
VISION_MODEL         = "gemini-2.0-flash"          # confirmed working with google-genai SDK
EMBED_MODEL          = "models/gemini-embedding-001"
VISION_BASE_DELAY    = 8.0          # seconds between vision calls (free ≈ 10 RPM)
EMBED_DELAY          = 1.5          # seconds between embed calls
MAX_RETRY_ATTEMPTS   = 3            # exponential backoff retries on 429
RETRY_WAIT_SECONDS   = [30, 60, 120]  # wait before each retry attempt

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

client_genai = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# ── Helpers ───────────────────────────────────────────────────────────────────
def infer_doc_type(pdf_path: str) -> str:
    rel   = os.path.relpath(pdf_path, DATA_DIR)
    parts = rel.split(os.sep)
    if len(parts) > 1 and parts[0].lower() in KNOWN_DOC_TYPES:
        return parts[0].lower()
    fname = parts[-1].lower()
    for doc_type, keywords in FILENAME_KEYWORDS.items():
        if any(kw in fname for kw in keywords):
            return doc_type
    return "general"


def image_md5(pil_img: Image.Image) -> str:
    """MD5 of raw image bytes — used to deduplicate identical images in a PDF."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return hashlib.md5(buf.getvalue()).hexdigest()


def get_text_embedding(text: str) -> list[float]:
    result = client_genai.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def describe_image_with_retry(pil_img: Image.Image, context: str = "") -> str:
    """
    Call Gemini Vision with exponential backoff on 429/quota errors.
    Returns description string, or empty string if all retries fail.

    google-genai SDK requires bytes + text parts to be wrapped inside a
    single Content object (role="user") — passing a bare list of mixed
    Part + str causes a 404 on some API versions.
    """
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    prompt_text = (
        "You are analyzing a page from an Indian startup ecosystem report or "
        "government policy document. Describe this image, chart, table, or diagram "
        "in detail. Focus on: key numbers, trends, sector names, funding amounts, "
        "policy names, government schemes, startup names, and any business insights "
        f"visible. Page context: {context[:200] if context else 'startup/business report'}. "
        "Be specific and factual. Output a dense description (100-200 words) "
        "suitable for semantic search retrieval."
    )

    # Wrap in a proper Content object — most reliable across SDK versions
    content = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            types.Part.from_text(text=prompt_text),
        ]
    )

    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            response = client_genai.models.generate_content(
                model=VISION_MODEL,
                contents=[content],
            )
            return response.text.strip()

        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "RESOURCE_EXHAUSTED" in err
            is_daily      = "daily" in err.lower() or "quota" in err.lower()

            if is_daily:
                print(f"\n🚫 Daily vision quota exhausted. Re-run tomorrow or switch to paid tier.")
                print(f"   Error: {err[:120]}")
                return "__DAILY_QUOTA__"

            if is_rate_limit and attempt < MAX_RETRY_ATTEMPTS - 1:
                wait = RETRY_WAIT_SECONDS[attempt]
                print(f"      ⏳ Rate limit (429). Waiting {wait}s before retry "
                      f"({attempt+1}/{MAX_RETRY_ATTEMPTS-1})...")
                time.sleep(wait)
                continue

            print(f"      ⚠️  Vision error (attempt {attempt+1}): {err[:100]}")
            if attempt == MAX_RETRY_ATTEMPTS - 1:
                return ""

    return ""


def get_embedded_visual_keys(collection) -> dict[str, set]:
    """Return {source: set_of_(page, img_idx)_tuples} already in visual_summaries."""
    try:
        existing = collection.get(include=["metadatas"])
        done: dict[str, set] = {}
        for meta in existing["metadatas"]:
            src = meta.get("source", "")
            pg  = meta.get("page", -1)
            idx = meta.get("image_idx", -1)
            done.setdefault(src, set()).add((pg, idx))
        return done
    except Exception:
        return {}


def get_next_visual_id(collection) -> int:
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


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def _validate_vision_model() -> bool:
    """
    Send a tiny test image to Gemini before processing any PDFs.
    Catches wrong model names / API version mismatches immediately.
    Returns True if OK, False if broken.
    """
    print(f"  🔍 Validating vision model '{VISION_MODEL}'...")
    try:
        # 10×10 white PNG — minimal payload
        test_img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        buf = io.BytesIO()
        test_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        content = types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                types.Part.from_text(text="What color is this image? One word answer."),
            ]
        )
        resp = client_genai.models.generate_content(
            model=VISION_MODEL,
            contents=[content],
        )
        print(f"  ✅ Model OK — test response: '{resp.text.strip()[:30]}'")
        return True
    except Exception as e:
        err = str(e)
        print(f"  ❌ Model validation FAILED: {err[:200]}")
        if "404" in err:
            print(f"\n  Try one of these model names instead:")
            print(f"    VISION_MODEL = \"gemini-2.0-flash\"")
            print(f"    VISION_MODEL = \"gemini-2.5-flash\"")
            print(f"    VISION_MODEL = \"gemini-2.0-flash-001\"")
        return False


def ingest_images():
    print("\n🖼️  Image-only Ingestion — Startup Blueprint Generator")
    print("=" * 62)
    print(f"  Vision model : {VISION_MODEL}")
    print(f"  Embed model  : {EMBED_MODEL}")
    print(f"  Delay        : {VISION_BASE_DELAY}s between vision calls")
    print(f"  Retry        : up to {MAX_RETRY_ATTEMPTS} attempts with backoff")
    print("=" * 62)

    # Validate before touching any PDFs
    if not _validate_vision_model():
        print("\n⛔ Aborting — fix VISION_MODEL at the top of this file and re-run.")
        return

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Connect to existing visual_summaries collection (created by data_ingestion.py)
    try:
        visual_col = chroma_client.get_collection(name="visual_summaries")
        print(f"\n✅ Connected to [visual_summaries] — {visual_col.count()} existing")
    except Exception:
        visual_col = chroma_client.create_collection(
            name="visual_summaries",
            metadata={"hnsw:space": "cosine"},
        )
        print("\n🆕 Created [visual_summaries]")

    visual_done = get_embedded_visual_keys(visual_col)
    visual_id   = get_next_visual_id(visual_col)

    pdf_files = sorted(glob.glob(f"{DATA_DIR}/**/*.pdf", recursive=True))
    if not pdf_files:
        print(f"\n⚠️  No PDFs found under {DATA_DIR}/")
        return

    print(f"\n📁 Found {len(pdf_files)} PDF(s)\n")

    added    = 0
    skipped  = 0
    deduped  = 0
    errors   = 0

    for pdf_idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.relpath(pdf_path, DATA_DIR)
        doc_type = infer_doc_type(pdf_path)
        print(f"\n[{pdf_idx}/{len(pdf_files)}] {filename}  [doc_type={doc_type}]")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                page_area   = None
                seen_hashes = set()   # deduplicate within this PDF

                for page_num, page in enumerate(pdf.pages, 1):
                    label    = f"p{page_num}/{total_pages}"
                    raw_text = page.extract_text() or ""

                    if page_area is None:
                        page_area = float(page.width) * float(page.height)

                    images = page.images or []
                    if not images:
                        continue

                    for img_idx, img_meta in enumerate(images):
                        resume_key = (page_num, img_idx)
                        if resume_key in visual_done.get(filename, set()):
                            skipped += 1
                            continue

                        try:
                            # ── Clip and validate bbox ────────────────────
                            x0  = max(float(img_meta["x0"]),      0.0)
                            top = max(float(img_meta["top"]),      0.0)
                            x1  = min(float(img_meta["x1"]),      float(page.width))
                            bot = min(float(img_meta["bottom"]),   float(page.height))

                            if x1 <= x0 or bot <= top:
                                continue

                            # ── Skip full-page scans ──────────────────────
                            img_area = (x1 - x0) * (bot - top)
                            if (img_area / max(page_area, 1)) > MAX_PAGE_AREA_FRAC:
                                print(f"  ⏭️  [{label}] img {img_idx} — "
                                      f"full-page scan ({img_area/page_area:.0%}), skipping")
                                continue

                            # ── Extract PIL image ─────────────────────────
                            page_img = page.crop((x0, top, x1, bot)).to_image(resolution=150)
                            pil_img  = page_img.original

                            if (pil_img.width  < MIN_IMG_SIZE[0] or
                                    pil_img.height < MIN_IMG_SIZE[1]):
                                continue

                            # ── Deduplicate by MD5 within this PDF ────────
                            img_hash = image_md5(pil_img)
                            if img_hash in seen_hashes:
                                print(f"  🔁 [{label}] img {img_idx} — duplicate, skipping")
                                deduped += 1
                                continue
                            seen_hashes.add(img_hash)

                            # ── Describe with Gemini Vision ───────────────
                            print(f"  🖼️  [{label}] img {img_idx} "
                                  f"({pil_img.width}×{pil_img.height}) → describing...")
                            time.sleep(VISION_BASE_DELAY)
                            description = describe_image_with_retry(
                                pil_img, context=raw_text[:300]
                            )

                            if description == "__DAILY_QUOTA__":
                                print("\n  Stopping — daily quota exhausted.")
                                print(f"  Progress: {added} images embedded so far.")
                                _print_stats(visual_col, added, skipped, deduped, errors)
                                return

                            if not description:
                                print(f"      ⚠️  No description returned, skipping")
                                continue

                            # ── Embed and store ───────────────────────────
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
                            visual_id += 1
                            added     += 1
                            print(f"      ✓ Stored as visual_{visual_id-1}. "
                                  f"Preview: {description[:80]}...")

                        except Exception as e:
                            err = str(e)
                            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                                print(f"\n  ⚠️  Unexpected 429 outside retry loop: {err[:80]}")
                            else:
                                print(f"  ❌ img error: {err[:100]}")
                            errors += 1

        except Exception as e:
            print(f"  ❌ PDF error: {str(e)[:120]}")
            errors += 1

    _print_stats(visual_col, added, skipped, deduped, errors)


def _print_stats(col, added, skipped, deduped, errors):
    print("\n" + "═" * 62)
    print("  ✅ IMAGE INGESTION COMPLETE")
    print("═" * 62)
    print(f"  Added this run    : +{added}")
    print(f"  Skipped (resume)  : {skipped}")
    print(f"  Deduped (MD5)     : {deduped}")
    if errors:
        print(f"  Errors            : {errors}")
    print(f"  Total in collection: {col.count()}")
    print("═" * 62 + "\n")


if __name__ == "__main__":
    ingest_images()