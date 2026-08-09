import sys
import unittest
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.extraction.text_preprocessor import TextPreprocessor
from app.extraction.header_extractor import HeaderExtractor


class TestSupplierNameExtraction(unittest.TestCase):
    """
    Tests supplier name extraction on the debug report invoices to ensure
    barcodes, invoice copies, page numbers, and drug license headers are not mistaken for supplier names.
    """

    @classmethod
    def setUpClass(cls):
        cls.parser_service = ParserService()
        cls.sample_dir = Path(__file__).parent / "sample_invoices"

    def _extract_supplier_name(self, pdf_path: Path) -> str:
        parse_result = self.parser_service.parse(str(pdf_path))
        raw_text = parse_result.get("text", "")
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["supplier"]["name"]["raw"]

    def test_sample1_vinayaka_supplier_name(self):
        """Test VINAYAKA ENTERPRISES invoice ignores '*1758* INVOICE COPY (1) PAGE 1 OF 1'."""
        pdf_path = self.sample_dir / "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        supplier_name = self._extract_supplier_name(pdf_path)
        print(f"\nSample 1 Supplier Name: '{supplier_name}'")
        self.assertIn("VINAYAKA ENTERPRISES", supplier_name.upper())
        self.assertNotIn("INVOICE COPY", supplier_name.upper())
        self.assertNotIn("1758", supplier_name)
        self.assertNotIn("PAGE 1", supplier_name.upper())

    def test_sample2_mcrb_pharma_supplier_name(self):
        """Test MCRB PHARMA invoice ignores '*MCRB-25-26-8898*' and '08898'."""
        pdf_path = self.sample_dir / "MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        supplier_name = self._extract_supplier_name(pdf_path)
        print(f"Sample 2 Supplier Name: '{supplier_name}'")
        self.assertIn("MCRB PHARMA", supplier_name.upper())
        self.assertNotEqual(supplier_name, "8898")
        self.assertNotEqual(supplier_name, "08898")
        self.assertNotIn("TAX INVOICE", supplier_name.upper())

    def test_sample3_tradelink_supplier_name(self):
        """Test TRADELINK / EMMARLINK invoice ignores 'DRUG LIC NO' and noise."""
        pdf_path = self.sample_dir / "4220 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        supplier_name = self._extract_supplier_name(pdf_path)
        print(f"Sample 3 Supplier Name: '{supplier_name}'")
        self.assertTrue(
            "TRADELINK" in supplier_name.upper() or "EMMARLINK" in supplier_name.upper(),
            f"Expected TRADELINK or EMMARLINK, got: '{supplier_name}'"
        )
        self.assertNotIn("DRUG LIC", supplier_name.upper())
        self.assertNotIn("TAX INVOICE", supplier_name.upper())

    def test_synthetic_headers(self):
        """Test synthetic text with various common invoice header noise patterns."""
        noise_text = """
        *99999* TAX INVOICE ORIGINAL COPY Page 1 of 2
        DRUG LIC NO: 20B/12345, 21B/67890
        MEDLIFE HEALTHCARE DISTRIBUTORS PVT LTD
        Building 12, Industrial Area, Mumbai
        GSTIN: 27AABCM1234F1Z5
        
        BUYER: APOLLO PHARMACY
        """
        _, cleaned = TextPreprocessor.preprocess(noise_text)
        header_data = HeaderExtractor.extract(cleaned)
        supplier_name = header_data["supplier"]["name"]["raw"]
        print(f"Synthetic Header Supplier Name: '{supplier_name}'")
        self.assertIn("MEDLIFE HEALTHCARE", supplier_name.upper())


if __name__ == "__main__":
    unittest.main()
