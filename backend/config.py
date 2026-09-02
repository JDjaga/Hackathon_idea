"""
Centralized Configuration for AI Product Guardian Backend

All model names, server endpoints, file paths, and detection thresholds
live here. Every other module imports from this file — nothing is hardcoded
elsewhere.
"""

import os
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OCR_OUTPUT_DIR = BASE_DIR / "ocr_output"
OCR_OUTPUT_DIR.mkdir(exist_ok=True)

PASSPORT_FILE = BASE_DIR / "product_passports.json"
OCR_EVIDENCE_FILE = OCR_OUTPUT_DIR / "ocr_evidence.json"
TESSERACT_PATH_FILE = BASE_DIR / "tesseract_path.txt"


# ============================================================
# OLLAMA
# ============================================================

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_GENERATE_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"


# ============================================================
# MODELS
# ============================================================

VISION_MODEL = "qwen2.5vl:7b"
TEXT_MODEL = "llama3.2:latest"


# ============================================================
# YOLO
# ============================================================

YOLO_MODEL_PATH = str(BASE_DIR / "yolo26n.pt")
YOLO_CONFIDENCE = 0.10
YOLO_IOU = 0.45
YOLO_IMAGE_SIZE = 1280
MIN_PRODUCT_CONFIDENCE = 0.20


# ============================================================
# API SERVER
# ============================================================

API_HOST = "0.0.0.0"
API_PORT = 8000


# ============================================================
# IDENTITY MATCHING THRESHOLDS
# ============================================================

# Levenshtein distance threshold for serial number fuzzy match
SERIAL_MATCH_THRESHOLD = 2

# Minimum fields that must match to consider two passports as
# referring to the same product
MIN_MATCH_FIELDS = 2
