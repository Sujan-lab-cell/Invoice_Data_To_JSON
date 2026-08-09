import unittest
from pathlib import Path
from unittest.mock import patch

from app.ocr.easyocr_engine import EasyOCREngine
from app.parsers.image_parser import ImageParser
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.schemas.invoice_schema import (
    Invoice,
    Supplier,
    Buyer,
    Totals,
    ValuePair,
    InvoiceItem,
    Product,
    Batch,
    Packaging,
    Quantity,
    Pricing,
    Tax,
)


class TestFallbackQualityDetection(unittest.TestCase):
    """
    Step 7: Quality-Aware Fallback Triggering and Merge Detection Tests.
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    def _build_valid_invoice(self) -> Invoice:
        item1 = InvoiceItem(
            line_number=1,
            product=Product(description=ValuePair(raw="Item A", normalized="Item A", confidence=0.9)),
            batch=Batch(batch_no=ValuePair(raw="B1", normalized="B1", confidence=0.9), expiry_date=ValuePair(raw="12/28", normalized="12/28", confidence=0.9)),
            packaging=Packaging(pack_size="10s", unit_count=10, unit_type="Tablets"),
            quantity=Quantity(qty=ValuePair(raw="10", normalized=10.0, confidence=0.9), total_qty=100.0),
            pricing=Pricing(
                mrp=ValuePair(raw="120.00", normalized=120.00, confidence=0.9),
                purchase_rate=ValuePair(raw="100.00", normalized=100.00, confidence=0.9),
                taxable_amount=ValuePair(raw="1000.00", normalized=1000.00, confidence=0.9)
            ),
            tax=Tax(gst_percentage=ValuePair(raw="5", normalized=5.0, confidence=0.9), gst_amount=ValuePair(raw="50.00", normalized=50.00, confidence=0.9))
        )
        return Invoice(
            invoice_number=ValuePair(raw="INV-001", normalized="INV-001", confidence=0.9),
            invoice_date=ValuePair(raw="2026-05-14", normalized="2026-05-14", confidence=0.9),
            supplier=Supplier(
                name=ValuePair(raw="SUPPLIER", normalized="SUPPLIER", confidence=0.9),
                gstin=ValuePair(raw="32ABCDE1234F1Z5", normalized="32ABCDE1234F1Z5", confidence=0.9),
                address=ValuePair(raw="CITY", normalized="CITY", confidence=0.9)
            ),
            buyer=Buyer(name=ValuePair(raw="BUYER", normalized="BUYER", confidence=0.9)),
            items=[item1],
            totals=Totals(
                subtotal=ValuePair(raw="1000.00", normalized=1000.00, confidence=0.9),
                tax_total=ValuePair(raw="50.00", normalized=50.00, confidence=0.9),
                grand_total=ValuePair(raw="1050.00", normalized=1050.00, confidence=0.9)
            )
        )

    def test_1_items_empty_triggers_fallback(self):
        """TEST 1: items = [] -> fallback triggered."""
        invoice = self._build_valid_invoice()
        invoice.items = []
        self.assertTrue(self.extractor._has_missing_data(invoice))

    def test_2_items_missing_critical_rate_triggers_fallback(self):
        """TEST 2: items exist but critical rate/pricing is missing -> fallback triggered."""
        invoice = self._build_valid_invoice()
        invoice.items[0].pricing.purchase_rate = None
        self.assertTrue(self.extractor._has_missing_data(invoice))

    def test_3_items_mathematically_inconsistent_triggers_fallback(self):
        """TEST 3: items exist but values are mathematically inconsistent (e.g. 10 * 100 != 1.00) -> fallback triggered."""
        invoice = self._build_valid_invoice()
        # qty=10, rate=100.0, but taxable_amount=1.00
        invoice.items[0].pricing.taxable_amount = ValuePair(raw="1.00", normalized=1.00, confidence=0.9)
        self.assertTrue(self.extractor._has_missing_data(invoice))

    def test_4_valid_items_and_totals_do_not_trigger_fallback(self):
        """TEST 4: items exist and all critical values are consistent -> fallback NOT triggered."""
        invoice = self._build_valid_invoice()
        self.assertFalse(self.extractor._has_missing_data(invoice))

    def test_5_suspicious_rule_items_replaced_by_valid_gemini_items(self):
        """TEST 5: suspicious/placeholder rule value + correct Gemini value -> Gemini value wins."""
        invoice = self._build_valid_invoice()
        # Make rule item suspicious
        invoice.items[0].pricing.purchase_rate = ValuePair(raw="1.00", normalized=1.00, confidence=0.5)
        invoice.items[0].pricing.taxable_amount = ValuePair(raw="1.00", normalized=1.00, confidence=0.5)

        gemini_payload = {
            "items": [
                {
                    "line_number": 1,
                    "product": {"description": "Item A"},
                    "quantity": {"qty": 10.0, "total_qty": 100.0},
                    "pricing": {"purchase_rate": 100.00, "taxable_amount": 1000.00}
                }
            ]
        }
        merged = self.extractor._merge_gemini_extraction(invoice, gemini_payload)
        self.assertEqual(merged.items[0].pricing.taxable_amount.normalized, 1000.00)
        self.assertEqual(merged.items[0].pricing.purchase_rate.normalized, 100.00)

    def test_6_valid_rule_items_preserved_over_gemini(self):
        """TEST 6: valid high-confidence rule value + different Gemini value -> valid rule value wins."""
        invoice = self._build_valid_invoice()

        gemini_payload = {
            "supplier": {"name": "DIFFERENT SUPPLIER"},
            "items": [
                {
                    "line_number": 1,
                    "product": {"description": "DIFFERENT ITEM"},
                    "quantity": {"qty": 999.0, "total_qty": 999.0},
                    "pricing": {"purchase_rate": 999.00, "taxable_amount": 999.00}
                }
            ]
        }
        merged = self.extractor._merge_gemini_extraction(invoice, gemini_payload)
        self.assertEqual(merged.supplier.name.normalized, "SUPPLIER")
        self.assertEqual(merged.items[0].product.description.normalized, "Item A")
        self.assertEqual(merged.items[0].pricing.taxable_amount.normalized, 1000.00)

    def test_7_sample_invoice_jpg_real_fallback_recovery(self):
        """TEST 7: Real sample_invoice_test.jpg recovery with exact expected fields and totals."""
        img_path = Path(__file__).resolve().parent / "sample_invoices" / "sample_invoice_test.jpg"
        if not img_path.exists():
            self.skipTest(f"Sample invoice not found: {img_path}")

        image_parser = ImageParser(ocr_engine=EasyOCREngine())
        ocr_result = image_parser.parse(str(img_path))

        mock_gemini = {
            "items": [
                {
                    "line_number": 1,
                    "product": {"description": "Digital Tnermomeler"},
                    "quantity": {"qty": 2.0, "total_qty": 2.0},
                    "pricing": {"purchase_rate": 250.00, "taxable_amount": 500.00}
                },
                {
                    "line_number": 2,
                    "product": {"description": "Syringe 5ml Box"},
                    "quantity": {"qty": 10.0, "total_qty": 10.0},
                    "pricing": {"purchase_rate": 120.00, "taxable_amount": 1200.00}
                },
                {
                    "line_number": 3,
                    "product": {"description": "Surgical Gloves Box"},
                    "quantity": {"qty": 5.0, "total_qty": 5.0},
                    "pricing": {"purchase_rate": 180.00, "taxable_amount": 900.00}
                }
            ],
            "totals": {
                "subtotal": {"raw": "2600.00", "normalized": 2600.00, "confidence": 0.95},
                "tax_total": {"raw": "468.00", "normalized": 468.00, "confidence": 0.95},
                "grand_total": {"raw": "3068.00", "normalized": 3068.00, "confidence": 0.95}
            }
        }

        with patch("app.ai.hybrid_extractor.generate_json", return_value=mock_gemini):
            doc = self.extractor.extract(ocr_result, file_name="sample_invoice_test.jpg", file_type="image")

        self.assertEqual(len(doc.invoice_data.items), 3)
        self.assertEqual(doc.invoice_data.items[0].quantity.qty.normalized, 2.0)
        self.assertEqual(doc.invoice_data.items[0].pricing.taxable_amount.normalized, 500.00)
        self.assertEqual(doc.invoice_data.items[1].quantity.qty.normalized, 10.0)
        self.assertEqual(doc.invoice_data.items[1].pricing.taxable_amount.normalized, 1200.00)
        self.assertEqual(doc.invoice_data.items[2].quantity.qty.normalized, 5.0)
        self.assertEqual(doc.invoice_data.items[2].pricing.taxable_amount.normalized, 900.00)

        self.assertEqual(doc.invoice_data.totals.subtotal.normalized, 2600.00)
        self.assertEqual(doc.invoice_data.totals.tax_total.normalized, 468.00)
        self.assertEqual(doc.invoice_data.totals.grand_total.normalized, 3068.00)


if __name__ == "__main__":
    unittest.main()
