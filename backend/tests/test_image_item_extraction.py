import unittest
from pathlib import Path

from app.ocr.easyocr_engine import EasyOCREngine
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.parsers.image_parser import ImageParser
from app.services.parser_service import ParserService


class TestImageItemExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocr_engine = EasyOCREngine()
        cls.image_parser = ImageParser(ocr_engine=cls.ocr_engine)
        cls.hybrid_extractor = HybridInvoiceExtractor()
        cls.sample_dir = Path(__file__).resolve().parent / "sample_invoices"

    def test_freeinvoice_stylish_png_item_count(self):
        """Verify freeinvoice-stylish.png extracts all 3 expected items."""
        img_path = self.sample_dir / "freeinvoice-stylish.png"
        if not img_path.exists():
            self.skipTest("Sample invoice not found")

        ocr_result = self.image_parser.parse(str(img_path))
        doc = self.hybrid_extractor.extract(ocr_result, file_name=img_path.name, file_type="image")

        self.assertIsNotNone(doc.invoice_data)
        items = doc.invoice_data.items
        self.assertEqual(len(items), 3, f"Expected 3 items in freeinvoice-stylish.png, got {len(items)}")

        # Validate item descriptions
        descriptions = [it.product.description.normalized for it in items]
        self.assertTrue(any("Tnermometer" in d for d in descriptions))
        self.assertTrue(any("SyringelNeedle" in d for d in descriptions))
        self.assertTrue(any("Instnumenis" in d for d in descriptions))

    def test_sample_invoice_jpg_item_count(self):
        """Verify sample_invoice_test.jpg extracts all 3 expected items."""
        img_path = self.sample_dir / "sample_invoice_test.jpg"
        if not img_path.exists():
            self.skipTest("Sample invoice not found")

        ocr_result = self.image_parser.parse(str(img_path))
        doc = self.hybrid_extractor.extract(ocr_result, file_name=img_path.name, file_type="image")

        self.assertIsNotNone(doc.invoice_data)
        items = doc.invoice_data.items
        self.assertEqual(len(items), 3, f"Expected 3 items in sample_invoice_test.jpg, got {len(items)}")

        descriptions = [it.product.description.normalized for it in items]
        self.assertTrue(any("Tnermomeler" in d or "Tnermometer" in d for d in descriptions))
        self.assertTrue(any("Syringe" in d for d in descriptions))
        self.assertTrue(any("Surgical" in d for d in descriptions))

    def test_pharma_template_png_item_count(self):
        """Verify Pharma Invoice Template extracts all 5 expected items."""
        img_path = self.sample_dir / "Pharma Invoice Template Software for Medicine Distributors.png"
        if not img_path.exists():
            self.skipTest("Sample invoice not found")

        ocr_result = self.image_parser.parse(str(img_path))
        doc = self.hybrid_extractor.extract(ocr_result, file_name=img_path.name, file_type="image")

        self.assertIsNotNone(doc.invoice_data)
        items = doc.invoice_data.items
        self.assertEqual(len(items), 5, f"Expected 5 items in Pharma Template, got {len(items)}")


if __name__ == "__main__":
    unittest.main()
