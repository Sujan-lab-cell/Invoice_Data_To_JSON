import json
import unittest
from pathlib import Path

from app.ocr.easyocr_engine import EasyOCREngine
from app.parsers.pdf_parser import PDFParser
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.extraction.item_extractor import ItemExtractor
from app.schemas.canonical_schema import (
    CanonicalNormalizer,
    CanonicalDocument,
    CanonicalItem,
    CanonicalProduct,
    CanonicalBatch,
    CanonicalPackaging,
    CanonicalQuantity,
    CanonicalPricing,
    CanonicalTax,
    CanonicalInventoryAction,
)
from app.schemas.invoice_schema import (
    Document,
    Invoice,
    Supplier,
    Buyer,
    Product,
    Batch,
    Packaging,
    Quantity,
    Pricing,
    Tax,
    InvoiceItem,
    Totals,
    TaxSummary,
    TaxSummaryItem,
    Validation,
    Review,
    RawExtraction,
    Confidence,
    ValuePair,
)


class TestCanonicalJSONNormalization(unittest.TestCase):
    """
    Unit tests validating the mentor's canonical JSON output normalization.
    Tests:
    1. Canonical top-level structure (10 sections)
    2. Canonical item structure (8 sub-objects)
    3. Raw and normalized value preservation
    4. Default unmapped inventory status ("unmapped")
    5. Missing optional fields becoming null
    6. Parity with real sample PDF invoice extraction
    """

    @classmethod
    def setUpClass(cls):
        cls.ocr_engine = EasyOCREngine()
        cls.pdf_parser = PDFParser(ocr_engine=cls.ocr_engine)
        cls.hybrid_extractor = HybridInvoiceExtractor()
        cls.sample_dir = Path(__file__).resolve().parent / "sample_invoices"

    def test_canonical_top_level_structure(self):
        """Verify the 10 top-level keys in canonical normalized output."""
        doc = Document(
            source_file_name="test_invoice.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.95, extraction=0.9, matching=0.8),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="INV-100", normalized="INV-100", confidence=1.0),
                invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
                supplier=Supplier(name=ValuePair(raw="ABC PHARMA", normalized="ABC PHARMA", confidence=1.0)),
                buyer=Buyer(name=ValuePair(raw="XYZ CLINIC", normalized="XYZ CLINIC", confidence=1.0)),
                items=[],
                totals=Totals(
                    subtotal=ValuePair(raw="100.00", normalized=100.00, confidence=1.0),
                    tax_total=ValuePair(raw="5.00", normalized=5.00, confidence=1.0),
                    grand_total=ValuePair(raw="105.00", normalized=105.00, confidence=1.0),
                ),
            ),
        )

        canonical_doc = CanonicalNormalizer.normalize(doc)
        data = canonical_doc.model_dump()

        expected_keys = [
            "document",
            "invoice",
            "supplier",
            "buyer",
            "items",
            "totals",
            "tax_summary",
            "validation",
            "review",
            "raw_extraction",
        ]

        self.assertEqual(list(data.keys()), expected_keys)
        self.assertIsInstance(data["document"], dict)
        self.assertIsInstance(data["invoice"], dict)
        self.assertIsInstance(data["supplier"], dict)
        self.assertIsInstance(data["buyer"], dict)
        self.assertIsInstance(data["items"], list)
        self.assertIsInstance(data["totals"], dict)
        self.assertIsInstance(data["tax_summary"], list)
        self.assertIsInstance(data["validation"], dict)
        self.assertIsInstance(data["review"], dict)
        self.assertIsInstance(data["raw_extraction"], dict)

    def test_canonical_item_structure_and_defaults(self):
        """Verify the 8 sub-objects per item and default unmapped inventory values."""
        item = InvoiceItem(
            line_number=1,
            product=Product(
                product_code=ValuePair(raw="MED01", normalized="MED01", confidence=1.0),
                description=ValuePair(raw="PARACETAMOL 500MG", normalized="PARACETAMOL 500MG", confidence=1.0),
                hsn_code=ValuePair(raw="30049000", normalized="30049000", confidence=1.0),
            ),
            batch=Batch(
                batch_no=ValuePair(raw="B123", normalized="B123", confidence=1.0),
                expiry_date=ValuePair(raw="12/26", normalized="12/26", confidence=1.0),
            ),
            packaging=Packaging(pack_size="10 Tabs", unit_count=10, unit_type="Tablets"),
            quantity=Quantity(
                qty=ValuePair(raw="2", normalized=2.0, confidence=1.0),
                free_qty=None,
                total_qty=20.0,
            ),
            pricing=Pricing(
                mrp=ValuePair(raw="20.00", normalized=20.0, confidence=1.0),
                purchase_rate=ValuePair(raw="15.00", normalized=15.0, confidence=1.0),
                taxable_amount=ValuePair(raw="30.00", normalized=30.0, confidence=1.0),
            ),
            tax=Tax(
                gst_percentage=ValuePair(raw="12", normalized=12.0, confidence=1.0),
                gst_amount=ValuePair(raw="3.60", normalized=3.60, confidence=1.0),
            ),
        )

        canonical_item = CanonicalNormalizer.normalize_item(item)
        item_dict = canonical_item.model_dump()

        # Check sub-objects
        self.assertIn("product", item_dict)
        self.assertIn("batch", item_dict)
        self.assertIn("packaging", item_dict)
        self.assertIn("quantity", item_dict)
        self.assertIn("pricing", item_dict)
        self.assertIn("tax", item_dict)
        self.assertIn("inventory_action", item_dict)
        self.assertIn("confidence", item_dict)

        # Check Product fields
        prod = item_dict["product"]
        self.assertEqual(prod["supplier_product_code"], "MED01")
        self.assertEqual(prod["name"], "PARACETAMOL 500MG")
        self.assertEqual(prod["normalized_name"], "PARACETAMOL 500MG")
        self.assertEqual(prod["hsn_code"], "30049000")
        self.assertEqual(prod["item_mapping_status"], "unmapped")
        self.assertIsNone(prod["inventory_item_id"])
        self.assertIsNone(prod["barcode"])
        self.assertIsNone(prod["manufacturer"])

        # Check Batch fields
        batch = item_dict["batch"]
        self.assertEqual(batch["batch_number"], "B123")
        self.assertEqual(batch["expiry_date"], "12/26")
        self.assertEqual(batch["expiry_raw"], "12/26")

        # Check Quantity fields
        qty = item_dict["quantity"]
        self.assertEqual(qty["billed_quantity"], 2.0)
        self.assertEqual(qty["free_quantity"], 0.0)
        self.assertEqual(qty["total_received_quantity"], 20.0)
        self.assertEqual(qty["quantity_raw"], "2")
        self.assertIsNone(qty["free_quantity_raw"])

        # Check Pricing fields
        pr = item_dict["pricing"]
        self.assertEqual(pr["ptr"], 15.0)
        self.assertEqual(pr["purchase_rate"], 15.0)
        self.assertEqual(pr["mrp"], 20.0)
        self.assertEqual(pr["taxable_amount"], 30.0)
        self.assertEqual(pr["net_amount"], 33.60)
        self.assertIsNone(pr["sale_rate"])

        # Check Tax fields
        tx = item_dict["tax"]
        self.assertEqual(tx["gst_percent"], 12.0)
        self.assertEqual(tx["total_tax_amount"], 3.60)
        self.assertEqual(tx["tax_type"], "GST")

        # Check Inventory Action defaults
        act = item_dict["inventory_action"]
        self.assertFalse(act["should_create_batch"])
        self.assertFalse(act["should_update_stock"])
        self.assertTrue(act["requires_manual_review"])
        self.assertEqual(act["review_reason"], "Item is unmapped to inventory master")

    def test_raw_and_normalized_preservation(self):
        """Verify headers and totals preserve both raw and normalized values."""
        doc = Document(
            source_file_name="test.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.9, extraction=1.0, matching=0.8),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="00123", normalized="123", confidence=1.0),
                invoice_date=ValuePair(raw="08/05/2026", normalized="2026-05-08", confidence=1.0),
                supplier=Supplier(
                    name=ValuePair(raw="ABC DISTRIBUTORS", normalized="ABC DISTRIBUTORS", confidence=1.0),
                    gstin=ValuePair(raw="32AABFV9893M1ZF", normalized="32AABFV9893M1ZF", confidence=1.0),
                    address=ValuePair(raw="Kannur, Kerala", normalized="Kannur, Kerala", confidence=1.0),
                    phone=ValuePair(raw="0497-2801582", normalized="0497-2801582", confidence=1.0),
                    state=ValuePair(raw="Kerala", normalized="Kerala", confidence=1.0),
                ),
                buyer=Buyer(
                    name=ValuePair(raw="CITY PHARMACY", normalized="CITY PHARMACY", confidence=1.0),
                ),
                items=[],
                totals=Totals(
                    subtotal=ValuePair(raw="500.00", normalized=500.0, confidence=1.0),
                    tax_total=ValuePair(raw="60.00", normalized=60.0, confidence=1.0),
                    grand_total=ValuePair(raw="560.00", normalized=560.0, confidence=1.0),
                ),
            ),
        )

        canonical = CanonicalNormalizer.normalize(doc)
        data = canonical.model_dump()

        self.assertEqual(data["invoice"]["invoice_number"], "123")
        self.assertEqual(data["invoice"]["invoice_number_raw"], "00123")
        self.assertEqual(data["invoice"]["invoice_date"], "2026-05-08")
        self.assertEqual(data["invoice"]["invoice_date_raw"], "08/05/2026")

        self.assertEqual(data["supplier"]["name"], "ABC DISTRIBUTORS")
        self.assertEqual(data["supplier"]["name_raw"], "ABC DISTRIBUTORS")

        self.assertEqual(data["totals"]["grand_total"], 560.0)
        self.assertEqual(data["totals"]["grand_total_raw"], "560.00")

    def test_missing_optional_fields_become_null(self):
        """Verify that optional missing fields serialize as null."""
        doc = Document(
            source_file_name="minimal.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.8, extraction=0.8, matching=0.8),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="INV-1", normalized="INV-1", confidence=1.0),
                invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
                due_date=None,
                order_number=None,
                payment_type=None,
                supplier=Supplier(name=ValuePair(raw="SUP", normalized="SUP", confidence=1.0)),
                buyer=Buyer(name=ValuePair(raw="BUY", normalized="BUY", confidence=1.0)),
                items=[],
                totals=Totals(
                    subtotal=ValuePair(raw="0", normalized=0.0, confidence=1.0),
                    tax_total=ValuePair(raw="0", normalized=0.0, confidence=1.0),
                    grand_total=ValuePair(raw="0", normalized=0.0, confidence=1.0),
                ),
            ),
        )

        canonical = CanonicalNormalizer.normalize(doc)
        data = canonical.model_dump()

        self.assertIsNone(data["invoice"]["due_date"])
        self.assertIsNone(data["invoice"]["order_number"])
        self.assertIsNone(data["invoice"]["payment_type"])
        self.assertIsNone(data["supplier"]["gstin"])
        self.assertIsNone(data["supplier"]["phone"])
        self.assertIsNone(data["buyer"]["address"])

    def test_pdf_invoice_tradelink_canonical_normalization(self):
        """Verify normalization against 4220 (1).pdf extracting 8 items."""
        fname = "4220 (1).pdf"
        fpath = self.sample_dir / fname
        if not fpath.exists():
            self.skipTest("Sample file missing")

        parse_res = self.pdf_parser.parse(str(fpath))
        items = ItemExtractor.extract_items(parse_res.full_text, ocr_result=parse_res)
        self.assertEqual(len(items), 8, f"Expected 8 items in 4220 (1).pdf, got {len(items)}")

        # Construct Document and normalize
        doc = self.hybrid_extractor.extract(parse_res, file_name=fname, file_type="pdf")
        canonical = CanonicalNormalizer.normalize(doc)
        data = canonical.model_dump()

        self.assertEqual(len(data["items"]), 8)
        self.assertEqual(data["supplier"]["name"], "TRADELINK")
        self.assertEqual(data["buyer"]["name"], "GERMAN PHARMACY")

        # Verify item fields
        item1 = data["items"][0]
        self.assertEqual(item1["product"]["normalized_name"], "SILGO 8MG CAPS")
        self.assertEqual(item1["product"]["item_mapping_status"], "unmapped")
        self.assertEqual(item1["batch"]["batch_number"], "AFSOE-2503")
        self.assertEqual(item1["batch"]["expiry_date"], "11/27")
        self.assertEqual(item1["quantity"]["billed_quantity"], 3.0)
        self.assertEqual(item1["pricing"]["purchase_rate"], 212.86)
        self.assertEqual(item1["pricing"]["mrp"], 279.38)
        self.assertEqual(item1["pricing"]["taxable_amount"], 638.58)


if __name__ == "__main__":
    unittest.main()
