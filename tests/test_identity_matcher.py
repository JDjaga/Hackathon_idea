"""
Unit Tests — Deterministic Identity Matcher & Conflict Radar
"""

import unittest
from app.core.identity_matcher import (
    levenshtein_distance,
    compare_field,
    score_match,
    match_passport
)


class TestIdentityMatcher(unittest.TestCase):

    def test_levenshtein_distance(self):
        self.assertEqual(levenshtein_distance("LG123456789", "LG123456789"), 0)
        self.assertEqual(levenshtein_distance("LG123456789", "LG123456780"), 1)
        self.assertEqual(levenshtein_distance("ABC", "ABCD"), 1)

    def test_compare_field(self):
        # Model match
        res_model = compare_field("model", "T75-SKSF1Z", "t75sksf1z")
        self.assertTrue(res_model["matches"])

        # Serial fuzzy match
        res_serial = compare_field("serial_number", "LG123456789", "LG123456780", serial_threshold=2)
        self.assertTrue(res_serial["matches"])

        # Seller token match
        res_seller = compare_field("seller", "Best Electrical Store Sdn Bhd", "Best Electrical Store")
        self.assertTrue(res_seller["matches"])

        # Date match
        res_date = compare_field("purchase_date", "12/08/2026", "2026-08-12")
        self.assertTrue(res_date["matches"])

    def test_score_match_verified(self):
        doc_a = {
            "model": "T75-SKSF1Z",
            "serial_number": "LG123456789",
            "purchase_date": "2026-08-12",
            "seller": "Best Electrical Store"
        }
        doc_b = {
            "model": "T75SKSF1Z",
            "serial_number": "LG123456789",
            "purchase_date": "12/08/2026",
            "seller": "Best Electrical Store Sdn Bhd"
        }
        res = score_match(doc_b, doc_a)
        self.assertEqual(len(res["conflicting_fields"]), 0)
        self.assertGreaterEqual(res["score"], 3)

    def test_score_match_conflict(self):
        doc_a = {
            "model": "T75-SKSF1Z",
            "serial_number": "LG123456789",
            "purchase_date": "2026-08-12"
        }
        doc_b = {
            "model": "T75-SKSF1Z",
            "serial_number": "LG999999999", # Conflicting serial
            "purchase_date": "2026-08-12"
        }
        res = score_match(doc_b, doc_a)
        self.assertEqual(len(res["conflicting_fields"]), 1)
        self.assertEqual(res["conflicting_fields"][0]["field"], "serial_number")

    def test_match_passport_against_store(self):
        existing = [
            {
                "passport_id": "PP-001",
                "model": "T75-SKSF1Z",
                "serial_number": "LG123456789",
                "purchase_date": "2026-08-12"
            }
        ]
        candidate = {
            "model": "T75SKSF1Z",
            "serial_number": "LG123456789",
            "purchase_date": "2026-08-12"
        }
        res = match_passport(candidate, existing)
        self.assertEqual(res["status"], "verified")
        self.assertEqual(res["matched_passport_id"], "PP-001")


if __name__ == "__main__":
    unittest.main()
