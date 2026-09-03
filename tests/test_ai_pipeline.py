"""
AI pipeline tests — honest extraction, Ask grounding, household match, path sandbox.
"""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.dpp_extractor import fallback_ocr_extractor, is_usable_passport, extraction_confidence
from app.core.household_rag import answer_household_query
from app.core.household_match import match_label_to_products, build_product_graph
from app.core.io_utils import resolve_sample_path
from app.main import app


class TestHonestExtraction(unittest.TestCase):

    def test_generic_ocr_does_not_invent_serial_or_price(self):
        with tempfile.NamedTemporaryFile(suffix="_live_scan.jpg", delete=False) as tmp:
            path = tmp.name
        try:
            result = fallback_ocr_extractor(path, {"text": "Thank you for shopping with us today."})
            self.assertEqual(result, [])
        finally:
            os.unlink(path)

    def test_ocr_extracts_only_present_fields(self):
        with tempfile.NamedTemporaryFile(suffix="_live_scan.jpg", delete=False) as tmp:
            path = tmp.name
        try:
            ocr = {"text": "Brand LG Model T75-SKSF1Z Serial SN: LG123456789"}
            result = fallback_ocr_extractor(path, ocr)
            self.assertEqual(len(result), 1)
            p = result[0]
            self.assertTrue(is_usable_passport(p))
            self.assertEqual(p.get("brand"), "LG")
            self.assertIn("T75", p.get("model") or "")
            self.assertIsNone(p.get("purchase_price"))
            self.assertNotEqual(p.get("serial_number"), "GEN-2026")
            self.assertIn(extraction_confidence(p), ("medium", "high", "low"))
        finally:
            os.unlink(path)

    def test_sample_fixture_filename(self):
        fake = str(Path("sample_warranty_1.png"))
        result = fallback_ocr_extractor(fake, {"text": ""})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].get("brand"), "LG")
        self.assertEqual(result[0].get("serial_number"), "LG123456789")


class TestAskGrounding(unittest.TestCase):

    def test_unknown_does_not_dump_inventory(self):
        products = [{
            "passport_id": "PP-1",
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75",
            "room": "Utility",
        }]
        res = answer_household_query("What is the meaning of life?", products)
        self.assertEqual(res["intent"], "unknown")
        self.assertEqual(res["confidence"], "none")
        self.assertIn("don't know", res["answer"].lower())
        self.assertNotIn("T75", res["answer"])

    def test_purchase_query_includes_header_without_price(self):
        products = [{
            "passport_id": "PP-1",
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75",
            "purchase_date": "2026-01-14",
            "seller": "Store",
        }]
        res = answer_household_query("When did I purchase my washing machine?", products)
        self.assertEqual(res["intent"], "purchase_query")
        self.assertIn("Purchase record", res["answer"])
        self.assertIn("2026-01-14", res["answer"])
        self.assertIn("Price", res["answer"])


class TestHouseholdMatch(unittest.TestCase):

    def test_match_washer_label(self):
        products = [{
            "passport_id": "PP-1",
            "product": "Washing Machine",
            "brand": "LG",
            "model": "T75",
            "room": "Utility",
        }]
        hit = match_label_to_products("Washer", products)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["passport_id"], "PP-1")

    def test_graph_lists_documents(self):
        graph = build_product_graph({
            "brand": "LG",
            "product": "Washing Machine",
            "model": "T75",
            "linked_documents": [{"type": "invoice", "snippet": "INV-1"}],
            "events": [{"type": "service", "date": "2026-07-15", "description": "Filter check"}],
        })
        self.assertEqual(graph["document_count"], 1)
        self.assertEqual(graph["event_count"], 1)
        self.assertTrue(any(c["kind"] == "document" for c in graph["children"]))


class TestSamplePathSandbox(unittest.TestCase):

    def test_rejects_path_outside_samples(self):
        with self.assertRaises(ValueError):
            resolve_sample_path(str(Path(__file__).resolve()))


class TestAskApiUnknown(unittest.TestCase):

    def test_ask_unknown_api(self):
        client = TestClient(app)
        res = client.post("/api/ask", json={"query": "Who won the world cup in 1998?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["confidence"], "none")
        self.assertIn("don't know", data["answer"].lower())


if __name__ == "__main__":
    unittest.main()
