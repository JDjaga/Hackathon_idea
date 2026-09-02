"""
AI Product Guardian — Multi-Variant OCR Engine
Preprocesses document images and extracts textual and spatial evidence using Tesseract.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.config import OCR_EVIDENCE_DIR, TESSERACT_PATH_FILE

# Global state for Tesseract availability
_TESSERACT_AVAILABLE = False
_TESSERACT_CMD = None

def _discover_tesseract() -> Optional[str]:
    """Find tesseract binary on host system."""
    import pytesseract

    # 1. Check custom override file
    if TESSERACT_PATH_FILE.exists():
        try:
            custom_path = TESSERACT_PATH_FILE.read_text().strip()
            if os.path.isfile(custom_path):
                pytesseract.pytesseract.tesseract_cmd = custom_path
                return custom_path
        except Exception:
            pass

    # 2. Check system PATH
    path_bin = shutil.which("tesseract")
    if path_bin:
        pytesseract.pytesseract.tesseract_cmd = path_bin
        return path_bin

    # 3. Check common Windows installation locations
    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in windows_paths:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return p

    return None

try:
    import pytesseract
    _TESSERACT_CMD = _discover_tesseract()
    _TESSERACT_AVAILABLE = (_TESSERACT_CMD is not None)
except ImportError:
    _TESSERACT_AVAILABLE = False


def is_ocr_available() -> bool:
    """Return True if Tesseract OCR is installed and available."""
    return _TESSERACT_AVAILABLE


def generate_image_variants(image: Image.Image) -> List[Image.Image]:
    """Create contrast and enhancement variants of image for multi-pass OCR."""
    variants = [image]

    # Grayscale
    gray = ImageOps.grayscale(image)
    variants.append(gray)

    # High Contrast
    enhancer = ImageEnhance.Contrast(gray)
    variants.append(enhancer.enhance(2.0))

    # Sharpened
    sharpened = gray.filter(ImageFilter.SHARPEN)
    variants.append(sharpened)

    return variants


def extract_ocr_text(image_path: str) -> Dict[str, Any]:
    """
    Run multi-variant OCR on an image and return extracted text and line evidence.
    """
    if not _TESSERACT_AVAILABLE:
        return {
            "image": str(image_path),
            "text": "",
            "lines": [],
            "available": False,
            "error": "Tesseract binary not found on system."
        }

    try:
        with Image.open(image_path) as img:
            variants = generate_image_variants(img)
            extracted_texts = []

            for var in variants:
                try:
                    txt = pytesseract.image_to_string(var, config="--psm 6")
                    if txt.strip():
                        extracted_texts.append(txt.strip())
                except Exception:
                    continue

            # Pick the longest / most complete text extraction
            best_text = max(extracted_texts, key=len) if extracted_texts else ""
            lines = [l.strip() for l in best_text.splitlines() if l.strip()]

            result = {
                "image": str(image_path),
                "text": best_text,
                "lines": lines,
                "available": True,
                "variants_processed": len(variants)
            }

            # Save OCR evidence to data directory
            evidence_file = OCR_EVIDENCE_DIR / f"{Path(image_path).stem}_ocr.json"
            with open(evidence_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            return result

    except Exception as e:
        return {
            "image": str(image_path),
            "text": "",
            "lines": [],
            "available": False,
            "error": str(e)
        }
