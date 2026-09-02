"""
Identity Matcher — Hero Feature
AI Product Guardian

Deterministic (not LLM-based) product identity matching engine.
When a new document is scanned, this module checks whether a passport
for the same product already exists and flags conflicts between
overlapping identity fields.

Match result statuses:
  "new_product"  — no existing passport matches
  "verified"     — matched, all overlapping fields agree
  "conflict"     — matched, but at least one identity field disagrees
"""

import re
from datetime import datetime


# ============================================================
# TEXT NORMALIZERS
# ============================================================

def normalize_model_number(value):
    """
    Strip whitespace, uppercase, remove hyphens/dots/slashes.
    'T75-SKSF1Z' and 't75sksf1z' should match.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.upper()
    text = re.sub(r"[\s\-\./]+", "", text)

    return text if text else None


def normalize_serial_number(value):
    """
    Strip whitespace, uppercase. Keep hyphens (they're often
    meaningful in serials), but collapse multiple spaces.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.upper()
    text = re.sub(r"\s+", "", text)

    return text if text else None


def normalize_seller_name(value):
    """
    Lowercase, strip common business suffixes so
    'Best Electrical Store Sdn Bhd' matches 'Best Electrical Store'.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.lower()

    # Remove common business suffixes
    suffixes = [
        r"\bsdn\.?\s*bhd\.?\b",
        r"\bpvt\.?\s*ltd\.?\b",
        r"\bpte\.?\s*ltd\.?\b",
        r"\bltd\.?\b",
        r"\bllc\.?\b",
        r"\binc\.?\b",
        r"\bcorp\.?\b",
        r"\bco\.?\b",
    ]

    for suffix in suffixes:
        text = re.sub(suffix, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def normalize_date_value(value):
    """
    Normalize a date string into YYYY-MM-DD format.
    Handles common separators and ordinal suffixes.
    Returns the original string if parsing fails.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Strip ordinal suffixes
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)

    formats = [
        "%Y-%m-%d", "%Y.%m.%d",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y",
    ]

    for target in [cleaned, text]:
        for fmt in formats:
            try:
                return datetime.strptime(target, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return text


# ============================================================
# LEVENSHTEIN DISTANCE
# ============================================================

def levenshtein_distance(s1, s2):
    """
    Pure Python edit distance. No external dependency.
    """
    if s1 is None or s2 is None:
        return float("inf")

    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


# ============================================================
# FIELD COMPARISON
# ============================================================

def compare_field(field_name, new_value, existing_value, threshold=0):
    """
    Compare two field values. Returns a dict with:
      "matches": True/False/None (None = both null, skip)
      "new_value": normalized new
      "existing_value": normalized existing
    """

    if field_name == "model":
        norm_new = normalize_model_number(new_value)
        norm_existing = normalize_model_number(existing_value)
    elif field_name == "serial_number":
        norm_new = normalize_serial_number(new_value)
        norm_existing = normalize_serial_number(existing_value)
    elif field_name == "seller":
        norm_new = normalize_seller_name(new_value)
        norm_existing = normalize_seller_name(existing_value)
    elif field_name == "purchase_date":
        norm_new = normalize_date_value(new_value)
        norm_existing = normalize_date_value(existing_value)
    else:
        norm_new = str(new_value).strip().lower() if new_value else None
        norm_existing = str(existing_value).strip().lower() if existing_value else None

    # If either side is null, we can't compare — skip
    if norm_new is None or norm_existing is None:
        return {
            "matches": None,
            "new_value": new_value,
            "existing_value": existing_value
        }

    # Seller uses substring containment
    if field_name == "seller":
        matches = (norm_new in norm_existing) or (norm_existing in norm_new)
    # Serial number uses Levenshtein
    elif field_name == "serial_number":
        dist = levenshtein_distance(norm_new, norm_existing)
        matches = dist <= threshold
    # Everything else uses exact match after normalization
    else:
        matches = (norm_new == norm_existing)

    return {
        "matches": matches,
        "new_value": new_value,
        "existing_value": existing_value
    }


# ============================================================
# IDENTITY FIELDS
# ============================================================

# These are the fields used for identity matching, in priority order.
# "brand" is intentionally included as a soft signal but not a
# hard requirement — OCR often misreads brand names.
IDENTITY_FIELDS = [
    "model",
    "serial_number",
    "brand",
    "seller",
    "purchase_date",
]


# ============================================================
# MATCH ONE PASSPORT AGAINST ANOTHER
# ============================================================

def score_match(new_passport, existing_passport, serial_threshold=2):
    """
    Compare a new passport against one existing passport.
    Returns:
      {
        "matched_fields": [...],
        "conflicting_fields": [...],
        "skipped_fields": [...],
        "score": int  (number of matched fields)
      }
    """
    matched = []
    conflicting = []
    skipped = []

    for field in IDENTITY_FIELDS:
        new_val = new_passport.get(field)
        existing_val = existing_passport.get(field)

        threshold = serial_threshold if field == "serial_number" else 0

        result = compare_field(field, new_val, existing_val, threshold)

        if result["matches"] is None:
            skipped.append(field)
        elif result["matches"]:
            matched.append(field)
        else:
            conflicting.append({
                "field": field,
                "existing_value": existing_val,
                "new_value": new_val
            })

    return {
        "matched_fields": matched,
        "conflicting_fields": conflicting,
        "skipped_fields": skipped,
        "score": len(matched)
    }


# ============================================================
# MATCH AGAINST ALL EXISTING PASSPORTS
# ============================================================

def match_passport(new_passport, existing_passports, min_match_fields=2, serial_threshold=2):
    """
    Try to match a new passport against all existing passports.

    Returns:
      {
        "status": "new_product" | "verified" | "conflict",
        "matched_passport_id": str | None,
        "match_confidence": "high" | "medium" | "low" | None,
        "matched_fields": [...],
        "conflicting_fields": [...],
      }
    """

    if not existing_passports:
        return {
            "status": "new_product",
            "matched_passport_id": None,
            "match_confidence": None,
            "matched_fields": [],
            "conflicting_fields": []
        }

    best_match = None
    best_score = 0

    for existing in existing_passports:
        result = score_match(new_passport, existing, serial_threshold)

        if result["score"] > best_score:
            best_score = result["score"]
            best_match = {
                "passport": existing,
                "result": result
            }

    # Not enough fields matched — treat as new product
    if best_match is None or best_score < min_match_fields:
        return {
            "status": "new_product",
            "matched_passport_id": None,
            "match_confidence": None,
            "matched_fields": [],
            "conflicting_fields": []
        }

    result = best_match["result"]
    existing_passport = best_match["passport"]
    passport_id = existing_passport.get("passport_id", "UNKNOWN")

    # Determine confidence
    if best_score >= 4:
        confidence = "high"
    elif best_score >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Determine status: conflict if ANY identity field disagrees
    if result["conflicting_fields"]:
        status = "conflict"
    else:
        status = "verified"

    return {
        "status": status,
        "matched_passport_id": passport_id,
        "match_confidence": confidence,
        "matched_fields": result["matched_fields"],
        "conflicting_fields": result["conflicting_fields"]
    }


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":

    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 65)
    print("  IDENTITY MATCHER — SELF TEST")
    print("=" * 65)

    # Existing passport in the store
    existing = [
        {
            "passport_id": "PP-20260901103000-1",
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75-SKSF1Z",
            "serial_number": "LG123456789",
            "purchase_price": 28500.0,
            "currency": "INR",
            "purchase_date": "2026-08-12",
            "warranty": "2-YEAR",
            "seller": "Best Electrical Store",
            "category": "Large Domestic Appliances",
        }
    ]

    # --- Test 1: Verified match ---
    print("\n--- Test 1: Verified Match ---")
    new_verified = {
        "product": "Washing Machine",
        "brand": "LG",
        "model": "T75SKSF1Z",  # same after normalization
        "serial_number": "LG123456789",
        "purchase_date": "12/08/2026",  # same date, different format
        "seller": "Best Electrical Store Sdn Bhd",
    }
    result = match_passport(new_verified, existing)
    print(f"  Status: {result['status']}")
    print(f"  Matched fields: {result['matched_fields']}")
    print(f"  Conflicts: {result['conflicting_fields']}")
    assert result["status"] == "verified", f"Expected 'verified', got '{result['status']}'"
    print("  ✓ PASSED")

    # --- Test 2: Conflict (mismatched serial) ---
    print("\n--- Test 2: Conflict (Serial Mismatch) ---")
    new_conflict = {
        "product": "Washing Machine",
        "brand": "LG",
        "model": "T75SKSF1Z",
        "serial_number": "LG999999999",  # DIFFERENT serial
        "purchase_date": "2026-08-12",
        "seller": "Best Electrical Store",
    }
    result = match_passport(new_conflict, existing)
    print(f"  Status: {result['status']}")
    print(f"  Matched fields: {result['matched_fields']}")
    print(f"  Conflicts: {result['conflicting_fields']}")
    assert result["status"] == "conflict", f"Expected 'conflict', got '{result['status']}'"
    print("  ✓ PASSED")

    # --- Test 3: New product (nothing matches) ---
    print("\n--- Test 3: New Product ---")
    new_product = {
        "product": "Refrigerator",
        "brand": "Samsung",
        "model": "RT28K3022SE",
        "serial_number": "SAM987654321",
        "purchase_date": "2026-09-01",
        "seller": "Cool Electronics",
    }
    result = match_passport(new_product, existing)
    print(f"  Status: {result['status']}")
    assert result["status"] == "new_product", f"Expected 'new_product', got '{result['status']}'"
    print("  ✓ PASSED")

    # --- Test 4: Fuzzy serial match (within Levenshtein threshold) ---
    print("\n--- Test 4: Fuzzy Serial Match (Levenshtein ≤ 2) ---")
    new_fuzzy = {
        "product": "Washing Machine",
        "brand": "LG",
        "model": "T75SKSF1Z",
        "serial_number": "LG123456780",  # 1 char different (9→0)
        "purchase_date": "2026-08-12",
        "seller": "Best Electrical Store",
    }
    result = match_passport(new_fuzzy, existing)
    print(f"  Status: {result['status']}")
    print(f"  Matched fields: {result['matched_fields']}")
    assert result["status"] == "verified", f"Expected 'verified', got '{result['status']}'"
    print("  ✓ PASSED")

    # --- Test 5: Empty store ---
    print("\n--- Test 5: Empty Store ---")
    result = match_passport(new_verified, [])
    assert result["status"] == "new_product"
    print("  ✓ PASSED")

    print("\n" + "=" * 65)
    print("  ALL TESTS PASSED")
    print("=" * 65)
