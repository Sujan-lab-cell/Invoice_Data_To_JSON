from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.invoice_schema import Document, InvoiceItem, TaxSummaryItem


class CanonicalMappingStatus(str, Enum):
    MATCHED_EXACT = "matched_exact"
    MATCHED_FUZZY = "matched_fuzzy"
    UNMAPPED = "unmapped"
    MULTIPLE_MATCHES = "multiple_matches"
    NEW_ITEM_SUGGESTED = "new_item_suggested"


class CanonicalProduct(BaseModel):
    supplier_product_code: Optional[str] = Field(None, description="Supplier item code / SKU.")
    barcode: Optional[str] = Field(None, description="Product barcode.")
    name: Optional[str] = Field(None, description="Raw product description.")
    normalized_name: Optional[str] = Field(None, description="Normalized product name.")
    manufacturer: Optional[str] = Field(None, description="Product manufacturer / brand.")
    manufacturer_code: Optional[str] = Field(None, description="Manufacturer code.")
    hsn_code: Optional[str] = Field(None, description="HSN/SAC code.")
    inventory_item_id: Optional[str] = Field(None, description="Internal ERP inventory item ID.")
    item_mapping_status: str = Field(CanonicalMappingStatus.UNMAPPED.value, description="Mapping status with master.")


class CanonicalBatch(BaseModel):
    batch_number: Optional[str] = Field(None, description="Normalized batch number.")
    expiry_date: Optional[str] = Field(None, description="Normalized expiry date.")
    expiry_raw: Optional[str] = Field(None, description="Raw expiry date string.")


class CanonicalPackaging(BaseModel):
    pack_size: Optional[str] = Field(None, description="Pack size descriptor.")
    unit_count: Optional[int] = Field(None, description="Units inside a pack.")
    unit_type: Optional[str] = Field(None, description="Type of unit.")


class CanonicalQuantity(BaseModel):
    billed_quantity: Optional[float] = Field(None, description="Billed purchase quantity.")
    free_quantity: Optional[float] = Field(None, description="Free / promotional quantity.")
    total_received_quantity: Optional[float] = Field(None, description="Total units received.")
    quantity_raw: Optional[str] = Field(None, description="Raw quantity string.")
    free_quantity_raw: Optional[str] = Field(None, description="Raw free quantity string.")


class CanonicalPricing(BaseModel):
    ptr: Optional[float] = Field(None, description="Price to retailer (PTR).")
    purchase_rate: Optional[float] = Field(None, description="Purchase rate.")
    sale_rate: Optional[float] = Field(None, description="Sale rate / retail rate.")
    mrp: Optional[float] = Field(None, description="Maximum Retail Price.")
    base_amount: Optional[float] = Field(None, description="Base amount before discount.")
    discount_percent: Optional[float] = Field(None, description="Discount percentage.")
    discount_amount: Optional[float] = Field(None, description="Discount amount.")
    taxable_amount: Optional[float] = Field(None, description="Taxable amount after discount.")
    net_amount: Optional[float] = Field(None, description="Net payable amount including taxes.")


class CanonicalTax(BaseModel):
    gst_percent: Optional[float] = Field(None, description="Total GST percentage.")
    cgst_percent: Optional[float] = Field(None, description="CGST percentage.")
    cgst_amount: Optional[float] = Field(None, description="CGST amount.")
    sgst_percent: Optional[float] = Field(None, description="SGST percentage.")
    sgst_amount: Optional[float] = Field(None, description="SGST amount.")
    igst_percent: Optional[float] = Field(None, description="IGST percentage.")
    igst_amount: Optional[float] = Field(None, description="IGST amount.")
    total_tax_amount: Optional[float] = Field(None, description="Combined GST amount.")
    tax_type: Optional[str] = Field("GST", description="Tax type identifier.")


class CanonicalInventoryAction(BaseModel):
    should_create_batch: bool = Field(False, description="Whether to auto-create batch in ERP.")
    should_update_stock: bool = Field(False, description="Whether to update stock.")
    requires_manual_review: bool = Field(True, description="Whether manual review is needed.")
    review_reason: Optional[str] = Field("Item is unmapped to inventory master", description="Reason for review.")


class CanonicalItem(BaseModel):
    line_number: int = Field(..., description="1-based line number.")
    product: CanonicalProduct = Field(..., description="Product details.")
    batch: CanonicalBatch = Field(..., description="Batch details.")
    packaging: CanonicalPackaging = Field(..., description="Packaging details.")
    quantity: CanonicalQuantity = Field(..., description="Quantity metrics.")
    pricing: CanonicalPricing = Field(..., description="Pricing metrics.")
    tax: CanonicalTax = Field(..., description="Tax breakdowns.")
    inventory_action: CanonicalInventoryAction = Field(default_factory=CanonicalInventoryAction, description="Inventory action.")
    confidence: float = Field(1.0, description="Item confidence score.")


class CanonicalDocumentMetadata(BaseModel):
    source_file_name: str
    source_file_type: str
    confidence: Dict[str, float]


class CanonicalInvoiceMetadata(BaseModel):
    invoice_number: Optional[str] = None
    invoice_number_raw: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_date_raw: Optional[str] = None
    due_date: Optional[str] = None
    due_date_raw: Optional[str] = None
    order_number: Optional[str] = None
    order_number_raw: Optional[str] = None
    payment_type: Optional[str] = None
    payment_type_raw: Optional[str] = None


class CanonicalPartyInfo(BaseModel):
    name: Optional[str] = None
    name_raw: Optional[str] = None
    gstin: Optional[str] = None
    gstin_raw: Optional[str] = None
    address: Optional[str] = None
    address_raw: Optional[str] = None
    phone: Optional[str] = None
    phone_raw: Optional[str] = None
    state: Optional[str] = None
    state_raw: Optional[str] = None


class CanonicalTotalsInfo(BaseModel):
    subtotal: Optional[float] = None
    subtotal_raw: Optional[str] = None
    discount_total: Optional[float] = None
    discount_total_raw: Optional[str] = None
    tax_total: Optional[float] = None
    tax_total_raw: Optional[str] = None
    grand_total: Optional[float] = None
    grand_total_raw: Optional[str] = None
    round_off: Optional[float] = None
    round_off_raw: Optional[str] = None


class CanonicalTaxSummaryItem(BaseModel):
    tax_rate: float
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    total_tax_amount: float


class CanonicalValidationInfo(BaseModel):
    is_valid: bool = True
    has_errors: bool = False
    has_warnings: bool = False
    error_count: int = 0
    warning_count: int = 0
    confidence_score: float = 1.0
    issues: List[Dict[str, Any]] = Field(default_factory=list)


class CanonicalReviewInfo(BaseModel):
    requires_review: bool = True
    reason: Optional[str] = None
    review_reasons: List[str] = Field(default_factory=list)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    is_approved: bool = False
    approval_notes: Optional[str] = None


class CanonicalRawExtractionInfo(BaseModel):
    ocr_text_snippet: Optional[str] = None
    raw_json: Optional[str] = None
    raw_fields: Dict[str, str] = Field(default_factory=dict)


class CanonicalDocument(BaseModel):
    """
    Mentor-approved Canonical JSON Output Format.
    Top-level structure:
    {
      "document": {},
      "invoice": {},
      "supplier": {},
      "buyer": {},
      "items": [],
      "totals": {},
      "tax_summary": [],
      "validation": {},
      "review": {},
      "raw_extraction": {}
    }
    """
    document: CanonicalDocumentMetadata
    invoice: CanonicalInvoiceMetadata
    supplier: CanonicalPartyInfo
    buyer: CanonicalPartyInfo
    items: List[CanonicalItem] = Field(default_factory=list)
    totals: CanonicalTotalsInfo
    tax_summary: List[CanonicalTaxSummaryItem] = Field(default_factory=list)
    validation: CanonicalValidationInfo
    review: CanonicalReviewInfo
    raw_extraction: CanonicalRawExtractionInfo


class CanonicalNormalizer:
    """
    Converts Document and Invoice models into the canonical JSON structure.
    """

    @classmethod
    def normalize_item(cls, item: InvoiceItem) -> CanonicalItem:
        # Product
        p = item.product
        prod = CanonicalProduct(
            supplier_product_code=p.product_code.normalized if p.product_code else None,
            barcode=None,
            name=p.description.raw if p.description else None,
            normalized_name=p.description.normalized if p.description else None,
            manufacturer=None,
            manufacturer_code=None,
            hsn_code=p.hsn_code.normalized if p.hsn_code else None,
            inventory_item_id=item.inventory_action.internal_item_id if item.inventory_action else None,
            item_mapping_status="unmapped",
        )

        # Batch
        b = item.batch
        batch = CanonicalBatch(
            batch_number=b.batch_no.normalized if b.batch_no else None,
            expiry_date=b.expiry_date.normalized if b.expiry_date else None,
            expiry_raw=b.expiry_date.raw if b.expiry_date else None,
        )

        # Packaging
        pkg = item.packaging
        packaging = CanonicalPackaging(
            pack_size=pkg.pack_size if pkg else None,
            unit_count=pkg.unit_count if pkg else None,
            unit_type=pkg.unit_type if pkg else None,
        )

        # Quantity
        q = item.quantity
        billed_qty = float(q.qty.normalized) if q and q.qty and q.qty.normalized is not None else None
        free_qty = float(q.free_qty.normalized) if q and q.free_qty and q.free_qty.normalized is not None else 0.0
        quantity = CanonicalQuantity(
            billed_quantity=billed_qty,
            free_quantity=free_qty,
            total_received_quantity=q.total_qty if q else None,
            quantity_raw=q.qty.raw if q and q.qty else None,
            free_quantity_raw=q.free_qty.raw if q and q.free_qty else None,
        )

        # Pricing
        pr = item.pricing
        purchase_rate = float(pr.purchase_rate.normalized) if pr and pr.purchase_rate and pr.purchase_rate.normalized is not None else None
        mrp = float(pr.mrp.normalized) if pr and pr.mrp and pr.mrp.normalized is not None else None
        taxable_amt = float(pr.taxable_amount.normalized) if pr and pr.taxable_amount and pr.taxable_amount.normalized is not None else None
        dis_pct = float(pr.discount_percentage.normalized) if pr and pr.discount_percentage and pr.discount_percentage.normalized is not None else 0.0
        dis_amt = float(pr.discount_amount.normalized) if pr and pr.discount_amount and pr.discount_amount.normalized is not None else 0.0
        
        # Calculate net_amount (taxable_amount + gst_amount)
        gst_amt = float(item.tax.gst_amount.normalized) if item.tax and item.tax.gst_amount and item.tax.gst_amount.normalized is not None else 0.0
        net_amt = round(taxable_amt + gst_amt, 2) if taxable_amt is not None else None

        pricing = CanonicalPricing(
            ptr=purchase_rate,
            purchase_rate=purchase_rate,
            sale_rate=None,
            mrp=mrp,
            base_amount=taxable_amt,
            discount_percent=dis_pct,
            discount_amount=dis_amt,
            taxable_amount=taxable_amt,
            net_amount=net_amt,
        )

        # Tax
        tx = item.tax
        tax = CanonicalTax(
            gst_percent=float(tx.gst_percentage.normalized) if tx and tx.gst_percentage and tx.gst_percentage.normalized is not None else None,
            cgst_percent=float(tx.cgst_percentage.normalized) if tx and tx.cgst_percentage and tx.cgst_percentage.normalized is not None else None,
            cgst_amount=float(tx.cgst_amount.normalized) if tx and tx.cgst_amount and tx.cgst_amount.normalized is not None else None,
            sgst_percent=float(tx.sgst_percentage.normalized) if tx and tx.sgst_percentage and tx.sgst_percentage.normalized is not None else None,
            sgst_amount=float(tx.sgst_amount.normalized) if tx and tx.sgst_amount and tx.sgst_amount.normalized is not None else None,
            igst_percent=float(tx.igst_percentage.normalized) if tx and tx.igst_percentage and tx.igst_percentage.normalized is not None else None,
            igst_amount=float(tx.igst_amount.normalized) if tx and tx.igst_amount and tx.igst_amount.normalized is not None else None,
            total_tax_amount=gst_amt if gst_amt > 0 else None,
            tax_type="GST",
        )

        # Inventory Action
        inv_action = CanonicalInventoryAction(
            should_create_batch=False,
            should_update_stock=False,
            requires_manual_review=True,
            review_reason="Item is unmapped to inventory master",
        )

        return CanonicalItem(
            line_number=item.line_number,
            product=prod,
            batch=batch,
            packaging=packaging,
            quantity=quantity,
            pricing=pricing,
            tax=tax,
            inventory_action=inv_action,
            confidence=0.9,
        )

    @classmethod
    def normalize(cls, doc: Document) -> CanonicalDocument:
        inv = doc.invoice_data

        # 1. Document
        doc_meta = CanonicalDocumentMetadata(
            source_file_name=doc.source_file_name,
            source_file_type=doc.source_file_type,
            confidence=doc.confidence.model_dump(),
        )

        # 2. Invoice
        inv_meta = CanonicalInvoiceMetadata(
            invoice_number=str(inv.invoice_number.normalized) if inv and inv.invoice_number and inv.invoice_number.normalized else None,
            invoice_number_raw=str(inv.invoice_number.raw) if inv and inv.invoice_number and inv.invoice_number.raw else None,
            invoice_date=str(inv.invoice_date.normalized) if inv and inv.invoice_date and inv.invoice_date.normalized else None,
            invoice_date_raw=str(inv.invoice_date.raw) if inv and inv.invoice_date and inv.invoice_date.raw else None,
            due_date=str(inv.due_date.normalized) if inv and inv.due_date and inv.due_date.normalized else None,
            due_date_raw=str(inv.due_date.raw) if inv and inv.due_date and inv.due_date.raw else None,
            order_number=str(inv.order_number.normalized) if inv and inv.order_number and inv.order_number.normalized else None,
            order_number_raw=str(inv.order_number.raw) if inv and inv.order_number and inv.order_number.raw else None,
            payment_type=str(inv.payment_type.normalized) if inv and inv.payment_type and inv.payment_type.normalized else None,
            payment_type_raw=str(inv.payment_type.raw) if inv and inv.payment_type and inv.payment_type.raw else None,
        )

        # 3. Supplier
        supp = inv.supplier if inv else None
        supp_info = CanonicalPartyInfo(
            name=str(supp.name.normalized) if supp and supp.name and supp.name.normalized else None,
            name_raw=str(supp.name.raw) if supp and supp.name and supp.name.raw else None,
            gstin=str(supp.gstin.normalized) if supp and supp.gstin and supp.gstin.normalized else None,
            gstin_raw=str(supp.gstin.raw) if supp and supp.gstin and supp.gstin.raw else None,
            address=str(supp.address.normalized) if supp and supp.address and supp.address.normalized else None,
            address_raw=str(supp.address.raw) if supp and supp.address and supp.address.raw else None,
            phone=str(supp.phone.normalized) if supp and supp.phone and supp.phone.normalized else None,
            phone_raw=str(supp.phone.raw) if supp and supp.phone and supp.phone.raw else None,
            state=str(supp.state.normalized) if supp and supp.state and supp.state.normalized else None,
            state_raw=str(supp.state.raw) if supp and supp.state and supp.state.raw else None,
        )

        # 4. Buyer
        byr = inv.buyer if inv else None
        buyer_info = CanonicalPartyInfo(
            name=str(byr.name.normalized) if byr and byr.name and byr.name.normalized else None,
            name_raw=str(byr.name.raw) if byr and byr.name and byr.name.raw else None,
            gstin=str(byr.gstin.normalized) if byr and byr.gstin and byr.gstin.normalized else None,
            gstin_raw=str(byr.gstin.raw) if byr and byr.gstin and byr.gstin.raw else None,
            address=str(byr.address.normalized) if byr and byr.address and byr.address.normalized else None,
            address_raw=str(byr.address.raw) if byr and byr.address and byr.address.raw else None,
            phone=str(byr.phone.normalized) if byr and byr.phone and byr.phone.normalized else None,
            phone_raw=str(byr.phone.raw) if byr and byr.phone and byr.phone.raw else None,
            state=str(byr.state.normalized) if byr and byr.state and byr.state.normalized else None,
            state_raw=str(byr.state.raw) if byr and byr.state and byr.state.raw else None,
        )

        # 5. Items
        canonical_items = [cls.normalize_item(it) for it in inv.items] if inv and inv.items else []

        # 6. Totals
        tot = inv.totals if inv else None
        totals_info = CanonicalTotalsInfo(
            subtotal=float(tot.subtotal.normalized) if tot and tot.subtotal and tot.subtotal.normalized is not None else None,
            subtotal_raw=str(tot.subtotal.raw) if tot and tot.subtotal and tot.subtotal.raw else None,
            discount_total=float(tot.discount_total.normalized) if tot and tot.discount_total and tot.discount_total.normalized is not None else None,
            discount_total_raw=str(tot.discount_total.raw) if tot and tot.discount_total and tot.discount_total.raw else None,
            tax_total=float(tot.tax_total.normalized) if tot and tot.tax_total and tot.tax_total.normalized is not None else None,
            tax_total_raw=str(tot.tax_total.raw) if tot and tot.tax_total and tot.tax_total.raw else None,
            grand_total=float(tot.grand_total.normalized) if tot and tot.grand_total and tot.grand_total.normalized is not None else None,
            grand_total_raw=str(tot.grand_total.raw) if tot and tot.grand_total and tot.grand_total.raw else None,
            round_off=float(tot.round_off.normalized) if tot and tot.round_off and tot.round_off.normalized is not None else None,
            round_off_raw=str(tot.round_off.raw) if tot and tot.round_off and tot.round_off.raw else None,
        )

        # 7. Tax Summary
        tax_summary_items = []
        if inv and inv.tax_summary and inv.tax_summary.items:
            for tsi in inv.tax_summary.items:
                tax_summary_items.append(
                    CanonicalTaxSummaryItem(
                        tax_rate=tsi.tax_rate,
                        taxable_amount=tsi.taxable_amount,
                        cgst_amount=tsi.cgst_amount,
                        sgst_amount=tsi.sgst_amount,
                        igst_amount=tsi.igst_amount,
                        total_tax_amount=tsi.total_gst_amount,
                    )
                )

        # 8. Validation
        v = doc.validation
        issues_list = [issue.model_dump() for issue in v.issues] if v and v.issues else []
        error_count = v.error_count if v else sum(1 for i in issues_list if i.get("severity") == "error")
        warning_count = v.warning_count if v else sum(1 for i in issues_list if i.get("severity") == "warning")
        has_errors = v.has_errors if v else (error_count > 0)
        has_warnings = v.has_warnings if v else (warning_count > 0)
        is_valid = v.is_valid if v else (not has_errors)
        conf_score = v.confidence_score if v else (round(doc.confidence.extraction, 2) if doc.confidence else 1.0)

        validation_info = CanonicalValidationInfo(
            is_valid=is_valid,
            has_errors=has_errors,
            has_warnings=has_warnings,
            error_count=error_count,
            warning_count=warning_count,
            confidence_score=conf_score,
            issues=issues_list,
        )

        # 9. Review
        review_reasons = []
        if doc.review and doc.review.reason:
            review_reasons.append(doc.review.reason)
        if doc.review and doc.review.review_reasons:
            for r in doc.review.review_reasons:
                if r not in review_reasons:
                    review_reasons.append(r)

        # Flag unmapped items
        if canonical_items:
            unmapped_items = [it for it in canonical_items if it.product.item_mapping_status == "unmapped"]
            if unmapped_items:
                unmapped_msg = f"{len(unmapped_items)} item(s) unmapped to inventory master"
                if unmapped_msg not in review_reasons:
                    review_reasons.append(unmapped_msg)

        if has_errors:
            err_msg = f"{error_count} validation error(s) detected"
            if err_msg not in review_reasons:
                review_reasons.append(err_msg)
        elif has_warnings:
            warn_msg = f"{warning_count} validation warning(s) detected"
            if warn_msg not in review_reasons:
                review_reasons.append(warn_msg)

        requires_review = len(review_reasons) > 0 or (doc.review.requires_review if doc.review else False)
        primary_reason = review_reasons[0] if review_reasons else (doc.review.reason if doc.review else None)

        review_info = CanonicalReviewInfo(
            requires_review=requires_review,
            reason=primary_reason,
            review_reasons=review_reasons,
            reviewed_by=doc.review.reviewed_by if doc.review else None,
            reviewed_at=doc.review.reviewed_at if doc.review else None,
            is_approved=doc.review.is_approved if doc.review else False,
            approval_notes=doc.review.approval_notes if doc.review else None,
        )

        # 10. Raw Extraction
        raw_ext = doc.raw_extraction
        raw_extraction_info = CanonicalRawExtractionInfo(
            ocr_text_snippet=raw_ext.ocr_text_snippet if raw_ext else None,
            raw_json=raw_ext.raw_json if raw_ext else None,
            raw_fields=raw_ext.raw_fields if raw_ext else {},
        )

        return CanonicalDocument(
            document=doc_meta,
            invoice=inv_meta,
            supplier=supp_info,
            buyer=buyer_info,
            items=canonical_items,
            totals=totals_info,
            tax_summary=tax_summary_items,
            validation=validation_info,
            review=review_info,
            raw_extraction=raw_extraction_info,
        )
