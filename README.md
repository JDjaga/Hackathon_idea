# 🛡️ AI Product Guardian

> **AI-Powered Digital Product Passport (DPP) & Product Identity Verification Engine**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://github.com/ultralytics/ultralytics)

---

## 🌟 Key Features

1. **📄 Document Intelligence Studio**
   - Multi-variant OCR preprocessing with Tesseract auto-discovery.
   - Multimodal VLM (Qwen2.5-VL) reasoning with explicit **checkbox discrimination** (only extracts checked items, ignoring unselected printed categories).
   - Multi-product isolation (produces independent passports per item from multi-product invoices).

2. **⚡ Deterministic Identity Matcher & Conflict Radar**
   - Pure mathematical comparison engine (fuzzy Levenshtein distance for serials, token overlap for corporate sellers, ISO date normalizers).
   - Real-time side-by-side visual diff highlighting verified matching fields (emerald green) vs conflicting serials/dates (crimson red).

3. **👁️ Appliance Object Vision**
   - Ultralytics YOLOv8 object localization on physical home appliances.
   - Bounding box rendering with confidence metrics and semantic VLM fallback.

4. **🛡️ Certificate-Style Passport Vault**
   - Luxury Dark & Gold digital certificate view with gold seal, QR verification code, barcode, and warranty tracking.
   - Persistent local JSON database with multi-attribute search, conflict filtering, and JSON export.

5. **⚡ Full-Featured REST API & Web Dashboard**
   - Luxury glassmorphic web dashboard.
   - Full OpenAPI/Swagger documentation at `/docs`.

---

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. Launch the Web Application
```powershell
python run.py
```
*This starts the FastAPI server and automatically opens `http://localhost:8000` in your browser.*

### 3. Optional: Interactive CLI Mode
```powershell
python run.py --cli
```

### 4. Optional: Run Automated Test Suite
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📁 Clean Project Architecture

```
c:\Users\acer\Documents\Hackathon_idea-main\
├── app/                            # Master Application Package
│   ├── config.py                   # Centralized settings & paths
│   ├── main.py                     # FastAPI application
│   ├── core/                       # Headless Core AI & Domain Engines
│   │   ├── normalizers.py          # Pure sanitizers for dates, prices, models, serials
│   │   ├── identity_matcher.py     # Deterministic matching & Conflict Radar
│   │   ├── passport_store.py       # Thread-safe JSON passport database
│   │   ├── ocr_engine.py           # Multi-variant OCR & Tesseract auto-discovery
│   │   ├── dpp_extractor.py        # Checkbox reasoning, VLM extractor & fallback
│   │   └── product_detector.py     # YOLO appliance localization & semantic fallback
│   ├── api/                        # REST API Router Endpoints
│   ├── static/                     # Web Dashboard Assets (CSS, JS, Images)
│   └── templates/                  # Responsive Web UI Dashboard HTML
├── samples/                        # Organized Test Datasets (Warranty, Invoices, Photos)
├── models/                         # Single copy of YOLO weights (yolo26n.pt)
├── data/                           # Local JSON Persistence
├── tests/                          # Automated Test Suite
└── run.py                          # Unified master launcher
```

---

## 🧪 API Documentation

Access the interactive Swagger UI at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**
