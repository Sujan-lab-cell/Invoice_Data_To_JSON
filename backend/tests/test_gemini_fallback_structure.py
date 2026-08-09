import unittest
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.schemas.invoice_schema import InvoiceItem


class TestGeminiFallbackStructure(unittest.TestCase):
    """
    Tests for Gemini fallback item structure normalization and validation:
    - Normalizes flat 'quantity.total_qty' into nested quantity.total_qty
    - Normalizes top-level 'total_qty' into nested quantity.total_qty
    - Derives total_qty if omitted
    - Validates resulting dictionary cleanly into InvoiceItem schema
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    def test_normalize_flat_quantity_dot_total_qty(self):
        """Verify that 'quantity.total_qty' at root of item gets migrated inside quantity."""
        raw_gemini_item = {
            "line_number": 1,
            "product": {
                "product_code": {"raw": "", "normalized": None, "confidence": 1.0},
                "description": {"raw": "AMPICARE DS TAB", "normalized": "AMPICARE DS TAB", "confidence": 1.0},
                "hsn_code": {"raw": "30049099", "normalized": "30049099", "confidence": 1.0},
            },
            "batch": {
                "batch_no": {"raw": "LBT2403026", "normalized": "LBT2403026", "confidence": 1.0},
                "expiry_date": {"raw": "02-27", "normalized": "02-27", "confidence": 1.0},
            },
            "packaging": {"pack_size": "15`S", "unit_count": 15, "unit_type": "Tablets"},
            "quantity": {
                "qty": {"raw": "10", "normalized": 10.0, "confidence": 1.0},
                "free_qty": {"raw": "0", "normalized": 0.0, "confidence": 1.0},
            },
            "pricing": {
                "mrp": {"raw": "125.00", "normalized": 125.0, "confidence": 1.0},
                "purchase_rate": {"raw": "89.28", "normalized": 89.28, "confidence": 1.0},
                "discount_percentage": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "discount_amount": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "taxable_amount": {"raw": "892.80", "normalized": 892.8, "confidence": 1.0},
            },
            "tax": {
                "cgst_percentage": {"raw": "6.00", "normalized": 6.0, "confidence": 1.0},
                "sgst_percentage": {"raw": "6.00", "normalized": 6.0, "confidence": 1.0},
                "igst_percentage": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "cgst_amount": {"raw": "53.57", "normalized": 53.57, "confidence": 1.0},
                "sgst_amount": {"raw": "53.57", "normalized": 53.57, "confidence": 1.0},
                "igst_amount": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "gst_percentage": {"raw": "12.00", "normalized": 12.0, "confidence": 1.0},
                "gst_amount": {"raw": "107.14", "normalized": 107.14, "confidence": 1.0},
            },
            "quantity.total_qty": 150.0,  # Dot-flattened key from LLM
        }

        normalized = self.extractor._normalize_gemini_item_structure(raw_gemini_item, 1)

        self.assertNotIn("quantity.total_qty", normalized)
        self.assertIn("total_qty", normalized["quantity"])
        self.assertEqual(normalized["quantity"]["total_qty"], 150.0)

        # Validate into Pydantic model
        item_obj = InvoiceItem.model_validate(normalized)
        self.assertEqual(item_obj.quantity.total_qty, 150.0)
        self.assertEqual(item_obj.product.description.normalized, "AMPICARE DS TAB")

    def test_normalize_nested_total_qty(self):
        """Verify that already properly nested total_qty passes through correctly."""
        raw_gemini_item = {
            "line_number": 2,
            "product": {
                "product_code": {"raw": "", "normalized": None, "confidence": 1.0},
                "description": {"raw": "NERVONAS TABLETS", "normalized": "NERVONAS TABLETS", "confidence": 1.0},
                "hsn_code": {"raw": "3004", "normalized": "3004", "confidence": 1.0},
            },
            "batch": {
                "batch_no": {"raw": "TN8751", "normalized": "TN8751", "confidence": 1.0},
                "expiry_date": {"raw": "02-28", "normalized": "02-28", "confidence": 1.0},
            },
            "packaging": {"pack_size": "10`S", "unit_count": 10, "unit_type": "Tablets"},
            "quantity": {
                "qty": {"raw": "5", "normalized": 5.0, "confidence": 1.0},
                "free_qty": {"raw": "0", "normalized": 0.0, "confidence": 1.0},
                "total_qty": 50.0,
            },
            "pricing": {
                "mrp": {"raw": "111.00", "normalized": 111.0, "confidence": 1.0},
                "purchase_rate": {"raw": "87.79", "normalized": 87.79, "confidence": 1.0},
                "discount_percentage": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "discount_amount": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                "taxable_amount": {"raw": "438.95", "normalized": 438.95, "confidence": 1.0},
            },
            "tax": {
                "cgst_percentage": {"raw": "2.5", "normalized": 2.5, "confidence": 1.0},
                "sgst_percentage": {"raw": "2.5", "normalized": 2.5, "confidence": 1.0},
                "igst_percentage": {"raw": "0.0", "normalized": 0.0, "confidence": 1.0},
                "cgst_amount": {"raw": "10.97", "normalized": 10.97, "confidence": 1.0},
                "sgst_amount": {"raw": "10.97", "normalized": 10.97, "confidence": 1.0},
                "igst_amount": {"raw": "0.0", "normalized": 0.0, "confidence": 1.0},
                "gst_percentage": {"raw": "5.0", "normalized": 5.0, "confidence": 1.0},
                "gst_amount": {"raw": "21.94", "normalized": 21.94, "confidence": 1.0},
            },
        }

        normalized = self.extractor._normalize_gemini_item_structure(raw_gemini_item, 2)
        item_obj = InvoiceItem.model_validate(normalized)
        self.assertEqual(item_obj.quantity.total_qty, 50.0)

    def test_derive_missing_total_qty(self):
        """Verify that total_qty is computed as qty * unit_count if omitted entirely."""
        raw_gemini_item = {
            "product": {
                "description": {"raw": "D2K CAL TABLETS", "normalized": "D2K CAL TABLETS", "confidence": 1.0},
            },
            "batch": {
                "batch_no": {"raw": "APT04870", "normalized": "APT04870", "confidence": 1.0},
                "expiry_date": {"raw": "11-27", "normalized": "11-27", "confidence": 1.0},
            },
            "packaging": {"pack_size": "15`S", "unit_count": 15, "unit_type": "Tablets"},
            "quantity": {
                "qty": {"raw": "4", "normalized": 4.0, "confidence": 1.0},
            },
            "pricing": {
                "mrp": {"raw": "75.00", "normalized": 75.0, "confidence": 1.0},
                "purchase_rate": {"raw": "59.52", "normalized": 59.52, "confidence": 1.0},
                "taxable_amount": {"raw": "238.08", "normalized": 238.08, "confidence": 1.0},
            },
            "tax": {
                "gst_percentage": {"raw": "5.0", "normalized": 5.0, "confidence": 1.0},
                "gst_amount": {"raw": "11.90", "normalized": 11.90, "confidence": 1.0},
            },
        }

        normalized = self.extractor._normalize_gemini_item_structure(raw_gemini_item, 1)
        self.assertEqual(normalized["quantity"]["total_qty"], 60.0)  # 4 * 15

    def test_gemini_prompt_specifies_nested_quantity(self):
        """Verify that the Gemini prompt includes nested structure guidelines for total_qty."""
        prompt = self.extractor._build_gemini_prompt("Sample OCR text")
        self.assertIn('"total_qty"', prompt)
        self.assertIn('"quantity":', prompt)


if __name__ == "__main__":
    unittest.main()
