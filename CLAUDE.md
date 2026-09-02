# CLAUDE.md — AI Product Guardian

Developer and agent technical reference for the **AI Product Guardian** platform — an end-to-end Digital Product Passport (DPP) generator, appliance object detector, and deterministic identity verification engine.

---

## 0. Non-Negotiables & Core Principles

1. **Deterministic Identity Verification:** Product identity matching and conflict detection use pure mathematical algorithms (Levenshtein edit-distance, token containment, ISO normalizers) — never an LLM.
2. **Clean Layer Separation:** The AI and business logic engines in `app/core/` are completely headless and independent of web, UI, or CLI layers.
3. **Graceful Degradation:** The pipeline operates seamlessly even if Ollama or Tesseract are unavailable by providing intelligent fallback extraction and diagnostics.
4. **Single Source of Truth:** All paths, models, endpoints, and detection thresholds live in `app/config.py`.

---

## 1. Project Overview & Architecture

**AI Product Guardian** provides:
- **Document Intelligence Studio:** Multi-variant OCR and multimodal VLM reasoning to generate Digital Product Passports with checkbox discrimination.
- **Certificate-Style Passports:** Luxury digital passports with verifiable security seals, barcodes, and warranty tracking.
- **Identity Matcher & Conflict Radar:** Cross-document verification highlighting matching fields (emerald) vs conflicting serials/dates (crimson).
- **Appliance Object Vision:** YOLOv8 appliance localization with bounding boxes and semantic VLM fallback.
- **Passport Vault:** Searchable, persistent local registry with conflict filters and JSON export.

### Directory Structure

```
c:\Users\acer\Documents\Hackathon_idea-main\
├── .gitignore                      # Git ignore rules
├── CLAUDE.md                       # Technical & architecture reference (this file)
├── README.md                       # Setup & quickstart guide
├── requirements.txt                # Unified dependency list
├── run.py                          # Master launcher (Web UI / API / CLI)
│
├── app/                            # Master Application Package
│   ├── __init__.py
│   ├── config.py                   # Centralized settings & paths
│   ├── main.py                     # FastAPI application (REST API + Web UI)
│   │
│   ├── core/                       # Headless Core AI & Domain Engines
│   │   ├── __init__.py
│   │   ├── normalizers.py          # Pure sanitizers for dates, prices, models, serials
│   │   ├── identity_matcher.py     # Deterministic matching & Conflict Radar
│   │   ├── passport_store.py       # Thread-safe JSON passport database
│   │   ├── ocr_engine.py           # Multi-variant OCR & Tesseract auto-discovery
│   │   ├── dpp_extractor.py        # Checkbox reasoning, VLM extractor & fallback
│   │   └── product_detector.py     # YOLO appliance localization & semantic fallback
│   │
│   ├── api/                        # REST API Router Endpoints
│   │   ├── __init__.py
│   │   ├── routes_dpp.py           # Document extraction & passport CRUD
│   │   ├── routes_matcher.py       # Identity comparison & conflict radar
│   │   ├── routes_detector.py      # Physical appliance photo detection
│   │   └── routes_samples.py       # Sample test asset loader
│   │
│   ├── static/                     # Web Dashboard Assets
│   │   ├── css/
│   │   │   └── dashboard.css       # Luxury Navy & Gold Theme, Glassmorphism
│   │   ├── js/
│   │   │   └── dashboard.js        # Interactive client (drag-drop, diff visualizer, tabs)
│   │   └── images/
│   │       └── icon.png
│   │
│   └── templates/
│       └── index.html              # Responsive Web UI Dashboard
│
├── samples/                        # Curated Test Datasets
│   ├── warranty_cards/             # sample_warranty_1.png, sample_warranty_2.png...
│   ├── invoices_receipts/          # sample_invoice_1.png, sample_receipt_2.webp...
│   └── appliance_photos/           # washing_machine.jpg, microwave.jpg...
│
├── models/                         # AI Neural Network Weights
│   └── yolo26n.pt                  # Ultralytics YOLOv8 weights (5.5 MB)
│
├── data/                           # Local JSON Persistence
│   ├── passports.json              # Digital Product Passport store
│   └── ocr_evidence/               # Cached OCR JSON outputs
│
└── tests/                          # Comprehensive Automated Test Suite
    ├── __init__.py
    ├── test_normalizers.py         # Normalizers unit tests
    ├── test_identity_matcher.py    # Identity matcher unit tests
    ├── test_passport_store.py      # Passport store unit tests
    └── test_api.py                 # FastAPI endpoint integration tests
```

---

## 2. API Endpoints Reference

Start server: `python run.py` → `http://localhost:8000` (Swagger UI at `/docs`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web Dashboard Single Page Application |
| `GET` | `/api/health` | Diagnostic health check (Ollama, OCR, YOLO, Store) |
| `POST` | `/api/dpp/extract` | Upload document or sample path → OCR + VLM extraction → passport |
| `GET` | `/api/dpp/passports` | Search & filter passports (`?q=`, `?brand=`, `?status=`) |
| `GET` | `/api/dpp/passports/{id}` | Get single passport by ID |
| `POST` | `/api/dpp/passports` | Manually insert passport with identity verification |
| `DELETE` | `/api/dpp/passports/{id}` | Delete passport by ID |
| `GET` | `/api/dpp/conflicts` | List only passports with flagged identity conflicts |
| `GET` | `/api/dpp/stats` | Registry summary counts |
| `POST` | `/api/matcher/compare` | Side-by-side comparison matrix between two documents |
| `POST` | `/api/matcher/match` | Match candidate document against database |
| `POST` | `/api/detector/detect` | Upload appliance photo → YOLO bounding boxes & classes |
| `GET` | `/api/samples` | List all curated sample assets for 1-click testing |

---

## 3. Development & Testing Workflows

### Run the Application (Web Dashboard + API)
```powershell
python run.py
```

### Run Interactive Terminal CLI
```powershell
python run.py --cli
```

### Run Automated Tests
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### Ollama Multimodal Setup (Optional)
```powershell
ollama pull qwen2.5vl:7b
ollama serve
```
