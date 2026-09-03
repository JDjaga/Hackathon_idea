"""
HomeMind — Centralized Configuration
Single source of truth for all paths, model configurations, endpoints, and detection thresholds.
"Your phone remembers everything you own."
"""

import os
from pathlib import Path

# ============================================================
# BASE PATHS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES_DIR = ROOT_DIR / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

OCR_EVIDENCE_DIR = DATA_DIR / "ocr_evidence"
OCR_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

PASSPORT_FILE = DATA_DIR / "passports.json"
TESSERACT_PATH_FILE = ROOT_DIR / "tesseract_path.txt"

STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

# ============================================================
# BRANDING
# ============================================================

APP_NAME = "HomeMind"
APP_TAGLINE = "Your phone remembers everything you own."
APP_VERSION = "3.0.0"

# ============================================================
# HOUSEHOLD CONFIGURATION
# ============================================================

ROOMS = [
    "Kitchen", "Living Room", "Bedroom", "Bathroom",
    "Utility", "Garage", "Office", "Balcony", "Other"
]

# Warranty duration string → days mapping
WARRANTY_DURATION_MAP = {
    "1-MONTH": 30,
    "3-MONTH": 90,
    "6-MONTH": 180,
    "1-YEAR": 365,
    "2-YEAR": 730,
    "3-YEAR": 1095,
    "4-YEAR": 1460,
    "5-YEAR": 1825,
    "10-YEAR": 3650,
    "LIFETIME": 36500,
}

# Default maintenance intervals (days) by product category
DEFAULT_MAINTENANCE_INTERVALS = {
    "Washing Machine": 180,
    "Air Conditioner": 90,
    "Water Purifier": 120,
    "Refrigerator": 365,
    "Dishwasher": 180,
    "Microwave": 365,
    "Vacuum": 90,
    "Air Purifier": 90,
}

# Health status thresholds (days until warranty expiry)
HEALTH_URGENT_DAYS = 30       # ≤30 days → urgent (red)
HEALTH_ATTENTION_DAYS = 90    # ≤90 days → attention (orange)

# ============================================================
# OLLAMA & VISION AI CONFIG
# ============================================================

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_GENERATE_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"

VISION_MODEL = os.environ.get("VISION_MODEL", "qwen3-vl:8b")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "gemma2:2b")

# Timeout for document VLM extraction
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", 120.0))
# Timeout for Ask My House local LLM (seconds)
ASK_LLM_TIMEOUT = float(os.environ.get("ASK_LLM_TIMEOUT", 45.0))

# ============================================================
# YOLO OBJECT DETECTION
# ============================================================

YOLO_MODEL_PATH = str(MODELS_DIR / "yolo26n.pt")
YOLO_CONFIDENCE = float(os.environ.get("YOLO_CONFIDENCE", 0.10))
YOLO_IOU = float(os.environ.get("YOLO_IOU", 0.45))
YOLO_IMAGE_SIZE = int(os.environ.get("YOLO_IMAGE_SIZE", 1280))
MIN_PRODUCT_CONFIDENCE = 0.20

# Supported appliance classes for YOLO detection filtering
APPLIANCE_CLASSES = {
    "refrigerator", "microwave", "oven", "toaster", "tv", "laptop",
    "mouse", "keyboard", "cell phone", "sink", "clock", "washer",
    "washing machine", "dryer", "dishwasher", "air conditioner",
    "heater", "fan", "vacuum", "blender", "iron"
}

REJECT_CLASSES = {
    "person", "backpack", "umbrella", "handbag", "tie", "suitcase",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet",
    "book", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
    "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear",
    "zebra", "giraffe"
}

# ============================================================
# IDENTITY MATCHING RULES & THRESHOLDS
# ============================================================

# Maximum Levenshtein distance for fuzzy serial number match (OCR 0/O, 1/I confusion)
SERIAL_MATCH_THRESHOLD = 2

# Minimum matching identity fields to link two passports as the same physical product
MIN_MATCH_FIELDS = 2

# ============================================================
# WEB SERVER
# ============================================================

SERVER_HOST = os.environ.get("HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("PORT", 8000))
