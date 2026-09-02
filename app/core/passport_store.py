"""
AI Product Guardian — Local JSON Digital Product Passport Database
Handles persistence, atomic crash-safe writes, identity match linking,
multi-attribute search, conflict filtering, and statistics.
"""

import os
import json
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import PASSPORT_FILE
from app.core.normalizers import normalize_passport
from app.core.identity_matcher import match_passport


class PassportStore:
    """Thread-safe, atomic-write JSON database for Digital Product Passports."""

    def __init__(self, filepath: Path = PASSPORT_FILE):
        self.filepath = Path(filepath)
        self.passports: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._last_mtime: float = 0.0
        self.load()

    def load(self) -> None:
        """Load stored passports from disk with thread-safety."""
        with self._lock:
            if not self.filepath.exists():
                self.passports = []
                self._last_mtime = 0.0
                return

            try:
                mtime = os.path.getmtime(self.filepath)
                if mtime == self._last_mtime and self.passports:
                    return  # Cache is still fresh

                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    self.passports = data
                elif isinstance(data, dict):
                    self.passports = data.get("passports", [data]) if "passports" in data else [data]
                else:
                    self.passports = []
                self._last_mtime = mtime
            except Exception as e:
                print(f"[PassportStore] Error loading database from {self.filepath}: {e}")
                self.passports = []

    def _sync(self) -> None:
        """Reload from disk if file was updated externally."""
        if self.filepath.exists():
            try:
                mtime = os.path.getmtime(self.filepath)
                if mtime != self._last_mtime:
                    self.load()
            except Exception:
                pass

    def save(self) -> None:
        """Persist passports atomically to disk to prevent corruption on crash."""
        with self._lock:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = None
            try:
                # Write to temp file first in the same directory (required for atomic os.replace)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=str(self.filepath.parent),
                    delete=False,
                    suffix=".tmp",
                    encoding="utf-8"
                ) as tmp:
                    tmp_file = tmp.name
                    json.dump(self.passports, tmp, indent=2, ensure_ascii=False)
                    tmp.flush()
                    os.fsync(tmp.fileno())

                # Atomic replace
                os.replace(tmp_file, self.filepath)
                self._last_mtime = os.path.getmtime(self.filepath)
            except Exception as e:
                print(f"[PassportStore] Error saving database to {self.filepath}: {e}")
                if tmp_file and os.path.exists(tmp_file):
                    try:
                        os.unlink(tmp_file)
                    except Exception:
                        pass

    def add_passport(self, passport_data: Dict[str, Any], source: str = "web_studio") -> Dict[str, Any]:
        """
        Normalize and insert a new passport into the database.
        Automatically executes identity verification against existing passports.
        """
        with self._lock:
            self._sync()
            norm_data = normalize_passport(passport_data)

            # Generate unique Passport ID if missing
            if not norm_data.get("passport_id"):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                norm_data["passport_id"] = f"PP-{timestamp}-{len(self.passports) + 1}"

            if not norm_data.get("created_at"):
                norm_data["created_at"] = datetime.now().isoformat()

            norm_data["source"] = source

            # Execute Identity Matching against existing store
            match_result = match_passport(norm_data, self.passports)
            norm_data["identity_match"] = match_result

            self.passports.append(norm_data)
            self.save()

            return {
                "passport": norm_data,
                "identity_match": match_result
            }

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all stored passports in reverse chronological order."""
        with self._lock:
            self._sync()
            return sorted(self.passports, key=lambda p: p.get("created_at", ""), reverse=True)

    def get_by_id(self, passport_id: str) -> Optional[Dict[str, Any]]:
        """Find a passport by its exact ID."""
        with self._lock:
            self._sync()
            for p in self.passports:
                if p.get("passport_id") == passport_id:
                    return p
            return None

    def search(
        self,
        query: Optional[str] = None,
        product: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter passports across multiple attributes and free-text queries."""
        with self._lock:
            self._sync()
            results = []
            q = query.lower().strip() if query else None

            for p in self.get_all():
                if status and p.get("identity_match", {}).get("status") != status:
                    continue

                if product and product.lower() not in str(p.get("product", "")).lower():
                    continue

                if brand and brand.lower() not in str(p.get("brand", "")).lower():
                    continue

                if model and model.lower() not in str(p.get("model", "")).lower():
                    continue

                if q:
                    searchable_text = f"{p.get('product', '')} {p.get('brand', '')} {p.get('model', '')} {p.get('serial_number', '')} {p.get('seller', '')} {p.get('passport_id', '')}".lower()
                    if q not in searchable_text:
                        continue

                results.append(p)
            return results

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Retrieve all passports with flagged identity conflicts."""
        with self._lock:
            self._sync()
            return [p for p in self.get_all() if p.get("identity_match", {}).get("status") == "conflict"]

    def update(self, passport_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields on an existing passport."""
        with self._lock:
            self._sync()
            passport = self.get_by_id(passport_id)
            if not passport:
                return None

            for k, v in updates.items():
                if k not in ["passport_id", "created_at"]:
                    passport[k] = v

            normalized = normalize_passport(passport)
            passport.clear()
            passport.update(normalized)

            self.save()
            return passport

    def delete(self, passport_id: str) -> bool:
        """Remove a passport by ID."""
        with self._lock:
            self._sync()
            for i, p in enumerate(self.passports):
                if p.get("passport_id") == passport_id:
                    self.passports.pop(i)
                    self.save()
                    return True
            return False

    def attach_product_image(self, passport_id: str, image_path: str, detection_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Attach an appliance photograph and bounding box detection to a passport."""
        with self._lock:
            self._sync()
            passport = self.get_by_id(passport_id)
            if not passport:
                return None

            if "product_images" not in passport:
                passport["product_images"] = []

            passport["product_images"].append({
                "image_path": str(image_path),
                "attached_at": datetime.now().isoformat(),
                "detection": detection_info or {}
            })
            self.save()
            return passport

    def stats(self) -> Dict[str, Any]:
        """Compute aggregate registry statistics."""
        with self._lock:
            self._sync()
            total = len(self.passports)
            conflicts = len(self.get_conflicts())
            verified = sum(1 for p in self.passports if p.get("identity_match", {}).get("status") == "verified")
            new_products = sum(1 for p in self.passports if p.get("identity_match", {}).get("status") == "new_product")

            brands = set(p.get("brand") for p in self.passports if p.get("brand"))
            categories = set(p.get("category") or p.get("product") for p in self.passports if p.get("category") or p.get("product"))

            return {
                "total_passports": total,
                "verified_matches": verified,
                "conflicts": conflicts,
                "new_products": new_products,
                "unique_brands": len(brands),
                "unique_categories": len(categories)
            }

    def seed_demo_passports(self) -> None:
        """Seed high-fidelity HomeMind demo products if store is completely empty."""
        with self._lock:
            self._sync()
            if self.passports:
                return

            demo_data = [
                {
                    "passport_id": "PP-20260815120000-1",
                    "document_type": "warranty_card",
                    "product": "Washing Machine",
                    "brand": "LG",
                    "model": "T75-SKSF1Z",
                    "serial_number": "LG123456789",
                    "purchase_price": 28500.0,
                    "currency": "INR",
                    "purchase_date": "2026-01-14",
                    "warranty": "2-YEAR",
                    "seller": "Best Electrical Store",
                    "category": "Large Domestic Appliances",
                    "customer_name": "Rohan Sharma",
                    "invoice_number": "INV-2026-9042",
                    "room": "Utility",
                    "created_at": "2026-08-15T12:00:00",
                    "linked_documents": [
                        {"type": "warranty_card", "source": "camera_scan", "extracted_at": "2026-08-15T12:00:00", "snippet": "LG Warranty Certificate - 2 Year Comprehensive"},
                        {"type": "invoice", "source": "camera_scan", "extracted_at": "2026-08-15T12:05:00", "snippet": "Tax Invoice INV-2026-9042 Best Electrical Store"}
                    ],
                    "events": [
                        {"type": "purchase", "date": "2026-01-14", "description": "Purchased from Best Electrical Store"},
                        {"type": "installation", "date": "2026-01-18", "description": "Professional installation completed"},
                        {"type": "service", "date": "2026-07-15", "description": "Routine maintenance — drum cleaning and filter check"}
                    ],
                    "identity_match": {
                        "status": "new_product",
                        "matched_passport_id": None,
                        "match_confidence": None,
                        "matched_fields": [],
                        "conflicting_fields": []
                    }
                },
                {
                    "passport_id": "PP-20260820153000-2",
                    "document_type": "tax_invoice",
                    "product": "Air Purifier",
                    "brand": "Philips",
                    "model": "AC3059-65",
                    "serial_number": "PH89234710",
                    "purchase_price": 22990.0,
                    "currency": "INR",
                    "purchase_date": "2026-06-10",
                    "warranty": "2-YEAR",
                    "seller": "Croma Electronics",
                    "category": "Small Domestic Appliances",
                    "customer_name": "Rohan Sharma",
                    "invoice_number": "CR-INV-88219",
                    "room": "Bedroom",
                    "created_at": "2026-08-20T15:30:00",
                    "linked_documents": [
                        {"type": "invoice", "source": "camera_scan", "extracted_at": "2026-08-20T15:30:00", "snippet": "Croma Tax Invoice CR-INV-88219 Philips Air Purifier"}
                    ],
                    "events": [
                        {"type": "purchase", "date": "2026-06-10", "description": "Purchased from Croma Electronics"},
                        {"type": "consumable", "date": "2026-09-10", "description": "HEPA filter replacement due (every 90 days)"}
                    ],
                    "identity_match": {
                        "status": "new_product",
                        "matched_passport_id": None,
                        "match_confidence": None,
                        "matched_fields": [],
                        "conflicting_fields": []
                    }
                },
                {
                    "passport_id": "PP-20260901100000-3",
                    "document_type": "warranty_card",
                    "product": "Air Conditioner",
                    "brand": "Daikin",
                    "model": "FTKF35UV16V",
                    "serial_number": "DK-2026-77541",
                    "purchase_price": 38500.0,
                    "currency": "INR",
                    "purchase_date": "2025-10-22",
                    "warranty": "1-YEAR",
                    "seller": "Cool Comfort Appliances",
                    "category": "HVAC",
                    "customer_name": "Rohan Sharma",
                    "invoice_number": "CC-7821",
                    "room": "Living Room",
                    "created_at": "2026-09-01T10:00:00",
                    "linked_documents": [
                        {"type": "warranty_card", "source": "camera_scan", "extracted_at": "2026-09-01T10:00:00", "snippet": "Daikin 1 Year Warranty FTKF35UV16V"},
                        {"type": "invoice", "source": "camera_scan", "extracted_at": "2026-09-01T10:02:00", "snippet": "Cool Comfort Appliances Tax Invoice CC-7821"},
                        {"type": "manual", "source": "upload", "extracted_at": "2026-09-01T10:05:00", "snippet": "Daikin Installation & Operation Manual"}
                    ],
                    "events": [
                        {"type": "purchase", "date": "2025-10-22", "description": "Purchased from Cool Comfort Appliances"},
                        {"type": "installation", "date": "2025-10-25", "description": "Professional installation with copper piping"},
                        {"type": "service", "date": "2026-04-15", "description": "Gas recharge and coil cleaning"},
                        {"type": "service", "date": "2026-07-20", "description": "Filter cleaning and performance check"}
                    ],
                    "identity_match": {
                        "status": "new_product",
                        "matched_passport_id": None,
                        "match_confidence": None,
                        "matched_fields": [],
                        "conflicting_fields": []
                    }
                }
            ]

            # Normalize each demo passport (auto-computes warranty expiry, health, maintenance)
            from app.core.normalizers import normalize_passport
            for d in demo_data:
                normalized = normalize_passport(d)
                d.update(normalized)

            self.passports.extend(demo_data)
            self.save()


# Singleton Instance Factory
_DEFAULT_STORE: Optional[PassportStore] = None

def get_passport_store() -> PassportStore:
    """Provide a thread-safe singleton store instance for all API routers."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = PassportStore()
    return _DEFAULT_STORE
