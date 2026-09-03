"""
AI Product Guardian — Multi-Variant Neural OCR Engine
Supports high-accuracy RapidOCR ONNX (primary, pure Python/ONNX, zero external binary)
and Tesseract OCR (secondary fallback).
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.config import OCR_EVIDENCE_DIR, TESSERACT_PATH_FILE

_RAPID_OCR = None
_RAPID_OCR_AVAILABLE = False
_TESSERACT_AVAILABLE = False
_TESSERACT_CMD = None

# 1. Initialize RapidOCR (Neural ONNX Engine)
try:
    from rapidocr_onnxruntime import RapidOCR
    _RAPID_OCR = RapidOCR()
    _RAPID_OCR_AVAILABLE = True
except Exception:
    _RAPID_OCR_AVAILABLE = False

# 2. Discover Tesseract (System Binary Fallback)
def _discover_tesseract() -> Optional[str]:
    """Find tesseract binary on host system if available."""
    try:
        import pytesseract

        if TESSERACT_PATH_FILE.exists():
            custom_path = TESSERACT_PATH_FILE.read_text().strip()
            if os.path.isfile(custom_path):
                pytesseract.pytesseract.tesseract_cmd = custom_path
                return custom_path

        path_bin = shutil.which("tesseract")
        if path_bin:
            pytesseract.pytesseract.tesseract_cmd = path_bin
            return path_bin

        windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for p in windows_paths:
            if os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return p
    except Exception:
        pass
    return None

try:
    import pytesseract
    _TESSERACT_CMD = _discover_tesseract()
    _TESSERACT_AVAILABLE = (_TESSERACT_CMD is not None)
except ImportError:
    _TESSERACT_AVAILABLE = False


def is_ocr_available() -> bool:
    """Return True if either RapidOCR ONNX or Tesseract OCR is available."""
    return _RAPID_OCR_AVAILABLE or _TESSERACT_AVAILABLE


def get_ocr_engine_name() -> str:
    """Return the name of the active OCR engine."""
    if _RAPID_OCR_AVAILABLE:
        return "RapidOCR (Neural ONNX)"
    elif _TESSERACT_AVAILABLE:
        return "Tesseract OCR"
    return "Fallback Mode"


def generate_image_variants(image: Image.Image) -> List[Image.Image]:
    """Create contrast and enhancement variants of image for multi-pass OCR."""
    variants = [image]
    gray = ImageOps.grayscale(image)
    variants.append(gray)
    enhancer = ImageEnhance.Contrast(gray)
    variants.append(enhancer.enhance(2.0))
    sharpened = gray.filter(ImageFilter.SHARPEN)
    variants.append(sharpened)
    return variants


def extract_ocr_text(image_path: str) -> Dict[str, Any]:
    """
    Run neural OCR on an image and return extracted text, confidence, and line evidence.
    Uses RapidOCR (ONNX Runtime) as primary engine, falling back to Tesseract.
    """
    if not os.path.isfile(image_path):
        return {
            "image": str(image_path),
            "text": "",
            "lines": [],
            "available": False,
            "error": "File not found"
        }

    # Method 1: RapidOCR (Neural ONNX — ultra-fast & high accuracy)
    if _RAPID_OCR_AVAILABLE:
        try:
            results, elapse = _RAPID_OCR(image_path)
            lines = []
            text_parts = []

            if results:
                for row in results:
                    txt = None
                    if isinstance(row, dict):
                        txt = row.get("txt") or row.get("text")
                    elif isinstance(row, (list, tuple)) and len(row) >= 2:
                        txt = row[1]
                    cleaned_txt = str(txt or "").strip()
                    if cleaned_txt:
                        lines.append(cleaned_txt)
                        text_parts.append(cleaned_txt)

            full_text = "\n".join(text_parts)
            result = {
                "image": str(image_path),
                "text": full_text,
                "lines": lines,
                "available": True,
                "engine": "rapidocr_onnx",
                "inference_time_ms": elapse if isinstance(elapse, (int, float)) else None
            }

            evidence_file = OCR_EVIDENCE_DIR / f"{Path(image_path).stem}_ocr.json"
            with open(evidence_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            return result
        except Exception as e:
            print(f"[OCR] RapidOCR error ({e}), trying secondary fallback...")

    # Method 2: Tesseract OCR fallback
    if _TESSERACT_AVAILABLE:
        try:
            import pytesseract
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

                best_text = max(extracted_texts, key=len) if extracted_texts else ""
                lines = [l.strip() for l in best_text.splitlines() if l.strip()]

                return {
                    "image": str(image_path),
                    "text": best_text,
                    "lines": lines,
                    "available": True,
                    "engine": "tesseract"
                }
        except Exception as e:
            print(f"[OCR] Tesseract error ({e})")

    # Method 3: Graceful fallback
    return {
        "image": str(image_path),
        "text": "",
        "lines": [],
        "available": False,
        "engine": "none",
        "error": "No OCR engine available"
    }
