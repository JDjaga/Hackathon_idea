# 🏠 HomeMind — Household Intelligence System

> **"Your phone remembers everything you own."**  
> An on-device Household OS built for the **iQOO 15 (Snapdragon 8 Elite)** Smart Living hackathon track.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Ultralytics YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://github.com/ultralytics/ultralytics)
[![RapidOCR](https://img.shields.io/badge/RapidOCR-ONNX-purple.svg)](https://github.com/RapidAI/RapidOCR)
[![Tests Passing](https://img.shields.io/badge/tests-50%2F50%20passing-success.svg)](#-automated-testing)
[![PWA Ready](https://img.shields.io/badge/PWA-offline%20ready-brightgreen.svg)](#-progressive-web-app-pwa)

---

## 💡 The Core Problem & Product Vision

Every home owns 20+ appliances, electronics, and machines — each with its own invoice, warranty card, user manual, and service receipt scattered across paper drawers and email inboxes. When something breaks, leaks, or needs maintenance:
- You don't remember when the warranty expires.
- You don't know which replacement filter or remote is compatible.
- You can't find the invoice to file a warranty claim.
- When the service technician arrives, you can't prove previous repairs.

**HomeMind** solves this by turning your phone into an intelligent **Household OS**:
> **Don't make the user fill forms.** Scan invoices, warranty cards, manuals, or part packaging. HomeMind automatically builds a unified **Household Product Graph**, proactively tracks health and upcoming services, checks replacement part compatibility, and answers natural language questions grounded in your home's actual records.

---

## 🌟 6 Pillars of HomeMind

### 1. 🏠 Proactive Household Health Dashboard
- **Health Distribution**: Instant count of Urgent Action items (expired coverage, overdue service), Upcoming deadlines (next 90 days), and Healthy appliances.
- **Attention Action Center**: Ranked alert cards with 1-click **🛡️ Claim Pack** downloads, **⚡ Service Pass** access, and detailed certificate views.
- **Interactive Room Navigator**: Filter appliances across rooms (`Living Room`, `Bedroom`, `Kitchen`, `Utility`, `Garage`, `Office`).
- **90-Day Event Timeline**: Visual chronological stream of maintenance schedules and warranty expirations.

### 2. 💬 "Ask My House" Grounded RAG with Voice Input
- Natural language chat engine grounded in the user's actual household memory.
- **Hands-Free Voice Querying**: Native **Web Speech API (`webkitSpeechRecognition`)** integration. Tap the 🎤 mic button and speak directly to your home.
- **Grounded Evidence Badges**: Every answer cites the exact document source, field, and model serial number.
- **Smart Follow-Up Chips**: One-tap suggestion chips for instant context exploration.

### 3. 🔍 Consumables & Parts Compatibility Scanner
- Point your camera or paste a part description (e.g. `Philips NanoProtect HEPA Filter Series 3000 FY3430/30 for AC3059`).
- Evaluates against the **Household Product Graph**:
  - **Verified Compatible (>=70%)**: Confirms safe purchase with matched appliance, room location, and manufacturer recommendations.
  - **Cannot Verify (<40%)**: Warns user that no registered appliance in the household matches the consumable.
  - **Duplicate Purchase Warning**: Alerts the user if an identical appliance or part is already active.

### 4. ⚡ Technician Service Mode with Real Scannable QR Codes
- When a technician arrives, tap **"⚡ Service Pass"** on any appliance.
- Generates a **Technician Service Briefing** with:
  - Appliance specifications (Brand, Model, Serial, Room)
  - Active warranty coverage status and expiry date
  - Complete chronological service, maintenance, and installation records
  - **Live Scannable QR Code (PNG data URL)**: Technicians scan the QR code with their mobile device to instantly load the maintenance dossier.

### 5. 📷 Point-and-Ask Appliance Vision (YOLO + Household Memory)
- Snap a photo or upload an image of any appliance.
- Ultralytics YOLO localizes the appliance bounding box.
- Automatically matches the localized object to the registered household appliance.
- Injects a **Point-and-Ask Interactive Action Box**:
  - `💬 "When does warranty expire?"`
  - `💬 "When was it last serviced?"`
  - `⚡ "Service Pass (QR)"`

### 6. 📋 Office Kit & Insurance Asset Schedule Export
- **Office Kit / Spreadsheet Export**: `GET /api/household/export/csv` generates a formatted `.csv` schedule compatible with **Microsoft Excel, Google Sheets, and LibreOffice**.
- **Insurance Asset Valuation Ledger**: Computes total declared replacement value with room-by-room breakdown and proof-of-purchase verification.
- **Printable PDF Letterhead**: Dedicated `@media print` CSS cleanly formats insurance schedules and service passes for physical printing or PDF saving.

---

## 📱 Mobile-First Architecture (iQOO 15 / Snapdragon 8 Elite)

- **Live WebRTC Camera Viewfinder**: Direct access to the device's rear-facing camera (`getUserMedia`) with real-time framing box and snapshot canvas routing.
- **Progressive Web App (PWA)**: Standalone launcher manifest (`manifest.json`) and offline service worker (`service-worker.js`) for zero-latency local execution.
- **Mobile Bottom Navigation Bar**: Automatically adapts to phone viewports (`<= 768px`) with touch-optimized buttons for Health, Ask, Scan, Compat, and Items.
- **Offline Resilient**: Local ONNX neural inference (RapidOCR), local YOLO object detection, and thread-safe local JSON persistence.

---

## 🚀 Quick Start

### 1. Prerequisites & Installation
```powershell
python -m pip install -r requirements.txt
```

### 2. Start the HomeMind Web Server
```powershell
python run.py
```
- **Web Dashboard:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger REST API:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Interactive Terminal CLI Mode
```powershell
python run.py --cli
```

---

## 🧪 Automated Testing

HomeMind includes an automated test suite with **50 unit and integration tests**:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

```
..................................................
----------------------------------------------------------------------
Ran 50 tests in 4.491s

OK — (50/50 Tests Passed, 100% Success Rate)
```

| Test Module | Tests | Description |
|---|---|---|
| `tests/test_normalizers.py` | 5 | Date, currency, model, serial, and warranty duration parsing |
| `tests/test_identity_matcher.py` | 5 | Levenshtein serial distance, multi-attribute matching, Conflict Radar |
| `tests/test_passport_store.py` | 3 | Thread-safe CRUD, multi-attribute search, aggregate statistics |
| `tests/test_dpp_extractor.py` | 5 | Checkbox discrimination, prompt formatting, extraction resilience |
| `tests/test_household_engine.py` | 19 | Health metrics, attention sorting, rooms, timeline, claim packs, compatibility engine, service pass QR, document auto-linking, CSV/insurance export, PWA assets, demo reset |
| `tests/test_household_rag.py` | 6 | Intent routing, warranty lookup, room lookup, purchase history, `/api/ask` |
| `tests/test_api.py` | 7 | Diagnostics, home dashboard, passport lifecycle, matcher, sample loader |

---

## 📁 Repository Structure

```
c:\Users\acer\Documents\Hackathon_idea-main\
├── app/                            # Core Application Package
│   ├── config.py                   # Central settings, room presets, warranty maps
│   ├── main.py                     # FastAPI application & router mounts
│   ├── core/                       # Headless Core Domain & AI Engines
│   │   ├── normalizers.py          # Warranty duration & date calculation
│   │   ├── household_engine.py     # Health metrics, attention ranking, timeline
│   │   ├── household_rag.py        # Natural language keyword RAG & intent routing
│   │   ├── compatibility_engine.py # Consumables & replacement parts evaluator
│   │   ├── identity_matcher.py     # Deterministic Conflict Radar
│   │   ├── passport_store.py       # Thread-safe product graph & auto-linking
│   │   ├── ocr_engine.py           # RapidOCR ONNX primary & Tesseract fallback
│   │   ├── dpp_extractor.py        # Checkbox reasoning & VLM extractor
│   │   └── product_detector.py     # YOLO appliance localization
│   ├── api/                        # REST API Router Endpoints
│   │   ├── routes_household.py     # /health, /attention, /rooms, /timeline, /claim-pack, /service-pass, /compatibility, /export
│   │   ├── routes_ask.py           # /api/ask grounded RAG endpoint
│   │   ├── routes_dpp.py           # /api/dpp extraction & passport registry
│   │   ├── routes_matcher.py       # /api/matcher conflict radar
│   │   └── routes_detector.py      # /api/detector YOLO vision
│   ├── static/                     # Dashboard Assets
│   │   ├── css/dashboard.css       # Luxury Glassmorphic & Mobile Bottom Nav CSS
│   │   ├── js/dashboard.js         # Interactive UI, Speech API, WebRTC camera
│   │   ├── manifest.json           # PWA standalone manifest
│   │   └── service-worker.js       # Offline caching service worker
│   └── templates/
│       └── index.html              # Responsive Web UI Dashboard
├── data/                           # Local JSON Persistence (passports.json)
├── models/                         # YOLO weights (yolo26n.pt)
├── samples/                        # Test Assets (Warranties, Invoices, Appliance Photos)
├── tests/                          # 50 Automated Unit & API Integration Tests
├── requirements.txt                # Production Dependencies
└── run.py                          # Master Application Launcher
```

---

## 🏆 Hackathon Alignment (Smart Living / iQOO 15)

- **Phone-First Physicality**: Uses the phone's camera (`getUserMedia`), microphone (Web Speech API), and local AI compute rather than serving as a passive viewer.
- **Office Kit Rubric Compliance**: Native `.csv` spreadsheet export and certified insurance asset schedules.
- **Novelty & Utility**: Moves beyond a simple "warranty tracker" into an active **Household OS** that prevents incompatible consumable purchases and generates instant technician briefings.
- **Robust Offline Fallback**: Runs on local ONNX weights with zero cloud dependencies required for baseline operation.
