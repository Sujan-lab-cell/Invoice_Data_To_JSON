import sys
import unittest
from pathlib import Path
from PIL import Image

sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.extraction.text_preprocessor import TextPreprocessor
from app.extraction.header_extractor import HeaderExtractor


class TestImageHeaderExtraction(unittest.TestCase):
    """
    Unit tests for image-based (PNG and JPG) invoice header extraction, ensuring:
    1. Recipient banners ('ORIGINALFOR RECIPIENT', 'Subject to...') are ignored and actual company name is extracted.
    2. Multiline phone labels ('Phone\n9508399874') are parsed.
    3. Noisy OCR dates with punctuation and timestamps ('13 Apr; 2026 03.23 PM') are normalized to '2026-04-13'.
    """

    @classmethod
    def setUpClass(cls):
        cls.parser_service = ParserService()
        cls.sample_dir = Path(__file__).parent / "sample_invoices"
        
        # Ensure JPG sample exists
        cls.png_path = cls.sample_dir / "freeinvoice-stylish.png"
        cls.jpg_path = cls.sample_dir / "sample_invoice_test.jpg"
        if cls.png_path.exists() and not cls.jpg_path.exists():
            im = Image.open(cls.png_path).convert("RGB")
            im.save(cls.jpg_path, "JPEG")

    def _extract_header(self, file_path: Path):
        parse_result = self.parser_service.parse(str(file_path))
        raw_text = parse_result.get("text", "")
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        return HeaderExtractor.extract(cleaned_text)

    def test_freeinvoice_png_header(self):
        """Test freeinvoice-stylish.png extracts Ravi kumar, 9508399874, and 2026-04-13."""
        self.assertTrue(self.png_path.exists(), f"File missing: {self.png_path}")
        header = self._extract_header(self.png_path)
        
        supplier_name = header["supplier"]["name"]["raw"]
        supplier_phone = header["supplier"]["phone"]["raw"]
        invoice_date_norm = header["invoice_date"]["normalized"]

        print(f"\nPNG Supplier Name:  '{supplier_name}'")
        print(f"PNG Supplier Phone: '{supplier_phone}'")
        print(f"PNG Invoice Date:   '{invoice_date_norm}'")

        self.assertEqual(supplier_name.upper(), "RAVI KUMAR")
        self.assertNotIn("ORIGINALFOR", supplier_name.upper())
        self.assertEqual(supplier_phone, "9508399874")
        self.assertEqual(invoice_date_norm, "2026-04-13")

    def test_freeinvoice_jpg_header(self):
        """Test sample_invoice_test.jpg extracts Ravi kumar, 9508399874, and 2026-04-13."""
        self.assertTrue(self.jpg_path.exists(), f"File missing: {self.jpg_path}")
        header = self._extract_header(self.jpg_path)

        supplier_name = header["supplier"]["name"]["raw"]
        supplier_phone = header["supplier"]["phone"]["raw"]
        invoice_date_norm = header["invoice_date"]["normalized"]

        print(f"\nJPG Supplier Name:  '{supplier_name}'")
        print(f"JPG Supplier Phone: '{supplier_phone}'")
        print(f"JPG Invoice Date:   '{invoice_date_norm}'")

        self.assertEqual(supplier_name.upper(), "RAVI KUMAR")
        self.assertNotIn("ORIGINALFOR", supplier_name.upper())
        self.assertEqual(supplier_phone, "9508399874")
        self.assertEqual(invoice_date_norm, "2026-04-13")

    def test_pharma_template_png_header(self):
        """Test Pharma Invoice Template extracts Jeqline Pharmacy and ignores legal jurisdiction."""
        pharma_path = self.sample_dir / "Pharma Invoice Template Software for Medicine Distributors.png"
        self.assertTrue(pharma_path.exists(), f"File missing: {pharma_path}")
        header = self._extract_header(pharma_path)

        supplier_name = header["supplier"]["name"]["raw"]
        print(f"\nPharma Template Supplier Name: '{supplier_name}'")

        self.assertIn("JEQLINE PHARMACY", supplier_name.upper())
        self.assertNotIn("JURIDUCTION", supplier_name.upper())
        self.assertNotIn("JURISDICTION", supplier_name.upper())


if __name__ == "__main__":
    unittest.main()
