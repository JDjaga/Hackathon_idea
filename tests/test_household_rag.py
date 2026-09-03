"""
Unit and Integration Tests — HomeMind Household RAG Engine & Ask API
"""

import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.core.household_rag import answer_household_query


class TestHouseholdRAG(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.sample_products = [
            {
                "passport_id": "PP-100",
                "product": "Washing Machine",
                "brand": "LG",
                "model": "T75-SKSF1Z",
                "serial_number": "LG123456789",
                "purchase_date": "2026-01-14",
                "warranty": "2-YEAR",
                "warranty_expiry_date": "2028-01-14",
                "next_maintenance_date": "2027-01-09",
                "purchase_price": 28500.0,
                "currency": "INR",
                "seller": "Best Electrical Store",
                "room": "Utility",
                "health_status": "good"
            },
            {
                "passport_id": "PP-200",
                "product": "Air Conditioner",
                "brand": "Daikin",
                "model": "FTKF35",
                "serial_number": "DK-77541",
                "purchase_date": "2025-10-22",
                "warranty": "1-YEAR",
                "warranty_expiry_date": "2026-10-22",
                "next_maintenance_date": "2026-10-17",
                "purchase_price": 38500.0,
                "currency": "INR",
                "seller": "Cool Comfort",
                "room": "Living Room",
                "health_status": "attention"
            }
        ]

    def test_attention_query(self):
        res = answer_household_query("What needs my attention this month?", self.sample_products)
        self.assertEqual(res["intent"], "attention")
        self.assertIn("Daikin Air Conditioner", res["answer"])
        self.assertGreater(len(res["sources"]), 0)

    def test_warranty_query(self):
        res = answer_household_query("When does my washing machine warranty expire?", self.sample_products)
        self.assertEqual(res["intent"], "warranty_query")
        self.assertIn("2028-01-14", res["answer"])

    def test_room_query(self):
        res = answer_household_query("Which appliances are in the Living Room?", self.sample_products)
        self.assertEqual(res["intent"], "room_query")
        self.assertIn("Daikin Air Conditioner", res["answer"])

    def test_purchase_query(self):
        res = answer_household_query("Show me purchase invoices and prices", self.sample_products)
        self.assertEqual(res["intent"], "purchase_list")
        self.assertIn("28,500.00", res["answer"])

    def test_ask_api_endpoint(self):
        res = self.client.post("/api/ask", json={"query": "When does my AC warranty expire?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertEqual(data["confidence"], "high")

    def test_ask_api_empty_query(self):
        res = self.client.post("/api/ask", json={"query": ""})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
