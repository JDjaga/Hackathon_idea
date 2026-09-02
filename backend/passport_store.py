"""
Passport Store — Local JSON Database with Identity Matching
AI Product Guardian

Stores Digital Product Passports in a local JSON file.
Integrates with identity_matcher to automatically check for
matching/conflicting passports on insertion.
"""

import json
from pathlib import Path
from datetime import datetime

from config import PASSPORT_FILE
from identity_matcher import match_passport


# ============================================================
# STORE
# ============================================================

class PassportStore:

    def __init__(self, filename=PASSPORT_FILE):

        self.filename = Path(filename)
        self.passports = []
        self.load()

    # ========================================================
    # LOAD
    # ========================================================

    def load(self):

        if not self.filename.exists():
            self.passports = []
            return

        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                # Old single-passport format or wrapped format
                if "passports" in data and isinstance(data["passports"], list):
                    self.passports = data["passports"]
                else:
                    self.passports = [data]

            elif isinstance(data, list):
                self.passports = data

            else:
                self.passports = []

        except Exception as e:
            print(f"Passport database error: {e}")
            self.passports = []

    # ========================================================
    # SAVE
    # ========================================================

    def save(self):

        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(
                self.passports,
                f,
                indent=4,
                ensure_ascii=False
            )

    # ========================================================
    # ADD PASSPORT (with identity matching)
    # ========================================================

    def add_passport(self, passport, source="backend_bridge"):
        """
        Add a passport to the store. Automatically runs identity
        matching against all existing passports before insertion.

        Returns:
          {
            "passport": <the stored passport dict>,
            "identity_match": <match result from identity_matcher>
          }
        """

        passport = dict(passport)

        # Generate passport ID if missing
        if "passport_id" not in passport:
            passport["passport_id"] = (
                f"PP-"
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}-"
                f"{len(self.passports) + 1}"
            )

        # Set source
        if "source" not in passport:
            passport["source"] = source

        # Ensure structural fields exist
        if "product_images" not in passport:
            passport["product_images"] = []
        if "linked_products" not in passport:
            passport["linked_products"] = []
        if "created_at" not in passport:
            passport["created_at"] = datetime.now().isoformat()

        # --- IDENTITY MATCHING (hero feature) ---
        match_result = match_passport(
            new_passport=passport,
            existing_passports=self.passports
        )

        passport["identity_match"] = match_result

        # Store the passport
        self.passports.append(passport)
        self.save()

        return {
            "passport": passport,
            "identity_match": match_result
        }

    # ========================================================
    # GET ALL
    # ========================================================

    def get_all(self):
        return self.passports

    # ========================================================
    # FIND BY ID
    # ========================================================

    def get_by_id(self, passport_id):

        for passport in self.passports:
            if passport.get("passport_id") == passport_id:
                return passport
        return None

    # ========================================================
    # SEARCH BY PRODUCT
    # ========================================================

    def search(self, product=None, brand=None, model=None):
        """Search passports by product name, brand, or model."""
        results = []
        for passport in self.passports:
            if product and product.lower() in str(passport.get("product", "")).lower():
                results.append(passport)
            elif brand and brand.lower() in str(passport.get("brand", "")).lower():
                results.append(passport)
            elif model and model.lower() in str(passport.get("model", "")).lower():
                results.append(passport)
        return results

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self, passport_id, updates):

        passport = self.get_by_id(passport_id)
        if passport is None:
            return None
        passport.update(updates)
        self.save()
        return passport

    # ========================================================
    # DELETE
    # ========================================================

    def delete(self, passport_id):
        """Delete a passport by ID. Returns True if deleted."""
        for i, passport in enumerate(self.passports):
            if passport.get("passport_id") == passport_id:
                self.passports.pop(i)
                self.save()
                return True
        return False

    # ========================================================
    # GET CONFLICTS
    # ========================================================

    def get_conflicts(self):
        """Return all passports that have identity conflicts."""
        conflicts = []
        for passport in self.passports:
            match_info = passport.get("identity_match", {})
            if match_info.get("status") == "conflict":
                conflicts.append(passport)
        return conflicts

    # ========================================================
    # ADD PRODUCT IMAGE
    # ========================================================

    def attach_product_image(self, passport_id, image_path, detection_info=None):

        passport = self.get_by_id(passport_id)
        if passport is None:
            return None

        if "product_images" not in passport:
            passport["product_images"] = []

        image_record = {
            "image_path": str(image_path),
            "attached_at": datetime.now().isoformat(),
            "detection": detection_info or {}
        }

        passport["product_images"].append(image_record)
        self.save()
        return passport

    # ========================================================
    # LINK DETECTION
    # ========================================================

    def link_detection(self, passport_id, detection_info):

        passport = self.get_by_id(passport_id)
        if passport is None:
            return None

        if "linked_products" not in passport:
            passport["linked_products"] = []

        passport["linked_products"].append(detection_info)
        self.save()
        return passport

    # ========================================================
    # STATS
    # ========================================================

    def stats(self):
        """Return summary statistics about the passport store."""
        total = len(self.passports)
        conflicts = len(self.get_conflicts())
        verified = sum(
            1 for p in self.passports
            if p.get("identity_match", {}).get("status") == "verified"
        )
        new_products = sum(
            1 for p in self.passports
            if p.get("identity_match", {}).get("status") == "new_product"
        )
        return {
            "total_passports": total,
            "new_products": new_products,
            "verified_matches": verified,
            "conflicts": conflicts
        }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    store = PassportStore()

    print(f"Passports loaded: {len(store.get_all())}")
    print(f"Stats: {store.stats()}")

    for passport in store.get_all():
        match_info = passport.get("identity_match", {})
        print(
            f"  {passport.get('passport_id', 'NO-ID')} | "
            f"{passport.get('product', 'Unknown')} | "
            f"{passport.get('brand', 'Unknown')} | "
            f"Status: {match_info.get('status', 'N/A')}"
        )