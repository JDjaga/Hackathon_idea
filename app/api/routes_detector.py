"""
AI Product Guardian — Appliance Object Detection API Routes
Runs YOLOv8 appliance localization and bounding box generation.
"""

import os
import tempfile
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.config import DATA_DIR
from app.core.product_detector import detect_appliances
from app.core.passport_store import PassportStore

router = APIRouter(prefix="/api/detector", tags=["Appliance Detection"])
store = PassportStore()


class LinkDetectionRequest(BaseModel):
    passport_id: str
    image_path: str
    detection_info: Dict[str, Any]


@router.post("/detect")
async def detect_appliance_in_image(
    file: Optional[UploadFile] = File(None),
    sample_path: Optional[str] = Form(None),
    annotate: bool = Form(True)
):
    """
    Detect physical appliances in a photograph using YOLOv8 with semantic fallback.
    Returns detected appliance classes, confidence scores, and bounding box coordinates.
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

        result = detect_appliances(target_image, annotate=annotate)
        return {
            "status": "success",
            "count": result.get("count", 0),
            "detections": result.get("detections", []),
            "annotated_image_base64": result.get("annotated_image_base64")
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
    """Link an appliance photograph and detection to an existing Digital Product Passport."""
    updated = store.attach_product_image(req.passport_id, req.image_path, req.detection_info)
    if not updated:
        raise HTTPException(status_code=404, detail="Passport not found")
    return {"status": "success", "passport": updated}
