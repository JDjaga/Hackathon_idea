"""
HomeMind — Appliance vision + Point-and-Ask matching.
"""

import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.core.product_detector import detect_appliances
from app.core.passport_store import get_passport_store
from app.core.household_match import match_label_to_products
from app.core.io_utils import resolve_sample_path, write_upload_bytes

router = APIRouter(prefix="/api/detector", tags=["Appliance Detection"])
store = get_passport_store()


class LinkDetectionRequest(BaseModel):
    passport_id: str
    image_path: str
    detection_info: Dict[str, Any]


def _attach_household_matches(detections):
    products = store.get_all()
    enriched = []
    for det in detections:
        item = dict(det)
        matched = match_label_to_products(item.get("label") or "", products)
        item["matched_product"] = matched
        if matched:
            item["point_and_ask"] = [
                f"When does my {matched.get('product')} warranty expire?",
                f"When was my {matched.get('product')} last serviced?",
                f"How old is my {matched.get('product')}?",
            ]
        else:
            item["point_and_ask"] = []
        enriched.append(item)
    return enriched


@router.post("/detect")
async def detect_appliance_in_image(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None),
    annotate: bool = Form(True)
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

        result = detect_appliances(target_image, annotate=annotate)
        detections = _attach_household_matches(result.get("detections", []))
        return {
            "status": "success",
            "count": len(detections),
            "detections": detections,
            "annotated_image_base64": result.get("annotated_image_base64"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Appliance detection error: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.post("/link")
async def link_appliance_to_passport(req: LinkDetectionRequest):
    updated = store.attach_product_image(req.passport_id, req.image_path, req.detection_info)
    if not updated:
        raise HTTPException(status_code=404, detail="Passport not found")
    return {"status": "success", "passport": updated}
