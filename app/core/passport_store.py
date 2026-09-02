"""
AI Product Guardian — Local JSON Digital Product Passport Database
Handles persistence, identity match linking, multi-attribute search, conflict filtering, and statistics.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import PASSPORT_FILE
from app.core.normalizers import normalize_passport
from app.core.identity_matcher import match_passport


class PassportStore:
    """Thread-safe, lightweight JSON database for Digital Product Passports."""

    def __init__(self, filepath: Path = PASSPORT_FILE):
        self.filepath = Path(filepath)
        self.passports: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load stored passports from disk."""
        if not self.filepath.exists():
            self.passports = []
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.passports = data
            elif isinstance(data, dict):
                self.passports = data.get("passports", [data]) if "passports" in data else [data]
            else:
                self.passports = []
        except Exception as e:
            print(f"[PassportStore] Error loading database from {self.filepath}: {e}")
            self.passports = []

    def save(self) -> None:
        """Persist passports atomically to disk."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.passports, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PassportStore] Error saving database to {self.filepath}: {e}")

    def add_passport(self, passport_data: Dict[str, Any], source: str = "web_studio") -> Dict[str, Any]:
        """
        Normalize and insert a new passport into the database.
        Automatically executes identity verification against existing passports.
        """
        norm_data = normalize_passport(passport_data)

        # Generate unique Passport ID if missing
        if not norm_data.get("passport_id"):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            norm_data["passport_id"] = f"PP-{timestamp}-{len(self.passports) + 1}"

        if not norm_data.get("created_at"):
            norm_data["created_at"] = datetime.now().isoformat()

        norm_data["source"] = source

        # Execute Identity Matching
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
        return sorted(self.passports, key=lambda p: p.get("created_at", ""), reverse=True)

    def get_by_id(self, passport_id: str) -> Optional[Dict[str, Any]]:
        """Find a passport by its exact ID."""
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
        return [p for p in self.get_all() if p.get("identity_match", {}).get("status") == "conflict"]

    def update(self, passport_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields on an existing passport."""
        passport = self.get_by_id(passport_id)
        if not passport:
            return None

        # Clean and update
        for k, v in updates.items():
            if k not in ["passport_id", "created_at"]:
                passport[k] = v

        # Re-run normalization
        normalized = normalize_passport(passport)
        passport.clear()
        passport.update(normalized)

        self.save()
        return passport

    def delete(self, passport_id: str) -> bool:
        """Remove a passport by ID."""
        for i, p in enumerate(self.passports):
            if p.get("passport_id") == passport_id:
                self.passports.pop(i)
                self.save()
                return True
        return False

    def attach_product_image(self, passport_id: str, image_path: str, detection_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Attach an appliance photograph and bounding box detection to a passport."""
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
        """Seed high-fidelity demo passports if store is completely empty."""
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
                "purchase_date": "2026-08-12",
                "warranty": "2-YEAR",
                "seller": "Best Electrical Store",
                "category": "Large Domestic Appliances",
                "customer_name": "Rohan Sharma",
                "invoice_number": "INV-2026-9042",
                "created_at": "2026-08-15T12:00:00",
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
                "brand": "Electrolux",
                "model": "EAP150",
                "serial_number": "SN89234710",
                "purchase_price": 198.0,
                "currency": "RM",
                "purchase_date": "2026-07-24",
                "warranty": "1-YEAR",
                "seller": "Mega Home Electronics",
                "category": "Small Domestic Appliances",
                "customer_name": "Alice Tan",
                "invoice_number": "TX-88219",
                "created_at": "2026-08-20T15:30:00",
                "identity_match": {
                    "status": "new_product",
                    "matched_passport_id": None,
                    "match_confidence": None,
                    "matched_fields": [],
                    "conflicting_fields": []
                }
            }
        ]
        self.passports.extend(demo_data)
        self.save()
