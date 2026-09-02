"""
Unit Tests — Passport Store Persistence & Queries
"""

import unittest
import tempfile
from pathlib import Path
from app.core.passport_store import PassportStore


class TestPassportStore(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.write(b"[]")
        self.temp_file.close()
        self.store = PassportStore(filepath=Path(self.temp_file.name))

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_add_and_get_passport(self):
        passport = {
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75-SKSF1Z",
            "serial_number": "LG123456789"
        }
        res = self.store.add_passport(passport)
        self.assertEqual(res["identity_match"]["status"], "new_product")
        p_id = res["passport"]["passport_id"]

        fetched = self.store.get_by_id(p_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["model"], "T75-SKSF1Z")

    def test_search_passports(self):
        self.store.add_passport({"product": "Microwave", "brand": "Samsung", "model": "MS23K"})
        self.store.add_passport({"product": "Refrigerator", "brand": "LG", "model": "GL-B201"})

        results = self.store.search(brand="Samsung")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["model"], "MS23K")

    def test_stats(self):
        self.store.add_passport({"product": "Microwave", "brand": "Samsung"})
        stats = self.store.stats()
        self.assertEqual(stats["total_passports"], 1)


if __name__ == "__main__":
    unittest.main()
