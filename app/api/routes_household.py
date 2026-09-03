"""
HomeMind — Household Intelligence API Routes
Provides endpoints for household health, attention center, room inventory,
event timeline, warranty claim pack generation, compatibility scanner, and technician service mode.
"""

import os
import io
import csv
import json
import base64
import tempfile
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Response
from pydantic import BaseModel

import qrcode

from app.config import DATA_DIR
from app.core.passport_store import get_passport_store
from app.core.household_engine import (
    compute_product_health,
    get_household_attention,
    get_room_inventory,
    get_household_timeline,
    generate_warranty_claim_pack,
    get_household_summary
)
from app.core.compatibility_engine import evaluate_compatibility

router = APIRouter(prefix="/api/household", tags=["Household Intelligence"])
store = get_passport_store()


def _generate_qr_data_url(data_str: str) -> str:
    """Generate base64 PNG data URL for a given string using qrcode."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=7,
        border=2,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


@router.get("/health")
async def household_health():
    """
    Household Health Dashboard — aggregate health stats, attention items, room distribution.
    This is the primary endpoint for the HomeMind home screen.
    """
    products = store.get_all()
    summary = get_household_summary(products)
    return summary


@router.get("/attention")
async def household_attention():
    """
    Products needing attention, sorted by urgency (most critical first).
    Returns detailed health info and actionable alerts for each product.
    """
    products = store.get_all()
    attention = get_household_attention(products)
    return {
        "count": len(attention),
        "items": [
            {
                "passport_id": item["product_health"]["passport_id"],
                "product": item["product_health"]["product"],
                "brand": item["product_health"]["brand"],
                "model": item["product_health"]["model"],
                "room": item["product_health"]["room"],
                "health_status": item["product_health"]["health_status"],
                "alerts": item["product_health"]["alerts"],
                "days_until_expiry": item["product_health"]["days_until_expiry"],
                "days_until_maintenance": item["product_health"]["days_until_maintenance"]
            }
            for item in attention
        ]
    }


@router.get("/rooms")
async def household_rooms():
    """
    Products grouped by room with per-product health summary.
    """
    products = store.get_all()
    rooms = get_room_inventory(products)
    return {
        "room_count": len(rooms),
        "rooms": rooms
    }


@router.get("/timeline")
async def household_timeline(
    days: int = Query(90, description="Number of days ahead to look for events")
):
    """
    Timeline of upcoming household events — warranty expiry, maintenance, services.
    """
    products = store.get_all()
    timeline = get_household_timeline(products, days_ahead=days)
    return {
        "event_count": len(timeline),
        "timeline": timeline
    }


@router.get("/product/{passport_id}/health")
async def product_health(passport_id: str):
    """
    Detailed health report for a single product.
    """
    product = store.get_by_id(passport_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    health = compute_product_health(product)
    return health


@router.post("/claim-pack/{passport_id}")
async def warranty_claim_pack(passport_id: str):
    """
    Generate a Warranty Claim Pack — all product data, documents, and service history
    bundled for warranty claim or service request.
    """
    product = store.get_by_id(passport_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    pack = generate_warranty_claim_pack(product)
    return pack


@router.get("/service-pass/{passport_id}")
async def get_service_pass(passport_id: str):
    """
    Generate a Technician Service Pass with full appliance history and scannable QR code.
    Technician can scan the QR code to load the maintenance profile on their device.
    """
    product = store.get_by_id(passport_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    health = compute_product_health(product)

    # Compact JSON payload for QR code
    qr_payload = {
        "type": "HomeMind_Service_Pass",
        "passport_id": product.get("passport_id"),
        "product": f"{product.get('brand')} {product.get('product')}",
        "model": product.get("model"),
        "serial": product.get("serial_number"),
        "warranty": product.get("warranty"),
        "warranty_expiry": product.get("warranty_expiry_date"),
        "health": health.get("health_status"),
        "services_count": len(product.get("events", []))
    }

    qr_data_url = _generate_qr_data_url(json.dumps(qr_payload))

    briefing = {
        "passport_id": product.get("passport_id"),
        "product": product.get("product"),
        "brand": product.get("brand"),
        "model": product.get("model"),
        "serial_number": product.get("serial_number"),
        "room": product.get("room", "Unassigned"),
        "purchase_date": product.get("purchase_date"),
        "seller": product.get("seller"),
        "invoice_number": product.get("invoice_number"),
        "warranty": product.get("warranty"),
        "warranty_expiry_date": product.get("warranty_expiry_date"),
        "health_status": health.get("health_status"),
        "alerts": health.get("alerts", []),
        "service_history": product.get("events", []),
        "linked_documents": product.get("linked_documents", []),
        "qr_image_data_url": qr_data_url
    }

    return briefing


@router.post("/compatibility/scan")
async def scan_compatibility(
    file: Optional[UploadFile] = File(None),
    part_text: Optional[str] = Form("")
):
    """
    Scan a replacement part, consumable, remote, or filter.
    Evaluates against all registered household appliances and returns confidence & recommendation.
    """
    tmp_path = None
    try:
        if file and file.filename:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=str(DATA_DIR)) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

        products = store.get_all()
        verdict = evaluate_compatibility(
            scanned_text=part_text or "",
            products=products,
            image_path=tmp_path
        )
        return verdict

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.get("/export/csv")
async def export_household_csv():
    """
    Export complete Household Asset & Insurance Schedule as a standard CSV spreadsheet
    compatible with Microsoft Excel, Google Sheets, and Office Suites.
    """
    products = store.get_all()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Passport ID",
        "Product Name",
        "Brand",
        "Model",
        "Serial Number",
        "Room Location",
        "Purchase Date",
        "Purchase Price",
        "Currency",
        "Seller / Merchant",
        "Invoice Number",
        "Warranty Term",
        "Warranty Expiry Date",
        "Health Status",
        "Linked Documents Count",
        "Service Records Count"
    ])

    for p in products:
        writer.writerow([
            p.get("passport_id", ""),
            p.get("product", ""),
            p.get("brand", ""),
            p.get("model", ""),
            p.get("serial_number", ""),
            p.get("room", "Unassigned"),
            p.get("purchase_date", ""),
            p.get("purchase_price", ""),
            p.get("currency", "INR"),
            p.get("seller", ""),
            p.get("invoice_number", ""),
            p.get("warranty", ""),
            p.get("warranty_expiry_date", ""),
            p.get("health_status", "good"),
            len(p.get("linked_documents", [])),
            len(p.get("events", []))
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=HomeMind_Household_Asset_Schedule.csv"}
    )


@router.get("/export/insurance")
async def get_insurance_schedule():
    """
    Generate complete Household Insurance Asset Schedule summary
    for home insurance policy riders, claims, and valuation audits.
    """
    products = store.get_all()
    total_val = sum(p.get("purchase_price", 0) for p in products if isinstance(p.get("purchase_price"), (int, float)))

    by_room = {}
    items = []
    for p in products:
        room = p.get("room") or "Unassigned"
        price = p.get("purchase_price") or 0.0
        by_room[room] = by_room.get(room, 0.0) + (price if isinstance(price, (int, float)) else 0.0)

        items.append({
            "passport_id": p.get("passport_id"),
            "product": f"{p.get('brand', '')} {p.get('product', '')}".strip(),
            "model": p.get("model"),
            "serial": p.get("serial_number"),
            "room": room,
            "purchase_date": p.get("purchase_date"),
            "purchase_price": price,
            "currency": p.get("currency", "INR"),
            "warranty_expiry": p.get("warranty_expiry_date"),
            "health_status": p.get("health_status", "good"),
            "has_invoice": bool(p.get("invoice_number") or any(d.get("type") == "invoice" for d in p.get("linked_documents", [])))
        })

    return {
        "report_title": "HomeMind Household Insurance Asset Schedule",
        "generated_at": datetime.now().isoformat(),
        "total_asset_count": len(products),
        "total_declared_value": round(total_val, 2),
        "currency": "INR",
        "room_valuations": {r: round(v, 2) for r, v in by_room.items()},
        "schedule_items": items
    }

