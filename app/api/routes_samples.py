"""
AI Product Guardian — Sample Assets & Test Documents API Router
Exposes curated sample warranty cards, tax invoices, and appliance photographs for 1-click testing.
"""

import os
import base64
from pathlib import Path
from fastapi import APIRouter
from app.config import SAMPLES_DIR

router = APIRouter(prefix="/api/samples", tags=["Sample Test Assets"])


def get_image_thumbnail_base64(filepath: Path, max_size: int = 120) -> str:
    """Generate small base64 thumbnail for quick UI preview."""
    try:
        from PIL import Image
        import io
        with Image.open(filepath) as img:
            img.thumbnail((max_size, max_size))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=75)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return ""


@router.get("")
async def list_sample_assets():
    """List all available curated sample documents and photographs for 1-click testing."""
    samples = {
        "warranty_cards": [],
        "invoices_receipts": [],
        "appliance_photos": []
    }

    categories = {
        "warranty_cards": ("Warranty Cards", "Physical manufacturer warranty registration cards"),
        "invoices_receipts": ("Invoices & Receipts", "Purchase receipts and tax invoices"),
        "appliance_photos": ("Appliance Photographs", "Physical home appliance photographs for YOLO vision")
    }

    for cat_key in samples.keys():
        cat_dir = SAMPLES_DIR / cat_key
        if not cat_dir.exists():
            continue

        for file_path in cat_dir.glob("*.*"):
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                thumb = get_image_thumbnail_base64(file_path)
                name_clean = file_path.stem.replace("_", " ").replace("-", " ").title()
                samples[cat_key].append({
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "title": name_clean,
                    "path": str(file_path.resolve()),
                    "category": cat_key,
                    "thumbnail_base64": thumb
                })

    return {
        "categories": categories,
        "samples": samples
    }
