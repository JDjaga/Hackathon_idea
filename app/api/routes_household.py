"""
HomeMind — Household Intelligence API Routes
Provides endpoints for household health, attention center, room inventory,
event timeline, and warranty claim pack generation.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.core.passport_store import get_passport_store
from app.core.household_engine import (
    compute_product_health,
    get_household_attention,
    get_room_inventory,
    get_household_timeline,
    generate_warranty_claim_pack,
    get_household_summary
)

router = APIRouter(prefix="/api/household", tags=["Household Intelligence"])
store = get_passport_store()


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
