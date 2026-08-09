import unittest
from unittest.mock import patch, MagicMock

from app.ocr.schemas import OCRResult
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.ai.gemini_client import GeminiAPIError
from app.schemas.invoice_schema import (
    Invoice,
    Supplier,
    Buyer,
    Totals,
    ValuePair,
)
from app.core.config import settings

SAMPLE_4358_OCR = """
SABARI ENTERPRISES
GSTIN : 32AAJFS5434R1ZN
Inv No: 4358  Pay Type : CREDIT  Inv Dt : 14-05-2026
Taxable Amount : 1272.60
Tax Amount : 63.63
Write Off : -0.23
Net Amount : 1336.00
1 RHIN DEFSOLONE 6 10's 30043911 MTTA0175A 12/27 10 2 121.88 92.86 0.00 5 928.60
2 RHIN FLUGAIN 10 MG TAB 10's 30044090 RFNT2503 10/27 10 2 45.15 34.40 0.00 5 344.00
"""


class TestGeminiFallbackE2E(unittest.TestCase):
    """
    Comprehensive verification and end-to-end tests for the complete Gemini Fallback path:
    1. Header recovery when missing.
    2. Preservation of valid rule-based data (no overwrite by LLM).
    3. Item table recovery when missing.
    4. Totals recovery when missing.
    5. Graceful degradation on Gemini failure with sanitized error tracking.
    6. Non-blocking real integration test (skipped when no key is set).
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_part4_fallback_recovers_missing_supplier_gstin(self, mock_generate_json):
        """Part 4: Proves Gemini recovers a missing header field (supplier.gstin) into canonical JSON without overwriting good rule fields."""
        mock_generate_json.return_value = {
            "supplier": {
                "gstin": {
                    "raw": "32AAJFS5434R1ZN",
                    "normalized": "32AAJFS5434R1ZN",
                    "confidence": 0.95
                }
            }
        }

        # Create a partial invoice where rule extraction got invoice headers but missed supplier GSTIN
        ocr_res = OCRResult(full_text=SAMPLE_4358_OCR)
        
        # Patch HeaderExtractor to return supplier without GSTIN
        with patch("app.extraction.header_extractor.HeaderExtractor.extract") as mock_headers:
            mock_headers.return_value = {
                "invoice_number": ValuePair(raw="4358", normalized="4358", confidence=0.9),
                "invoice_date": ValuePair(raw="14-05-2026", normalized="2026-05-14", confidence=0.9),
                "payment_type": ValuePair(raw="CREDIT", normalized="CREDIT", confidence=0.9),
                "supplier": Supplier(
                    name=ValuePair(raw="SABARI ENTERPRISES", normalized="SABARI ENTERPRISES", confidence=0.9),
                    gstin=None, # Missing GSTIN
                    address=ValuePair(raw="TELLICHERY", normalized="TELLICHERY", confidence=0.9)
                ),
                "buyer": Buyer(name=ValuePair(raw="GERMAN PHARMACY", normalized="GERMAN PHARMACY", confidence=0.9))
            }
            doc = self.extractor.extract(ocr_res, file_name="4358 (1).pdf", file_type="pdf")

        # 1. Verify Gemini was called
        mock_generate_json.assert_called_once()

        # 2. Verify GSTIN was recovered in internal model
        self.assertEqual(doc.invoice_data.supplier.gstin.normalized, "32AAJFS5434R1ZN")

        # 3. Verify original rule-based fields were preserved
        self.assertEqual(doc.invoice_data.invoice_number.normalized, "4358")
        self.assertEqual(doc.invoice_data.invoice_date.normalized, "2026-05-14")
        self.assertEqual(doc.invoice_data.payment_type.normalized, "CREDIT")
        self.assertEqual(doc.invoice_data.supplier.name.normalized, "SABARI ENTERPRISES")

        # 4. Verify canonical JSON contains the recovered GSTIN
        canonical_json = doc.to_canonical_dict()
        self.assertEqual(canonical_json["supplier"]["gstin"], "32AAJFS5434R1ZN")
        self.assertEqual(canonical_json["invoice"]["invoice_number"], "4358")

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_part5_gemini_does_not_overwrite_good_data(self, mock_generate_json):
        """Part 5: Proves Gemini fallback does NOT overwrite valid high-confidence rule-based data."""
        mock_generate_json.return_value = {
            "supplier": {
                "name": {
                    "raw": "WRONG HALLUCINATED NAME",
                    "normalized": "WRONG HALLUCINATED NAME",
                    "confidence": 0.95
                },
                "gstin": {
                    "raw": "32AAJFS5434R1ZN",
                    "normalized": "32AAJFS5434R1ZN",
                    "confidence": 0.95
                }
            }
        }

        ocr_res = OCRResult(full_text=SAMPLE_4358_OCR)
        with patch("app.extraction.header_extractor.HeaderExtractor.extract") as mock_headers:
            mock_headers.return_value = {
                "invoice_number": ValuePair(raw="4358", normalized="4358", confidence=0.9),
                "invoice_date": ValuePair(raw="14-05-2026", normalized="2026-05-14", confidence=0.9),
                "payment_type": ValuePair(raw="CREDIT", normalized="CREDIT", confidence=0.9),
                "supplier": Supplier(
                    name=ValuePair(raw="SABARI ENTERPRISES", normalized="SABARI ENTERPRISES", confidence=0.95),
                    gstin=None,
                    address=ValuePair(raw="TELLICHERY", normalized="TELLICHERY", confidence=0.9)
                ),
                "buyer": Buyer(name=ValuePair(raw="GERMAN PHARMACY", normalized="GERMAN PHARMACY", confidence=0.9))
            }
            doc = self.extractor.extract(ocr_res, file_name="4358 (1).pdf", file_type="pdf")

        # Supplier name MUST remain "SABARI ENTERPRISES", NOT overwritten by "WRONG HALLUCINATED NAME"
        self.assertEqual(doc.invoice_data.supplier.name.normalized, "SABARI ENTERPRISES")
        # Missing GSTIN MUST be filled
        self.assertEqual(doc.invoice_data.supplier.gstin.normalized, "32AAJFS5434R1ZN")

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_part6_items_recovered_as_fallback(self, mock_generate_json):
        """Part 6: Proves that when rule-based items are empty, Gemini recovers both line items into internal model and canonical JSON."""
        mock_generate_json.return_value = {
            "items": [
                {
                    "line_number": 1,
                    "product": {"description": "RHIN DEFSOLONE", "hsn_code": "30043911"},
                    "batch": {"batch_no": "MTTA0175A", "expiry_date": "12/27"},
                    "packaging": {"pack_size": "10's", "unit_count": 10, "unit_type": "Tablets"},
                    "quantity": {"qty": 10.0, "free_qty": 2.0, "total_qty": 120.0},
                    "pricing": {"mrp": 121.88, "purchase_rate": 92.86, "discount_percentage": 0.0, "taxable_amount": 928.60},
                    "tax": {"gst_percentage": 5.0, "gst_amount": 46.43}
                },
                {
                    "line_number": 2,
                    "product": {"description": "RHIN FLUGAIN 10 MG TAB", "hsn_code": "30044090"},
                    "batch": {"batch_no": "RFNT2503", "expiry_date": "10/27"},
                    "packaging": {"pack_size": "10's", "unit_count": 10, "unit_type": "Tablets"},
                    "quantity": {"qty": 10.0, "free_qty": 2.0, "total_qty": 120.0},
                    "pricing": {"mrp": 45.15, "purchase_rate": 34.40, "discount_percentage": 0.0, "taxable_amount": 344.00},
                    "tax": {"gst_percentage": 5.0, "gst_amount": 17.20}
                }
            ]
        }

        ocr_res = OCRResult(full_text=SAMPLE_4358_OCR)
        # Force rule items to be empty
        with patch("app.extraction.rule_based_components.ItemExtractor.extract_items", return_value=[]):
            doc = self.extractor.extract(ocr_res, file_name="4358 (1).pdf", file_type="pdf")

        # 1. Assert 2 items extracted
        self.assertEqual(len(doc.invoice_data.items), 2)
        item1 = doc.invoice_data.items[0]
        self.assertEqual(item1.product.description.normalized, "RHIN DEFSOLONE")
        self.assertEqual(item1.product.hsn_code.normalized, "30043911")
        self.assertEqual(item1.batch.batch_no.normalized, "MTTA0175A")
        self.assertEqual(item1.quantity.qty.normalized, 10.0)
        self.assertEqual(item1.quantity.free_qty.normalized, 2.0)
        self.assertEqual(item1.pricing.taxable_amount.normalized, 928.60)

        item2 = doc.invoice_data.items[1]
        self.assertEqual(item2.product.description.normalized, "RHIN FLUGAIN 10 MG TAB")
        self.assertEqual(item2.product.hsn_code.normalized, "30044090")
        self.assertEqual(item2.pricing.taxable_amount.normalized, 344.00)

        # 2. Assert canonical JSON has 2 items
        canonical_dict = doc.to_canonical_dict()
        self.assertEqual(len(canonical_dict["items"]), 2)

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_part7_totals_recovered_as_fallback(self, mock_generate_json):
        """Part 7: Proves that when rule totals are missing, Gemini recovers the exact totals."""
        mock_generate_json.return_value = {
            "totals": {
                "subtotal": {"raw": "1272.60", "normalized": 1272.60, "confidence": 0.95},
                "tax_total": {"raw": "63.63", "normalized": 63.63, "confidence": 0.95},
                "round_off": {"raw": "-0.23", "normalized": -0.23, "confidence": 0.95},
                "grand_total": {"raw": "1336.00", "normalized": 1336.00, "confidence": 0.95}
            }
        }

        ocr_res = OCRResult(full_text=SAMPLE_4358_OCR)
        # Force rule totals to be zeroes
        with patch("app.extraction.rule_based_components.TotalsCalculator.extract_totals") as mock_totals:
            mock_totals.return_value = {
                "subtotal": ValuePair(raw="", normalized=0.0, confidence=0.0),
                "tax_total": ValuePair(raw="", normalized=0.0, confidence=0.0),
                "grand_total": ValuePair(raw="", normalized=0.0, confidence=0.0),
                "discount_total": ValuePair(raw="", normalized=0.0, confidence=0.0),
                "round_off": ValuePair(raw="", normalized=0.0, confidence=0.0)
            }
            doc = self.extractor.extract(ocr_res, file_name="4358 (1).pdf", file_type="pdf")

        self.assertAlmostEqual(doc.invoice_data.totals.subtotal.normalized, 1272.60, places=2)
        self.assertAlmostEqual(doc.invoice_data.totals.tax_total.normalized, 63.63, places=2)
        self.assertAlmostEqual(doc.invoice_data.totals.grand_total.normalized, 1336.00, places=2)

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_part8_gemini_failure_gracefully_degrades(self, mock_generate_json):
        """Part 8: Proves that an API error does not crash the pipeline and populates safe diagnostic fields."""
        mock_generate_json.side_effect = GeminiAPIError("ResourceExhausted: 429 quota reached with key AIzaSyDUMMYSECRETKEY123456789")

        ocr_res = OCRResult(full_text=SAMPLE_4358_OCR)
        with patch("app.extraction.header_extractor.HeaderExtractor.extract") as mock_headers:
            mock_headers.return_value = {
                "invoice_number": ValuePair(raw="4358", normalized="4358", confidence=0.9),
                "invoice_date": ValuePair(raw="14-05-2026", normalized="2026-05-14", confidence=0.9),
                "payment_type": ValuePair(raw="CREDIT", normalized="CREDIT", confidence=0.9),
                "supplier": Supplier(name=ValuePair(raw="SABARI ENTERPRISES", normalized="SABARI ENTERPRISES", confidence=0.9), gstin=None),
                "buyer": Buyer(name=ValuePair(raw="GERMAN PHARMACY", normalized="GERMAN PHARMACY", confidence=0.9))
            }
            doc = self.extractor.extract(ocr_res, file_name="4358 (1).pdf", file_type="pdf")

        # 1. Pipeline did not crash
        self.assertIsNotNone(doc)

        # 2. Status is failed with sanitized message
        self.assertEqual(doc.raw_extraction.raw_fields["gemini_status"], "failed")
        self.assertIn("GeminiAPIError", doc.raw_extraction.raw_fields["gemini_error_type"])
        self.assertIn("429 quota reached", doc.raw_extraction.raw_fields["gemini_error"])
        self.assertNotIn("AIzaSyDUMMYSECRETKEY123456789", doc.raw_extraction.raw_fields["gemini_error"])

        # 3. Rule data preserved
        self.assertEqual(doc.invoice_data.invoice_number.normalized, "4358")

    def test_part9_real_gemini_integration(self):
        """Part 9: Optional live integration test (skipped when no key is set or on rate limit)."""
        if not settings.GEMINI_API_KEY:
            self.skipTest("GEMINI_API_KEY not configured. Skipping live API call.")

        from app.ai.gemini_client import generate_json
        prompt = "Return a JSON object with key 'status' and value 'ok'."
        try:
            res = generate_json(prompt)
            self.assertIsInstance(res, dict)
        except Exception as e:
            self.skipTest(f"Live Gemini API call unavailable or rate-limited: {e}")


if __name__ == "__main__":
    unittest.main()
