import unittest
from pathlib import Path
from unittest.mock import patch

from app.ocr.schemas import OCRResult
from app.parsers.image_parser import ImageParser
from app.ai.hybrid_extractor import HybridInvoiceExtractor


class TestFallbackSampleJpg(unittest.TestCase):
    """
    Step 8: End-to-End verification for sample_invoice_test.jpg.
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    def test_sample_jpg_e2e_with_full_source_text(self):
        """
        Verify the complete pipeline on the exact sample invoice OCR text:
        - Invoice No: 154
        - Date: 13-04-2026
        - Supplier: Ravi kumar
        - Buyer: NOVELTY DRUG STORE, KANNUR ROAD, KOZHIKODE, GSTIN: 32ACGPK8901L1Z2
        - Items:
          1. Digital Tnermomeler (2 x 250.00 = 500.00)
          2. Syringe 5ml Box (10 x 120.00 = 1200.00)
          3. Surgical Gloves Box (5 x 180.00 = 900.00)
        - Totals:
          Subtotal: 2600.00
          GST (18%): 468.00
          Grand Total: 3068.00
        """
        ocr_text = """
Tax Invoice
Ravi kumar
Invoice No: 154
Date: 13-04-2026
9508399874
Billed To:
NOVELTY DRUG STORE
KANNUR ROAD, KOZHIKODE
GSTIN: 32ACGPK8901L1Z2
Item Description
Qty
Rate
Amount
Digital Tnermomeler
2
250.00
500.00
Syringe 5ml Box
10
120.00
1200.00
Surgical Gloves Box
5
180.00
900.00
Subtotal:
2600.00
GST (18%):
468.00
Grand Total:
3068.00
"""
        ocr_result = OCRResult(full_text=ocr_text, structured_data={}, lines=[])
        doc = self.extractor.extract(ocr_result, file_name="sample_invoice_test.jpg", file_type="image")
        inv = doc.invoice_data

        # 1. Header assertions
        self.assertEqual(inv.invoice_number.normalized, "154")
        self.assertEqual(inv.invoice_date.normalized, "2026-04-13")
        self.assertEqual(inv.supplier.name.normalized, "Ravi kumar")
        self.assertEqual(inv.buyer.name.normalized, "NOVELTY DRUG STORE")
        self.assertEqual(inv.buyer.gstin.normalized, "32ACGPK8901L1Z2")

        # 2. Line item assertions
        self.assertEqual(len(inv.items), 3)

        # Item 1
        self.assertEqual(inv.items[0].product.description.normalized, "Digital Tnermomeler")
        self.assertEqual(inv.items[0].quantity.qty.normalized, 2.0)
        self.assertEqual(inv.items[0].pricing.purchase_rate.normalized, 250.00)
        self.assertEqual(inv.items[0].pricing.taxable_amount.normalized, 500.00)

        # Item 2
        self.assertEqual(inv.items[1].product.description.normalized, "Syringe 5ml Box")
        self.assertEqual(inv.items[1].quantity.qty.normalized, 10.0)
        self.assertEqual(inv.items[1].pricing.purchase_rate.normalized, 120.00)
        self.assertEqual(inv.items[1].pricing.taxable_amount.normalized, 1200.00)

        # Item 3
        self.assertEqual(inv.items[2].product.description.normalized, "Surgical Gloves Box")
        self.assertEqual(inv.items[2].quantity.qty.normalized, 5.0)
        self.assertEqual(inv.items[2].pricing.purchase_rate.normalized, 180.00)
        self.assertEqual(inv.items[2].pricing.taxable_amount.normalized, 900.00)

        # 3. Mathematical validation assertions
        self.assertEqual(
            inv.items[0].quantity.qty.normalized * inv.items[0].pricing.purchase_rate.normalized,
            inv.items[0].pricing.taxable_amount.normalized
        )
        self.assertEqual(
            inv.items[1].quantity.qty.normalized * inv.items[1].pricing.purchase_rate.normalized,
            inv.items[1].pricing.taxable_amount.normalized
        )
        self.assertEqual(
            inv.items[2].quantity.qty.normalized * inv.items[2].pricing.purchase_rate.normalized,
            inv.items[2].pricing.taxable_amount.normalized
        )

        sum_taxable = sum(item.pricing.taxable_amount.normalized for item in inv.items)
        self.assertEqual(sum_taxable, 2600.00)

        # 4. Totals assertions
        self.assertEqual(inv.totals.subtotal.normalized, 2600.00)
        self.assertEqual(inv.totals.tax_total.normalized, 468.00)
        self.assertEqual(inv.totals.grand_total.normalized, 3068.00)

        # 5. Canonical JSON structure
        canonical = doc.to_canonical_dict()
        self.assertEqual(canonical["invoice"]["invoice_number"], "154")
        self.assertEqual(canonical["totals"]["subtotal"], 2600.00)
        self.assertEqual(canonical["totals"]["tax_total"], 468.00)
        self.assertEqual(canonical["totals"]["grand_total"], 3068.00)
        self.assertEqual(len(canonical["items"]), 3)

        # 6. Overall validation
        self.assertTrue(doc.validation.is_valid)
        error_issues = [issue for issue in doc.validation.issues if issue.severity == "error"]
        self.assertEqual(len(error_issues), 0)

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_sample_jpg_preserves_rule_priority_over_gemini_hallucination(self, mock_gen):
        """Proves that Gemini cannot overwrite high-confidence rule-extracted headers."""
        ocr_text = """
Tax Invoice
Ravi kumar
Invoice No: 154
Date: 13-04-2026
9508399874
Billed To:
NOVELTY DRUG STORE
KANNUR ROAD, KOZHIKODE
GSTIN: 32ACGPK8901L1Z2
Item Description
Qty
Rate
Amount
Digital Tnermomeler
2
250.00
500.00
"""
        ocr_result = OCRResult(full_text=ocr_text, structured_data={}, lines=[])

        mock_gen.return_value = {
            "supplier": {"name": {"raw": "HALLUCINATED SUPPLIER", "normalized": "HALLUCINATED SUPPLIER", "confidence": 0.95}},
            "totals": {
                "subtotal": {"raw": "2600.00", "normalized": 2600.00, "confidence": 0.95},
                "tax_total": {"raw": "468.00", "normalized": 468.00, "confidence": 0.95},
                "grand_total": {"raw": "3068.00", "normalized": 3068.00, "confidence": 0.95}
            }
        }

        doc = self.extractor.extract(ocr_result, file_name="sample_invoice_test.jpg", file_type="image")

        # Must preserve high-confidence rule-extracted supplier 'Ravi kumar'
        self.assertEqual(doc.invoice_data.supplier.name.normalized, "Ravi kumar")


if __name__ == "__main__":
    unittest.main()
