"""
Shared upload and sample-path helpers for camera / file ingestion.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR, SAMPLES_DIR

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def resolve_sample_path(sample_path: str) -> Path:
    """Resolve a sample image path, allowing only files under samples/."""
    if not sample_path or not str(sample_path).strip():
        raise ValueError("sample_path is empty")

    samples_root = SAMPLES_DIR.resolve()
    candidate = Path(sample_path).expanduser()
    if not candidate.is_absolute():
        candidate = (samples_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(samples_root)
    except ValueError:
        raise ValueError("sample_path must be inside the samples directory") from None

    if not candidate.is_file():
        raise FileNotFoundError(f"Sample not found: {candidate}")

    if candidate.suffix.lower() not in ALLOWED_IMAGE_EXT:
        raise ValueError("sample_path must be an image file")

    return candidate


def suffix_from_filename(filename: Optional[str]) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in ALLOWED_IMAGE_EXT:
        return ext
    return ".jpg"


def write_upload_bytes(content: bytes, filename: Optional[str] = None) -> str:
    """Persist an uploaded image to a temp file under data/. Raises ValueError if invalid."""
    if not content:
        raise ValueError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

    suffix = suffix_from_filename(filename)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(DATA_DIR)) as tmp:
        tmp.write(content)
        return tmp.name
