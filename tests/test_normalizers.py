"""
Unit Tests — Data Normalizers
"""

import unittest
from app.core.normalizers import (
    normalize_date,
    normalize_price,
    normalize_model_number,
    normalize_serial_number,
    normalize_seller_name,
    normalize_passport
)


class TestNormalizers(unittest.TestCase):

    def test_normalize_date_formats(self):
        self.assertEqual(normalize_date("2026-08-12"), "2026-08-12")
        self.assertEqual(normalize_date("12/08/2026"), "2026-08-12")
        self.assertEqual(normalize_date("12.08.2026"), "2026-08-12")
        self.assertEqual(normalize_date("12th August 2026"), "2026-08-12")
        self.assertEqual(normalize_date("August 12, 2026"), "2026-08-12")
        self.assertEqual(normalize_date("1st Jan 2025"), "2025-01-01")
        self.assertIsNone(normalize_date("N/A"))
        self.assertIsNone(normalize_date(None))

    def test_normalize_price(self):
        self.assertEqual(normalize_price("28,500.00"), 28500.0)
        self.assertEqual(normalize_price("RM 198.50"), 198.50)
        self.assertEqual(normalize_price("INR 28500"), 28500.0)
        self.assertEqual(normalize_price("$1,299.99"), 1299.99)
        self.assertEqual(normalize_price(500), 500.0)
        self.assertIsNone(normalize_price("unknown"))
        self.assertIsNone(normalize_price(None))

    def test_normalize_model_number(self):
        self.assertEqual(normalize_model_number("T75-SKSF1Z"), "T75SKSF1Z")
        self.assertEqual(normalize_model_number("t75.sksf1z"), "T75SKSF1Z")
        self.assertEqual(normalize_model_number(" EAP 150 "), "EAP150")
        self.assertIsNone(normalize_model_number(""))
        self.assertIsNone(normalize_model_number("null"))

    def test_normalize_serial_number(self):
        self.assertEqual(normalize_serial_number(" lg 123456789 "), "LG123456789")
        self.assertEqual(normalize_serial_number("SN-89234-710"), "SN-89234-710")

    def test_normalize_seller_name(self):
        self.assertEqual(normalize_seller_name("Best Electrical Store Sdn Bhd"), "best electrical store")
        self.assertEqual(normalize_seller_name("Mega Electronics Pvt Ltd"), "mega electronics")
        self.assertEqual(normalize_seller_name("Cool Tech LLC"), "cool tech")

    def test_normalize_passport(self):
        raw = {
            "product": " Washing Machine ",
            "brand": "LG",
            "model": "T75-SKSF1Z",
            "serial_number": " LG123456 ",
            "purchase_price": "Rs. 28,500",
            "purchase_date": "12/08/2026",
            "seller": "Best Store Sdn Bhd"
        }
        res = normalize_passport(raw)
        self.assertEqual(res["product"], "Washing Machine")
        self.assertEqual(res["purchase_price"], 28500.0)
        self.assertEqual(res["purchase_date"], "2026-08-12")


if __name__ == "__main__":
    unittest.main()
