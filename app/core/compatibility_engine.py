"""
HomeMind — Consumables & Parts Compatibility Engine
Evaluates replacement parts, consumables (filters, remotes, batteries, vacuum bags, cartridges),
and accessories against the user's Household Product Graph with grounded confidence scores.
"""

import re
from typing import Dict, Any, List, Optional
from app.core.ocr_engine import extract_ocr_text
from app.core.normalizers import normalize_model_number, clean_str


# Appliance consumable keyword affinities
CONSUMABLE_AFFINITIES = {
    "filter": ["air purifier", "air conditioner", "water purifier", "vacuum", "refrigerator"],
    "hepa": ["air purifier", "vacuum"],
    "carbon": ["air purifier", "water purifier", "refrigerator"],
    "remote": ["tv", "air conditioner"],
    "battery": ["laptop", "vacuum", "clock", "remote"],
    "bag": ["vacuum"],
    "drum": ["washing machine", "washer", "dryer"],
    "belt": ["washing machine", "washer", "dryer"],
    "cartridge": ["water purifier", "printer"],
    "coil": ["air conditioner", "refrigerator"]
}


def evaluate_compatibility(
    scanned_text: str,
    products: List[Dict[str, Any]],
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate scanned part or consumable against registered household products.
    Returns compatibility verdict, matched product, confidence, evidence, duplicate warnings, and recommendation.
    """
    # If image provided and text is sparse, run OCR to gather part text
    raw_ocr = ""
    if image_path:
        try:
            ocr_res = extract_ocr_text(image_path)
            raw_ocr = ocr_res.get("text", "")
        except Exception:
            pass

    combined_text = f"{scanned_text} {raw_ocr}".strip()
    text_lower = combined_text.lower()

    if not text_lower:
        return {
            "compatible": False,
            "status": "unverifiable",
            "confidence": 0.0,
            "matched_product": None,
            "evidence": "No legible text, model number, or brand detected on the scanned part.",
            "recommendation": "Hold the camera closer or ensure adequate lighting on the part label.",
            "duplicate_warning": None
        }

    best_match = None
    best_score = 0.0
    match_evidence = ""

    # Check each registered household product
    for product in products:
        p_name = str(product.get("product", "")).lower()
        p_brand = str(product.get("brand", "")).lower()
        p_model = str(product.get("model", "")).lower()
        norm_model = normalize_model_number(product.get("model")) or ""

        score = 0.0
        reasons = []

        # 1. Exact or normalized model number match in scanned text
        if p_model and len(p_model) >= 3 and p_model in text_lower:
            score += 0.55
            reasons.append(f"exact model '{product.get('model')}' printed on part packaging")
        elif norm_model and len(norm_model) >= 4 and norm_model.lower() in text_lower.replace("-", "").replace(" ", ""):
            score += 0.50
            reasons.append(f"normalized model code '{norm_model}' match")
        elif norm_model and len(norm_model) >= 4:
            # Check 4-character model prefix (e.g. AC30, FTKF, T75)
            prefix = norm_model[:4].lower()
            if prefix in text_lower.replace("-", "").replace(" ", ""):
                score += 0.35
                reasons.append(f"model series prefix '{prefix.upper()}' match")

        # 2. Brand match
        if p_brand and len(p_brand) >= 2 and p_brand in text_lower:
            score += 0.25
            reasons.append(f"brand '{product.get('brand')}' confirmed")

        # 3. Product type / category affinity
        for keyword, affinities in CONSUMABLE_AFFINITIES.items():
            if keyword in text_lower:
                if any(aff in p_name for aff in affinities):
                    score += 0.20
                    reasons.append(f"consumable type '{keyword}' is designed for {product.get('product')}")
                    break

        if score > best_score:
            best_score = score
            best_match = product
            match_evidence = "; ".join(reasons)

    # Check for duplicate item warning
    duplicate_warning = None
    if best_match:
        same_category_count = sum(
            1 for p in products
            if str(p.get("product", "")).lower() == str(best_match.get("product", "")).lower()
        )
        if same_category_count > 1:
            duplicate_warning = f"Note: You have {same_category_count} registered {best_match.get('product')}s in your home."

    # Verdict generation based on confidence
    confidence = min(round(best_score, 2), 0.98)

    if confidence >= 0.70:
        return {
            "compatible": True,
            "status": "verified_compatible",
            "confidence": confidence,
            "matched_product": {
                "passport_id": best_match.get("passport_id"),
                "product": best_match.get("product"),
                "brand": best_match.get("brand"),
                "model": best_match.get("model"),
                "room": best_match.get("room", "Unassigned")
            },
            "evidence": f"Model & brand compatibility confirmed: {match_evidence}.",
            "recommendation": f"✅ Compatible: Safe to purchase for your {best_match.get('brand')} {best_match.get('product')} in the {best_match.get('room', 'home')}.",
            "duplicate_warning": duplicate_warning
        }
    elif confidence >= 0.40:
        return {
            "compatible": True,
            "status": "likely_compatible",
            "confidence": confidence,
            "matched_product": {
                "passport_id": best_match.get("passport_id"),
                "product": best_match.get("product"),
                "brand": best_match.get("brand"),
                "model": best_match.get("model"),
                "room": best_match.get("room", "Unassigned")
            },
            "evidence": f"Partial compatibility match: {match_evidence}.",
            "recommendation": "⚠️ Likely compatible, but check physical connector/dimensions before unsealing packaging.",
            "duplicate_warning": duplicate_warning
        }
    else:
        return {
            "compatible": False,
            "status": "unverified",
            "confidence": confidence,
            "matched_product": None,
            "evidence": "No registered household appliance matches this part model or manufacturer specification.",
            "recommendation": "❌ Cannot verify compatibility. No matching registered appliance found in your household.",
            "duplicate_warning": None
        }
