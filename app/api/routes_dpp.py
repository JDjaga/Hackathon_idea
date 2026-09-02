"""
AI Product Guardian — Digital Product Passport API Routes
Handles document extraction, passport persistence, search, stats, and conflict listing.
"""

import os
import tempfile
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import DATA_DIR
from app.core.passport_store import PassportStore
from app.core.dpp_extractor import extract_document_dpp

router = APIRouter(prefix="/api/dpp", tags=["Digital Product Passports"])
store = PassportStore()

# Ensure demo data is seeded if empty
store.seed_demo_passports()


class PassportInputSchema(BaseModel):
    document_type: Optional[str] = "warranty_card"
    product: Optional[str] = Field(None, example="Washing Machine")
    brand: Optional[str] = Field(None, example="LG")
    model: Optional[str] = Field(None, example="T75-SKSF1Z")
    serial_number: Optional[str] = Field(None, example="LG123456789")
    purchase_price: Optional[Any] = Field(None, example=28500.0)
    currency: Optional[str] = Field("INR", example="INR")
    purchase_date: Optional[str] = Field(None, example="2026-08-12")
    warranty: Optional[str] = Field("2-YEAR", example="2-YEAR")
    seller: Optional[str] = Field(None, example="Best Electrical Store")
    category: Optional[str] = Field(None, example="Large Domestic Appliances")
    customer_name: Optional[str] = Field(None, example="Rohan Sharma")
    order_id: Optional[str] = None
    invoice_number: Optional[str] = None
    selection_evidence: Optional[str] = None


@router.post("/extract")
async def extract_passport_from_document(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None)
):
    """
    Extract Digital Product Passport(s) from an uploaded document or sample image path.
    Runs OCR + VLM Checkbox Reasoning, normalizes data, and automatically links/verifies against database.
    """
    tmp_path = None
    try:
        if file and file.filename:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(DATA_DIR)) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            target_image = tmp_path
        elif sample_path and os.path.isfile(sample_path):
            target_image = sample_path
        else:
            raise HTTPException(status_code=400, detail="Must provide an image file upload or valid sample_path.")

        # Run extraction pipeline
        extraction_result = extract_document_dpp(target_image)
        extracted_passports = extraction_result.get("passports", [])

        # Store each extracted passport into the local database
        stored_results = []
        for p in extracted_passports:
            res = store.add_passport(p, source="document_extractor")
            stored_results.append(res)

        return {
            "status": "success",
            "extraction_source": extraction_result.get("extraction_source"),
            "ollama_online": extraction_result.get("ollama_online"),
            "ocr_available": extraction_result.get("ocr_available"),
            "passport_count": len(stored_results),
            "results": stored_results,
            "raw_ocr_snippet": extraction_result.get("ocr_text", "")[:300]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.get("/passports")
async def list_passports(
    q: Optional[str] = Query(None, description="Free text search"),
    brand: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="'verified', 'conflict', or 'new_product'")
):
    """Retrieve all passports with optional multi-attribute filtering."""
    results = store.search(query=q, brand=brand, model=model, status=status)
    return {
        "count": len(results),
        "passports": results
    }


@router.get("/passports/stats")
async def get_passport_stats():
    """Get registry statistics (totals, conflicts, verified, brand counts)."""
    return store.stats()


@router.get("/passports/conflicts")
async def get_passport_conflicts():
    """Retrieve all passports with flagged identity conflicts."""
    conflicts = store.get_conflicts()
    return {
        "count": len(conflicts),
        "conflicts": conflicts
    }


@router.get("/passports/{passport_id}")
async def get_single_passport(passport_id: str):
    """Get a single Digital Product Passport by ID."""
    passport = store.get_by_id(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    return passport


@router.post("/passports")
async def create_passport(passport: PassportInputSchema):
    """Manually add a Digital Product Passport to the store with identity verification."""
    result = store.add_passport(passport.model_dump(exclude_none=True), source="manual_api")
    return result


@router.delete("/passports/{passport_id}")
async def delete_passport(passport_id: str):
    """Delete a passport from the database."""
    deleted = store.delete(passport_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Passport not found")
    return {"deleted": True, "passport_id": passport_id}
