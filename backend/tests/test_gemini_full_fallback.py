import unittest
from unittest.mock import patch

from app.ocr.schemas import OCRResult
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.schemas.invoice_schema import (
    Invoice,
    Supplier,
    Buyer,
    Totals,
    ValuePair,
)


class TestGeminiFullFallback(unittest.TestCase):
    """
    Tests ensuring that if ANY part is left empty after rule-based extraction,
    Gemini AI fallback extracts and backfills all missing data across headers,
    supplier, buyer, items, totals, and tax summary.
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    def test_has_missing_data_triggers_on_empty_header(self):
        """Verify that empty header fields trigger fallback."""
        inv = Invoice(
            invoice_number=ValuePair(raw="", normalized="", confidence=0.0),
            invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
            supplier=Supplier(name=ValuePair(raw="SUP", normalized="SUP", confidence=1.0)),
            buyer=Buyer(name=ValuePair(raw="BUY", normalized="BUY", confidence=1.0)),
            items=[],
            totals=Totals(subtotal=ValuePair(raw="0.00", normalized=0.0, confidence=1.0), tax_total=ValuePair(raw="0.00", normalized=0.0, confidence=1.0), grand_total=ValuePair(raw="0.00", normalized=0.0, confidence=1.0)),
        )
        self.assertTrue(self.extractor._has_missing_data(inv))

    def test_merge_gemini_backfills_missing_headers_and_items(self):
        """Verify that missing supplier, buyer, items, and totals are merged cleanly from Gemini."""
        inv = Invoice(
            invoice_number=ValuePair(raw="INV-001", normalized="INV-001", confidence=1.0),
            invoice_date=ValuePair(raw="", normalized="", confidence=0.0),
            supplier=Supplier(
                name=ValuePair(raw="RULE SUPPLIER", normalized="RULE SUPPLIER", confidence=1.0),
                address=None,
                phone=None,
            ),
            buyer=Buyer(
                name=ValuePair(raw="", normalized="", confidence=0.0),
                address=None,
            ),
            items=[],
            totals=Totals(subtotal=ValuePair(raw="0.00", normalized=0.0, confidence=0.0), tax_total=ValuePair(raw="0.00", normalized=0.0, confidence=0.0), grand_total=ValuePair(raw="0.00", normalized=0.0, confidence=0.0)),
        )

        mock_gemini_data = {
            "invoice": {
                "invoice_number": "INV-001",
                "invoice_date": "2026-05-14",
                "payment_type": "CREDIT",
            },
            "supplier": {
                "name": "RULE SUPPLIER",
                "gstin": "32AGHPR0323G1ZU",
                "address": "123 Healthcare Ave, Kerala",
                "phone": "0490 2326443",
                "state": "KERALA",
            },
            "buyer": {
                "name": "GERMAN PHARMACY",
                "gstin": "32ABCDE1234F1Z5",
                "address": "456 City Center, Thalassery",
                "phone": "9847593760",
                "state": "KERALA",
            },
            "items": [
                {
                    "line_number": 1,
                    "product": {"description": "PARACETAMOL 500MG", "hsn_code": "30049099"},
                    "batch": {"batch_no": "B123", "expiry_date": "12/27"},
                    "packaging": {"pack_size": "10s", "unit_count": 10, "unit_type": "Tablets"},
                    "quantity": {"qty": 5.0, "total_qty": 50.0},
                    "pricing": {"mrp": 20.0, "purchase_rate": 15.0, "taxable_amount": 75.0},
                    "tax": {"gst_percentage": 5.0, "gst_amount": 3.75},
                }
            ],
            "totals": {
                "subtotal": 75.0,
                "tax_total": 3.75,
                "grand_total": 78.75,
            },
            "tax_summary": [
                {
                    "tax_rate": 5.0,
                    "taxable_amount": 75.0,
                    "cgst_amount": 1.88,
                    "sgst_amount": 1.87,
                    "total_tax_amount": 3.75,
                }
            ]
        }

        merged = self.extractor._merge_gemini_extraction(inv, mock_gemini_data)

        # 1. Preserved rule invoice number
        self.assertEqual(merged.invoice_number.normalized, "INV-001")

        # 2. Backfilled invoice date
        self.assertEqual(merged.invoice_date.normalized, "2026-05-14")

        # 3. Backfilled supplier address & phone
        self.assertEqual(merged.supplier.address.normalized, "123 Healthcare Ave, Kerala")
        self.assertEqual(merged.supplier.phone.normalized, "0490 2326443")
        self.assertEqual(merged.supplier.gstin.normalized, "32AGHPR0323G1ZU")

        # 4. Backfilled buyer details
        self.assertEqual(merged.buyer.name.normalized, "GERMAN PHARMACY")
        self.assertEqual(merged.buyer.address.normalized, "456 City Center, Thalassery")

        # 5. Merged line items & totals
        self.assertEqual(len(merged.items), 1)
        self.assertEqual(merged.items[0].product.description.normalized, "PARACETAMOL 500MG")
        self.assertAlmostEqual(merged.totals.grand_total.normalized, 78.75, places=2)

        # 6. Tax Summary
        self.assertEqual(len(merged.tax_summary.items), 1)
        self.assertEqual(merged.tax_summary.items[0].tax_rate, 5.0)


if __name__ == "__main__":
    unittest.main()
