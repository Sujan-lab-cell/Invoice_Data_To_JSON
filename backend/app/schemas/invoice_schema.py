from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MappingStatus(str, Enum):
    """
    Status of the mapping between the supplier product and the internal inventory item master.
    """
    MATCHED_EXACT = "matched_exact"
    MATCHED_FUZZY = "matched_fuzzy"
    UNMAPPED = "unmapped"
    MULTIPLE_MATCHES = "multiple_matches"
    NEW_ITEM_SUGGESTED = "new_item_suggested"
    IGNORE = "ignore"


class ValuePair(BaseModel):
    """
    Keeps both the raw extracted string and the normalized/converted typed value.
    """
    raw: str = Field(..., description="The raw value exactly as extracted from the invoice.")
    normalized: Optional[Any] = Field(None, description="The normalized/parsed type-specific value.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Field extraction confidence score (0.0 to 1.0).")


class Supplier(BaseModel):
    """
    Information about the selling pharmacy distributor/supplier.
    """
    name: ValuePair = Field(..., description="Supplier company name.")
    gstin: Optional[ValuePair] = Field(None, description="Supplier GST Identification Number.")
    address: Optional[ValuePair] = Field(None, description="Supplier physical address.")
    phone: Optional[ValuePair] = Field(None, description="Supplier contact number.")
    state: Optional[ValuePair] = Field(None, description="Supplier state.")


class Buyer(BaseModel):
    """
    Information about the buying pharmacy entity.
    """
    name: ValuePair = Field(..., description="Buyer pharmacy name.")
    gstin: Optional[ValuePair] = Field(None, description="Buyer GST Identification Number.")
    address: Optional[ValuePair] = Field(None, description="Buyer delivery address.")
    phone: Optional[ValuePair] = Field(None, description="Buyer contact number.")
    state: Optional[ValuePair] = Field(None, description="Buyer state.")


class Product(BaseModel):
    """
    Details of the product as identified on the supplier's invoice.
    """
    product_code: Optional[ValuePair] = Field(None, description="Supplier code/SKU for the item.")
    description: ValuePair = Field(..., description="Product name or description on invoice.")
    hsn_code: Optional[ValuePair] = Field(None, description="Harmonized System of Nomenclature code.")


class Batch(BaseModel):
    """
    Pharmacy batch details for drug tracking.
    """
    batch_no: ValuePair = Field(..., description="Manufacturer batch/lot number.")
    expiry_date: ValuePair = Field(..., description="Expiry date of the batch.")


class Packaging(BaseModel):
    """
    Packaging and composition details for pharmaceutical products.
    """
    pack_size: str = Field(..., description="Raw pack size descriptor (e.g. '10 Tabs', '100ml Bottle').")
    unit_count: int = Field(..., description="Calculated quantity of units inside a single pack (e.g. 10 for a strip of 10).")
    unit_type: str = Field(..., description="The standardized type of unit (e.g. 'Tablets', 'Capsules', 'Vial', 'Syrup').")


class Quantity(BaseModel):
    """
    Quantity details including packs, free items, and packaging sizes.
    """
    qty: ValuePair = Field(..., description="Purchased quantity (packs or units).")
    free_qty: Optional[ValuePair] = Field(None, description="Free quantity supplied under promotional schemes.")
    total_qty: float = Field(..., description="Total unit or pack count (qty + free_qty).")


class Pricing(BaseModel):
    """
    Price details at unit and total levels.
    """
    mrp: ValuePair = Field(..., description="Maximum Retail Price (selling limit).")
    purchase_rate: ValuePair = Field(..., description="Purchase price per unit/pack from distributor.")
    discount_percentage: Optional[ValuePair] = Field(None, description="Discount rate percentage applied.")
    discount_amount: Optional[ValuePair] = Field(None, description="Calculated absolute discount amount.")
    taxable_amount: ValuePair = Field(..., description="Subtotal amount subject to tax after discounts.")


class Tax(BaseModel):
    """
    Breakdown of GST/taxes applied to the item.
    """
    cgst_percentage: Optional[ValuePair] = Field(None, description="Central GST rate percentage.")
    sgst_percentage: Optional[ValuePair] = Field(None, description="State GST rate percentage.")
    igst_percentage: Optional[ValuePair] = Field(None, description="Integrated GST rate percentage.")
    cgst_amount: Optional[ValuePair] = Field(None, description="Central GST tax amount.")
    sgst_amount: Optional[ValuePair] = Field(None, description="State GST tax amount.")
    igst_amount: Optional[ValuePair] = Field(None, description="Integrated GST tax amount.")
    gst_percentage: ValuePair = Field(..., description="Combined total GST percentage applied.")
    gst_amount: ValuePair = Field(..., description="Combined total GST tax amount.")


class InventoryAction(BaseModel):
    """
    Match mapping determination between the distributor item and the ERP inventory master.
    """
    internal_item_id: Optional[str] = Field(None, description="Matched internal item master primary key.")
    internal_item_name: Optional[str] = Field(None, description="Name of mapped internal item master record.")
    status: MappingStatus = Field(MappingStatus.UNMAPPED, description="Inventory mapping action status.")
    match_score: float = Field(0.0, description="Fuzzy string matching score (0.0 to 100.0).")
    suggestions: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Fuzzy matching alternative items and scores."
    )


class Confidence(BaseModel):
    """
    Aggregated extraction confidence scores across different stages.
    """
    ocr: float = Field(1.0, ge=0.0, le=1.0, description="OCR text recognition average confidence.")
    extraction: float = Field(1.0, ge=0.0, le=1.0, description="AI extraction/parsing confidence.")
    matching: float = Field(1.0, ge=0.0, le=1.0, description="Fuzzy matching confidence score.")


class InvoiceItem(BaseModel):
    """
    A single line item representing a pharmaceutical product in the invoice.
    """
    line_number: int = Field(..., description="Sequential line index (1-based).")
    product: Product = Field(..., description="Product details.")
    batch: Batch = Field(..., description="Batch details.")
    packaging: Packaging = Field(..., description="Packaging details.")
    quantity: Quantity = Field(..., description="Quantity metrics.")
    pricing: Pricing = Field(..., description="Pricing metrics.")
    tax: Tax = Field(..., description="Tax breakdowns.")
    inventory_action: InventoryAction = Field(
        default_factory=InventoryAction,
        description="Inventory matching action configuration. Never auto-saved."
    )


class Totals(BaseModel):
    """
    Aggregated totals for the entire invoice.
    """
    subtotal: ValuePair = Field(..., description="Sum of line taxable amounts before taxes.")
    discount_total: Optional[ValuePair] = Field(None, description="Sum of discount amounts.")
    tax_total: ValuePair = Field(..., description="Sum of GST/taxes applied.")
    grand_total: ValuePair = Field(..., description="Total invoice amount payable (Subtotal + Taxes).")
    round_off: Optional[ValuePair] = Field(None, description="Adjustment amount to round total to nearest integer.")


class TaxSummaryItem(BaseModel):
    """
    Subtotals grouped under a specific GST tax rate.
    """
    tax_rate: float = Field(..., description="GST Tax percentage rate (e.g. 5.0, 12.0, 18.0).")
    taxable_amount: float = Field(..., description="Sum of taxable amounts at this rate.")
    cgst_amount: float = Field(0.0, description="Sum of CGST tax at this rate.")
    sgst_amount: float = Field(0.0, description="Sum of SGST tax at this rate.")
    igst_amount: float = Field(0.0, description="Sum of IGST tax at this rate.")
    total_gst_amount: float = Field(..., description="Sum of combined GST taxes (cgst + sgst + igst) at this rate.")


class TaxSummary(BaseModel):
    """
    Invoice-level tax summary grid grouped by GST rate.
    """
    items: List[TaxSummaryItem] = Field(default_factory=list, description="GST summaries grouped by tax percentage rates.")


class ValidationIssue(BaseModel):
    """
    Describes an automated rule validation warning or error.
    """
    field: str = Field(..., description="Field path that triggered the rule, e.g. 'totals.grand_total'.")
    rule: str = Field(..., description="Name of validation rule.")
    message: str = Field(..., description="Human readable description of validation mismatch.")
    severity: str = Field(..., description="Severity of mismatch: 'error' or 'warning'.")


class Validation(BaseModel):
    """
    Validation results of mathematical and logical checks conforming to mentor format.
    """
    is_valid: bool = Field(True, description="True if no severe 'error' issues are present.")
    has_errors: bool = Field(False, description="True if error count > 0.")
    has_warnings: bool = Field(False, description="True if warning count > 0.")
    error_count: int = Field(0, description="Total count of error severity issues.")
    warning_count: int = Field(0, description="Total count of warning severity issues.")
    confidence_score: float = Field(1.0, description="Overall validation confidence score.")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Mathematical validation errors/warnings.")


class Review(BaseModel):
    """
    Human-in-the-loop review audit trail conforming to mentor format.
    """
    requires_review: bool = Field(True, description="Flags if manual review is needed.")
    reason: Optional[str] = Field(None, description="Primary reason triggering review request.")
    review_reasons: List[str] = Field(default_factory=list, description="Detailed list of reasons requiring review.")
    reviewed_by: Optional[str] = Field(None, description="User identifier of reviewer.")
    reviewed_at: Optional[str] = Field(None, description="ISO Timestamp of review completion.")
    is_approved: bool = Field(False, description="Flag indicating if review approved entry to ERP.")
    approval_notes: Optional[str] = Field(None, description="Optional notes from reviewer.")


class RawExtraction(BaseModel):
    """
    Holds raw unstructured output from intermediate extraction phases for audit.
    """
    ocr_text_snippet: Optional[str] = Field(None, description="Raw OCR snippet linked to this model.")
    raw_json: Optional[str] = Field(None, description="Raw JSON output returned from the extraction provider.")
    raw_fields: Dict[str, str] = Field(default_factory=dict, description="KeyValue pairs exactly as extracted by the provider.")


class Invoice(BaseModel):
    """
    The canonical parsed structure representing a Pharmacy invoice.
    """
    invoice_number: ValuePair = Field(..., description="Unique invoice ID reference.")
    invoice_date: ValuePair = Field(..., description="Date of invoice issue.")
    due_date: Optional[ValuePair] = Field(None, description="Due date of invoice payment.")
    order_number: Optional[ValuePair] = Field(None, description="Order or PO number.")
    payment_type: Optional[ValuePair] = Field(None, description="Payment type (e.g. CREDIT, CASH).")
    supplier: Supplier = Field(..., description="Supplier details.")
    buyer: Buyer = Field(..., description="Buyer/Hospital details.")
    items: List[InvoiceItem] = Field(..., description="Table of product line items.")
    totals: Totals = Field(..., description="Aggregated invoice totals.")
    tax_summary: TaxSummary = Field(default_factory=TaxSummary, description="GST summaries grouped by tax percentage rates.")


class Document(BaseModel):
    """
    The top-level model representing the processed document artifact.
    """
    source_file_name: str = Field(..., description="Name of the parsed source file.")
    source_file_type: str = Field(..., description="Format type: 'pdf', 'image', 'csv', 'excel'.")
    confidence: Confidence = Field(default_factory=Confidence, description="Granular extraction confidence metrics.")
    invoice_data: Optional[Invoice] = Field(None, description="Canonical invoice data parsed from source.")
    raw_extraction: Optional[RawExtraction] = Field(None, description="Intermediate extraction audit payloads.")
    validation: Validation = Field(default_factory=Validation, description="Auto-calculation validation checks.")
    review: Review = Field(default_factory=Review, description="Human review status block.")

    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Maps extracted fields into the canonical 10 top-level sections:
        document, invoice, supplier, buyer, items, totals, tax_summary,
        validation, review, raw_extraction.
        """
        from app.schemas.canonical_schema import CanonicalNormalizer
        return CanonicalNormalizer.normalize(self).model_dump()
