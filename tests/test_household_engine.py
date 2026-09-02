"""
Unit and Integration Tests — HomeMind Household Intelligence Engine
Tests health computation, attention sorting, room grouping, timeline,
warranty claim pack generation, and household API endpoints.
"""

import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.core.household_engine import (
    compute_product_health,
    get_household_attention,
    get_room_inventory,
    get_household_timeline,
    generate_warranty_claim_pack,
    get_household_summary
)


class TestHouseholdIntelligence(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.sample_product = {
            "passport_id": "TEST-PP-01",
            "product": "Air Conditioner",
            "brand": "Daikin",
            "model": "FTKF35",
            "serial_number": "DK12345",
            "purchase_date": "2025-10-22",
            "warranty": "1-YEAR",
            "warranty_expiry_date": "2026-10-22",
            "next_maintenance_date": "2026-10-17",
            "purchase_price": 38500.0,
            "currency": "INR",
            "seller": "Cool Comfort",
            "room": "Living Room",
            "health_status": "attention",
            "linked_documents": [
                {"type": "warranty_card", "snippet": "Daikin 1 Year Warranty"}
            ],
            "events": [
                {"type": "purchase", "date": "2025-10-22", "description": "Purchased"},
                {"type": "service", "date": "2026-04-15", "description": "Gas recharge"}
            ]
        }

    def test_compute_product_health(self):
        health = compute_product_health(self.sample_product)
        self.assertEqual(health["passport_id"], "TEST-PP-01")
        self.assertEqual(health["room"], "Living Room")
        self.assertIn("days_until_expiry", health)
        self.assertGreater(len(health["alerts"]), 0)

    def test_household_attention(self):
        attention = get_household_attention([self.sample_product])
        self.assertEqual(len(attention), 1)
        self.assertEqual(attention[0]["product_health"]["passport_id"], "TEST-PP-01")

    def test_room_inventory(self):
        inventory = get_room_inventory([self.sample_product])
        self.assertIn("Living Room", inventory)
        self.assertEqual(len(inventory["Living Room"]), 1)

    def test_household_timeline(self):
        timeline = get_household_timeline([self.sample_product], days_ahead=90)
        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 0)

    def test_warranty_claim_pack(self):
        pack = generate_warranty_claim_pack(self.sample_product)
        self.assertEqual(pack["claim_pack_type"], "warranty_claim")
        self.assertEqual(pack["product"]["brand"], "Daikin")
        self.assertEqual(pack["warranty"]["status"], "active")
        self.assertEqual(len(pack["linked_documents"]), 1)
        self.assertEqual(len(pack["service_history"]), 1)

    def test_household_summary(self):
        summary = get_household_summary([self.sample_product])
        self.assertEqual(summary["total_products"], 1)
        self.assertIn("rooms", summary)
        self.assertEqual(summary["total_household_value"], 38500.0)

    def test_api_household_health(self):
        res = self.client.get("/api/household/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_products", data)
        self.assertIn("health_distribution", data)

    def test_api_household_attention(self):
        res = self.client.get("/api/household/attention")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)

    def test_api_household_rooms(self):
        res = self.client.get("/api/household/rooms")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("rooms", data)

    def test_api_household_timeline(self):
        res = self.client.get("/api/household/timeline")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("timeline", data)

    def test_api_rooms_list(self):
        res = self.client.get("/api/rooms")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("rooms", data)
        self.assertIn("Kitchen", data["rooms"])


if __name__ == "__main__":
    unittest.main()
