"""
AI Product Guardian — Identity Matcher & Conflict Radar API Routes
Provides endpoints for direct side-by-side document comparison and candidate matching against stored passports.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.identity_matcher import score_match, match_passport
from app.core.passport_store import get_passport_store

router = APIRouter(prefix="/api/matcher", tags=["Identity Matcher & Conflict Radar"])
store = get_passport_store()


class PassportComparisonRequest(BaseModel):
    document_a: Dict[str, Any] = Field(..., description="First document passport data")
    document_b: Dict[str, Any] = Field(..., description="Second document passport data to verify against")


class SingleMatchRequest(BaseModel):
    product: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    seller: Optional[str] = None


@router.post("/compare")
async def compare_two_documents(req: PassportComparisonRequest):
    """
    Directly compare two document passports (e.g. Warranty Card vs Tax Invoice)
    and produce a detailed field-by-field comparison with conflict detection.
    """
    result = score_match(req.document_b, req.document_a)
    has_conflicts = bool(result["conflicting_fields"])
    score = result["score"]

    if has_conflicts:
        status = "conflict"
    elif score >= 2:
        status = "verified"
    else:
        status = "inconclusive"

    return {
        "status": status,
        "score": score,
        "matched_fields": result["matched_fields"],
        "conflicting_fields": result["conflicting_fields"],
        "skipped_fields": result["skipped_fields"],
        "document_a": req.document_a,
        "document_b": req.document_b
    }


@router.post("/match")
async def match_against_store(req: SingleMatchRequest):
    """
    Match a candidate document's identity fields against the entire passport database
    without storing it. Returns the best match result and conflict analysis.
    """
    candidate = req.model_dump(exclude_none=True)
    result = match_passport(candidate, store.get_all())
    return result
