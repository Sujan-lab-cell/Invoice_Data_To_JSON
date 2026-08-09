import unittest
from app.schemas.canonical_schema import CanonicalNormalizer
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
    Validation,
    ValidationIssue,
    Review,
    Confidence,
    ValuePair,
)


class TestCanonicalValidationAndReview(unittest.TestCase):
    """
    Tests for canonical validation and review sections conforming to mentor JSON format:
    - Validation: is_valid, has_errors, has_warnings, error_count, warning_count, confidence_score, issues
    - Review: requires_review, reason, review_reasons, reviewed_by, reviewed_at, is_approved, approval_notes
    - Inventory unmapped status and null inventory_item_id preservation
    """

    def test_validation_clean_pass(self):
        """Test validation structure when all checks pass cleanly."""
        doc = Document(
            source_file_name="clean_invoice.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.98, extraction=1.0, matching=0.8),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="1001", normalized="1001", confidence=1.0),
                invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
                supplier=Supplier(name=ValuePair(raw="ABC DISTRIBUTORS", normalized="ABC DISTRIBUTORS", confidence=1.0)),
                buyer=Buyer(name=ValuePair(raw="XYZ PHARMACY", normalized="XYZ PHARMACY", confidence=1.0)),
                items=[
                    InvoiceItem(
                        line_number=1,
                        product=Product(
                            description=ValuePair(raw="PARACETAMOL 500MG", normalized="PARACETAMOL 500MG", confidence=1.0)
                        ),
                        batch=Batch(batch_no=ValuePair(raw="B1", normalized="B1", confidence=1.0), expiry_date=ValuePair(raw="12/26", normalized="12/26", confidence=1.0)),
                        packaging=Packaging(pack_size="10S", unit_count=10, unit_type="Tablets"),
                        quantity=Quantity(qty=ValuePair(raw="1", normalized=1.0, confidence=1.0), free_qty=None, total_qty=10.0),
                        pricing=Pricing(
                            mrp=ValuePair(raw="10.00", normalized=10.0, confidence=1.0),
                            purchase_rate=ValuePair(raw="8.00", normalized=8.0, confidence=1.0),
                            taxable_amount=ValuePair(raw="8.00", normalized=8.0, confidence=1.0),
                        ),
                        tax=Tax(
                            gst_percentage=ValuePair(raw="5", normalized=5.0, confidence=1.0),
                            gst_amount=ValuePair(raw="0.40", normalized=0.40, confidence=1.0),
                        ),
                    )
                ],
                totals=Totals(
                    subtotal=ValuePair(raw="8.00", normalized=8.00, confidence=1.0),
                    tax_total=ValuePair(raw="0.40", normalized=0.40, confidence=1.0),
                    grand_total=ValuePair(raw="8.40", normalized=8.40, confidence=1.0),
                ),
            ),
            validation=Validation(
                is_valid=True,
                has_errors=False,
                has_warnings=False,
                error_count=0,
                warning_count=0,
                confidence_score=1.0,
                issues=[],
            ),
            review=Review(
                requires_review=False,
                reason=None,
                reviewed_by=None,
                reviewed_at=None,
                is_approved=False,
            ),
        )

        canonical = CanonicalNormalizer.normalize(doc)
        val = canonical.validation
        rev = canonical.review

        # Validation assertions
        self.assertTrue(val.is_valid)
        self.assertFalse(val.has_errors)
        self.assertFalse(val.has_warnings)
        self.assertEqual(val.error_count, 0)
        self.assertEqual(val.warning_count, 0)
        self.assertEqual(val.confidence_score, 1.0)
        self.assertEqual(val.issues, [])

        # Review assertions - since item is unmapped, requires_review becomes True with reason
        self.assertTrue(rev.requires_review)
        self.assertTrue(any("unmapped" in r for r in rev.review_reasons))
        self.assertFalse(rev.is_approved)

    def test_validation_with_warnings_and_errors(self):
        """Test validation structure with mathematical mismatch and missing field."""
        doc = Document(
            source_file_name="mismatch_invoice.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.85, extraction=0.7, matching=0.5),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="", normalized="", confidence=0.0),
                invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
                supplier=Supplier(name=ValuePair(raw="ABC DISTRIBUTORS", normalized="ABC DISTRIBUTORS", confidence=1.0)),
                buyer=Buyer(name=ValuePair(raw="XYZ PHARMACY", normalized="XYZ PHARMACY", confidence=1.0)),
                items=[],
                totals=Totals(
                    subtotal=ValuePair(raw="100.00", normalized=100.00, confidence=1.0),
                    tax_total=ValuePair(raw="5.00", normalized=5.00, confidence=1.0),
                    grand_total=ValuePair(raw="200.00", normalized=200.00, confidence=1.0),
                ),
            ),
            validation=Validation(
                is_valid=False,
                has_errors=True,
                has_warnings=True,
                error_count=1,
                warning_count=1,
                confidence_score=0.75,
                issues=[
                    ValidationIssue(
                        field="invoice_number",
                        rule="missing_invoice_number",
                        message="Invoice number is missing or empty.",
                        severity="error",
                    ),
                    ValidationIssue(
                        field="totals.grand_total",
                        rule="grand_total_mismatch",
                        message="Subtotal + Tax does not match grand total.",
                        severity="warning",
                    ),
                ],
            ),
            review=Review(
                requires_review=True,
                reason="Validation errors present",
                review_reasons=["Validation errors present"],
                is_approved=False,
            ),
        )

        canonical = CanonicalNormalizer.normalize(doc)
        val = canonical.validation
        rev = canonical.review

        # Validation checks
        self.assertFalse(val.is_valid)
        self.assertTrue(val.has_errors)
        self.assertTrue(val.has_warnings)
        self.assertEqual(val.error_count, 1)
        self.assertEqual(val.warning_count, 1)
        self.assertEqual(len(val.issues), 2)

        # Review checks
        self.assertTrue(rev.requires_review)
        self.assertTrue(any("error" in r for r in rev.review_reasons))
        self.assertFalse(rev.is_approved)

    def test_item_unmapped_invariants(self):
        """Verify item_mapping_status is 'unmapped' and inventory_item_id is null."""
        doc = Document(
            source_file_name="item_test.pdf",
            source_file_type="pdf",
            confidence=Confidence(ocr=0.95, extraction=0.9, matching=0.8),
            invoice_data=Invoice(
                invoice_number=ValuePair(raw="123", normalized="123", confidence=1.0),
                invoice_date=ValuePair(raw="01-01-2026", normalized="2026-01-01", confidence=1.0),
                supplier=Supplier(name=ValuePair(raw="SUP", normalized="SUP", confidence=1.0)),
                buyer=Buyer(name=ValuePair(raw="BUY", normalized="BUY", confidence=1.0)),
                items=[
                    InvoiceItem(
                        line_number=1,
                        product=Product(description=ValuePair(raw="TEST DRUG", normalized="TEST DRUG", confidence=1.0)),
                        batch=Batch(batch_no=ValuePair(raw="B99", normalized="B99", confidence=1.0), expiry_date=ValuePair(raw="01/28", normalized="01/28", confidence=1.0)),
                        packaging=Packaging(pack_size="10S", unit_count=10, unit_type="Tablets"),
                        quantity=Quantity(qty=ValuePair(raw="5", normalized=5.0, confidence=1.0), free_qty=None, total_qty=50.0),
                        pricing=Pricing(mrp=ValuePair(raw="50", normalized=50.0, confidence=1.0), purchase_rate=ValuePair(raw="40", normalized=40.0, confidence=1.0), taxable_amount=ValuePair(raw="200", normalized=200.0, confidence=1.0)),
                        tax=Tax(gst_percentage=ValuePair(raw="5", normalized=5.0, confidence=1.0), gst_amount=ValuePair(raw="10", normalized=10.0, confidence=1.0)),
                    )
                ],
                totals=Totals(subtotal=ValuePair(raw="200", normalized=200.0, confidence=1.0), tax_total=ValuePair(raw="10", normalized=10.0, confidence=1.0), grand_total=ValuePair(raw="210", normalized=210.0, confidence=1.0)),
            ),
        )

        canonical = CanonicalNormalizer.normalize(doc)
        item = canonical.items[0]

        self.assertEqual(item.product.item_mapping_status, "unmapped")
        self.assertIsNone(item.product.inventory_item_id)
        self.assertFalse(item.inventory_action.should_create_batch)
        self.assertFalse(item.inventory_action.should_update_stock)
        self.assertTrue(item.inventory_action.requires_manual_review)


if __name__ == "__main__":
    unittest.main()
