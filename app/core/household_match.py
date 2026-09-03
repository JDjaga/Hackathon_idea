"""
Match YOLO / camera labels to registered household products.
"""

from typing import Any, Dict, List, Optional

APPLIANCE_SYNONYMS = {
    "washing machine": ["washing machine", "washer", "washing", "laundry"],
    "air conditioner": ["air conditioner", "airconditioning", "ac", "split ac", "hvac"],
    "air purifier": ["air purifier", "purifier"],
    "water purifier": ["water purifier", "ro", "aquaguard"],
    "refrigerator": ["refrigerator", "fridge", "freezer"],
    "microwave": ["microwave", "microwave oven"],
    "television": ["television", "tv", "smart tv"],
    "dishwasher": ["dishwasher"],
    "vacuum": ["vacuum", "vacuum cleaner"],
    "oven": ["oven"],
    "laptop": ["laptop"],
    "cell phone": ["cell phone", "phone", "smartphone"],
}


def _normalize_label(text: str) -> str:
    return " ".join(str(text or "").lower().replace("_", " ").split())


def _product_aliases(product: Dict[str, Any]) -> List[str]:
    name = _normalize_label(product.get("product") or "")
    aliases = [name] if name else []
    for canonical, words in APPLIANCE_SYNONYMS.items():
        if name == canonical or any(w in name for w in words if len(w) > 2):
            aliases.extend(words)
            aliases.append(canonical)
            break
    return [a for a in aliases if a]


def match_label_to_products(
    label: str,
    products: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Return the best registered product for a detected appliance label, or None."""
    needle = _normalize_label(label)
    if not needle or not products:
        return None

    best = None
    best_score = 0

    for product in products:
        score = 0
        name = _normalize_label(product.get("product") or "")
        brand = _normalize_label(product.get("brand") or "")
        model = _normalize_label(product.get("model") or "")

        if name and (name in needle or needle in name):
            score += 80
        for alias in _product_aliases(product):
            if alias == needle or (len(alias) >= 3 and alias in needle) or (len(needle) >= 3 and needle in alias):
                score += 50
                break
        if brand and brand in needle:
            score += 20
        if model and len(model) >= 4 and model.replace("-", "") in needle.replace("-", "").replace(" ", ""):
            score += 40

        # Token "ac" only matches air conditioner aliases, not random text
        if needle in {"ac", "a.c."} and "air conditioner" in name:
            score += 70

        if score > best_score:
            best_score = score
            best = product

    if best_score < 50:
        return None

    return {
        "passport_id": best.get("passport_id"),
        "product": best.get("product"),
        "brand": best.get("brand"),
        "model": best.get("model"),
        "room": best.get("room") or "Unassigned",
        "serial_number": best.get("serial_number"),
        "warranty_expiry_date": best.get("warranty_expiry_date"),
        "match_score": best_score,
    }


def find_similar_owned_products(
    candidate: Dict[str, Any],
    products: List[Dict[str, Any]],
    exclude_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Products already owned that look like the candidate (duplicate purchase)."""
    c_name = _normalize_label(candidate.get("product") or "")
    c_brand = _normalize_label(candidate.get("brand") or "")
    hits = []
    for p in products:
        if exclude_id and p.get("passport_id") == exclude_id:
            continue
        p_name = _normalize_label(p.get("product") or "")
        p_brand = _normalize_label(p.get("brand") or "")
        same_type = c_name and p_name and (c_name in p_name or p_name in c_name)
        same_brand = c_brand and p_brand and c_brand == p_brand
        if same_type and (same_brand or not c_brand):
            hits.append({
                "passport_id": p.get("passport_id"),
                "product": p.get("product"),
                "brand": p.get("brand"),
                "model": p.get("model"),
                "room": p.get("room") or "Unassigned",
            })
    return hits


def build_product_graph(product: Dict[str, Any]) -> Dict[str, Any]:
    """Compact graph for UI: product root + documents + events."""
    docs = product.get("linked_documents") or []
    events = product.get("events") or []
    children = []
    seen_types = set()
    for d in docs:
        dtype = str(d.get("type") or "document").replace("_", " ").title()
        children.append({
            "kind": "document",
            "label": dtype,
            "detail": d.get("snippet") or d.get("source") or "",
        })
        seen_types.add(str(d.get("type") or "").lower())
    for e in events:
        children.append({
            "kind": "event",
            "label": str(e.get("type") or "event").replace("_", " ").title(),
            "detail": f"{e.get('date') or ''} {e.get('description') or ''}".strip(),
        })
    return {
        "root": f"{product.get('brand') or ''} {product.get('product') or 'Product'}".strip(),
        "model": product.get("model"),
        "children": children,
        "document_types": sorted(seen_types),
        "document_count": len(docs),
        "event_count": len(events),
    }
