import sys
import unittest
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.extraction.text_preprocessor import TextPreprocessor
from app.extraction.header_extractor import HeaderExtractor


class TestSupplierAddressExtraction(unittest.TestCase):
    """
    Unit tests for supplier address extraction from invoice headers (both labeled and positional).
    """

    @classmethod
    def setUpClass(cls):
        cls.parser_service = ParserService()
        cls.sample_dir = Path(__file__).parent / "sample_invoices"

    def _extract_supplier_address(self, pdf_path: Path) -> str:
        parse_result = self.parser_service.parse(str(pdf_path))
        raw_text = parse_result.get("text", "")
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["supplier"]["address"]["raw"]

    def test_sample1_vinayaka_supplier_address(self):
        """Test VINAYAKA ENTERPRISES extracts address 'PAYYANUR, KANNUR DISTT'."""
        pdf_path = self.sample_dir / "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        address = self._extract_supplier_address(pdf_path)
        print(f"\nSample 1 Address: '{address}'")
        self.assertTrue(
            "PAYYANUR" in address.upper() or "KANNUR" in address.upper(),
            f"Expected PAYYANUR/KANNUR in address, got: '{address}'"
        )
        self.assertNotIn("GSTIN", address.upper())
        self.assertNotIn("INVOICE COPY", address.upper())

    def test_sample2_mcrb_supplier_address(self):
        """Test MCRB PHARMA extracts address with PILATHARA, PIN - 670504."""
        pdf_path = self.sample_dir / "MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        address = self._extract_supplier_address(pdf_path)
        print(f"Sample 2 Address: '{address}'")
        self.assertTrue(
            "PILATHARA" in address.upper() or "670504" in address or "MADAI" in address.upper(),
            f"Expected PILATHARA/670504 in address, got: '{address}'"
        )
        self.assertNotIn("GSTIN", address.upper())
        self.assertNotIn("TAX INVOICE", address.upper())

    def test_sample3_tradelink_supplier_address(self):
        """Test TRADELINK extracts address with DOOR NO:52/5265, HAJI BUILDING, FORT ROAD, KANNUR."""
        pdf_path = self.sample_dir / "4220 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        address = self._extract_supplier_address(pdf_path)
        print(f"Sample 3 Address: '{address}'")
        self.assertTrue(
            "52/5265" in address or "HAJI BUILDING" in address.upper() or "FORT ROAD" in address.upper() or "670001" in address,
            f"Expected HAJI BUILDING/FORT ROAD/52/5265 in address, got: '{address}'"
        )
        self.assertNotIn("TAX INVOICE", address.upper())

    def test_labeled_supplier_address(self):
        """Test invoice header with explicit 'Address:' label."""
        labeled_text = """
        TAX INVOICE
        SUN PHARMA DISTRIBUTORS
        Address: 123 Pharma Complex, Andheri East, Mumbai, Maharashtra - 400069
        Phone: +91 98765 43210
        GSTIN: 27AABCS1429B1Z
        
        BUYER: APOLLO PHARMACY
        """
        _, cleaned = TextPreprocessor.preprocess(labeled_text)
        header_data = HeaderExtractor.extract(cleaned)
        address = header_data["supplier"]["address"]["raw"]
        print(f"Labeled Header Address: '{address}'")
        self.assertIn("123 PHARMA COMPLEX", address.upper())
        self.assertIn("MUMBAI", address.upper())
        self.assertIn("400069", address)


if __name__ == "__main__":
    unittest.main()
