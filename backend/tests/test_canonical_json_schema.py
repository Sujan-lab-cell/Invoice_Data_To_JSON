import json
import unittest
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
    ValidationIssue,
    Review,
    RawExtraction,
    Confidence,
    ValuePair,
    MappingStatus,
    InventoryAction,
)


class TestCanonicalJSONSchema(unittest.TestCase):
    """
    Tests for the canonical invoice JSON schema.
    Verifies that all 10 canonical sections:
    (document, invoice, supplier, buyer, items, totals, tax_summary, validation, review, raw_extraction)
    are properly mapped, typed, and preserve both raw and normalized values.
    """

    def setUp(self):
        self.sample_document = Document(
            source_file_name="sample_invoice.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.98, extraction=0.95, matching=1.0),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="INV-2026-001", normalized="INV-2026-001", confidence=1.0),
                invoice_date=ValuePair(raw="08-05-2026", normalized="2026-05-08", confidence=1.0),
                due_date=ValuePair(raw="22-05-2026", normalized="2026-05-22", confidence=0.9),
                order_number=ValuePair(raw="PO-9988", normalized="PO-9988", confidence=0.95),
                payment_type=ValuePair(raw="CREDIT", normalized="CREDIT", confidence=1.0),
                supplier=Supplier(
                    name=ValuePair(raw="VINAYAKA ENTERPRISES", normalized="VINAYAKA ENTERPRISES", confidence=1.0),
                    gstin=ValuePair(raw="32AABFV9893M1ZF", normalized="32AABFV9893M1ZF", confidence=1.0),
                    address=ValuePair(raw="Payyanur, Kannur - 670307", normalized="Payyanur, Kannur - 670307", confidence=1.0),
                    phone=ValuePair(raw="04985202475", normalized="04985202475", confidence=1.0),
                    state=ValuePair(raw="Kerala", normalized="Kerala", confidence=1.0),
                ),
                buyer=Buyer(
                    name=ValuePair(raw="GERMAN PHARMACY", normalized="GERMAN PHARMACY", confidence=1.0),
                    gstin=ValuePair(raw="32AAGCE9732J6ZC", normalized="32AAGCE9732J6ZC", confidence=1.0),
                    address=ValuePair(raw="KANNUR - 670662", normalized="KANNUR - 670662", confidence=1.0),
                    phone=ValuePair(raw="8129778297", normalized="8129778297", confidence=1.0),
                    state=ValuePair(raw="Kerala", normalized="Kerala", confidence=1.0),
                ),
                items=[
                    InvoiceItem(
                        line_number=1,
                        product=Product(
                            product_code=ValuePair(raw="MED001", normalized="MED001", confidence=1.0),
                            description=ValuePair(raw="EASODAY 40 MG 10X15", normalized="EASODAY 40 MG 10X15", confidence=0.9),
                            hsn_code=ValuePair(raw="30049034", normalized="30049034", confidence=0.9),
                        ),
                        batch=Batch(
                            batch_no=ValuePair(raw="APGT250937G", normalized="APGT250937G", confidence=0.95),
                            expiry_date=ValuePair(raw="05/27", normalized="05/27", confidence=0.95),
                        ),
                        packaging=Packaging(pack_size="10X15", unit_count=150, unit_type="Tablets"),
                        quantity=Quantity(
                            qty=ValuePair(raw="5", normalized=5.0, confidence=1.0),
                            free_qty=ValuePair(raw="0", normalized=0.0, confidence=1.0),
                            total_qty=750.0,
                        ),
                        pricing=Pricing(
                            mrp=ValuePair(raw="121.78", normalized=121.78, confidence=1.0),
                            purchase_rate=ValuePair(raw="91.85", normalized=91.85, confidence=1.0),
                            discount_percentage=ValuePair(raw="2.00", normalized=2.0, confidence=1.0),
                            discount_amount=ValuePair(raw="9.19", normalized=9.19, confidence=1.0),
                            taxable_amount=ValuePair(raw="450.07", normalized=450.07, confidence=1.0),
                        ),
                        tax=Tax(
                            cgst_percentage=ValuePair(raw="2.5", normalized=2.5, confidence=1.0),
                            sgst_percentage=ValuePair(raw="2.5", normalized=2.5, confidence=1.0),
                            igst_percentage=None,
                            cgst_amount=ValuePair(raw="11.25", normalized=11.25, confidence=1.0),
                            sgst_amount=ValuePair(raw="11.25", normalized=11.25, confidence=1.0),
                            igst_amount=None,
                            gst_percentage=ValuePair(raw="5.0", normalized=5.0, confidence=1.0),
                            gst_amount=ValuePair(raw="22.50", normalized=22.50, confidence=1.0),
                        ),
                        inventory_action=InventoryAction(
                            internal_item_id="INT-EASO-40",
                            internal_item_name="Easoday 40mg Tab",
                            status=MappingStatus.MATCHED_EXACT,
                            match_score=100.0,
                            suggestions=[],
                        ),
                    )
                ],
                totals=Totals(
                    subtotal=ValuePair(raw="450.07", normalized=450.07, confidence=1.0),
                    discount_total=ValuePair(raw="9.19", normalized=9.19, confidence=1.0),
                    tax_total=ValuePair(raw="22.50", normalized=22.50, confidence=1.0),
                    grand_total=ValuePair(raw="472.57", normalized=472.57, confidence=1.0),
                    round_off=ValuePair(raw="0.03", normalized=0.03, confidence=1.0),
                ),
                tax_summary=TaxSummary(
                    items=[
                        TaxSummaryItem(
                            tax_rate=5.0,
                            taxable_amount=450.07,
                            cgst_amount=11.25,
                            sgst_amount=11.25,
                            igst_amount=0.0,
                            total_gst_amount=22.50,
                        )
                    ]
                ),
            ),
            validation=Validation(
                is_valid=True,
                issues=[
                    ValidationIssue(
                        field="totals.grand_total",
                        rule="math_cross_check",
                        message="Calculated sum matches invoice grand total",
                        severity="info",
                    )
                ],
            ),
            review=Review(
                requires_review=False,
                reason="Automatic high-confidence extraction",
                reviewed_by="system",
                reviewed_at="2026-08-09T12:00:00Z",
                is_approved=True,
            ),
            raw_extraction=RawExtraction(
                ocr_text_snippet="VINAYAKA ENTERPRISES... INV-2026-001",
                raw_json='{"invoice_no": "INV-2026-001"}',
                raw_fields={"invoice_no": "INV-2026-001"},
            ),
        )

    def test_raw_and_normalized_preservation(self):
        """Verify ValuePair preserves raw, normalized, and confidence fields without data loss."""
        inv = self.sample_document.invoice_data
        self.assertEqual(inv.invoice_number.raw, "INV-2026-001")
        self.assertEqual(inv.invoice_number.normalized, "INV-2026-001")
        self.assertEqual(inv.invoice_number.confidence, 1.0)

        # Date normalization
        self.assertEqual(inv.invoice_date.raw, "08-05-2026")
        self.assertEqual(inv.invoice_date.normalized, "2026-05-08")

        # Numeric price fields
        item = inv.items[0]
        self.assertEqual(item.pricing.mrp.raw, "121.78")
        self.assertEqual(item.pricing.mrp.normalized, 121.78)
        self.assertEqual(item.pricing.taxable_amount.raw, "450.07")
        self.assertEqual(item.pricing.taxable_amount.normalized, 450.07)

    def test_canonical_10_sections_mapping(self):
        """Verify all 10 canonical sections exist in the exported canonical dictionary."""
        canonical_dict = self.sample_document.to_canonical_dict()

        expected_sections = [
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

        for section in expected_sections:
            self.assertIn(section, canonical_dict, f"Missing canonical section: '{section}'")

        # Verify section content types
        self.assertIsInstance(canonical_dict["document"], dict)
        self.assertIsInstance(canonical_dict["invoice"], dict)
        self.assertIsInstance(canonical_dict["supplier"], dict)
        self.assertIsInstance(canonical_dict["buyer"], dict)
        self.assertIsInstance(canonical_dict["items"], list)
        self.assertIsInstance(canonical_dict["totals"], dict)
        self.assertIsInstance(canonical_dict["tax_summary"], list)
        self.assertIsInstance(canonical_dict["validation"], dict)
        self.assertIsInstance(canonical_dict["review"], dict)
        self.assertIsInstance(canonical_dict["raw_extraction"], dict)

    def test_json_roundtrip_serialization(self):
        """Verify the Document model serializes cleanly to JSON and reconstructs identically."""
        json_str = self.sample_document.model_dump_json()
        self.assertIsInstance(json_str, str)

        parsed_data = json.loads(json_str)
        reconstructed_doc = Document.model_validate(parsed_data)

        self.assertEqual(reconstructed_doc.source_file_name, self.sample_document.source_file_name)
        self.assertEqual(reconstructed_doc.invoice_data.invoice_number.normalized, "INV-2026-001")
        self.assertEqual(len(reconstructed_doc.invoice_data.items), 1)
        self.assertEqual(reconstructed_doc.invoice_data.items[0].product.description.normalized, "EASODAY 40 MG 10X15")


if __name__ == "__main__":
    unittest.main()
