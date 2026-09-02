"""
HomeMind — Household Intelligence Engine
Computes product health, household attention items, warranty claim packs,
room-grouped inventories, and event timelines.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.core.normalizers import compute_health_status


def compute_product_health(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute detailed health information for a single product entity.
    Returns health status, days until expiry, days until maintenance, and actionable alerts.
    """
    today = datetime.now()
    alerts = []

    warranty_expiry = product.get("warranty_expiry_date")
    next_maintenance = product.get("next_maintenance_date")
    health = product.get("health_status", "good")

    days_until_expiry = None
    days_until_maintenance = None

    if warranty_expiry:
        try:
            expiry_dt = datetime.strptime(warranty_expiry, "%Y-%m-%d")
            days_until_expiry = (expiry_dt - today).days
            if days_until_expiry < 0:
                alerts.append({
                    "severity": "expired",
                    "icon": "🔴",
                    "message": f"Warranty expired {abs(days_until_expiry)} days ago",
                    "action": "Consider extended warranty or replacement plan"
                })
            elif days_until_expiry <= 30:
                alerts.append({
                    "severity": "urgent",
                    "icon": "🔴",
                    "message": f"Warranty expires in {days_until_expiry} days",
                    "action": "Review warranty terms and file any pending claims"
                })
            elif days_until_expiry <= 90:
                alerts.append({
                    "severity": "attention",
                    "icon": "🟠",
                    "message": f"Warranty expires in {days_until_expiry} days",
                    "action": "Schedule preventive inspection before warranty ends"
                })
        except (ValueError, TypeError):
            pass

    if next_maintenance:
        try:
            maint_dt = datetime.strptime(next_maintenance, "%Y-%m-%d")
            days_until_maintenance = (maint_dt - today).days
            if days_until_maintenance <= 0:
                alerts.append({
                    "severity": "urgent",
                    "icon": "🔧",
                    "message": f"Maintenance is overdue by {abs(days_until_maintenance)} days",
                    "action": "Schedule service appointment immediately"
                })
            elif days_until_maintenance <= 14:
                alerts.append({
                    "severity": "attention",
                    "icon": "🔧",
                    "message": f"Maintenance due in {days_until_maintenance} days",
                    "action": "Plan routine maintenance visit"
                })
        except (ValueError, TypeError):
            pass

    return {
        "passport_id": product.get("passport_id"),
        "product": product.get("product"),
        "brand": product.get("brand"),
        "model": product.get("model"),
        "room": product.get("room", "Unassigned"),
        "health_status": health,
        "days_until_expiry": days_until_expiry,
        "days_until_maintenance": days_until_maintenance,
        "warranty_expiry_date": warranty_expiry,
        "next_maintenance_date": next_maintenance,
        "alerts": alerts,
        "alert_count": len(alerts)
    }


def get_household_attention(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute attention items across all household products.
    Returns sorted list (most urgent first) of products needing action.
    """
    attention_items = []
    severity_order = {"expired": 0, "urgent": 1, "attention": 2}

    for product in products:
        health = compute_product_health(product)
        if health["alerts"]:
            # Use the most severe alert for sorting
            worst_severity = min(
                severity_order.get(a["severity"], 99) for a in health["alerts"]
            )
            attention_items.append({
                "product_health": health,
                "sort_key": worst_severity,
                "worst_alert": health["alerts"][0]
            })

    attention_items.sort(key=lambda x: x["sort_key"])
    return attention_items


def get_room_inventory(products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group products by room with health summary per room.
    """
    rooms = {}
    for product in products:
        room = product.get("room") or "Unassigned"
        if room not in rooms:
            rooms[room] = []
        rooms[room].append({
            "passport_id": product.get("passport_id"),
            "product": product.get("product"),
            "brand": product.get("brand"),
            "model": product.get("model"),
            "health_status": product.get("health_status", "good"),
            "warranty_expiry_date": product.get("warranty_expiry_date"),
            "next_maintenance_date": product.get("next_maintenance_date")
        })
    return rooms


def get_household_timeline(products: List[Dict[str, Any]], days_ahead: int = 90) -> List[Dict[str, Any]]:
    """
    Build a timeline of upcoming household events (warranty expiry, maintenance, etc.).
    Returns events sorted by date.
    """
    today = datetime.now()
    cutoff = today + timedelta(days=days_ahead)
    timeline = []

    for product in products:
        product_label = f"{product.get('brand', '')} {product.get('product', '')}".strip()
        pid = product.get("passport_id")

        # Warranty expiry event
        expiry = product.get("warranty_expiry_date")
        if expiry:
            try:
                dt = datetime.strptime(expiry, "%Y-%m-%d")
                if today - timedelta(days=30) <= dt <= cutoff:
                    timeline.append({
                        "date": expiry,
                        "type": "warranty_expiry",
                        "icon": "🛡️",
                        "title": f"Warranty expires — {product_label}",
                        "product": product_label,
                        "passport_id": pid,
                        "days_from_now": (dt - today).days,
                        "severity": "urgent" if (dt - today).days <= 30 else "attention"
                    })
            except (ValueError, TypeError):
                pass

        # Next maintenance event
        maint = product.get("next_maintenance_date")
        if maint:
            try:
                dt = datetime.strptime(maint, "%Y-%m-%d")
                if today - timedelta(days=7) <= dt <= cutoff:
                    timeline.append({
                        "date": maint,
                        "type": "maintenance",
                        "icon": "🔧",
                        "title": f"Maintenance due — {product_label}",
                        "product": product_label,
                        "passport_id": pid,
                        "days_from_now": (dt - today).days,
                        "severity": "urgent" if (dt - today).days <= 0 else "attention"
                    })
            except (ValueError, TypeError):
                pass

        # Stored events from product history
        for event in product.get("events", []):
            event_date = event.get("date")
            if event_date:
                try:
                    dt = datetime.strptime(event_date, "%Y-%m-%d")
                    if today - timedelta(days=30) <= dt <= cutoff:
                        timeline.append({
                            "date": event_date,
                            "type": event.get("type", "event"),
                            "icon": _event_icon(event.get("type")),
                            "title": event.get("description", "Event"),
                            "product": product_label,
                            "passport_id": pid,
                            "days_from_now": (dt - today).days,
                            "severity": "info"
                        })
                except (ValueError, TypeError):
                    pass

    timeline.sort(key=lambda x: x["date"])
    return timeline


def generate_warranty_claim_pack(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a complete Warranty Claim Pack — all relevant product data,
    linked documents, and service history bundled for a claim or service request.
    """
    return {
        "claim_pack_type": "warranty_claim",
        "generated_at": datetime.now().isoformat(),
        "product": {
            "name": product.get("product"),
            "brand": product.get("brand"),
            "model": product.get("model"),
            "serial_number": product.get("serial_number"),
            "category": product.get("category"),
            "room": product.get("room")
        },
        "purchase": {
            "date": product.get("purchase_date"),
            "price": product.get("purchase_price"),
            "currency": product.get("currency"),
            "seller": product.get("seller"),
            "invoice_number": product.get("invoice_number"),
            "customer_name": product.get("customer_name")
        },
        "warranty": {
            "duration": product.get("warranty"),
            "expiry_date": product.get("warranty_expiry_date"),
            "status": "active" if product.get("health_status") != "expired" else "expired"
        },
        "service_history": [
            e for e in product.get("events", []) if e.get("type") in ("service", "installation", "consumable")
        ],
        "linked_documents": product.get("linked_documents", []),
        "passport_id": product.get("passport_id")
    }


def get_household_summary(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute comprehensive household summary with health distribution,
    room counts, and aggregate statistics.
    """
    health_counts = {"good": 0, "attention": 0, "urgent": 0, "expired": 0}
    room_counts = {}
    total_value = 0.0

    for p in products:
        status = p.get("health_status", "good")
        health_counts[status] = health_counts.get(status, 0) + 1

        room = p.get("room") or "Unassigned"
        room_counts[room] = room_counts.get(room, 0) + 1

        price = p.get("purchase_price")
        if isinstance(price, (int, float)):
            total_value += price

    attention_items = get_household_attention(products)

    return {
        "total_products": len(products),
        "health_distribution": health_counts,
        "needs_attention": health_counts.get("urgent", 0) + health_counts.get("expired", 0),
        "upcoming_issues": health_counts.get("attention", 0),
        "healthy": health_counts.get("good", 0),
        "rooms": room_counts,
        "room_count": len(room_counts),
        "total_household_value": round(total_value, 2),
        "attention_item_count": len(attention_items),
        "top_attention": [
            {
                "product": item["product_health"]["product"],
                "brand": item["product_health"]["brand"],
                "room": item["product_health"]["room"],
                "alert": item["worst_alert"]["message"],
                "icon": item["worst_alert"]["icon"],
                "passport_id": item["product_health"]["passport_id"]
            }
            for item in attention_items[:5]
        ]
    }


def _event_icon(event_type: Optional[str]) -> str:
    """Map event type to display icon."""
    icons = {
        "purchase": "🛒",
        "installation": "🔩",
        "service": "🔧",
        "consumable": "🧹",
        "warranty_expiry": "🛡️",
        "maintenance": "🔧",
    }
    return icons.get(event_type or "", "📅")
