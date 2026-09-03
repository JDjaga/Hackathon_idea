"""
AI Product Guardian — Deterministic Identity Matching & Conflict Detection Engine
Compares document identity fields (model, serial, seller, date, brand) to verify
authenticity and detect conflicting claims across multi-scan lifecycles.
"""

from typing import Dict, Any, List, Optional
from app.config import SERIAL_MATCH_THRESHOLD, MIN_MATCH_FIELDS
from app.core.normalizers import (
    normalize_model_number,
    normalize_serial_number,
    normalize_seller_name,
    normalize_date,
    clean_str
)

IDENTITY_FIELDS = [
    "model",
    "serial_number",
    "brand",
    "seller",
    "purchase_date"
]


def levenshtein_distance(s1: Optional[str], s2: Optional[str]) -> int:
    """Compute standard Levenshtein edit distance between two strings."""
    if s1 is None or s2 is None:
        return 999
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compare_field(
    field_name: str,
    new_val: Any,
    existing_val: Any,
    serial_threshold: int = SERIAL_MATCH_THRESHOLD
) -> Dict[str, Any]:
    """
    Compare two field values with field-specific normalization and matching rules.
    Returns matching boolean, or None if either field is missing/empty.
    """
    if field_name == "model":
        n_val = normalize_model_number(new_val)
        e_val = normalize_model_number(existing_val)
    elif field_name == "serial_number":
        n_val = normalize_serial_number(new_val)
        e_val = normalize_serial_number(existing_val)
    elif field_name == "seller":
        n_val = normalize_seller_name(new_val)
        e_val = normalize_seller_name(existing_val)
    elif field_name == "purchase_date":
        n_val = normalize_date(new_val)
        e_val = normalize_date(existing_val)
    else:
        n_val = clean_str(new_val)
        e_val = clean_str(existing_val)
        if n_val:
            n_val = n_val.lower()
        if e_val:
            e_val = e_val.lower()

    # Skip comparison if either value is unpopulated
    if n_val is None or e_val is None:
        return {
            "field": field_name,
            "matches": None,
            "new_value": new_val,
            "existing_value": existing_val
        }

    # Field-specific matching logic
    if field_name == "seller":
        # Substring containment allows for "Best Electrical" matching "Best Electrical Store"
        matches = (n_val in e_val) or (e_val in n_val)
    elif field_name == "serial_number":
        # Fuzzy serial match for OCR character misreads (e.g. 0 vs O, 1 vs I)
        dist = levenshtein_distance(n_val, e_val)
        matches = (dist <= serial_threshold)
    else:
        matches = (n_val == e_val)

    return {
        "field": field_name,
        "matches": matches,
        "new_value": new_val,
        "existing_value": existing_val
    }


def score_match(
    new_passport: Dict[str, Any],
    existing_passport: Dict[str, Any],
    serial_threshold: int = SERIAL_MATCH_THRESHOLD
) -> Dict[str, Any]:
    """
    Compare a candidate passport against a single stored passport across all identity fields.
    """
    matched_fields = []
    conflicting_fields = []
    skipped_fields = []

    for field in IDENTITY_FIELDS:
        new_val = new_passport.get(field)
        exist_val = existing_passport.get(field)

        res = compare_field(field, new_val, exist_val, serial_threshold)
        if res["matches"] is None:
            skipped_fields.append(field)
        elif res["matches"]:
            matched_fields.append(field)
        else:
            conflicting_fields.append({
                "field": field,
                "existing_value": exist_val,
                "new_value": new_val
            })

    return {
        "score": len(matched_fields),
        "matched_fields": matched_fields,
        "conflicting_fields": conflicting_fields,
        "skipped_fields": skipped_fields
    }


def match_passport(
    new_passport: Dict[str, Any],
    existing_passports: List[Dict[str, Any]],
    min_match_fields: int = MIN_MATCH_FIELDS,
    serial_threshold: int = SERIAL_MATCH_THRESHOLD
) -> Dict[str, Any]:
    """
    Match a candidate passport against an entire store of existing passports.
    Returns status: 'new_product', 'verified', or 'conflict'.
    """
    if not existing_passports:
        return {
            "status": "new_product",
            "matched_passport_id": None,
            "match_confidence": None,
            "matched_fields": [],
            "conflicting_fields": [],
            "score": 0
        }

    best_match = None
    best_score = 0

    for existing in existing_passports:
        # Don't match a passport against itself if IDs match
        if new_passport.get("passport_id") and new_passport.get("passport_id") == existing.get("passport_id"):
            continue

        res = score_match(new_passport, existing, serial_threshold)
        score = res["score"]
        conflicts_count = len(res["conflicting_fields"])

        if best_match is None:
            if score >= min_match_fields:
                best_score = score
                best_match = {
                    "passport": existing,
                    "result": res
                }
        else:
            best_conflicts = len(best_match["result"]["conflicting_fields"])
            if (score > best_score) or (score == best_score and conflicts_count < best_conflicts):
                best_score = score
                best_match = {
                    "passport": existing,
                    "result": res
                }

    # If insufficient identity fields matched, consider it a new product
    if best_match is None or best_score < min_match_fields:
        return {
            "status": "new_product",
            "matched_passport_id": None,
            "match_confidence": None,
            "matched_fields": [],
            "conflicting_fields": [],
            "score": best_score
        }

    match_res = best_match["result"]
    matched_passport = best_match["passport"]
    passport_id = matched_passport.get("passport_id", "UNKNOWN")

    if best_score >= 4:
        confidence = "high"
    elif best_score >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    matched_fields = match_res["matched_fields"]
    has_identity_key = "serial_number" in matched_fields or "model" in matched_fields

    # Conflicts on compared identity fields always flag conflict
    if match_res["conflicting_fields"]:
        status = "conflict"
    elif has_identity_key:
        status = "verified"
    else:
        # Brand + seller alone is too weak to claim the same physical product
        return {
            "status": "new_product",
            "matched_passport_id": None,
            "match_confidence": None,
            "matched_fields": [],
            "conflicting_fields": [],
            "score": best_score,
        }

    return {
        "status": status,
        "matched_passport_id": passport_id,
        "match_confidence": confidence,
        "matched_fields": matched_fields,
        "conflicting_fields": match_res["conflicting_fields"],
        "score": best_score
    }
