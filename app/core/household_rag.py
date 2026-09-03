"""
HomeMind — Grounded household Q&A.
Keyword retrieval over the product graph, optional local LLM phrasing, never invents facts.
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

from app.config import OLLAMA_GENERATE_URL, TEXT_MODEL
from app.core.household_engine import get_household_attention, compute_product_health
from app.core.dpp_extractor import check_ollama, clean_json_response


def answer_household_query(
    query: str,
    products: List[Dict[str, Any]],
    scoped_passport_id: Optional[str] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    if not query or not query.strip():
        return {
            "answer": "Please ask a question about your household products, warranties, or maintenance schedules.",
            "sources": [],
            "confidence": "high",
            "why": "Empty question.",
            "intent": "empty",
            "engine": "none",
            "model": None,
            "suggestions": [
                "What needs my attention this month?",
                "When does my washing machine warranty expire?",
                "Which appliances are still under warranty?",
            ],
        }

    scoped = products
    if scoped_passport_id:
        scoped = [p for p in products if p.get("passport_id") == scoped_passport_id] or products

    # Always retrieve with deterministic memory first (grounding).
    fallback = _route_query(query.strip(), scoped, products)
    fallback["engine"] = "grounded_rules"
    fallback["model"] = None

    if use_llm:
        phrased = _maybe_phrase_with_local_llm(query.strip(), fallback)
        if phrased and isinstance(phrased, dict):
            fallback["answer"] = phrased.get("text") or fallback["answer"]
            fallback["engine"] = "grounded_rules+llm_phrasing"
            fallback["model"] = phrased.get("model") or TEXT_MODEL

    return fallback


def _route_query(query: str, scoped: List[Dict[str, Any]], all_products: List[Dict[str, Any]]) -> Dict[str, Any]:
    q = query.lower()

    if any(k in q for k in ["attention", "urgent", "overdue", "need my", "needs my", "this month", "alert"]):
        return _handle_attention_query(q, all_products)

    if any(k in q for k in ["still under warranty", "under warranty", "active warranty", "which appliances are still"]):
        return _handle_active_warranty_list(all_products)

    if any(k in q for k in ["warranty card", "where is the warranty", "show me my", "find everything", "invoice for", "manual for"]):
        if "warranty" in q or "invoice" in q or "manual" in q or "document" in q or "find everything" in q:
            return _handle_document_lookup(q, scoped if len(scoped) == 1 else all_products)

    if any(k in q for k in ["warranty", "guarantee", "expire", "expiry"]):
        return _handle_warranty_query(q, scoped)

    if any(k in q for k in ["filter", "consumable", "cartridge", "compatible part"]):
        return _handle_filter_query(q, scoped)

    if any(k in q for k in ["technician", "replaced", "last time", "service history", "last serviced", "serviced"]):
        return _handle_maintenance_query(q, scoped)

    if any(k in q for k in ["service", "maintenance", "repair", "clean this", "error"]):
        if any(k in q for k in ["error", "ie ", "showing an error", "troubleshooting"]):
            return _handle_troubleshooting(q, scoped)
        return _handle_maintenance_query(q, scoped)

    if any(k in q for k in ["room", "kitchen", "bedroom", "living", "utility", "garage", "office", "balcony"]):
        return _handle_room_query(q, all_products)

    if any(k in q for k in ["bought this year", "purchased this year", "this year"]):
        return _handle_year_purchases(all_products, datetime.now().year)

    if any(k in q for k in ["bought", "purchased", "purchase", "price", "cost", "how old", "invoice", "buy "]):
        return _handle_purchase_query(q, scoped)

    matched = _find_matching_product(q, scoped)
    if matched:
        return _handle_single_product_overview(matched)

    return _unknown(query)


def _unknown(query: str) -> Dict[str, Any]:
    return {
        "answer": (
            f"I don't know from your household records. "
            f"I couldn't ground an answer to “{query.strip()}” in a registered product, document, or event."
        ),
        "sources": [],
        "confidence": "none",
        "why": "No matching product, document snippet, or event was retrieved.",
        "intent": "unknown",
        "suggestions": [
            "What needs my attention this month?",
            "When does my washing machine warranty expire?",
            "Which appliances are still under warranty?",
        ],
    }


def _evidence(title: str, passport_id: Optional[str] = None, field: str = "", confidence: str = "high") -> Dict[str, Any]:
    return {
        "title": title,
        "passport_id": passport_id,
        "field": field,
        "confidence": confidence,
    }


def _handle_attention_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    attention_items = get_household_attention(products)
    if not attention_items:
        return {
            "answer": "All products in your household are currently in good health. No warranties are expiring soon, and no maintenance is overdue.",
            "sources": [_evidence("Household Health Engine")],
            "confidence": "high",
            "why": "Health engine found no urgent or attention alerts.",
            "intent": "attention",
            "suggestions": ["Show all registered products", "Which appliances are in the Bedroom?"],
        }

    lines = [f"Your household has {len(attention_items)} action(s):\n"]
    sources = []
    for item in attention_items:
        ph = item["product_health"]
        alert = item["worst_alert"]
        lines.append(f"- **{ph['brand']} {ph['product']}** ({ph['room']}): {alert['message']}. Action: {alert['action']}")
        sources.append(_evidence(f"{ph['brand']} {ph['product']} Passport", ph["passport_id"], "warranty_expiry_date / next_maintenance_date"))

    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Computed from stored warranty expiry and maintenance dates.",
        "intent": "attention",
        "suggestions": ["Generate Warranty Claim Pack for the AC", "Show events timeline for next 90 days"],
    }


def _handle_room_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "why": "Room field on stored passports.",
                "intent": "room_query",
                "suggestions": ["Show all rooms", "Show Kitchen products"],
            }
        lines = [f"The **{room_title}** has **{len(matched)} registered product(s)**:\n"]
        sources = []
        for p in matched:
            lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}** (Model: `{p.get('model', 'N/A')}`)")
            sources.append(_evidence(f"{p.get('brand')} {p.get('product')}", p.get("passport_id"), "room"))
        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "confidence": "high",
            "why": "Filtered household graph by room.",
            "intent": "room_query",
            "suggestions": [f"What needs attention in the {room_title}?", "Show all household products"],
        }

    room_map: Dict[str, int] = {}
    for p in products:
        r = p.get("room") or "Unassigned"
        room_map[r] = room_map.get(r, 0) + 1
    lines = ["Here is your product breakdown by room:\n"]
    for r, count in room_map.items():
        lines.append(f"• **{r}**: {count} product(s)")
    return {
        "answer": "\n".join(lines),
        "sources": [_evidence("Household Room Inventory")],
        "confidence": "high",
        "why": "Aggregated room fields on passports.",
        "intent": "room_list",
        "suggestions": ["Which appliances are in the Living Room?", "Which products need maintenance?"],
    }


def _warranty_status_line(expiry: Optional[str]) -> str:
    if not expiry:
        return "Warranty expiry date is not recorded."
    try:
        dt = datetime.strptime(expiry, "%Y-%m-%d")
        days_left = (dt.date() - datetime.now().date()).days
        if days_left < 0:
            return f"**Expired** ({abs(days_left)} days ago on {expiry})"
        if days_left <= 30:
            return f"**Expiring in {days_left} days** (on {expiry})"
        if days_left <= 90:
            return f"**Expiring in {days_left} days** (on {expiry})"
        return f"**Active until {expiry}** ({days_left} days remaining)"
    except (ValueError, TypeError):
        return f"Expires on {expiry}"


def _handle_warranty_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)
    if matched:
        p_label = f"**{matched.get('brand', '')} {matched.get('product', '')}**"
        expiry = matched.get("warranty_expiry_date")
        status_msg = _warranty_status_line(expiry)
        answer = (
            f"The warranty for your {p_label} (Model: `{matched.get('model', 'N/A')}`):\n\n"
            f"• **Warranty Term**: {matched.get('warranty') or 'Not recorded'}\n"
            f"• **Purchase Date**: {matched.get('purchase_date') or 'N/A'}\n"
            f"• **Expiry Status**: {status_msg}\n"
            f"• **Seller**: {matched.get('seller') or 'N/A'}\n"
            f"• **Invoice #**: {matched.get('invoice_number') or 'N/A'}"
        )
        return {
            "answer": answer,
            "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} Warranty & Invoice", matched.get("passport_id"), "warranty_expiry_date")],
            "confidence": "high" if expiry else "medium",
            "why": "Computed from stored purchase date and warranty term, or the stored expiry date.",
            "intent": "warranty_query",
            "suggestions": [f"Where is the warranty card for my {matched.get('product')}?", "Show service history"],
        }

    if any(k in q for k in ["when does my", "expire"]):
        return _unknown("that warranty question — name the appliance")

    lines = ["Warranty expiry statuses for registered products:\n"]
    sources = []
    for p in products:
        expiry = p.get("warranty_expiry_date") or "N/A"
        health = p.get("health_status", "good")
        icon = "expired" if health in ("urgent", "expired") else ("soon" if health == "attention" else "ok")
        lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}**: {p.get('warranty', 'N/A')} — Expires `{expiry}` ({icon})")
        sources.append(_evidence(f"{p.get('brand')} {p.get('product')} Passport", p.get("passport_id")))
    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Listed warranty_expiry_date from each passport.",
        "intent": "warranty_list",
        "suggestions": ["What needs attention this month?", "Which appliances are still under warranty?"],
    }


def _handle_active_warranty_list(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    active = []
    for p in products:
        expiry = p.get("warranty_expiry_date")
        if not expiry:
            continue
        try:
            if datetime.strptime(expiry, "%Y-%m-%d").date() >= datetime.now().date():
                active.append(p)
        except (ValueError, TypeError):
            continue
    if not active:
        return {
            "answer": "I don't have any products with a recorded future warranty expiry date.",
            "sources": [],
            "confidence": "medium",
            "why": "No passport had warranty_expiry_date on or after today.",
            "intent": "active_warranty",
            "suggestions": ["What needs my attention this month?"],
        }
    lines = [f"**{len(active)} appliance(s)** still under warranty:\n"]
    sources = []
    for p in active:
        lines.append(f"• **{p.get('brand')} {p.get('product')}** — until `{p.get('warranty_expiry_date')}`")
        sources.append(_evidence(f"{p.get('brand')} {p.get('product')}", p.get("passport_id"), "warranty_expiry_date"))
    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Filtered passports whose warranty_expiry_date is today or later.",
        "intent": "active_warranty",
        "suggestions": ["What needs attention this month?"],
    }


def _handle_document_lookup(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)
    if not matched:
        return _unknown(q)

    docs = matched.get("linked_documents") or []
    want_w = "warranty" in q
    want_inv = "invoice" in q
    want_man = "manual" in q
    want_all = "everything" in q or "related" in q

    lines = [f"Documents on **{matched.get('brand')} {matched.get('product')}** (`{matched.get('model') or 'N/A'}`):\n"]
    shown = 0
    for d in docs:
        dtype = str(d.get("type") or "").lower()
        if want_all or (want_w and "warranty" in dtype) or (want_inv and "invoice" in dtype) or (want_man and "manual" in dtype) or (not want_w and not want_inv and not want_man):
            lines.append(f"• **{str(d.get('type') or 'document').replace('_', ' ').title()}** — {d.get('snippet') or d.get('source') or 'linked'}")
            shown += 1
    if shown == 0:
        return {
            "answer": (
                f"I don't have that document on file for your {matched.get('product')}. "
                "Scan the warranty card, invoice, or manual and HomeMind will link it to this product."
            ),
            "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} Passport", matched.get("passport_id"), "linked_documents", "low")],
            "confidence": "low",
            "why": "No linked_documents matched the requested type.",
            "intent": "document_lookup",
            "suggestions": ["Scan a warranty card", "Show service history"],
        }
    return {
        "answer": "\n".join(lines),
        "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} linked documents", matched.get("passport_id"), "linked_documents")],
        "confidence": "high",
        "why": "Listed linked_documents on the product node.",
        "intent": "document_lookup",
        "suggestions": ["When does the warranty expire?", "Show service history"],
    }


def _handle_filter_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products) or _find_matching_product("purifier", products)
    if not matched:
        return _unknown(q)
    events = [e for e in (matched.get("events") or []) if e.get("type") == "consumable"]
    model = matched.get("model") or "this model"
    if events:
        last = events[-1]
        answer = (
            f"For your **{matched.get('brand')} {matched.get('product')}** (model `{model}`), "
            f"the household record notes: {last.get('description')} (date `{last.get('date')}`).\n\n"
            "I can only confirm filters/parts that appear on your documents or service events — "
            "I will not invent a SKU."
        )
        conf = "high"
        why = "Grounded in a stored consumable event."
    else:
        answer = (
            f"I don't have a stored filter SKU for your **{matched.get('brand')} {matched.get('product')}** (`{model}`). "
            "Scan the manual, a filter box, or a service receipt and I will link it. "
            "Use Compatibility Scanner to check a part against this model."
        )
        conf = "low"
        why = "No consumable event or part SKU on the product graph."
    return {
        "answer": answer,
        "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} service/consumable log", matched.get("passport_id"), "events")],
        "confidence": conf,
        "why": why,
        "intent": "filter_query",
        "suggestions": ["Scan a replacement filter", "When was it last serviced?"],
    }


def _handle_troubleshooting(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)
    if not matched:
        return _unknown(q)
    snippets = []
    for d in matched.get("linked_documents") or []:
        if str(d.get("type") or "").lower() in ("manual", "service_receipt", "document"):
            if d.get("snippet"):
                snippets.append(d["snippet"])
    if not snippets:
        return {
            "answer": (
                f"I identified **{matched.get('brand')} {matched.get('product')}** (`{matched.get('model') or 'N/A'}`), "
                "but I don't have a manual excerpt for this error. Upload the troubleshooting section of the manual — "
                "I will not guess repairs."
            ),
            "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')}", matched.get("passport_id"), "linked_documents", "low")],
            "confidence": "none",
            "why": "No manual snippet stored; refused to diagnose from the model alone.",
            "intent": "troubleshooting",
            "suggestions": ["Show service history", "Open Service Pass"],
        }
    answer = (
        f"From your stored documents for **{matched.get('brand')} {matched.get('product')}**:\n\n"
        + "\n".join(f"• {s}" for s in snippets[:4])
        + "\n\nThis is document-grounded only, not a live diagnosis."
    )
    return {
        "answer": answer,
        "sources": [_evidence("Linked manual / service snippets", matched.get("passport_id"), "linked_documents")],
        "confidence": "medium",
        "why": "Quoted stored document snippets only.",
        "intent": "troubleshooting",
        "suggestions": ["Show service history", "Open Service Pass"],
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
                lines.append(f"  • `{s.get('date')}` ({str(s.get('type')).title()}): {s.get('description')}")
            last = services[-1]
            lines.append(f"\nLast recorded technician work: `{last.get('date')}` — {last.get('description')}")
        else:
            lines.append("• No past service receipts recorded yet.")
        return {
            "answer": "\n".join(lines),
            "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} Service Log", matched.get("passport_id"), "events")],
            "confidence": "high" if services or next_maint else "medium",
            "why": "Read from product events and next_maintenance_date.",
            "intent": "maintenance_query",
            "suggestions": ["Show upcoming timeline", "What needs attention this month?"],
        }

    lines = ["Scheduled maintenance across your household:\n"]
    sources = []
    for p in products:
        maint = p.get("next_maintenance_date")
        if maint:
            lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}**: Next service due `{maint}`")
            sources.append(_evidence(f"{p.get('brand')} {p.get('product')} Maintenance Record", p.get("passport_id")))
    if len(lines) == 1:
        return _unknown("household maintenance")
    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Listed next_maintenance_date from passports.",
        "intent": "maintenance_list",
        "suggestions": ["What needs attention this month?", "Show warranty expiries"],
    }


def _handle_year_purchases(products: List[Dict[str, Any]], year: int) -> Dict[str, Any]:
    matched = []
    for p in products:
        d = str(p.get("purchase_date") or "")
        if d.startswith(str(year)):
            matched.append(p)
    if not matched:
        return {
            "answer": f"I don't have any products with a purchase date in {year}.",
            "sources": [],
            "confidence": "high",
            "why": f"No purchase_date started with {year}.",
            "intent": "purchase_year",
            "suggestions": ["Show all invoices", "What needs attention this month?"],
        }
    lines = [f"Purchases recorded in **{year}**:\n"]
    sources = []
    for p in matched:
        price = p.get("purchase_price")
        price_str = f"{p.get('currency') or 'INR'} {price:,.2f}" if isinstance(price, (int, float)) else "N/A"
        lines.append(f"• **{p.get('brand')} {p.get('product')}** — `{p.get('purchase_date')}` | {price_str}")
        sources.append(_evidence(f"{p.get('brand')} {p.get('product')} Invoice", p.get("passport_id"), "purchase_date"))
    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Filtered purchase_date by calendar year.",
        "intent": "purchase_year",
        "suggestions": ["Which appliances are still under warranty?"],
    }


def _handle_purchase_query(q: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    matched = _find_matching_product(q, products)

    if matched:
        p_label = f"**{matched.get('brand', '')} {matched.get('product', '')}**"
        p_date = matched.get("purchase_date")
        price = matched.get("purchase_price")
        currency = matched.get("currency") or "INR"
        seller = matched.get("seller")
        invoice = matched.get("invoice_number")

        lines = [f"Purchase record for {p_label}:\n"]
        lines.append(f"• **Date**: {p_date or 'N/A'}")
        if isinstance(price, (int, float)):
            lines.append(f"• **Price**: {currency} {price:,.2f}")
        else:
            lines.append("• **Price**: N/A")
        if q.find("how old") >= 0 or "old is" in q:
            if p_date:
                try:
                    dt = datetime.strptime(p_date, "%Y-%m-%d")
                    days = (datetime.now().date() - dt.date()).days
                    years = days / 365.0
                    lines.append(f"• **Age**: about {years:.1f} years ({days} days since purchase)")
                except (ValueError, TypeError):
                    pass
        lines.append(f"• **Store**: {seller or 'N/A'}")
        lines.append(f"• **Invoice #**: {invoice or 'N/A'}")
        lines.append(f"• **Room**: {matched.get('room') or 'N/A'}")

        return {
            "answer": "\n".join(lines),
            "sources": [_evidence(f"{matched.get('brand')} {matched.get('product')} Invoice", matched.get("passport_id"), "purchase_date")],
            "confidence": "high" if p_date or price else "medium",
            "why": "Read purchase fields from the product passport.",
            "intent": "purchase_query",
            "suggestions": ["When does warranty expire?", "Show linked documents"],
        }

    total_val = sum(p.get("purchase_price", 0) for p in products if isinstance(p.get("purchase_price"), (int, float)))
    lines = [f"You have **{len(products)} registered products** (logged value: **INR {total_val:,.2f}**):\n"]
    sources = []
    for p in sorted(products, key=lambda x: str(x.get("purchase_date", "")), reverse=True):
        price_str = f"INR {p.get('purchase_price'):,.2f}" if isinstance(p.get("purchase_price"), (int, float)) else "N/A"
        lines.append(f"• **{p.get('brand', '')} {p.get('product', '')}** — `{p.get('purchase_date', 'N/A')}` | {price_str}")
        sources.append(_evidence(f"{p.get('brand')} {p.get('product')} Invoice", p.get("passport_id")))
    return {
        "answer": "\n".join(lines),
        "sources": sources,
        "confidence": "high",
        "why": "Listed purchase_date and purchase_price from all passports.",
        "intent": "purchase_list",
        "suggestions": ["Show everything I bought this year", "What needs attention this month?"],
    }


def _handle_single_product_overview(product: Dict[str, Any]) -> Dict[str, Any]:
    ph = compute_product_health(product)
    alerts = ph["alerts"]
    alert_text = f"\n**Action Alert**: {alerts[0]['message']}" if alerts else "\n**Health Status**: Good (no urgent alerts)"
    answer = (
        f"**{product.get('brand', '')} {product.get('product', '')}**\n\n"
        f"• **Model**: `{product.get('model', 'N/A')}`\n"
        f"• **Serial #**: `{product.get('serial_number', 'N/A')}`\n"
        f"• **Room**: {product.get('room', 'N/A')}\n"
        f"• **Purchase Date**: {product.get('purchase_date', 'N/A')}\n"
        f"• **Warranty**: {product.get('warranty', 'N/A')} (Expires: `{product.get('warranty_expiry_date', 'N/A')}`)\n"
        f"• **Next Maintenance**: `{product.get('next_maintenance_date', 'N/A')}`\n"
        f"• **Seller**: {product.get('seller', 'N/A')}\n"
        f"• **Linked Documents**: {len(product.get('linked_documents', []))} file(s)"
        f"{alert_text}"
    )
    return {
        "answer": answer,
        "sources": [_evidence(f"{product.get('brand')} {product.get('product')} Passport", product.get("passport_id"))],
        "confidence": "high",
        "why": "Full passport overview for a matched product.",
        "intent": "product_overview",
        "suggestions": [
            f"When does my {product.get('product')} warranty expire?",
            "Show service history",
        ],
    }


def _find_matching_product(q: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    q_lower = q.lower()
    tokens = set(re.findall(r"[a-z0-9]+", q_lower))
    best = None
    best_score = 0
    for p in products:
        score = 0
        p_name = str(p.get("product") or "").lower()
        p_brand = str(p.get("brand") or "").lower()
        p_model = str(p.get("model") or "").lower()
        if p_name and p_name in q_lower:
            score += 100
        if p_model and len(p_model) >= 4 and p_model.replace("-", "") in q_lower.replace("-", "").replace(" ", ""):
            score += 90
        if p_brand and len(p_brand) >= 3 and p_brand in q_lower:
            score += 40
        if "washer" in tokens and "washing" in p_name:
            score += 80
        if "purifier" in q_lower and "purifier" in p_name:
            score += 80
        if "ac" in tokens and ("air conditioner" in p_name or p_name == "ac"):
            score += 80
        if "fridge" in tokens and "refrigerat" in p_name:
            score += 80
        if score > best_score:
            best_score = score
            best = p
    if best_score < 40:
        return None
    return best


def _maybe_phrase_with_local_llm(query: str, result: Dict[str, Any]) -> Optional[Dict[str, str]]:
    info = check_ollama()
    if not info.get("online") or not info.get("has_text_model"):
        return None
    model_to_use = info.get("chat_model") or TEXT_MODEL
    facts = {
        "answer": result.get("answer"),
        "sources": result.get("sources"),
        "why": result.get("why"),
        "confidence": result.get("confidence"),
    }
    prompt = (
        "Rewrite the household assistant answer in clear spoken English. "
        "Use ONLY these facts. Do not add products, dates, prices, or SKUs that are not in the JSON. "
        "If confidence is none, keep saying you don't know.\n\n"
        f"USER QUESTION: {query}\nFACTS JSON:\n{json.dumps(facts, ensure_ascii=False)[:4000]}\n"
    )
    try:
        res = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=15.0,
        )
        if res.status_code == 200:
            text = (res.json().get("response") or "").strip()
            if text:
                return {"text": text, "model": model_to_use}
    except Exception:
        return None
    return None
