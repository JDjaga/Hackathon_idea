# CLAUDE.md — AI Product Guardian (Textemage DPP Engine)

Developer and agent reference for the **AI Product Guardian** codebase — a Digital Product Passport (DPP) and Product Identity Verification system.

---

## 0. Non-Negotiables

1. **Product Identity Matching + Mismatch Detection** is the hero feature. If it doesn't work, nothing else matters.
2. **Deterministic matching only.** Identity matching uses Levenshtein, substring containment, and normalization — never an LLM.
3. **Schema parity.** Both Track A (future mobile) and Track B (Python backend) write into the same passport JSON schema.
4. **Graceful degradation.** OCR, YOLO, and Ollama are designed to fail gracefully. The pipeline continues if any one component is unavailable.

---

## 1. Project Overview

**AI Product Guardian** is an AI-powered document intelligence and computer vision platform that:

- Generates standardized **Digital Product Passports (DPP)** from warranty cards, invoices, receipts, and product labels
- Detects physical appliances from photographs using YOLO + Qwen2.5-VL
- **Verifies product identity** across multiple scans and flags mismatches (e.g., serial number conflicts between warranty card and invoice for the "same" product)

---

## 2. Two-Track Architecture

| Track | Purpose | Status |
|---|---|---|
| **Track A — Mobile App** | Flutter app + ML Kit (scanning/OCR) + on-device matching | Future build |
| **Track B — Python Backend** | FastAPI wrapper around existing pipeline; serves as LAN API and batch processor | **Active — implemented** |

Both tracks read and write the same passport JSON schema. Track B is the working backend, exposed at `http://<laptop-ip>:8000`.

---

## 3. Project File Structure

```
Hackathon_idea-main/
├── .gitignore
├── CLAUDE.md                        ← This file
├── README.md                        ← User documentation
├── requirements.txt                 ← Root dependency list
├── main.py                          ← Interactive CLI launcher
├── Textemage.py                     ← Root delegate launcher
│
├── backend/                         ← Track B: Active backend
│   ├── config.py                    ← Centralized configuration (single source of truth)
│   ├── api.py                       ← FastAPI REST API server
│   ├── identity_matcher.py          ← Hero feature: deterministic identity matching
│   ├── passport_store.py            ← JSON passport store with auto-matching
│   ├── Textemage.py                 ← Primary pipeline: Image → OCR → VLM → Passport
│   ├── product_detector.py          ← YOLO + Qwen appliance detector
│   ├── ocr_engine.py                ← Image preprocessing + OCR evidence builder
│   ├── extract_product.py           ← Multi-product extractor + normalizers
│   ├── product_passport.py          ← Tkinter certificate-style viewer (debug only)
│   ├── requirements.txt             ← Backend-specific dependencies
│   ├── yolo26n.pt                   ← YOLO model weights
│   ├── tesseract_path.txt           ← Tesseract binary path
│   ├── ocr_output/                  ← Generated OCR evidence
│   └── test_data/
│       └── test_identity_matcher.py ← Integration test suite
│
├── Hackathon_idea-main/             ← Legacy source (reference copy)
│   └── (original Python files)
│
└── shared/                          ← Shared contracts (future schema files)
```

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| **Language** | Python 3.10+ |
| **Vision-Language Model** | Ollama `qwen2.5vl:7b` (local, `http://127.0.0.1:11434`) |
| **Object Detection** | Ultralytics YOLO (`yolo26n.pt`), OpenCV |
| **OCR** | Tesseract OCR (`pytesseract`) |
| **API Server** | FastAPI + Uvicorn |
| **Image Processing** | Pillow, NumPy |
| **Identity Matching** | Pure Python — Levenshtein distance, normalization, substring containment |
| **Data** | Local JSON store, Pydantic models |

---

## 5. Digital Product Passport Schema

```json
{
  "passport_id": "PP-20260902140000-1",
  "document_type": "warranty_card",
  "product": "Washing Machine",
  "brand": "LG",
  "model": "T75-SKSF1Z",
  "serial_number": "LG123456789",
  "purchase_price": 28500.0,
  "currency": "INR",
  "purchase_date": "2026-08-12",
  "warranty": "2-YEAR",
  "seller": "Best Electrical Store",
  "category": "Large Domestic Appliances",
  "customer_name": "John Doe",
  "order_id": null,
  "invoice_number": "INV-2026-001",
  "source": "backend_bridge",
  "product_images": [],
  "linked_products": [],
  "created_at": "2026-09-02T14:00:00.000000",
  "identity_match": {
    "status": "verified",
    "matched_passport_id": "PP-20260901103000-1",
    "match_confidence": "high",
    "matched_fields": ["model", "serial_number", "brand", "seller", "purchase_date"],
    "conflicting_fields": []
  }
}
```

### `identity_match.status` values:
- `"new_product"` — No existing passport matches. First scan of this product.
- `"verified"` — Matched an existing passport, all overlapping identity fields agree.
- `"conflict"` — Matched an existing passport, but at least one identity field disagrees (e.g., mismatched serial number).

---

## 6. Identity Matching Rules

The matching engine in [`identity_matcher.py`](backend/identity_matcher.py) is **deterministic** (no LLM):

| Field | Normalization | Match Strategy |
|---|---|---|
| `model` | Strip whitespace, uppercase, remove hyphens/dots | Exact match after normalization |
| `serial_number` | Strip whitespace, uppercase | Levenshtein distance ≤ 2 (handles OCR misreads 0/O, 1/I) |
| `brand` | Lowercase | Exact match after normalization |
| `seller` | Lowercase, strip business suffixes (Sdn Bhd, Pvt Ltd, etc.) | Substring containment |
| `purchase_date` | Parse to YYYY-MM-DD from any common format | Exact match after normalization |

**Minimum 2 fields must match** to consider two passports as referring to the same product. If any matched field has conflicting values, status = `"conflict"`.

---

## 7. API Endpoints (Track B)

Start: `cd backend && python api.py` → runs at `http://0.0.0.0:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server status + passport count |
| `GET` | `/passports` | List all passports |
| `GET` | `/passports/stats` | Summary: total, verified, conflicts, new |
| `GET` | `/passports/conflicts` | List only passports with identity conflicts |
| `GET` | `/passports/{id}` | Get single passport by ID |
| `POST` | `/passports` | Add passport (auto-runs identity matching) |
| `DELETE` | `/passports/{id}` | Delete a passport |
| `POST` | `/match` | Check a passport against store (without inserting) |
| `POST` | `/extract` | Upload image → OCR + VLM → passport(s) |
| `POST` | `/detect-appliance` | Upload image → YOLO + Qwen detection |

---

## 8. Execution Flows

### Flow 1: Document → Digital Product Passport

```
Image → inspect_image() → run_optional_tesseract() → save_ocr_evidence()
  → base64 encode → build VLM prompt + OCR context
  → Ollama qwen2.5vl:7b → extract JSON → normalize_model_output()
  → validate & deduplicate → PassportStore.add_passport()
  → identity_matcher.match_passport() → store with identity_match
```

### Flow 2: Appliance Photo → Detection

```
Image → OpenCV read → YOLO yolo26n.pt (conf=0.10, iou=0.45, imgsz=1280)
  → filter appliance classes → remove duplicates by IoU/center-distance
  → (if no YOLO hit) → Qwen2.5-VL semantic fallback
  → save annotated image → return detection list
```

### Flow 3: Identity Verification (Hero Feature)

```
New passport extracted → identity_matcher.match_passport(new, existing_store)
  → normalize all identity fields
  → compare each field (model, serial, brand, seller, date)
  → score: count matched fields
  → if score < 2: "new_product"
  → if score >= 2 and no conflicts: "verified"
  → if score >= 2 and any conflict: "conflict"
  → result embedded as passport.identity_match
```

---

## 9. Development Workflows

### Quick Start
```powershell
# Install dependencies
cd backend
python -m pip install -r requirements.txt

# Pull Ollama vision model
ollama pull qwen2.5vl:7b
ollama serve

# Start the API server
python api.py
# → http://0.0.0.0:8000/docs (Swagger UI)
```

### Run Tests
```powershell
cd backend

# Identity matcher unit test
python identity_matcher.py

# Integration test (store + matching)
python test_data/test_identity_matcher.py
```

### CLI Launcher (Legacy)
```powershell
# From project root
python main.py
```

---

## 10. Configuration

All configuration lives in [`backend/config.py`](backend/config.py):

| Setting | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server (env: `OLLAMA_HOST`) |
| `VISION_MODEL` | `qwen2.5vl:7b` | Vision-language model for extraction |
| `YOLO_MODEL_PATH` | `backend/yolo26n.pt` | YOLO weights |
| `YOLO_CONFIDENCE` | `0.10` | Detection confidence threshold |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `SERIAL_MATCH_THRESHOLD` | `2` | Levenshtein distance for serial fuzzy match |
| `MIN_MATCH_FIELDS` | `2` | Minimum fields to consider a match |

---

## 11. Architectural Rules

1. **Deterministic matching only.** Identity matching uses edit-distance and normalization — never call an LLM for matching decisions.
2. **Path resolution.** Always resolve paths relative to `__file__` (`BASE_DIR = Path(__file__).resolve().parent`), never assume cwd.
3. **VLM zero-hallucination.** Prompts instruct the VLM to output `null` for unreadable fields — never fabricate serial numbers.
4. **Graceful degradation.** If Tesseract is missing, continue with VLM-only. If YOLO finds nothing, fall back to Qwen semantic classification.
5. **Checkbox discrimination.** Never convert an entire printed list into passports — only items with explicit checkmarks qualify.
6. **No cross-product leakage.** Multi-product documents produce isolated passports per item.
7. **Config centralization.** All model names, URLs, thresholds live in `config.py`. Nothing hardcoded elsewhere.
