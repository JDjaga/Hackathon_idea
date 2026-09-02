"""
HomeMind — Data Normalizers
Robust, deterministic sanitizers and formatters for text, dates, prices, models, serial numbers,
sellers, warranty durations, and maintenance schedules.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from app.config import WARRANTY_DURATION_MAP, DEFAULT_MAINTENANCE_INTERVALS, HEALTH_URGENT_DAYS, HEALTH_ATTENTION_DAYS

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


# ============================================================
# WARRANTY & MAINTENANCE INTELLIGENCE
# ============================================================

def parse_warranty_duration(warranty_str: Any) -> Optional[int]:
    """
    Parse a warranty string into days.
    Examples: '2-YEAR' -> 730, '6 months' -> 180, '1 Year Comprehensive' -> 365
    """
    if warranty_str is None:
        return None
    s = str(warranty_str).upper().strip()
    if not s or s.lower() in NULL_LIKE_STRINGS:
        return None

    # Direct lookup
    if s in WARRANTY_DURATION_MAP:
        return WARRANTY_DURATION_MAP[s]

    # Extract number + unit pattern
    match = re.search(r"(\d+)\s*[-\s]?\s*(YEAR|MONTH|DAY)S?", s, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        unit = match.group(2).upper()
        if unit == "YEAR":
            return num * 365
        elif unit == "MONTH":
            return num * 30
        elif unit == "DAY":
            return num

    # Try just a number (assume years if ≤10, else days)
    num_match = re.search(r"(\d+)", s)
    if num_match:
        num = int(num_match.group(1))
        if num <= 10:
            return num * 365
        return num

    return None


def compute_expiry_date(purchase_date_str: Optional[str], warranty_str: Optional[str]) -> Optional[str]:
    """
    Compute warranty expiry date from purchase date and warranty duration.
    Returns ISO date string or None.
    """
    if not purchase_date_str or not warranty_str:
        return None

    duration_days = parse_warranty_duration(warranty_str)
    if not duration_days:
        return None

    norm_date = normalize_date(purchase_date_str)
    if not norm_date:
        return None

    try:
        purchase_dt = datetime.strptime(norm_date, "%Y-%m-%d")
        expiry_dt = purchase_dt + timedelta(days=duration_days)
        return expiry_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def compute_next_maintenance(purchase_date_str: Optional[str], interval_days: Optional[int] = None, product_name: Optional[str] = None) -> Optional[str]:
    """
    Compute next maintenance date based on purchase date and interval.
    If interval_days is not provided, uses DEFAULT_MAINTENANCE_INTERVALS by product name.
    Returns the next future maintenance date as ISO string.
    """
    if not purchase_date_str:
        return None

    if interval_days is None and product_name:
        for key, days in DEFAULT_MAINTENANCE_INTERVALS.items():
            if key.lower() in str(product_name).lower():
                interval_days = days
                break

    if not interval_days:
        return None

    norm_date = normalize_date(purchase_date_str)
    if not norm_date:
        return None

    try:
        purchase_dt = datetime.strptime(norm_date, "%Y-%m-%d")
        today = datetime.now()
        next_date = purchase_dt + timedelta(days=interval_days)

        # Fast-forward to the next future maintenance date
        while next_date < today:
            next_date += timedelta(days=interval_days)

        return next_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def compute_health_status(warranty_expiry: Optional[str], next_maintenance: Optional[str]) -> str:
    """
    Compute product health status based on warranty expiry and maintenance schedule.
    Returns: 'expired', 'urgent', 'attention', 'good'
    """
    today = datetime.now()
    status = "good"

    if warranty_expiry:
        try:
            expiry_dt = datetime.strptime(warranty_expiry, "%Y-%m-%d")
            days_until = (expiry_dt - today).days
            if days_until < 0:
                return "expired"
            elif days_until <= HEALTH_URGENT_DAYS:
                status = "urgent"
            elif days_until <= HEALTH_ATTENTION_DAYS:
                status = "attention"
        except (ValueError, TypeError):
            pass

    if next_maintenance and status == "good":
        try:
            maint_dt = datetime.strptime(next_maintenance, "%Y-%m-%d")
            days_until = (maint_dt - today).days
            if days_until <= 0:
                status = "urgent"
            elif days_until <= 14:
                status = "attention"
        except (ValueError, TypeError):
            pass

    return status


# ============================================================
# PASSPORT NORMALIZER
# ============================================================

def normalize_passport(passport: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply comprehensive normalization to all fields of a Digital Product Passport dictionary.
    Auto-computes warranty expiry, next maintenance, and health status.
    """
    if not isinstance(passport, dict):
        return {}

    normalized = dict(passport)

    # String fields
    for field in ["product", "brand", "model", "serial_number", "seller",
                  "category", "customer_name", "order_id", "invoice_number",
                  "warranty", "currency", "document_type", "room"]:
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
    if "linked_documents" not in normalized or not isinstance(normalized["linked_documents"], list):
        normalized["linked_documents"] = []
    if "events" not in normalized or not isinstance(normalized["events"], list):
        normalized["events"] = []

    # Remove legacy field
    normalized.pop("linked_products", None)

    # Auto-compute warranty expiry
    if normalized.get("purchase_date") and normalized.get("warranty"):
        computed_expiry = compute_expiry_date(normalized["purchase_date"], normalized["warranty"])
        if computed_expiry:
            normalized["warranty_expiry_date"] = computed_expiry

    # Auto-compute next maintenance date
    if normalized.get("purchase_date"):
        interval = normalized.get("maintenance_interval_days")
        product_name = normalized.get("product")
        computed_maint = compute_next_maintenance(
            normalized["purchase_date"],
            interval_days=interval,
            product_name=product_name
        )
        if computed_maint:
            normalized["next_maintenance_date"] = computed_maint
        # Store the interval if it was auto-detected
        if not interval and product_name:
            for key, days in DEFAULT_MAINTENANCE_INTERVALS.items():
                if key.lower() in str(product_name).lower():
                    normalized["maintenance_interval_days"] = days
                    break

    # Auto-compute health status
    normalized["health_status"] = compute_health_status(
        normalized.get("warranty_expiry_date"),
        normalized.get("next_maintenance_date")
    )

    return normalized

