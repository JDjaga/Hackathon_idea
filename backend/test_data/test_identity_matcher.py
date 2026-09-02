"""
Integration Test — Identity Matching + Passport Store

Tests the full flow: add passports to the store, verify identity
matching produces correct new_product / verified / conflict results,
and check the conflict retrieval API.
"""

import sys
import os
import json
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import BASE_DIR
from passport_store import PassportStore
from identity_matcher import match_passport


def run_tests():

    print("=" * 65)
    print("  INTEGRATION TEST — PASSPORT STORE + IDENTITY MATCHING")
    print("=" * 65)

    # Use a temp file so we don't pollute the real store
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".json",
        dir=str(BASE_DIR), mode="w"
    )
    tmp.write("[]")
    tmp.close()

    try:
        store = PassportStore(filename=tmp.name)

        # --- Test 1: First passport is always new_product ---
        print("\n--- Test 1: First Passport → new_product ---")
        result1 = store.add_passport({
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
        })
        assert result1["identity_match"]["status"] == "new_product"
        print(f"  Status: {result1['identity_match']['status']}")
        print(f"  Passport ID: {result1['passport']['passport_id']}")
        print("  ✓ PASSED")

        # --- Test 2: Second scan of same product → verified ---
        print("\n--- Test 2: Second Scan Same Product → verified ---")
        result2 = store.add_passport({
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75SKSF1Z",           # same after normalization
            "serial_number": "LG123456789",
            "purchase_date": "12/08/2026",    # same date, different format
            "seller": "Best Electrical Store Sdn Bhd",
        })
        assert result2["identity_match"]["status"] == "verified"
        print(f"  Status: {result2['identity_match']['status']}")
        print(f"  Matched against: {result2['identity_match']['matched_passport_id']}")
        print(f"  Matched fields: {result2['identity_match']['matched_fields']}")
        print("  ✓ PASSED")

        # --- Test 3: Conflicting serial → conflict ---
        print("\n--- Test 3: Conflicting Serial → conflict ---")
        result3 = store.add_passport({
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75SKSF1Z",
            "serial_number": "LG999888777",  # DIFFERENT serial
            "purchase_date": "2026-08-12",
            "seller": "Best Electrical Store",
        })
        assert result3["identity_match"]["status"] == "conflict"
        print(f"  Status: {result3['identity_match']['status']}")
        print(f"  Conflicts: {result3['identity_match']['conflicting_fields']}")
        print("  ✓ PASSED")

        # --- Test 4: Completely different product → new_product ---
        print("\n--- Test 4: Different Product → new_product ---")
        result4 = store.add_passport({
            "product": "Refrigerator",
            "brand": "Samsung",
            "model": "RT28K3022SE",
            "serial_number": "SAM555666777",
            "purchase_date": "2026-09-01",
            "seller": "Cool Electronics",
        })
        assert result4["identity_match"]["status"] == "new_product"
        print(f"  Status: {result4['identity_match']['status']}")
        print("  ✓ PASSED")

        # --- Test 5: Stats ---
        print("\n--- Test 5: Store Stats ---")
        stats = store.stats()
        print(f"  {stats}")
        assert stats["total_passports"] == 4
        assert stats["conflicts"] == 1
        assert stats["new_products"] == 2
        assert stats["verified_matches"] == 1
        print("  ✓ PASSED")

        # --- Test 6: Get Conflicts ---
        print("\n--- Test 6: Get Conflicts ---")
        conflicts = store.get_conflicts()
        assert len(conflicts) == 1
        print(f"  Found {len(conflicts)} conflict(s)")
        print(f"  Conflict passport: {conflicts[0]['passport_id']}")
        print("  ✓ PASSED")

        # --- Test 7: Search ---
        print("\n--- Test 7: Search ---")
        lg_results = store.search(brand="LG")
        samsung_results = store.search(brand="Samsung")
        assert len(lg_results) == 3
        assert len(samsung_results) == 1
        print(f"  LG passports: {len(lg_results)}")
        print(f"  Samsung passports: {len(samsung_results)}")
        print("  ✓ PASSED")

        print("\n" + "=" * 65)
        print("  ALL INTEGRATION TESTS PASSED")
        print("=" * 65)

    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


if __name__ == "__main__":
    run_tests()
