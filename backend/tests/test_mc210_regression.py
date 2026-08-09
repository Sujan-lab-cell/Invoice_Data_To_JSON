import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app.ocr.easyocr_engine import EasyOCREngine
from app.parsers.pdf_parser import PDFParser
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.schemas.invoice_schema import Document


class TestMC210Regression(unittest.TestCase):
    """
    Regression test for MC-210 invoice extraction:
    - Asserts that the final invoice_data.items contains 8 items.
    - Asserts that raw_extraction.raw_json is populated with JSON containing the extracted items.
    - Asserts that totals (subtotal, tax_total, grand_total) are updated accordingly.
    """

    @classmethod
    def setUpClass(cls):
        cls.ocr_engine = EasyOCREngine()
        cls.pdf_parser = PDFParser(ocr_engine=cls.ocr_engine)
        cls.extractor = HybridInvoiceExtractor()
        cls.sample_path = Path(__file__).resolve().parent / "sample_invoices" / "MC 210 (1).pdf"

    def test_mc210_extracts_8_items_and_populates_raw_json(self):
        """Verify that MC-210 extraction merges all 8 line items and populates raw_json."""
        if not self.sample_path.exists():
            self.skipTest(f"Sample invoice not found: {self.sample_path}")

        parse_res = self.pdf_parser.parse(str(self.sample_path))

        # Mock Gemini response with the exact 8 items payload from MC-210
        mock_gemini_payload = {
            "items": [
                {
                    "line_number": 1,
                    "product": {"product_code": "LIFE", "description": "AMPICARE DS TAB", "hsn_code": "30049099"},
                    "batch": {"batch_no": "LBT2403026", "expiry_date": "02-27"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 10.0, "free_qty": 0.0, "total_qty": 10.0},
                    "pricing": {"mrp": 225.0, "purchase_rate": 179.0, "taxable_amount": 1790.0, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 44.75, "sgst_percentage": 2.5, "sgst_amount": 44.75, "gst_percentage": 5.0, "gst_amount": 89.50},
                },
                {
                    "line_number": 2,
                    "product": {"product_code": "LIFE", "description": "AMPICARE DS TAB", "hsn_code": "30049099"},
                    "batch": {"batch_no": "LBT2403026", "expiry_date": "02-27"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 0.0, "free_qty": 1.0, "total_qty": 1.0},
                    "pricing": {"mrp": 225.0, "purchase_rate": 179.0, "taxable_amount": 0.0, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 0.0, "sgst_percentage": 2.5, "sgst_amount": 0.0, "gst_percentage": 5.0, "gst_amount": 0.0},
                },
                {
                    "line_number": 3,
                    "product": {"product_code": "LIFE", "description": "NERVONAS TABLETS", "hsn_code": "3004"},
                    "batch": {"batch_no": "TN8751", "expiry_date": "02-28"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 10.0, "free_qty": 0.0, "total_qty": 10.0},
                    "pricing": {"mrp": 111.0, "purchase_rate": 87.79, "taxable_amount": 877.90, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 21.95, "sgst_percentage": 2.5, "sgst_amount": 21.95, "gst_percentage": 5.0, "gst_amount": 43.90},
                },
                {
                    "line_number": 4,
                    "product": {"product_code": "LIFE", "description": "NERVONAS TABLETS", "hsn_code": "3004"},
                    "batch": {"batch_no": "TN8751", "expiry_date": "02-28"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 0.0, "free_qty": 1.0, "total_qty": 1.0},
                    "pricing": {"mrp": 111.0, "purchase_rate": 87.79, "taxable_amount": 0.0, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 0.0, "sgst_percentage": 2.5, "sgst_amount": 0.0, "gst_percentage": 5.0, "gst_amount": 0.0},
                },
                {
                    "line_number": 5,
                    "product": {"product_code": "LIFE", "description": "D2K CAL TABLETS", "hsn_code": "21069099"},
                    "batch": {"batch_no": "APT04870", "expiry_date": "11-27"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 10.0, "free_qty": 0.0, "total_qty": 10.0},
                    "pricing": {"mrp": 75.0, "purchase_rate": 59.52, "taxable_amount": 595.20, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 14.88, "sgst_percentage": 2.5, "sgst_amount": 14.88, "gst_percentage": 5.0, "gst_amount": 29.76},
                },
                {
                    "line_number": 6,
                    "product": {"product_code": "LIFE", "description": "D2K CAL TABLETS", "hsn_code": "21069099"},
                    "batch": {"batch_no": "APT04870", "expiry_date": "11-27"},
                    "packaging": {"pack_size": "1", "unit_count": 1, "unit_type": "TABLETS"},
                    "quantity": {"qty": 0.0, "free_qty": 1.0, "total_qty": 1.0},
                    "pricing": {"mrp": 75.0, "purchase_rate": 59.52, "taxable_amount": 0.0, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 0.0, "sgst_percentage": 2.5, "sgst_amount": 0.0, "gst_percentage": 5.0, "gst_amount": 0.0},
                },
                {
                    "line_number": 7,
                    "product": {"product_code": "LIFE", "description": "TRIPCARE TABLETS", "hsn_code": "30049069"},
                    "batch": {"batch_no": "UGT25296G", "expiry_date": "02-27"},
                    "packaging": {"pack_size": "1X10", "unit_count": 10, "unit_type": "TABLETS"},
                    "quantity": {"qty": 10.0, "free_qty": 0.0, "total_qty": 100.0},
                    "pricing": {"mrp": 183.0, "purchase_rate": 145.08, "taxable_amount": 1450.80, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 36.27, "sgst_percentage": 2.5, "sgst_amount": 36.27, "gst_percentage": 5.0, "gst_amount": 72.54},
                },
                {
                    "line_number": 8,
                    "product": {"product_code": "LIFE", "description": "TRIPCARE TABLETS", "hsn_code": "30049069"},
                    "batch": {"batch_no": "UGT25296G", "expiry_date": "02-27"},
                    "packaging": {"pack_size": "1X10", "unit_count": 10, "unit_type": "TABLETS"},
                    "quantity": {"qty": 0.0, "free_qty": 1.0, "total_qty": 10.0},
                    "pricing": {"mrp": 183.0, "purchase_rate": 145.08, "taxable_amount": 0.0, "discount_percentage": 0.0, "discount_amount": 0.0},
                    "tax": {"cgst_percentage": 2.5, "cgst_amount": 0.0, "sgst_percentage": 2.5, "sgst_amount": 0.0, "gst_percentage": 5.0, "gst_amount": 0.0},
                },
            ]
        }

        with patch("app.ai.hybrid_extractor.generate_json", return_value=mock_gemini_payload):
            doc = self.extractor.extract(parse_res, file_name="MC 210 (1).pdf", file_type="pdf")

        # 1. Assert invoice items count is 8
        self.assertIsNotNone(doc.invoice_data)
        self.assertEqual(len(doc.invoice_data.items), 8)

        # 2. Assert raw_extraction.raw_json is populated
        self.assertIsNotNone(doc.raw_extraction)
        self.assertIsNotNone(doc.raw_extraction.raw_json)
        parsed_raw_json = json.loads(doc.raw_extraction.raw_json)
        self.assertIn("items", parsed_raw_json)
        self.assertEqual(len(parsed_raw_json["items"]), 8)

        # 3. Assert item values and totals
        first_item = doc.invoice_data.items[0]
        self.assertEqual(first_item.product.description.normalized, "AMPICARE DS TAB")
        self.assertEqual(first_item.quantity.total_qty, 10.0)
        self.assertEqual(first_item.pricing.taxable_amount.normalized, 1790.0)

        # 4. Assert totals calculation
        self.assertAlmostEqual(doc.invoice_data.totals.subtotal.normalized, 4713.90, places=2)
        self.assertAlmostEqual(doc.invoice_data.totals.tax_total.normalized, 235.70, places=2)
        self.assertIn(round(doc.invoice_data.totals.grand_total.normalized, 2), [4949.60, 4950.00])


if __name__ == "__main__":
    unittest.main()
