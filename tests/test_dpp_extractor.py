"""
Unit Tests — DPP Extractor & JSON Cleaner
"""

import unittest
from app.core.dpp_extractor import clean_json_response, build_vlm_prompt


class TestDPPExtractor(unittest.TestCase):

    def test_clean_json_standard(self):
        raw = """```json
{
  "document_type": "warranty_card",
  "passports": [
    {
      "product": "Washing Machine",
      "model": "T75-SKSF1Z"
    }
  ]
}
```"""
        parsed = clean_json_response(raw)
        self.assertEqual(parsed["document_type"], "warranty_card")
        self.assertEqual(len(parsed["passports"]), 1)

    def test_clean_json_trailing_commas(self):
        raw = """{
  "document_type": "tax_invoice",
  "passports": [
    {
      "product": "Microwave",
      "price": 199.00,
    },
  ],
}"""
        parsed = clean_json_response(raw)
        self.assertEqual(parsed["document_type"], "tax_invoice")
        self.assertEqual(parsed["passports"][0]["product"], "Microwave")

    def test_clean_json_flat_array(self):
        raw = """[
  {
    "product": "Air Purifier",
    "model": "EAP150"
  }
]"""
        parsed = clean_json_response(raw)
        self.assertIn("passports", parsed)
        self.assertEqual(len(parsed["passports"]), 1)
        self.assertEqual(parsed["passports"][0]["product"], "Air Purifier")

    def test_clean_json_single_product_dict(self):
        raw = """{
  "product": "Refrigerator",
  "brand": "Samsung",
  "model": "RT28K"
}"""
        parsed = clean_json_response(raw)
        self.assertIn("passports", parsed)
        self.assertEqual(parsed["passports"][0]["product"], "Refrigerator")

    def test_build_vlm_prompt(self):
        prompt = build_vlm_prompt("Serial: LG123456 Model: T75-SKSF1Z")
        self.assertIn("CHECKBOX DISCRIMINATION", prompt)
        self.assertIn("LG123456", prompt)


if __name__ == "__main__":
    unittest.main()
