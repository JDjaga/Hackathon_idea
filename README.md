# Textemage - Digital Product Passport (DPP) & Vision AI Engine

An intelligent document and appliance understanding system that automatically extracts, validates, and generates **Digital Product Passports** from paper warranty cards, invoices, receipts, and product labels using Vision-Language Models (VLM) and YOLO object detection.

---

## 🌟 Key Features

- **Document Understanding & Checkbox Reasoning:** Analyzes multi-product warranty cards, receipts, and invoices. Confirms actual purchase intent by recognizing checked/selected boxes (e.g. `[✓] Washing Machine`).
- **Multi-Product Passport Generation:** Generates individual, isolated Digital Product Passports for each verified product on a single document without hallucinating or cross-contaminating metadata.
- **Hybrid Appliance Detection:** Combines **YOLO (yolo26n.pt)** object localization with **Qwen2.5-VL** semantic fallback for recognizing home appliances and consumer electronics.
- **Multi-Stage OCR Preprocessing:** Generates image enhancement variants (grayscale, contrast boost, unsharp mask, adaptive binarization) with Tesseract/PaddleOCR supporting evidence.
- **Certificate-Style Passport UI:** Interactive desktop viewer featuring a dark navy and gold theme, security seals, barcode visuals, warranty status badges, and metadata details.
- **Persistent Passport Store:** Local JSON document store supporting ID generation, image attachments, and detection linkage.

---

## 🏗️ Architecture & Pipeline

```
┌────────────────────────────────┐
│  Input Document / Photo Image  │
└───────────────┬────────────────┘
                │
     ┌──────────┴──────────┐
     ▼                     ▼
┌──────────────┐    ┌──────────────┐
│  OCR Engine  │    │ YOLO + Qwen  │
│ Preprocess & │    │  Appliance   │
│  Tesseract   │    │  Detection   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
     ┌───────────────────────┐
     │   Ollama Qwen2.5-VL   │
     │  Document Reasoning   │
     └───────────┬───────────┘
                 ▼
     ┌───────────────────────┐
     │ Passport Normalization│
     └───────────┬───────────┘
                 ▼
     ┌───────────────────────┐
     │  Passport UI & Store  │
     └───────────────────────┘
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Ollama**: Download and install from [ollama.com](https://ollama.com)
- **Tesseract OCR** (Optional for auxiliary OCR): [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Pull the Ollama Vision Model
```bash
ollama pull qwen2.5vl:7b
ollama serve
```

---

## 💻 Usage

### Quick Launch Menu
```bash
python main.py
```

### Direct Script Execution
1. **Extract Passport from Document Image:**
   ```bash
   python Textemage.py
   ```
2. **Detect Appliances in Physical Photo:**
   ```bash
   python Hackathon_idea-main/product_detector.py
   ```
3. **Open Passport Viewer UI:**
   ```bash
   python Hackathon_idea-main/product_passport.py
   ```
4. **Test OCR Preprocessor:**
   ```bash
   python Hackathon_idea-main/test_ocr.py
   ```

---

## 📁 Project Structure

```
├── main.py                  # Unified CLI launcher
├── Textemage.py             # Root launcher / main DPP pipeline
├── requirements.txt         # Core dependencies
└── Hackathon_idea-main/
    ├── Textemage.py         # Document extraction & UI coordinator
    ├── product_passport.py  # Tkinter/CustomTkinter Passport Viewer GUI
    ├── product_detector.py  # YOLO + Qwen appliance detector
    ├── ocr_engine.py        # Multi-stage image preprocessor & OCR
    ├── extract_product.py   # Multi-product extraction engine
    ├── passport_store.py    # Local JSON document database
    ├── test_ocr.py          # OCR diagnostics script
    ├── yolo26n.pt           # YOLO neural network weights
    └── tesseract_path.txt   # Custom Tesseract binary path configuration
```
