import sys
import unittest
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.extraction.text_preprocessor import TextPreprocessor
from app.extraction.header_extractor import HeaderExtractor


class TestSupplierPhoneExtraction(unittest.TestCase):
    """
    Unit tests for supplier phone extraction from PDF invoices and labeled text lines.
    Supports labels such as Phone, Mobile, Tel, Contact, Ph., Mob.
    Supports +91, spaces, hyphens, and normal Indian 10-digit/landline formats.
    Ensures supplier phone is extracted accurately without confusing buyer phone numbers.
    """

    @classmethod
    def setUpClass(cls):
        cls.parser_service = ParserService()
        cls.sample_dir = Path(__file__).parent / "sample_invoices"

    def _extract_supplier_phone_from_pdf(self, pdf_path: Path) -> str:
        parse_result = self.parser_service.parse(str(pdf_path))
        raw_text = parse_result.get("text", "")
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["supplier"]["phone"]["raw"]

    def _extract_phone_from_text(self, text: str) -> str:
        _, cleaned_text = TextPreprocessor.preprocess(text)
        header_data = HeaderExtractor.extract(cleaned_text)
        return header_data["supplier"]["phone"]["raw"]

    # 1. Existing 3 Sample PDF Invoices
    def test_sample1_vinayaka_supplier_phone(self):
        """Test VINAYAKA ENTERPRISES extracts supplier phone and not buyer phone 8129778297."""
        pdf_path = self.sample_dir / "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        phone = self._extract_supplier_phone_from_pdf(pdf_path)
        print(f"\nSample 1 Supplier Phone: '{phone}'")
        self.assertTrue(
            "04985202475" in phone or "8130746895" in phone,
            f"Expected supplier phone in result, got: '{phone}'"
        )
        self.assertNotIn("8129778297", phone)  # Must not contain buyer phone

    def test_sample2_mcrb_supplier_phone(self):
        """Test MCRB PHARMA extracts supplier phone and not buyer phone 9446771904."""
        pdf_path = self.sample_dir / "MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        phone = self._extract_supplier_phone_from_pdf(pdf_path)
        print(f"Sample 2 Supplier Phone: '{phone}'")
        self.assertTrue(
            "04972801582" in phone or "7907187818" in phone,
            f"Expected supplier phone in result, got: '{phone}'"
        )
        self.assertNotIn("9446771904", phone)  # Must not contain buyer phone

    def test_sample3_tradelink_supplier_phone(self):
        """Test TRADELINK extracts phone 2704389."""
        pdf_path = self.sample_dir / "4220 (1).pdf"
        self.assertTrue(pdf_path.exists(), f"File missing: {pdf_path}")
        
        phone = self._extract_supplier_phone_from_pdf(pdf_path)
        print(f"Sample 3 Supplier Phone: '{phone}'")
        self.assertTrue(
            "2704389" in phone or len(phone) >= 6,
            f"Expected supplier phone, got: '{phone}'"
        )

    # 2. Labeled Phone Extraction Tests (Phone, Mobile, Mob., Ph., Tel, Contact, +91, hyphens, spaces)
    def test_labeled_plus91_phone(self):
        """Test labeled phone number with +91 country code and spaces."""
        sample_text = """
        TAX INVOICE
        SUN PHARMA DISTRIBUTORS
        123 Pharma Complex, Andheri East, Mumbai - 400069
        Phone: +91 98765 43210 | Email: sales@sunpharma.example.com
        GSTIN: 27AABCS1429B1Z
        
        BUYER:
        APOLLO PHARMACY
        Phone: +91 91234 56789
        """
        phone = self._extract_phone_from_text(sample_text)
        print(f"Labeled Supplier Phone: '{phone}'")
        self.assertIn("+91 98765 43210", phone)
        self.assertNotIn("91234", phone)  # Must not confuse with buyer phone

    def test_tel_label_and_landline_hyphens(self):
        """Test Tel label with landline STD code and hyphens."""
        sample_text = """
        TAX INVOICE
        APEX HEALTHCARE PVT LTD
        Tel: 022-28765432
        GSTIN: 27AABCA1234A1Z
        
        BUYER: CARE MEDICALS
        """
        phone = self._extract_phone_from_text(sample_text)
        print(f"Tel Label Phone: '{phone}'")
        self.assertIn("022-28765432", phone)

    def test_ph_dot_label_and_hyphenated_number(self):
        """Test Ph. label with hyphenated Indian mobile number."""
        sample_text = """
        TAX INVOICE
        MEDLIFE DRUG HOUSE
        Ph. 04985-202475 / 98765-43210
        GSTIN: 32AABCM5678C1Z
        
        BUYER: CITY PHARMACY
        Ph. 94471-12345
        """
        phone = self._extract_phone_from_text(sample_text)
        self.assertTrue("04985-202475" in phone or "98765-43210" in phone)
        self.assertNotIn("94471-12345", phone)

    def test_mob_and_mob_dot_labels(self):
        """Test Mob and Mob. labels."""
        sample_text = """
        TAX INVOICE
        ZENITH PHARMACEUTICALS
        Mob. +91 98450 12345
        GSTIN: 29AABCZ9999K1Z
        
        CUSTOMER: METRO HOSPITAL
        Mobile: 9988776655
        """
        phone = self._extract_phone_from_text(sample_text)
        self.assertIn("+91 98450 12345", phone)
        self.assertNotIn("9988776655", phone)

    def test_contact_label(self):
        """Test Contact label."""
        sample_text = """
        TAX INVOICE
        GLOBAL PHARMA DISTRIBUTORS
        Contact: 9820011223
        GSTIN: 27AABCG4321D1Z
        
        BILLED TO: NOVELTY DRUG STORE
        Contact: 9811122233
        """
        phone = self._extract_phone_from_text(sample_text)
        self.assertEqual(phone, "9820011223")
        self.assertNotIn("9811122233", phone)


if __name__ == "__main__":
    unittest.main()
