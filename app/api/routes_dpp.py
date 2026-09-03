"""
HomeMind — Digital Product Passport API Routes
"""

import os
from typing import Optional, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.passport_store import get_passport_store
from app.core.dpp_extractor import extract_document_dpp, is_usable_passport, found_fields_checklist
from app.core.household_match import build_product_graph, find_similar_owned_products
from app.core.io_utils import resolve_sample_path, write_upload_bytes

router = APIRouter(prefix="/api/dpp", tags=["Digital Product Passports"])
store = get_passport_store()

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
    room: Optional[str] = None


@router.post("/extract")
async def extract_passport_from_document(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None),
    room: Optional[str] = Form(None),
):
    tmp_path = None
    try:
        if file and file.filename:
            content = await file.read()
            try:
                tmp_path = write_upload_bytes(content, file.filename)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            target_image = tmp_path
        elif sample_path:
            try:
                target_image = str(resolve_sample_path(sample_path))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except FileNotFoundError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail="Must provide an image file upload or valid sample_path.")

        extraction_result = extract_document_dpp(target_image)
        extracted_passports = extraction_result.get("passports", [])

        stored_results = []
        for p in extracted_passports:
            if not is_usable_passport(p):
                continue
            if room:
                p["room"] = room
            res = store.add_passport(p, source="document_extractor")
            passport = res.get("passport") or {}
            similar = find_similar_owned_products(
                passport,
                store.get_all(),
                exclude_id=passport.get("passport_id"),
            )
            res["product_graph"] = build_product_graph(passport)
            res["found_fields"] = found_fields_checklist(passport)
            res["duplicate_warning"] = (
                f"Similar item already registered: "
                + ", ".join(f"{s.get('brand')} {s.get('product')}" for s in similar[:3])
                if similar else None
            )
            res["message"] = res.get("message") or (
                f"I created a household product from this {extraction_result.get('document_type') or 'document'}."
                if res.get("action") == "created"
                else f"I linked this document to {passport.get('brand')} {passport.get('product')}."
            )
            stored_results.append(res)

        if not stored_results:
            return {
                "status": "incomplete",
                "extraction_source": extraction_result.get("extraction_source"),
                "document_type": extraction_result.get("document_type"),
                "ollama_online": extraction_result.get("ollama_online"),
                "ocr_available": extraction_result.get("ocr_available"),
                "passport_count": 0,
                "results": [],
                "raw_ocr_snippet": extraction_result.get("ocr_text", "")[:300],
                "extraction_confidence": extraction_result.get("extraction_confidence"),
                "found_fields": extraction_result.get("found_fields"),
                "message": "I could not create a household product from this scan. No product, model, or serial was readable. Try a closer photo or better lighting.",
            }

        return {
            "status": "success",
            "extraction_source": extraction_result.get("extraction_source"),
            "document_type": extraction_result.get("document_type"),
            "ollama_online": extraction_result.get("ollama_online"),
            "ocr_available": extraction_result.get("ocr_available"),
            "passport_count": len(stored_results),
            "results": stored_results,
            "raw_ocr_snippet": extraction_result.get("ocr_text", "")[:300],
            "extraction_confidence": extraction_result.get("extraction_confidence"),
            "message": stored_results[0].get("message"),
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
    results = store.search(query=q, brand=brand, model=model, status=status)
    return {
        "count": len(results),
        "passports": results
    }


@router.get("/passports/stats")
async def get_passport_stats():
    return store.stats()


@router.get("/passports/conflicts")
async def get_passport_conflicts():
    conflicts = store.get_conflicts()
    return {
        "count": len(conflicts),
        "conflicts": conflicts
    }


@router.get("/passports/{passport_id}")
async def get_single_passport(passport_id: str):
    passport = store.get_by_id(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    payload = dict(passport)
    payload["product_graph"] = build_product_graph(passport)
    return payload


@router.post("/passports")
async def create_passport(passport: PassportInputSchema):
    result = store.add_passport(passport.model_dump(exclude_none=True), source="manual_api")
    return result


@router.delete("/passports/{passport_id}")
async def delete_passport(passport_id: str):
    deleted = store.delete(passport_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Passport not found")
    return {"deleted": True, "passport_id": passport_id}
