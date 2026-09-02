"""
AI Product Guardian — Data Normalizers
Robust, deterministic sanitizers and formatters for text, dates, prices, models, serial numbers, and sellers.
"""

import re
from datetime import datetime
from typing import Optional, Any, Dict

NULL_LIKE_STRINGS = {
    "", "null", "none", "unknown", "n/a", "na", "nil", "undefined",
    "-", "--", "---", "not available", "not specified", "pending"
}

def clean_str(value: Any) -> Optional[str]:
    """Strip whitespace and return None if empty or null-like."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in NULL_LIKE_STRINGS:
        return None
    return s


def normalize_text(text: Any) -> Optional[str]:
    """Collapse consecutive whitespace and clean string."""
    cleaned = clean_str(text)
    if not cleaned:
        return None
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalize any date string into standard ISO format (YYYY-MM-DD).
    Handles ordinal suffixes ('12th Aug 2026'), dot separators ('12.08.2026'),
    slash/dash variants, and textual month formats.
    """
    cleaned = clean_str(value)
    if not cleaned:
        return None

    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    sanitized = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", cleaned, flags=re.IGNORECASE)

    date_formats = [
        "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%d-%b-%Y", "%d-%B-%Y", "%d/%b/%Y", "%d/%B/%Y",
        "%b-%d-%Y", "%B-%d-%Y", "%b/%d/%Y", "%B/%d/%Y",
        "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y",
        "%B %d %Y", "%b %d %Y",
        "%Y%m%d",
    ]

    for candidate in [sanitized, cleaned]:
        for fmt in date_formats:
            try:
                dt = datetime.strptime(candidate, fmt)
                # Sanity check: year must be reasonable
                if 1980 <= dt.year <= 2100:
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue

    # Fallback: extract 4-digit year and month/day if regex matches
    iso_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", cleaned)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    dmy_match = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", cleaned)
    if dmy_match:
        d, m, y = dmy_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    return cleaned


def normalize_price(value: Any) -> Optional[float]:
    """
    Extract numeric price as float from currency strings.
    Examples: 'RM 198.00' -> 198.0, 'Rs. 28,500' -> 28500.0, '$1,299.99' -> 1299.99
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if s.lower() in NULL_LIKE_STRINGS:
        return None

    # First strip currency prefix words like "Rs.", "RM", "INR", "USD", "$", "€", "£", etc.
    s = re.sub(r"^[^\d]+", "", s)
    # Strip trailing currency words or non-digits
    s = re.sub(r"[^\d]+$", "", s)

    # Strip any remaining characters except digits, commas, dots
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None

    # Handle comma as thousands separator vs decimal separator
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # European format: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # Standard format: 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        # Check if comma is decimal (e.g. 198,50) or thousands (e.g. 28,500)
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        val = float(s)
        return round(val, 2)
    except ValueError:
        return None


def normalize_model_number(value: Any) -> Optional[str]:
    """
    Strip whitespace, uppercase, remove hyphens, dots, slashes.
    Ensures 'T75-SKSF1Z', 'T75.SKSF1Z' and 't75sksf1z' match deterministically.
    """
    cleaned = clean_str(value)
    if not cleaned:
        return None
    normalized = re.sub(r"[\s\-\./_]+", "", cleaned.upper())
    return normalized if normalized else None


def normalize_serial_number(value: Any) -> Optional[str]:
    """
    Strip internal whitespace, uppercase.
    Preserves meaningful dashes while removing accidental spaces.
    """
    cleaned = clean_str(value)
    if not cleaned:
        return None
    normalized = re.sub(r"\s+", "", cleaned.upper())
    return normalized if normalized else None


def normalize_seller_name(value: Any) -> Optional[str]:
    """
    Lowercase, remove common business and corporate suffixes so
    'Best Electrical Store Sdn Bhd' matches 'Best Electrical Store'.
    """
    cleaned = clean_str(value)
    if not cleaned:
        return None

    text = cleaned.lower()
    suffixes = [
        r"\bsdn\.?\s*bhd\.?\b",
        r"\bpvt\.?\s*ltd\.?\b",
        r"\bpte\.?\s*ltd\.?\b",
        r"\bltd\.?\b",
        r"\bllc\.?\b",
        r"\binc\.?\b",
        r"\bcorp\.?\b",
        r"\bco\.?\b",
        r"\benterprise\b",
        r"\bretail\b",
    ]
    for suffix in suffixes:
        text = re.sub(suffix, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def normalize_passport(passport: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply comprehensive normalization to all fields of a Digital Product Passport dictionary.
    """
    if not isinstance(passport, dict):
        return {}

    normalized = dict(passport)

    # String fields
    for field in ["product", "brand", "model", "serial_number", "seller",
                  "category", "customer_name", "order_id", "invoice_number",
                  "warranty", "currency", "document_type"]:
        if field in normalized:
            normalized[field] = normalize_text(normalized[field])

    # Date normalization
    if "purchase_date" in normalized:
        normalized["purchase_date"] = normalize_date(normalized["purchase_date"])

    # Price normalization
    if "purchase_price" in normalized:
        normalized["purchase_price"] = normalize_price(normalized["purchase_price"])

    # Default lists
    if "product_images" not in normalized or not isinstance(normalized["product_images"], list):
        normalized["product_images"] = []
    if "linked_products" not in normalized or not isinstance(normalized["linked_products"], list):
        normalized["linked_products"] = []

    return normalized
