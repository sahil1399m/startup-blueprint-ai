"""
chroma_loader.py — Downloads ChromaDB from HuggingFace Hub on backend startup.

Only downloads if chroma.sqlite3 is missing locally.
Resume-safe: snapshot_download is idempotent — already-downloaded files are skipped.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def download_chroma_if_needed(
    repo_id: str,
    local_dir: str,
    hf_token: str,
) -> None:
    """
    Download the ChromaDB snapshot from HuggingFace if not already present.
    Called once at FastAPI lifespan startup — blocks until complete.

    Args:
        repo_id:   HF dataset repo, e.g. "sahilsks/startup-blueprint-chroma-db"
        local_dir: Where to store locally, e.g. "./chroma_db"
        hf_token:  HF read token (required for private datasets)
    """
    local_path  = Path(local_dir)
    sqlite_file = local_path / "chroma.sqlite3"

    if sqlite_file.exists() and sqlite_file.stat().st_size > 0:
        log.info(f"✅ ChromaDB already present at '{local_dir}' — skipping download.")
        return

    log.info(f"⬇️  ChromaDB not found locally. Downloading from HF Hub…")
    log.info(f"   Repo : {repo_id}")
    log.info(f"   Dest : {local_dir}")
    log.info(f"   Note : First startup may take ~60s for 104MB download.")

    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN is not set. Set it in Railway Variables or your .env file. "
            "Required to download the private ChromaDB dataset."
        )

    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=local_dir,
            local_dir_use_symlinks=False,   # copy files, not symlinks (safer on Railway)
            token=hf_token,
            ignore_patterns=[               # skip non-ChromaDB files
                ".gitattributes",
                "README.md",
                "*.md",
            ],
        )

        # Verify the download actually produced the SQLite file
        if not sqlite_file.exists():
            raise RuntimeError(
                f"Download completed but chroma.sqlite3 not found in '{local_dir}'. "
                "Check that the HF dataset contains the ChromaDB files at the root level."
            )

        size_mb = sqlite_file.stat().st_size / (1024 * 1024)
        log.info(f"✅ ChromaDB downloaded successfully. sqlite3 size: {size_mb:.1f} MB")

    except RuntimeError:
        raise
    except Exception as e:
        log.error(f"❌ ChromaDB download failed: {e}")
        raise RuntimeError(
            f"Failed to download ChromaDB from HuggingFace Hub.\n"
            f"Repo: {repo_id}\n"
            f"Error: {e}\n"
            f"Check HF_TOKEN and HF_CHROMA_REPO in your environment variables."
        ) from e