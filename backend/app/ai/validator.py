import logging
from typing import List
from app.schemas.invoice_schema import Invoice, Validation, ValidationIssue

logger = logging.getLogger(__name__)


def validate_invoice(invoice: Invoice) -> Validation:
    """
    Validates the structure and mathematical consistency of the extracted Invoice data.

    Checks:
    - Critical header fields (invoice number, date, supplier name, buyer name).
    - Items presence.
    - Mathematical consistency:
      - Sum of item taxable amounts equals invoice subtotal.
      - Sum of GST amounts equals invoice GST total.
      - Subtotal + GST equals grand total.

    Returns:
        Validation: Validation model containing is_valid status and a list of warning/error issues.
    """
    issues: List[ValidationIssue] = []

    # 1. Critical Header Fields Validation (errors)
    if not invoice.invoice_number or not invoice.invoice_number.raw.strip():
        issues.append(
            ValidationIssue(
                field="invoice_number",
                rule="missing_invoice_number",
                message="Invoice number is missing or empty.",
                severity="error"
            )
        )

    if not invoice.invoice_date or not invoice.invoice_date.raw.strip():
        issues.append(
            ValidationIssue(
                field="invoice_date",
                rule="missing_invoice_date",
                message="Invoice date is missing or empty.",
                severity="error"
            )
        )

    if not invoice.supplier or not invoice.supplier.name or not invoice.supplier.name.raw.strip():
        issues.append(
            ValidationIssue(
                field="supplier.name",
                rule="missing_supplier_name",
                message="Supplier name is missing or empty.",
                severity="error"
            )
        )

    if not invoice.buyer or not invoice.buyer.name or not invoice.buyer.name.raw.strip():
        issues.append(
            ValidationIssue(
                field="buyer.name",
                rule="missing_buyer_name",
                message="Buyer name is missing or empty.",
                severity="error"
            )
        )

    # 2. Line Items Presence Validation (errors)
    if not invoice.items or len(invoice.items) == 0:
        issues.append(
            ValidationIssue(
                field="items",
                rule="missing_line_items",
                message="Invoice does not contain any line items.",
                severity="error"
            )
        )

    # 3. Mathematical Consistency Checks (warnings, does not raise exceptions)
    if invoice.items and len(invoice.items) > 0:
        # Sum of line-item taxable amounts vs subtotal
        sum_taxable = sum(
            float(item.pricing.taxable_amount.normalized)
            for item in invoice.items
            if item.pricing and item.pricing.taxable_amount and item.pricing.taxable_amount.normalized is not None
        )
        
        declared_subtotal = float(invoice.totals.subtotal.normalized) if invoice.totals.subtotal and invoice.totals.subtotal.normalized is not None else 0.0
        if abs(sum_taxable - declared_subtotal) > 2.0:
            issues.append(
                ValidationIssue(
                    field="totals.subtotal",
                    rule="subtotal_mismatch",
                    message=f"Sum of item taxable amounts ({sum_taxable:.2f}) does not match invoice subtotal ({declared_subtotal:.2f}).",
                    severity="warning"
                )
            )

        # Sum of line-item tax amounts vs total tax
        sum_tax = sum(
            float(item.tax.gst_amount.normalized)
            for item in invoice.items
            if item.tax and item.tax.gst_amount and item.tax.gst_amount.normalized is not None
        )
        
        declared_tax_total = float(invoice.totals.tax_total.normalized) if invoice.totals.tax_total and invoice.totals.tax_total.normalized is not None else 0.0
        if abs(sum_tax - declared_tax_total) > 2.0:
            issues.append(
                ValidationIssue(
                    field="totals.tax_total",
                    rule="tax_total_mismatch",
                    message=f"Sum of item GST tax amounts ({sum_tax:.2f}) does not match invoice tax total ({declared_tax_total:.2f}).",
                    severity="warning"
                )
            )

        # Grand Total Consistency check: Grand Total = Gross Amount (subtotal) - Discount + GST + Round Off
        declared_grand_total = float(invoice.totals.grand_total.normalized) if invoice.totals.grand_total and invoice.totals.grand_total.normalized is not None else 0.0
        declared_discount = float(invoice.totals.discount_total.normalized) if invoice.totals.discount_total and invoice.totals.discount_total.normalized is not None else 0.0
        declared_round_off = float(invoice.totals.round_off.normalized) if invoice.totals.round_off and invoice.totals.round_off.normalized is not None else 0.0
        
        calculated_grand_total = declared_subtotal - declared_discount + declared_tax_total + declared_round_off
        if abs(calculated_grand_total - declared_grand_total) > 2.0:
            issues.append(
                ValidationIssue(
                    field="totals.grand_total",
                    rule="grand_total_mismatch",
                    message=f"Subtotal - Discount + Tax + Round Off ({calculated_grand_total:.2f}) does not match invoice grand total ({declared_grand_total:.2f}).",
                    severity="warning"
                )
            )

    # Validation is considered invalid only if there is a severe 'error' severity issue
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    has_errors = error_count > 0
    has_warnings = warning_count > 0
    is_valid = not has_errors
    confidence_score = max(0.0, min(1.0, 1.0 - (error_count * 0.2 + warning_count * 0.05)))

    return Validation(
        is_valid=is_valid,
        has_errors=has_errors,
        has_warnings=has_warnings,
        error_count=error_count,
        warning_count=warning_count,
        confidence_score=confidence_score,
        issues=issues
    )
