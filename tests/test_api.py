"""
Integration Tests — FastAPI Endpoints
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("diagnostics", data)

    def test_list_passports(self):
        res = self.client.get("/api/dpp/passports")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("passports", data)

    def test_matcher_compare(self):
        payload = {
            "document_a": {
                "model": "T75-SKSF1Z",
                "serial_number": "LG123456789",
                "purchase_date": "2026-08-12"
            },
            "document_b": {
                "model": "T75SKSF1Z",
                "serial_number": "LG123456789",
                "purchase_date": "12/08/2026"
            }
        }
        res = self.client.post("/api/matcher/compare", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "verified")

    def test_samples_endpoint(self):
        res = self.client.get("/api/samples")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("samples", data)


if __name__ == "__main__":
    unittest.main()
