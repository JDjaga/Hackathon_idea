"""
HomeMind — Household RAG Engine
Deterministic keyword & semantic query engine for household intelligence.
Parses natural language questions about appliances, warranties, expiries,
room locations, service history, and attention alerts, providing grounded answers with source evidence.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.household_engine import get_household_attention, compute_product_health


def answer_household_query(query: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute natural language RAG query over household products.
    Returns structured answer, source list, confidence, and suggested follow-up questions.
    """
    if not query or not query.strip():
        return {
            "answer": "Please ask a question about your household products, warranties, or maintenance schedules.",
            "sources": [],
            "confidence": "high",
            "intent": "empty",
            "suggestions": [
                "What needs my attention this month?",
                "When does my washing machine warranty expire?",
                "Which appliances are in the Living Room?"
            ]
        }

    q = query.strip().lower()

    # Intent 1: Specific product warranty lookup ("when does my washing machine warranty expire?")
    if any(k in q for k in ["warranty", "guarantee"]):
        return _handle_warranty_query(q, products)

    # Intent 2: Maintenance / Service history ("when was it last serviced", "maintenance")
    if any(k in q for k in ["service", "serviced", "maintenance", "repair", "clean"]):
        return _handle_maintenance_query(q, products)

    # Intent 3: Room location queries ("which products are in the living room", "what's in the kitchen")
    if any(k in q for k in ["room", "kitchen", "bedroom", "living", "utility", "garage", "office", "balcony"]):
        return _handle_room_query(q, products)

    # Intent 4: Purchase date / price queries ("when did I buy", "how old", "purchase")
    if any(k in q for k in ["bought", "purchased", "purchase", "price", "cost", "store", "seller", "invoice"]):
        return _handle_purchase_query(q, products)

    # Intent 5: Attention / Urgent / Expiry alerts ("what needs my attention", "urgent issues")
    if any(k in q for k in ["attention", "urgent", "overdue", "action", "need", "problem", "alert"]):
        return _handle_attention_query(q, products)

    # Intent 5: Purchase date / age queries ("when did I buy", "how old", "purchase")
    if any(k in q for k in ["bought", "purchased", "purchase", "age", "old", "cost", "price"]):
        return _handle_purchase_query(q, products)

    # Intent 6: Specific product general lookup
    matched_product = _find_matching_product(q, products)
    if matched_product:
        return _handle_single_product_overview(matched_product)

    # General Fallback
    return _handle_general_fallback(q, products)


def _handle_attention_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    attention_items = get_household_attention(products)

    if not attention_items:
        return {
            "answer": "🟢 **Great news!** All products in your household are currently in good health. No warranties are expiring soon, and no maintenance is overdue.",
            "sources": [{"title": "Household Health Engine", "confidence": "high"}],
            "confidence": "high",
            "intent": "attention",
            "suggestions": [
                "Show all registered products",
                "Which appliances are in the Bedroom?"
            ]
        }

    lines = [f"Found **{len(attention_items)} item(s)** requiring your attention in your household:\n"]
    sources = []

    for item in attention_items:
        ph = item["product_health"]
        alert = item["worst_alert"]
        p_label = f"**{ph['brand']} {ph['product']}** ({ph['room']})"
        lines.append(f"{alert['icon']} {p_label}: {alert['message']}. *Action: {alert['action']}*")

        sources.append({
            "title": f"{ph['brand']} {ph['product']} Passport ({ph['passport_id']})",
            "field": "warranty_expiry_date / next_maintenance_date",
            "confidence": "high"
        })

    return {
        "answer": "\n\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "intent": "attention",
        "suggestions": [
            "Generate Warranty Claim Pack for Daikin AC",
            "Show events timeline for next 90 days"
        ]
    }


def _handle_room_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Identify target room
    target_room = None
    rooms = ["kitchen", "living room", "bedroom", "bathroom", "utility", "garage", "office", "balcony"]
    for r in rooms:
        if r in q:
            target_room = r
            break

    if target_room:
        matched = [p for p in products if target_room in str(p.get("room", "")).lower()]
        room_title = target_room.title()

        if not matched:
            return {
                "answer": f"No products are currently registered in the **{room_title}**.",
                "sources": [],
                "confidence": "high",
                "intent": "room_query",
                "suggestions": ["Show all rooms", "Show Kitchen products"]
            }

        lines = [f"The **{room_title}** has **{len(matched)} registered product(s)**:\n"]
        sources = []
        for p in matched:
            health_badge = "🟢 Good" if p.get("health_status") == "good" else f"⚠️ {p.get('health_status', '').title()}"
            lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}** (Model: `{p.get('model', 'N/A')}`) — {health_badge}")
            sources.append({
                "title": f"{p.get('brand')} {p.get('product')} ({p.get('passport_id')})",
                "room": p.get("room"),
                "confidence": "high"
            })

        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "confidence": "high",
            "intent": "room_query",
            "suggestions": [f"What needs attention in the {room_title}?", "Show all household products"]
        }

    # List all rooms
    room_map = {}
    for p in products:
        r = p.get("room") or "Unassigned"
        room_map[r] = room_map.get(r, 0) + 1

    lines = ["Here is your product breakdown by room:\n"]
    for r, count in room_map.items():
        lines.append(f"• **{r}**: {count} product(s)")

    return {
        "answer": "\n".join(lines),
        "sources": [{"title": "Household Room Inventory", "confidence": "high"}],
        "confidence": "high",
        "intent": "room_list",
        "suggestions": ["Which appliances are in the Living Room?", "Which products need maintenance?"]
    }


def _handle_warranty_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)

    if matched:
        p_label = f"**{matched.get('brand', '')} {matched.get('product', '')}**"
        expiry = matched.get("warranty_expiry_date")
        warranty_str = matched.get("warranty", "Standard")
        purchase_date = matched.get("purchase_date")
        health = matched.get("health_status")

        if expiry:
            today = datetime.now()
            try:
                dt = datetime.strptime(expiry, "%Y-%m-%d")
                days_left = (dt - today).days
                if days_left < 0:
                    status_msg = f"🔴 **Expired** ({abs(days_left)} days ago on {expiry})"
                elif days_left <= 30:
                    status_msg = f"🔴 **Expiring in {days_left} days** (on {expiry})"
                elif days_left <= 90:
                    status_msg = f"🟠 **Expiring in {days_left} days** (on {expiry})"
                else:
                    status_msg = f"🟢 **Active until {expiry}** ({days_left} days remaining)"
            except (ValueError, TypeError):
                status_msg = f"Expires on {expiry}"
        else:
            status_msg = "Warranty expiry date is not recorded."

        answer = f"The warranty for your {p_label} (Model: `{matched.get('model', 'N/A')}`):\n\n" \
                 f"• **Warranty Term**: {warranty_str}\n" \
                 f"• **Purchase Date**: {purchase_date or 'N/A'}\n" \
                 f"• **Expiry Status**: {status_msg}\n" \
                 f"• **Seller**: {matched.get('seller', 'N/A')}\n" \
                 f"• **Invoice #**: {matched.get('invoice_number', 'N/A')}"

        sources = [{
            "title": f"{matched.get('brand')} {matched.get('product')} Warranty Card & Invoice",
            "passport_id": matched.get("passport_id"),
            "confidence": "high"
        }]

        return {
            "answer": answer,
            "sources": sources,
            "confidence": "high",
            "intent": "warranty_query",
            "suggestions": [
                f"Generate Warranty Claim Pack for {matched.get('product')}",
                "Show service history"
            ]
        }

    # List all warranties
    lines = ["Here are the warranty expiry statuses for all registered products:\n"]
    sources = []
    for p in products:
        expiry = p.get("warranty_expiry_date") or "N/A"
        health = p.get("health_status", "good")
        icon = "🔴" if health in ("urgent", "expired") else ("🟠" if health == "attention" else "🟢")
        lines.append(f"• {icon} **{p.get('brand', '')} {p.get('product', '')}**: {p.get('warranty', 'N/A')} — Expires `{expiry}`")
        sources.append({"title": f"{p.get('brand')} {p.get('product')} Passport", "passport_id": p.get("passport_id"), "confidence": "high"})

    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "intent": "warranty_list",
        "suggestions": ["What needs attention this month?", "Which appliances are in the Kitchen?"]
    }


def _handle_maintenance_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)

    if matched:
        p_label = f"**{matched.get('brand', '')} {matched.get('product', '')}**"
        next_maint = matched.get("next_maintenance_date")
        events = matched.get("events", [])
        services = [e for e in events if e.get("type") in ("service", "installation", "consumable")]

        lines = [f"Maintenance summary for {p_label}:\n"]
        if next_maint:
            lines.append(f"• **Next Scheduled Maintenance**: `{next_maint}`")
        if services:
            lines.append("\n**Past Service History:**")
            for s in services:
                lines.append(f"  • `{s.get('date')}` ({s.get('type').title()}): {s.get('description')}")
        else:
            lines.append("• No past service receipts recorded yet.")

        return {
            "answer": "\n".join(lines),
            "sources": [{"title": f"{matched.get('brand')} {matched.get('product')} Service Log", "passport_id": matched.get("passport_id"), "confidence": "high"}],
            "confidence": "high",
            "intent": "maintenance_query",
            "suggestions": ["Show upcoming timeline", "What needs attention this month?"]
        }

    # General maintenance overview
    lines = ["Scheduled maintenance across your household:\n"]
    sources = []
    for p in products:
        maint = p.get("next_maintenance_date")
        if maint:
            lines.append(f"• 🔧 **{p.get('brand', '')} {p.get('product', '')}**: Next service due `{maint}`")
            sources.append({"title": f"{p.get('brand')} {p.get('product')} Maintenance Record", "confidence": "high"})

    return {
        "answer": "\n".join(lines) if len(lines) > 1 else "No maintenance schedules recorded.",
        "sources": sources,
        "confidence": "high",
        "intent": "maintenance_list",
        "suggestions": ["What needs attention this month?", "Show warranty expiries"]
    }


def _handle_purchase_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)

    if matched:
        p_label = f"**{matched.get('brand', '')} {matched.get('product', '')}**"
        p_date = matched.get("purchase_date")
        price = matched.get("purchase_price")
        currency = matched.get("currency", "INR")
        seller = matched.get("seller")
        invoice = matched.get("invoice_number")

        answer = f"Purchase record for {p_label}:\n\n" \
                 f"• **Date**: {p_date or 'N/A'}\n" \
                 f"• **Price**: {currency} {price:,.2f}" if price else f"• **Price**: N/A\n"
        answer += f"\n• **Store**: {seller or 'N/A'}\n" \
                  f"• **Invoice #**: {invoice or 'N/A'}\n" \
                  f"• **Room**: {matched.get('room', 'N/A')}"

        return {
            "answer": answer,
            "sources": [{"title": f"{matched.get('brand')} {matched.get('product')} Invoice ({matched.get('passport_id')})", "confidence": "high"}],
            "confidence": "high",
            "intent": "purchase_query",
            "suggestions": ["Show all invoices", "When does warranty expire?"]
        }

    # Summary of all purchases
    total_val = sum(p.get("purchase_price", 0) for p in products if isinstance(p.get("purchase_price"), (int, float)))
    lines = [f"You have **{len(products)} registered products** in your household (Total logged value: **INR {total_val:,.2f}**):\n"]
    sources = []

    for p in sorted(products, key=lambda x: str(x.get("purchase_date", "")), reverse=True):
        price_str = f"INR {p.get('purchase_price'):,.2f}" if p.get("purchase_price") else "N/A"
        lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}** — `{p.get('purchase_date', 'N/A')}` | {price_str} | {p.get('seller', 'N/A')}")
        sources.append({"title": f"{p.get('brand')} {p.get('product')} Invoice", "confidence": "high"})

    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "intent": "purchase_list",
        "suggestions": ["What needs attention this month?", "Which products are in the Living Room?"]
    }


def _handle_single_product_overview(product: Dict[str, Any]) -> Dict[str, Any]:
    ph = compute_product_health(product)
    alerts = ph["alerts"]
    alert_text = f"\n⚠️ **Action Alert**: {alerts[0]['message']}" if alerts else "\n🟢 **Health Status**: Good (No urgent alerts)"

    answer = f"### 📦 **{product.get('brand', '')} {product.get('product', '')}**\n\n" \
             f"• **Model**: `{product.get('model', 'N/A')}`\n" \
             f"• **Serial #**: `{product.get('serial_number', 'N/A')}`\n" \
             f"• **Room**: {product.get('room', 'N/A')}\n" \
             f"• **Purchase Date**: {product.get('purchase_date', 'N/A')}\n" \
             f"• **Warranty**: {product.get('warranty', 'N/A')} (Expires: `{product.get('warranty_expiry_date', 'N/A')}`)\n" \
             f"• **Next Maintenance**: `{product.get('next_maintenance_date', 'N/A')}`\n" \
             f"• **Seller**: {product.get('seller', 'N/A')}\n" \
             f"• **Linked Documents**: {len(product.get('linked_documents', []))} file(s)" \
             f"{alert_text}"

    return {
        "answer": answer,
        "sources": [{"title": f"{product.get('brand')} {product.get('product')} Digital Product Passport ({product.get('passport_id')})", "confidence": "high"}],
        "confidence": "high",
        "intent": "product_overview",
        "suggestions": [
            f"Generate Warranty Claim Pack for {product.get('product')}",
            "Show all products in this room"
        ]
    }


def _handle_general_fallback(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    lines = [f"I searched your household memory for *\"{q}\"*.\n\nHere are your registered products:\n"]
    sources = []
    for p in products:
        lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}** ({p.get('room', 'Unassigned')}) — Model: `{p.get('model', 'N/A')}`")
        sources.append({"title": f"{p.get('brand')} {p.get('product')} Passport", "confidence": "medium"})

    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "medium",
        "intent": "general_search",
        "suggestions": [
            "What needs attention this month?",
            "When does my washing machine warranty expire?",
            "Which appliances are in the Living Room?"
        ]
    }


def _find_matching_product(q: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Match query text against product names, brands, or models."""
    q_lower = q.lower()
    for p in products:
        p_name = str(p.get("product", "")).lower()
        p_brand = str(p.get("brand", "")).lower()
        p_model = str(p.get("model", "")).lower()

        if p_name and p_name in q_lower:
            return p
        if p_brand and p_brand in q_lower:
            return p
        if p_model and p_model in q_lower:
            return p

        # Check sub-words like 'ac' for air conditioner, 'washer' for washing machine
        if "ac" in q_lower.split() and ("air conditioner" in p_name or "ac" in p_name):
            return p
        if "washer" in q_lower and "washing" in p_name:
            return p
        if "purifier" in q_lower and "purifier" in p_name:
            return p

    return None
