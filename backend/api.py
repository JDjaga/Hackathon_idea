"""
FastAPI Backend — AI Product Guardian
Track B: Legacy Pipeline API Wrapper

Exposes the existing Python pipeline over LAN so the Flutter mobile app
(Track A) can call it during Green Light windows via Office Kit.

Endpoints:
  GET  /health             — server status
  GET  /passports          — list all passports
  GET  /passports/{id}     — get single passport
  GET  /passports/conflicts — list passports with identity conflicts
  GET  /passports/stats    — passport store statistics
  POST /passports          — manually add a passport (with identity matching)
  POST /extract            — upload image → OCR + VLM extraction → passport
  POST /detect-appliance   — upload image → YOLO + Qwen detection
  POST /match              — check a passport against the store for matches

Start:
  uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import tempfile
import traceback
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from config import API_HOST, API_PORT, BASE_DIR
from passport_store import PassportStore
from identity_matcher import match_passport


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Product Guardian — Backend API",
    description="Track B: Legacy pipeline exposed over LAN for Green Light usage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store instance
store = PassportStore()


# ============================================================
# MODELS
# ============================================================

class PassportInput(BaseModel):
    document_type: Optional[str] = None
    product: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_price: Optional[Any] = None
    currency: Optional[str] = None
    purchase_date: Optional[str] = None
    warranty: Optional[str] = None
    seller: Optional[str] = None
    category: Optional[str] = None
    customer_name: Optional[str] = None
    order_id: Optional[str] = None
    invoice_number: Optional[str] = None
    source: Optional[str] = "backend_bridge"


class MatchRequest(BaseModel):
    product: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    seller: Optional[str] = None


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "AI Product Guardian Backend",
        "timestamp": datetime.now().isoformat(),
        "passport_count": len(store.get_all())
    }


# ============================================================
# PASSPORTS — LIST
# ============================================================

@app.get("/passports")
async def list_passports():
    return {
        "count": len(store.get_all()),
        "passports": store.get_all()
    }


# ============================================================
# PASSPORTS — STATS
# ============================================================

@app.get("/passports/stats")
async def passport_stats():
    return store.stats()


# ============================================================
# PASSPORTS — CONFLICTS
# ============================================================

@app.get("/passports/conflicts")
async def passport_conflicts():
    conflicts = store.get_conflicts()
    return {
        "count": len(conflicts),
        "conflicts": conflicts
    }


# ============================================================
# PASSPORTS — GET BY ID
# ============================================================

@app.get("/passports/{passport_id}")
async def get_passport(passport_id: str):
    passport = store.get_by_id(passport_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport not found")
    return passport


# ============================================================
# PASSPORTS — ADD (with identity matching)
# ============================================================

@app.post("/passports")
async def add_passport(passport: PassportInput):
    """
    Add a passport to the store. Automatically runs identity
    matching against all existing passports.
    """
    result = store.add_passport(
        passport.model_dump(exclude_none=False),
        source=passport.source or "backend_bridge"
    )
    return result


# ============================================================
# PASSPORTS — DELETE
# ============================================================

@app.delete("/passports/{passport_id}")
async def delete_passport(passport_id: str):
    deleted = store.delete(passport_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Passport not found")
    return {"deleted": True, "passport_id": passport_id}


# ============================================================
# MATCH — Check against store without inserting
# ============================================================

@app.post("/match")
async def match_against_store(req: MatchRequest):
    """
    Check a passport's identity fields against all stored passports
    WITHOUT inserting it. Returns the match result.
    """
    result = match_passport(
        new_passport=req.model_dump(exclude_none=True),
        existing_passports=store.get_all()
    )
    return result


# ============================================================
# EXTRACT — Image → OCR + VLM → Passport
# ============================================================

@app.post("/extract")
async def extract_from_image(file: UploadFile = File(...)):
    """
    Upload a document image (warranty card, invoice, receipt).
    Runs the full Textemage pipeline: OCR → VLM → normalization.
    Returns extracted passport(s) with identity matching.
    """
    try:
        # Save uploaded file to temp
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=str(BASE_DIR)
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Import here to avoid heavy load on startup
        from Textemage import (
            check_ollama, image_to_base64, inspect_image,
            run_optional_tesseract, analyze_image_with_vision,
            normalize_model_output, save_ocr_evidence
        )

        # Check Ollama
        if not check_ollama():
            raise HTTPException(
                status_code=503,
                detail="Ollama is not available. Start Ollama and pull the vision model."
            )

        # Run optional OCR
        ocr_text = run_optional_tesseract(tmp_path)
        save_ocr_evidence(tmp_path, ocr_text)

        # Run VLM extraction
        ai_result = analyze_image_with_vision(tmp_path, ocr_text)

        # Normalize
        passports = normalize_model_output(ai_result)

        if not passports:
            return {
                "status": "no_products_detected",
                "passports": [],
                "message": "No selected/purchased product was detected in the document."
            }

        # Store each passport with identity matching
        results = []
        for passport_data in passports:
            result = store.add_passport(passport_data, source="backend_bridge")
            results.append(result)

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ============================================================
# DETECT APPLIANCE — Image → YOLO + Qwen
# ============================================================

@app.post("/detect-appliance")
async def detect_appliance(file: UploadFile = File(...)):
    """
    Upload a photo of a physical appliance.
    Runs YOLO detection with Qwen VLM fallback.
    Returns detected products.
    """
    try:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=str(BASE_DIR)
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        from product_detector import detect_products

        detections = detect_products(tmp_path)

        return {
            "status": "success",
            "count": len(detections),
            "detections": detections
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print("  AI PRODUCT GUARDIAN — BACKEND API")
    print(f"  http://{API_HOST}:{API_PORT}")
    print("=" * 65)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
