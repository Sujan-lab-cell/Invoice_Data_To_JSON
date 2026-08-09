import unittest
from pathlib import Path

from app.ocr.easyocr_engine import EasyOCREngine
from app.parsers.pdf_parser import PDFParser
from app.ai.hybrid_extractor import HybridInvoiceExtractor


class TestInvoice4358E2E(unittest.TestCase):
    """
    End-to-end regression test for real invoice sample:
    sample_invoices/4358 (1).pdf

    Verifies complete pipeline from PDF parsing through canonical JSON and validation.
    """

    @classmethod
    def setUpClass(cls):
        cls.ocr_engine = EasyOCREngine()
        cls.parser = PDFParser(ocr_engine=cls.ocr_engine)
        cls.extractor = HybridInvoiceExtractor()
        cls.pdf_path = Path(__file__).resolve().parent / "sample_invoices" / "4358 (1).pdf"

    def test_full_pipeline_invoice_4358(self):
        if not self.pdf_path.exists():
            self.skipTest(f"Sample invoice not found at {self.pdf_path}")

        # 1. Parse PDF
        ocr_result = self.parser.parse(str(self.pdf_path))
        self.assertIsNotNone(ocr_result)
        self.assertIn("4358", ocr_result.full_text)

        # 2. Extract Document
        doc = self.extractor.extract(ocr_result, file_name=self.pdf_path.name, file_type="pdf")
        self.assertIsNotNone(doc)
        self.assertIsNotNone(doc.invoice_data)

        # 3. Header assertions
        inv = doc.invoice_data
        self.assertEqual(inv.invoice_number.normalized, "4358")
        self.assertEqual(inv.invoice_date.normalized, "2026-05-14")
        self.assertEqual(inv.invoice_date.raw, "14-05-2026")
        self.assertEqual(inv.payment_type.normalized, "CREDIT")
        self.assertEqual(inv.supplier.name.normalized, "SABARI ENTERPRISES")
        self.assertEqual(inv.supplier.gstin.normalized, "32AAJFS5434R1ZN")
        self.assertEqual(inv.buyer.name.normalized, "GERMAN PHARMACY")

        # 4. Item table assertions
        items = inv.items
        self.assertEqual(len(items), 2, f"Expected 2 items, got {len(items)}")

        # Item 1
        it1 = items[0]
        self.assertIn("RHIN DEFSOLONE", it1.product.description.normalized)
        self.assertEqual(it1.product.hsn_code.normalized, "30043911")
        self.assertEqual(it1.batch.batch_no.normalized, "MTTA0175A")
        self.assertEqual(it1.batch.expiry_date.raw, "12/27")
        self.assertEqual(it1.quantity.qty.normalized, 10.0)
        self.assertIsNotNone(it1.quantity.free_qty)
        self.assertEqual(it1.quantity.free_qty.normalized, 2.0)
        self.assertEqual(it1.pricing.mrp.normalized, 121.88)
        self.assertEqual(it1.pricing.purchase_rate.normalized, 92.86)
        self.assertEqual(it1.tax.gst_percentage.normalized, 5.0)
        self.assertEqual(it1.pricing.taxable_amount.normalized, 928.60)

        # Item 2
        it2 = items[1]
        self.assertEqual(it2.product.description.normalized, "RHIN FLUGAIN 10 MG TAB")
        self.assertEqual(it2.product.hsn_code.normalized, "30044090")
        self.assertEqual(it2.batch.batch_no.normalized, "RFNT2503")
        self.assertEqual(it2.batch.expiry_date.raw, "10/27")
        self.assertEqual(it2.quantity.qty.normalized, 10.0)
        self.assertIsNotNone(it2.quantity.free_qty)
        self.assertEqual(it2.quantity.free_qty.normalized, 2.0)
        self.assertEqual(it2.pricing.mrp.normalized, 45.15)
        self.assertEqual(it2.pricing.purchase_rate.normalized, 34.40)
        self.assertEqual(it2.tax.gst_percentage.normalized, 5.0)
        self.assertEqual(it2.pricing.taxable_amount.normalized, 344.00)

        # 5. Totals assertions
        totals = inv.totals
        self.assertEqual(totals.subtotal.normalized, 1272.60)
        self.assertEqual(totals.subtotal.raw, "1272.60")
        self.assertEqual(totals.tax_total.normalized, 63.63)
        self.assertEqual(totals.tax_total.raw, "63.63")
        self.assertEqual(totals.round_off.normalized, -0.23)
        self.assertEqual(totals.round_off.raw, "-0.23")
        self.assertEqual(totals.grand_total.normalized, 1336.00)
        self.assertEqual(totals.grand_total.raw, "1336.00")

        # 6. Fallback not unnecessarily triggered
        self.assertEqual(doc.raw_extraction.raw_fields.get("fallback_triggered"), "False")
        self.assertEqual(doc.raw_extraction.raw_fields.get("gemini_status"), "not_triggered")

        # 7. Canonical JSON assertions
        canonical = doc.to_canonical_dict()
        self.assertIn("document", canonical)
        self.assertIn("invoice", canonical)
        self.assertIn("supplier", canonical)
        self.assertIn("buyer", canonical)
        self.assertIn("items", canonical)
        self.assertIn("totals", canonical)
        self.assertEqual(len(canonical["items"]), 2)
        self.assertEqual(canonical["totals"]["grand_total"], 1336.00)
        self.assertEqual(canonical["totals"]["subtotal"], 1272.60)
        self.assertEqual(canonical["totals"]["tax_total"], 63.63)
        self.assertEqual(canonical["supplier"]["name"], "SABARI ENTERPRISES")
        self.assertEqual(canonical["supplier"]["gstin"], "32AAJFS5434R1ZN")

        # 8. Validation assertion
        self.assertTrue(doc.validation.is_valid)
        self.assertEqual(len(doc.validation.issues), 0)


if __name__ == "__main__":
    unittest.main()
