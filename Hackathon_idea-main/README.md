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

1. **Extract Passport from Document Image:**
   ```bash
   python Textemage.py
   ```
2. **Detect Appliances in Physical Photo:**
   ```bash
   python product_detector.py
   ```
3. **Open Passport Viewer UI:**
   ```bash
   python product_passport.py
   ```
4. **Test OCR Preprocessor:**
   ```bash
   python test_ocr.py
   ```
