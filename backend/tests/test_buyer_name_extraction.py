import sys
import unittest
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.extraction.text_preprocessor import TextPreprocessor
from app.extraction.header_extractor import HeaderExtractor


class TestBuyerNameExtraction(unittest.TestCase):
    """
    Unit tests for buyer name extraction from PDF invoices and labeled text lines.
    Supports labels such as Buyer, Customer, Billed To, Bill To, Receiver Details.
    Validates buyer names across the 3 sample PDF invoices and synthetic examples.
    """

    @classmethod
    def setUpClass(cls):
        cls.parser_service = ParserService()
        cls.sample_dir = Path(__file__).parent / "sample_invoices"

    def _extract_buyer_name_from_pdf(self, pdf_path: Path) -> str:
        parse_result = self.parser_service.parse(str(pdf_path))
        raw_text = parse_result.get("text", "")
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["buyer"]["name"]["raw"]

    def _extract_buyer_name_from_text(self, text: str) -> str:
        _, cleaned_text = TextPreprocessor.preprocess(text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["buyer"]["name"]["raw"]

    # 1. Tests for the 3 Sample PDF Invoices
    def test_sample1_vinayaka_buyer_name(self):
        """Test Sample 1 extracts buyer name 'GERMAN PHARMACY'."""
        pdf_path = self.sample_dir / "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")

        buyer_name = self._extract_buyer_name_from_pdf(pdf_path)
        print(f"\nSample 1 Buyer Name: '{buyer_name}'")
        self.assertEqual(buyer_name, "GERMAN PHARMACY")

    def test_sample2_mcrb_buyer_name(self):
        """Test Sample 2 extracts buyer name 'M M C PHARMACY'."""
        pdf_path = self.sample_dir / "MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")

        buyer_name = self._extract_buyer_name_from_pdf(pdf_path)
        print(f"Sample 2 Buyer Name: '{buyer_name}'")
        self.assertEqual(buyer_name, "M M C PHARMACY")

    def test_sample3_tradelink_buyer_name(self):
        """Test Sample 3 extracts buyer name 'GERMAN PHARMACY'."""
        pdf_path = self.sample_dir / "4220 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")

        buyer_name = self._extract_buyer_name_from_pdf(pdf_path)
        print(f"Sample 3 Buyer Name: '{buyer_name}'")
        self.assertEqual(buyer_name, "GERMAN PHARMACY")

    # 2. Tests for Labeled Buyer Sections
    def test_buyer_label(self):
        """Test explicit 'BUYER:' label."""
        text = """
        TAX INVOICE
        SUN PHARMA DISTRIBUTORS
        123 Pharma Complex, Andheri East, Mumbai - 400069
        
        BUYER:
        APOLLO PHARMACY
        456 Health Way, Bandra, Mumbai
        """
        buyer_name = self._extract_buyer_name_from_text(text)
        print(f"Explicit Buyer Label: '{buyer_name}'")
        self.assertEqual(buyer_name, "APOLLO PHARMACY")

    def test_billed_to_label(self):
        """Test 'BILLED TO:' label."""
        text = """
        TAX INVOICE
        MEDLIFE DISTRIBUTORS PVT LTD
        
        BILLED TO: NOVELTY DRUG STORE
        Address: Fort Road, Kannur
        """
        buyer_name = self._extract_buyer_name_from_text(text)
        print(f"Billed To Label: '{buyer_name}'")
        self.assertEqual(buyer_name, "NOVELTY DRUG STORE")

    def test_customer_label(self):
        """Test 'Customer:' label."""
        text = """
        TAX INVOICE
        ZENITH PHARMA
        
        Customer: METRO HOSPITAL & RESEARCH CENTRE
        GSTIN: 29AABCZ9999K1Z
        """
        buyer_name = self._extract_buyer_name_from_text(text)
        print(f"Customer Label: '{buyer_name}'")
        self.assertEqual(buyer_name, "METRO HOSPITAL & RESEARCH CENTRE")

    def test_receiver_details_label(self):
        """Test 'Receiver Details:' label."""
        text = """
        TAX INVOICE
        GLOBAL HEALTHCARE SUPPLIERS
        
        Receiver Details: CITY CARE MEDICALS
        """
        buyer_name = self._extract_buyer_name_from_text(text)
        print(f"Receiver Details Label: '{buyer_name}'")
        self.assertEqual(buyer_name, "CITY CARE MEDICALS")


if __name__ == "__main__":
    unittest.main()
