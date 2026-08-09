import unittest
from unittest.mock import patch

from app.ocr.schemas import OCRResult
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.ai.gemini_client import GeminiAPIError
from app.schemas.invoice_schema import ValuePair, Supplier, Buyer, Totals, Invoice


class TestGeminiFallbackDiagnostics(unittest.TestCase):
    """
    Tests ensuring that when Gemini fallback fails:
    1. Pipeline does not crash.
    2. gemini_status becomes 'failed'.
    3. gemini_error_type and gemini_error are populated.
    4. Secrets / API keys are sanitized and not leaked.
    5. Existing rule-based extractions are preserved.
    """

    def setUp(self):
        self.extractor = HybridInvoiceExtractor()

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_gemini_failure_captures_safe_diagnostics_without_crashing(self, mock_generate_json):
        # Simulate a Gemini API failure containing an API key in the error string
        mock_generate_json.side_effect = GeminiAPIError("429 Quota exceeded for key AIzaSyDUMMYKEY1234567890abcdefghijklm: limit 20 reached")

        # Create a mock OCR result that triggers fallback (empty text / missing fields)
        ocr_result = OCRResult(full_text="INVOICE 123\nDATE: 01/01/2026")

        doc = self.extractor.extract(ocr_result=ocr_result, file_name="sample_test.pdf", file_type="pdf")

        # 1. Pipeline did not crash and returned a Document
        self.assertIsNotNone(doc)

        # 2. Raw extraction fields contain diagnostic metadata
        raw_fields = doc.raw_extraction.raw_fields
        self.assertEqual(raw_fields.get("fallback_triggered"), "True")
        self.assertEqual(raw_fields.get("gemini_status"), "failed")
        self.assertIn("GeminiAPIError", raw_fields.get("gemini_error_type", ""))
        self.assertIn("429 Quota exceeded", raw_fields.get("gemini_error", ""))

        # 3. Verify API key was sanitized and redacted
        self.assertNotIn("AIzaSyDUMMYKEY1234567890abcdefghijklm", raw_fields.get("gemini_error", ""))
        self.assertIn("[REDACTED_API_KEY]", raw_fields.get("gemini_error", ""))

        # 4. Existing rule-based invoice data and validation are preserved
        self.assertIsNotNone(doc.invoice_data)
        self.assertIsNotNone(doc.validation)
        self.assertFalse(doc.validation.is_valid)

    @patch("app.ai.hybrid_extractor.generate_json")
    def test_gemini_success_sets_status_success(self, mock_generate_json):
        mock_generate_json.return_value = {
            "invoice": {"invoice_number": "INV-999", "invoice_date": "2026-05-14"},
            "supplier": {"name": "TEST SUPPLIER"},
            "buyer": {"name": "TEST BUYER"},
            "items": [],
            "totals": {"grand_total": 0.0}
        }

        ocr_result = OCRResult(full_text="INVOICE 123\nDATE: 01/01/2026")
        doc = self.extractor.extract(ocr_result=ocr_result, file_name="sample_test.pdf", file_type="pdf")

        raw_fields = doc.raw_extraction.raw_fields
        self.assertEqual(raw_fields.get("fallback_triggered"), "True")
        self.assertEqual(raw_fields.get("gemini_status"), "success")
        self.assertNotIn("gemini_error", raw_fields)


if __name__ == "__main__":
    unittest.main()
