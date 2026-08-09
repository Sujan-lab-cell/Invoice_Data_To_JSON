import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from app.ocr.schemas import OCRResult
from app.schemas.invoice_schema import (
    Invoice,
    Document,
    Confidence,
    RawExtraction,
    Review,
    ValuePair,
    Supplier,
    Buyer,
    Totals,
    TaxSummary,
    TaxSummaryItem,
    InvoiceItem,
)
from app.extraction.header_extractor import HeaderExtractor
from app.extraction.rule_based_components import ItemExtractor, TotalsCalculator
from app.ai.gemini_client import generate_json
from app.ai.validator import validate_invoice

logger = logging.getLogger(__name__)


class HybridInvoiceExtractor:
    """
    Orchestrates the hybrid invoice extraction pipeline.
    Runs rule-based extractors, validates the results, and triggers Gemini AI fallback
    if ANY part (headers, supplier, buyer, items, pricing, totals) is left empty/missing,
    merging and re-validating the final output.
    """

    def extract(self, ocr_result: OCRResult, file_name: str = "invoice.pdf", file_type: str = "pdf") -> Document:
        """
        Executes the hybrid extraction pipeline.

        Args:
            ocr_result (OCRResult): Unified OCR text result from document.
            file_name (str): Original document file name.
            file_type (str): Type of file (pdf, image, csv, excel).

        Returns:
            Document: The parsed and validated canonical Document model.
        """
        logger.info("Executing hybrid extraction pipeline.")
        t_start = time.perf_counter()
        raw_text = ocr_result.full_text

        # Preprocess text
        t_prep_start = time.perf_counter()
        from app.extraction.text_preprocessor import TextPreprocessor
        _, cleaned_text = TextPreprocessor.preprocess(raw_text)
        t_prep = time.perf_counter() - t_prep_start

        # 1. Rule-Based Extraction
        logger.info("Step 1: Running rule-based extraction.")
        t_rules_start = time.perf_counter()
        partial_data = HeaderExtractor.extract(cleaned_text)
        
        # Add basic items and totals using rule components
        partial_data["items"] = ItemExtractor.extract_items(cleaned_text, ocr_result=ocr_result)
        partial_data["totals"] = TotalsCalculator.extract_totals(cleaned_text)
        t_rules = time.perf_counter() - t_rules_start

        # Instantiate a partial Invoice object
        try:
            invoice = Invoice.model_validate(partial_data)
        except Exception as e:
            logger.warning(f"Failed to instantiate partial Invoice model directly: {e}. Falling back to default initial structure.")
            invoice = Invoice(
                invoice_number=ValuePair(raw="", confidence=0.0),
                invoice_date=ValuePair(raw="", confidence=0.0),
                supplier=partial_data.get("supplier", Supplier(name=ValuePair(raw="", confidence=0.0))),
                buyer=partial_data.get("buyer", Buyer(name=ValuePair(raw="", confidence=0.0))),
                items=[],
                totals=partial_data.get("totals", Totals(subtotal=ValuePair(raw="0.00", normalized=0.0, confidence=0.0), tax_total=ValuePair(raw="0.00", normalized=0.0, confidence=0.0), grand_total=ValuePair(raw="0.00", normalized=0.0, confidence=0.0)))
            )

        # 2. Validation Checks
        logger.info("Step 2: Checking schema and math validation on partial JSON.")
        t_val1_start = time.perf_counter()
        validation = validate_invoice(invoice)
        t_val1 = time.perf_counter() - t_val1_start

        # 3. Decision Point: Has any missing data?
        # Trigger Gemini AI fallback if ANY part (headers, supplier, buyer, items, pricing, totals) is left empty/missing
        missing_data_detected = self._has_missing_data(invoice)

        gemini_raw_json = None
        gemini_status = "not_triggered"
        gemini_error_type = None
        gemini_error = None
        gemini_model_name = "gemini-2.5-flash"
        t_gemini = 0.0

        if missing_data_detected:
            gemini_status = "triggered"
            logger.info("Step 3: Missing fields/data detected after rule-based extraction. Triggering Gemini AI fallback.")
            prompt = self._build_gemini_prompt(raw_text)

            try:
                t_gemini_start = time.perf_counter()
                gemini_data = generate_json(prompt, model_name=gemini_model_name)
                
                # Sanitize value pairs to ensure 'raw' is always a string
                gemini_data = self._sanitize_value_pairs(gemini_data)
                gemini_raw_json = json.dumps(gemini_data, default=str)
                
                # Merge Gemini's extraction across all missing sections
                invoice = self._merge_gemini_extraction(invoice, gemini_data)
                t_gemini = time.perf_counter() - t_gemini_start
                gemini_status = "success"
                logger.info("Successfully merged Gemini AI fallback extraction into invoice.")
                
            except Exception as e:
                t_gemini = time.perf_counter() - t_gemini_start
                gemini_status = "failed"
                gemini_error_type = type(e).__name__

                root_cause = e.__cause__ if e.__cause__ is not None else e
                if root_cause and type(root_cause).__name__ != gemini_error_type:
                    gemini_error_type = f"{gemini_error_type}({type(root_cause).__name__})"

                sanitized_msg = self._sanitize_error_message(str(e))
                gemini_error = sanitized_msg

                logger.exception(
                    f"[GEMINI FALLBACK ERROR]\n"
                    f"Model: {gemini_model_name}\n"
                    f"Exception Type: {gemini_error_type}\n"
                    f"Sanitized Error Message: {sanitized_msg}"
                )
        else:
            logger.info("Step 3: All fields and items successfully parsed via rules. Skipping Gemini fallback.")

        # 5. Final Validation Check
        t_val2_start = time.perf_counter()
        final_validation = validate_invoice(invoice)
        t_val2 = time.perf_counter() - t_val2_start

        # Total pipeline time
        t_total = time.perf_counter() - t_start

        # 6. Build the Audit Payloads & Document wrapper
        raw_fields_dict = {
            "fallback_triggered": str(missing_data_detected),
            "gemini_status": gemini_status,
            "duration_preprocessing": f"{t_prep:.4f}s",
            "duration_rules": f"{t_rules:.4f}s",
            "duration_gemini": f"{t_gemini:.4f}s",
            "duration_validation": f"{(t_val1 + t_val2):.4f}s",
            "duration_pipeline": f"{t_total:.4f}s"
        }
        if gemini_status == "failed":
            raw_fields_dict["gemini_error_type"] = gemini_error_type
            raw_fields_dict["gemini_error"] = gemini_error
            raw_fields_dict["gemini_model"] = gemini_model_name
        elif gemini_status == "success":
            raw_fields_dict["gemini_model"] = gemini_model_name

        raw_extraction = RawExtraction(
            ocr_text_snippet=raw_text[:2000],
            raw_json=gemini_raw_json,
            raw_fields=raw_fields_dict
        )

        review = Review(
            requires_review=not final_validation.is_valid,
            reason="Validation errors present" if not final_validation.is_valid else "Automatic extraction completed",
            review_reasons=[issue.message for issue in final_validation.issues] if not final_validation.is_valid else [],
        )

        extraction_confidence = 1.0 if final_validation.is_valid else 0.7
        confidence = Confidence(
            ocr=0.9,
            extraction=extraction_confidence,
            matching=0.8
        )

        return Document(
            source_file_name=file_name,
            source_file_type=file_type,
            confidence=confidence,
            invoice_data=invoice,
            raw_extraction=raw_extraction,
            validation=final_validation,
            review=review
        )

    def _has_missing_data(self, invoice: Invoice) -> bool:
        """
        Determines if ANY part of the invoice (headers, supplier, buyer, items, pricing, totals)
        is empty, missing, or suspicious (low-confidence / mathematically inconsistent) after rule-based extraction.
        """
        # 1. Critical headers
        if not invoice.invoice_number or not str(invoice.invoice_number.raw).strip() or invoice.invoice_number.confidence < 0.6:
            return True
        if not invoice.invoice_date or not str(invoice.invoice_date.raw).strip() or invoice.invoice_date.confidence < 0.6:
            return True

        # 2. Supplier & Buyer details
        if not invoice.supplier or not invoice.supplier.name or not str(invoice.supplier.name.raw).strip() or invoice.supplier.name.confidence < 0.6:
            return True
        if not invoice.buyer or not invoice.buyer.name or not str(invoice.buyer.name.raw).strip() or invoice.buyer.name.confidence < 0.6:
            return True
        if not invoice.supplier.gstin or not str(invoice.supplier.gstin.raw).strip():
            return True
        if not invoice.supplier.address or not str(invoice.supplier.address.raw).strip():
            return True

        # 3. Line Items Quality and Consistency
        if not invoice.items or len(invoice.items) == 0:
            return True

        for item in invoice.items:
            # Missing product description
            if not item.product or not item.product.description or not str(item.product.description.raw).strip():
                return True
            
            # Missing or non-positive quantity
            if not item.quantity or item.quantity.qty is None or item.quantity.qty.normalized is None or item.quantity.qty.normalized <= 0:
                return True
            if item.quantity.qty.confidence < 0.7:
                return True

            # Missing or non-positive pricing details
            pricing = item.pricing
            if (not pricing or
                not pricing.purchase_rate or pricing.purchase_rate.normalized is None or pricing.purchase_rate.normalized <= 0.0 or
                not pricing.taxable_amount or pricing.taxable_amount.normalized is None or pricing.taxable_amount.normalized <= 0.0 or
                pricing.purchase_rate.confidence < 0.7 or
                pricing.taxable_amount.confidence < 0.7):
                return True

            # Mathematical consistency check per line item (qty * rate ≈ taxable_amount)
            qty_val = float(item.quantity.qty.normalized or 0.0)
            rate_val = float(pricing.purchase_rate.normalized or 0.0)
            taxable_val = float(pricing.taxable_amount.normalized or 0.0)
            if qty_val > 0 and rate_val > 0 and taxable_val > 0:
                expected_taxable = round(qty_val * rate_val, 2)
                dis_pct = float(pricing.discount_percentage.normalized or 0.0) if pricing.discount_percentage and pricing.discount_percentage.normalized is not None else 0.0
                expected_with_dis = round(expected_taxable * (1.0 - dis_pct / 100.0), 2)
                # If taxable differs by more than threshold from expected
                if abs(taxable_val - expected_with_dis) > max(2.0, 0.15 * expected_with_dis) and abs(taxable_val - expected_taxable) > max(2.0, 0.15 * expected_taxable):
                    return True # Suspicious line item math!

        # 4. Totals Quality and Consistency
        if not invoice.totals or not invoice.totals.grand_total or invoice.totals.grand_total.normalized is None or invoice.totals.grand_total.normalized <= 0.0 or invoice.totals.grand_total.confidence < 0.75:
            return True
        if not invoice.totals.subtotal or invoice.totals.subtotal.normalized is None or invoice.totals.subtotal.normalized <= 0.0 or invoice.totals.subtotal.confidence < 0.75:
            return True

        # Check total vs sum of line items
        sum_items_taxable = sum(
            float(it.pricing.taxable_amount.normalized or 0.0)
            for it in invoice.items
            if it.pricing and it.pricing.taxable_amount and it.pricing.taxable_amount.normalized is not None
        )
        if sum_items_taxable > 0 and invoice.totals.subtotal.normalized > 0:
            if abs(invoice.totals.subtotal.normalized - sum_items_taxable) > max(2.0, 0.15 * sum_items_taxable):
                return True # Suspicious totals vs items mismatch!

        return False

    def _merge_gemini_extraction(self, invoice: Invoice, gemini_data: Dict[str, Any]) -> Invoice:
        """
        Merges Gemini AI fallback extraction across all sections:
        - Invoice metadata (number, date, due_date, order_number, payment_type)
        - Supplier details (name, gstin, address, phone, state)
        - Buyer details (name, gstin, address, phone, state)
        - Items table
        - Totals and Tax Summary
        """
        if not isinstance(gemini_data, dict):
            return invoice

        totals_data = gemini_data.get("totals") if isinstance(gemini_data.get("totals"), dict) else {}

        # 1. Invoice Metadata
        inv_data = gemini_data.get("invoice") if isinstance(gemini_data.get("invoice"), dict) else gemini_data
        for field in ["invoice_number", "invoice_date", "due_date", "order_number", "payment_type"]:
            curr_val = getattr(invoice, field, None)
            if not curr_val or not str(curr_val.raw).strip() or curr_val.confidence < 0.75:
                if field in inv_data and inv_data[field] is not None:
                    vp = self._to_value_pair(inv_data[field])
                    if vp["raw"].strip():
                        setattr(invoice, field, ValuePair.model_validate(vp))

        # 2. Supplier Details
        supp_data = gemini_data.get("supplier") if isinstance(gemini_data.get("supplier"), dict) else {}
        if not invoice.supplier:
            invoice.supplier = Supplier(name=ValuePair(raw="", confidence=0.0))
        for field in ["name", "gstin", "address", "phone", "state"]:
            curr_val = getattr(invoice.supplier, field, None)
            if not curr_val or not str(curr_val.raw).strip() or curr_val.confidence < 0.75:
                if field in supp_data and supp_data[field] is not None:
                    vp = self._to_value_pair(supp_data[field])
                    if vp["raw"].strip():
                        setattr(invoice.supplier, field, ValuePair.model_validate(vp))

        # 3. Buyer Details
        buyer_data = gemini_data.get("buyer") if isinstance(gemini_data.get("buyer"), dict) else {}
        if not invoice.buyer:
            invoice.buyer = Buyer(name=ValuePair(raw="", confidence=0.0))
        for field in ["name", "gstin", "address", "phone", "state"]:
            curr_val = getattr(invoice.buyer, field, None)
            if not curr_val or not str(curr_val.raw).strip() or curr_val.confidence < 0.75:
                if field in buyer_data and buyer_data[field] is not None:
                    vp = self._to_value_pair(buyer_data[field])
                    if vp["raw"].strip():
                        setattr(invoice.buyer, field, ValuePair.model_validate(vp))

        # 4. Items Table (Quality-Aware Merge)
        gemini_items = gemini_data.get("items")
        if isinstance(gemini_items, list) and len(gemini_items) > 0:
            validated_items: List[InvoiceItem] = []
            for idx, raw_item in enumerate(gemini_items):
                normalized_item = self._normalize_gemini_item_structure(raw_item, idx + 1)
                validated_items.append(InvoiceItem.model_validate(normalized_item))
            
            # Check if existing rule items are empty, incomplete, low-confidence, or suspicious
            if not invoice.items or len(invoice.items) == 0:
                invoice.items = validated_items
            else:
                sum_rule_items = sum(
                    float(it.pricing.taxable_amount.normalized or 0.0)
                    for it in invoice.items
                    if it.pricing and it.pricing.taxable_amount
                )
                sum_gemini_items = sum(
                    float(it.pricing.taxable_amount.normalized or 0.0)
                    for it in validated_items
                    if it.pricing and it.pricing.taxable_amount
                )
                gemini_subtotal_raw = totals_data.get("subtotal")
                gemini_subtotal = 0.0
                if isinstance(gemini_subtotal_raw, dict):
                    gemini_subtotal = float(gemini_subtotal_raw.get("normalized") or 0.0)
                elif isinstance(gemini_subtotal_raw, (int, float)):
                    gemini_subtotal = float(gemini_subtotal_raw)

                rule_items_suspicious = any(
                    not item.pricing or
                    not item.pricing.purchase_rate or item.pricing.purchase_rate.normalized is None or item.pricing.purchase_rate.normalized <= 0.0 or
                    not item.pricing.taxable_amount or item.pricing.taxable_amount.normalized is None or item.pricing.taxable_amount.normalized <= 0.0 or
                    item.pricing.taxable_amount.confidence < 0.75 or
                    item.pricing.purchase_rate.confidence < 0.75 or
                    item.quantity.qty.confidence < 0.75
                    for item in invoice.items
                )
                if not rule_items_suspicious:
                    for it in invoice.items:
                        q = float(it.quantity.qty.normalized or 0.0)
                        r = float(it.pricing.purchase_rate.normalized or 0.0)
                        t = float(it.pricing.taxable_amount.normalized or 0.0)
                        if q > 0 and r > 0 and t > 0:
                            if abs(t - round(q * r, 2)) > max(2.0, 0.2 * (q * r)):
                                rule_items_suspicious = True
                                break

                if not rule_items_suspicious:
                    if sum_gemini_items > 0 and sum_rule_items > 0 and sum_gemini_items > sum_rule_items * 2.0:
                        rule_items_suspicious = True
                    elif gemini_subtotal > 0 and sum_rule_items > 0 and abs(gemini_subtotal - sum_rule_items) > max(10.0, 0.2 * gemini_subtotal):
                        rule_items_suspicious = True

                # If rule items are suspicious/incomplete and Gemini returned valid items, replace with Gemini items
                if rule_items_suspicious and len(validated_items) >= len(invoice.items):
                    invoice.items = validated_items

        # 5. Totals Merge
        totals_data = gemini_data.get("totals") if isinstance(gemini_data.get("totals"), dict) else {}
        if not invoice.totals:
            invoice.totals = Totals(
                subtotal=ValuePair(raw="", normalized=0.0, confidence=0.0),
                discount_total=ValuePair(raw="", normalized=0.0, confidence=0.0),
                tax_total=ValuePair(raw="", normalized=0.0, confidence=0.0),
                grand_total=ValuePair(raw="", normalized=0.0, confidence=0.0),
                round_off=ValuePair(raw="", normalized=0.0, confidence=0.0),
            )

        rule_totals_incomplete = (
            not invoice.totals.grand_total or
            invoice.totals.grand_total.normalized is None or
            invoice.totals.grand_total.normalized == 0.0 or
            invoice.totals.grand_total.confidence < 0.75
        )

        for field in ["subtotal", "discount_total", "tax_total", "grand_total", "round_off"]:
            curr_val = getattr(invoice.totals, field, None)
            should_update = (
                rule_totals_incomplete or
                not curr_val or
                not str(curr_val.raw).strip() or
                curr_val.confidence < 0.75 or
                (curr_val.normalized == 0.0 and field in ["subtotal", "tax_total", "grand_total"])
            )
            if should_update and field in totals_data and totals_data[field] is not None:
                vp = self._to_value_pair(totals_data[field])
                if vp["raw"].strip():
                    setattr(invoice.totals, field, ValuePair.model_validate(vp))

        # Only if totals are still missing/0.0 after checking both rule and Gemini totals, derive from items as fallback
        if (not invoice.totals.grand_total or invoice.totals.grand_total.normalized is None or invoice.totals.grand_total.normalized == 0.0) and invoice.items:
            subtotal_val = sum(
                float(item.pricing.taxable_amount.normalized)
                for item in invoice.items
                if item.pricing and item.pricing.taxable_amount and item.pricing.taxable_amount.normalized is not None
            )
            tax_val = sum(
                float(item.tax.gst_amount.normalized)
                for item in invoice.items
                if item.tax and item.tax.gst_amount and item.tax.gst_amount.normalized is not None
            )
            ro_val = float(invoice.totals.round_off.normalized) if invoice.totals.round_off and invoice.totals.round_off.normalized is not None else 0.0
            grand_val = subtotal_val + tax_val + ro_val
            
            if not invoice.totals.subtotal or invoice.totals.subtotal.normalized == 0.0:
                invoice.totals.subtotal.normalized = subtotal_val
                invoice.totals.subtotal.raw = f"{subtotal_val:.2f}"
            if not invoice.totals.tax_total or invoice.totals.tax_total.normalized == 0.0:
                invoice.totals.tax_total.normalized = tax_val
                invoice.totals.tax_total.raw = f"{tax_val:.2f}"
            invoice.totals.grand_total.normalized = grand_val
            invoice.totals.grand_total.raw = f"{grand_val:.2f}"

        # 6. Tax Summary Merge
        tax_sum_data = gemini_data.get("tax_summary")
        if isinstance(tax_sum_data, list) and len(tax_sum_data) > 0:
            tax_items = []
            for ts in tax_sum_data:
                if isinstance(ts, dict) and "tax_rate" in ts:
                    tax_items.append(
                        TaxSummaryItem(
                            tax_rate=float(ts.get("tax_rate") or ts.get("tax_percent") or 0.0),
                            taxable_amount=float(ts.get("taxable_amount") or 0.0),
                            cgst_amount=float(ts.get("cgst_amount") or 0.0),
                            sgst_amount=float(ts.get("sgst_amount") or 0.0),
                            igst_amount=float(ts.get("igst_amount") or 0.0),
                            total_gst_amount=float(ts.get("total_tax_amount") or ts.get("total_gst_amount") or 0.0),
                        )
                    )
            if tax_items:
                invoice.tax_summary = TaxSummary(items=tax_items)

        return invoice

    def _to_value_pair(self, val: Any, default_normalized: Any = None, default_raw: str = "") -> Dict[str, Any]:
        """
        Guarantees that a value is wrapped as a valid ValuePair dict with non-null raw and normalized fields.
        """
        if val is None:
            return {
                "raw": default_raw,
                "normalized": default_normalized,
                "confidence": 0.5 if default_normalized is not None else 0.0,
            }
        if isinstance(val, dict):
            raw = val.get("raw")
            if raw is None:
                raw = str(val.get("normalized", default_raw)) if val.get("normalized") is not None else default_raw
            norm = val.get("normalized")
            if norm is None and default_normalized is not None:
                norm = default_normalized
            conf = float(val.get("confidence", 1.0) or 1.0)
            return {"raw": str(raw), "normalized": norm, "confidence": conf}
        
        # Primitive scalar string, float, int, bool
        return {
            "raw": str(val),
            "normalized": val,
            "confidence": 1.0,
        }

    def _normalize_gemini_item_structure(self, raw_item: Dict[str, Any], line_num: int) -> Dict[str, Any]:
        """
        Normalizes any LLM key layout quirks (such as dot-flattened keys, raw scalars, missing ValuePairs)
        into the exact nested Pydantic schema structure.
        """
        if not isinstance(raw_item, dict):
            raw_item = {}

        item: Dict[str, Any] = {"line_number": raw_item.get("line_number", line_num)}

        # 1. Product
        prod = raw_item.get("product") if isinstance(raw_item.get("product"), dict) else {}
        desc_val = prod.get("description") or prod.get("name") or raw_item.get("description")
        item["product"] = {
            "product_code": self._to_value_pair(prod.get("product_code")),
            "description": self._to_value_pair(desc_val, default_normalized="UNKNOWN ITEM", default_raw="UNKNOWN ITEM"),
            "hsn_code": self._to_value_pair(prod.get("hsn_code")),
        }

        # 2. Batch
        b = raw_item.get("batch") if isinstance(raw_item.get("batch"), dict) else {}
        batch_no = b.get("batch_no") or b.get("batch_number") or raw_item.get("batch_no")
        exp_date = b.get("expiry_date") or b.get("expiry") or raw_item.get("expiry_date")
        item["batch"] = {
            "batch_no": self._to_value_pair(batch_no, default_normalized="", default_raw=""),
            "expiry_date": self._to_value_pair(exp_date, default_normalized="", default_raw=""),
        }

        # 3. Packaging
        pkg = raw_item.get("packaging") if isinstance(raw_item.get("packaging"), dict) else {}
        unit_cnt = int(pkg.get("unit_count") or 1)
        item["packaging"] = {
            "pack_size": str(pkg.get("pack_size") or "1s"),
            "unit_count": unit_cnt,
            "unit_type": str(pkg.get("unit_type") or "Units"),
        }

        # 4. Quantity
        q = raw_item.get("quantity") if isinstance(raw_item.get("quantity"), dict) else {}
        qty_val = q.get("qty") or raw_item.get("qty") or 1.0
        qty_pair = self._to_value_pair(qty_val, default_normalized=1.0, default_raw="1")
        free_qty_val = q.get("free_qty")
        free_qty_pair = self._to_value_pair(free_qty_val) if free_qty_val is not None else None

        # Calculate total_qty
        tot_qty = q.get("total_qty") or raw_item.get("quantity.total_qty") or raw_item.get("total_qty")
        if tot_qty is None:
            billed_num = float(qty_pair.get("normalized") or 0.0)
            tot_qty = billed_num * unit_cnt
        else:
            tot_qty = float(tot_qty)

        item["quantity"] = {
            "qty": qty_pair,
            "free_qty": free_qty_pair,
            "total_qty": tot_qty,
        }

        # 5. Pricing
        pr = raw_item.get("pricing") if isinstance(raw_item.get("pricing"), dict) else {}
        mrp_val = pr.get("mrp") or raw_item.get("mrp")
        rate_val = pr.get("purchase_rate") or pr.get("rate") or pr.get("ptr") or raw_item.get("purchase_rate")
        taxable_val = pr.get("taxable_amount") or pr.get("amount") or raw_item.get("taxable_amount")
        disc_pct_val = pr.get("discount_percentage") or pr.get("discount_percent")
        disc_amt_val = pr.get("discount_amount")

        item["pricing"] = {
            "mrp": self._to_value_pair(mrp_val, default_normalized=0.0, default_raw="0.00"),
            "purchase_rate": self._to_value_pair(rate_val, default_normalized=0.0, default_raw="0.00"),
            "discount_percentage": self._to_value_pair(disc_pct_val, default_normalized=0.0, default_raw="0.00") if disc_pct_val is not None else None,
            "discount_amount": self._to_value_pair(disc_amt_val, default_normalized=0.0, default_raw="0.00") if disc_amt_val is not None else None,
            "taxable_amount": self._to_value_pair(taxable_val, default_normalized=0.0, default_raw="0.00"),
        }

        # 6. Tax
        tx = raw_item.get("tax") if isinstance(raw_item.get("tax"), dict) else {}
        gst_pct = tx.get("gst_percentage") or tx.get("gst_percent")
        gst_amt = tx.get("gst_amount")
        cgst_pct = tx.get("cgst_percentage") or tx.get("cgst_percent")
        cgst_amt = tx.get("cgst_amount")
        sgst_pct = tx.get("sgst_percentage") or tx.get("sgst_percent")
        sgst_amt = tx.get("sgst_amount")
        igst_pct = tx.get("igst_percentage") or tx.get("igst_percent")
        igst_amt = tx.get("igst_amount")

        if gst_pct is None and (cgst_pct is not None or sgst_pct is not None):
            cgst_num = float(cgst_pct.get("normalized") if isinstance(cgst_pct, dict) else (cgst_pct or 0.0))
            sgst_num = float(sgst_pct.get("normalized") if isinstance(sgst_pct, dict) else (sgst_pct or 0.0))
            gst_pct = cgst_num + sgst_num

        if gst_amt is None and (cgst_amt is not None or sgst_amt is not None):
            cgst_amt_num = float(cgst_amt.get("normalized") if isinstance(cgst_amt, dict) else (cgst_amt or 0.0))
            sgst_amt_num = float(sgst_amt.get("normalized") if isinstance(sgst_amt, dict) else (sgst_amt or 0.0))
            gst_amt = cgst_amt_num + sgst_amt_num

        item["tax"] = {
            "cgst_percentage": self._to_value_pair(cgst_pct) if cgst_pct is not None else None,
            "sgst_percentage": self._to_value_pair(sgst_pct) if sgst_pct is not None else None,
            "igst_percentage": self._to_value_pair(igst_pct) if igst_pct is not None else None,
            "cgst_amount": self._to_value_pair(cgst_amt) if cgst_amt is not None else None,
            "sgst_amount": self._to_value_pair(sgst_amt) if sgst_amt is not None else None,
            "igst_amount": self._to_value_pair(igst_amt) if igst_amt is not None else None,
            "gst_percentage": self._to_value_pair(gst_pct, default_normalized=0.0, default_raw="0.00"),
            "gst_amount": self._to_value_pair(gst_amt, default_normalized=0.0, default_raw="0.00"),
        }

        return item

    def _sanitize_value_pairs(self, data: Any) -> Any:
        """
        Recursively cleans a dictionary to ensure ValuePairs satisfy constraints.
        Converts any None 'raw' values to empty strings.
        """
        if isinstance(data, dict):
            if "raw" in data and data["raw"] is None:
                data["raw"] = ""
            return {k: self._sanitize_value_pairs(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_value_pairs(item) for item in data]
        return data

    @staticmethod
    def _sanitize_error_message(msg: str) -> str:
        """
        Sanitizes error messages to strip API keys, Bearer tokens, and sensitive headers.
        """
        if not msg:
            return ""
        # Redact Google API keys (AIza...)
        sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{10,}", "[REDACTED_API_KEY]", msg)
        # Redact key/token patterns
        sanitized = re.sub(r"(?i)(key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+", r"\1=[REDACTED]", sanitized)
        try:
            from app.core.config import settings
            if settings.GEMINI_API_KEY:
                sanitized = sanitized.replace(settings.GEMINI_API_KEY, "[REDACTED_API_KEY]")
            if settings.API_BEARER_TOKEN:
                sanitized = sanitized.replace(settings.API_BEARER_TOKEN, "[REDACTED_TOKEN]")
        except Exception:
            pass
        return sanitized

    def _build_gemini_prompt(self, ocr_text: str) -> str:
        """
        Builds the prompt instructing Gemini to extract ALL structured invoice data.
        """
        return f"""You are an expert invoice data extraction assistant.
Analyze the following raw OCR text extracted from a pharmacy tax invoice and extract ALL invoice data including:
1. invoice details (invoice_number, invoice_date, due_date, order_number, payment_type)
2. supplier details (name, gstin, address, phone, state)
3. buyer details (name, gstin, address, phone, state)
4. items table (all product line items with batch, expiry, packaging, quantity, pricing, tax)
5. totals (subtotal, discount_total, tax_total, grand_total, round_off)
6. tax_summary

--- RAW OCR TEXT ---
{ocr_text}

--- SCHEMA STRUCTURAL GUIDELINES ---
Every item and field in the JSON must conform to the following nested JSON structure:

{{
  "invoice": {{
    "invoice_number": {{"raw": "MC-210", "normalized": "MC-210", "confidence": 1.0}},
    "invoice_date": {{"raw": "14/05/26", "normalized": "2026-05-14", "confidence": 1.0}},
    "due_date": null,
    "order_number": null,
    "payment_type": {{"raw": "CREDIT", "normalized": "CREDIT", "confidence": 1.0}}
  }},
  "supplier": {{
    "name": {{"raw": "MEDICARE PHARMA", "normalized": "MEDICARE PHARMA", "confidence": 1.0}},
    "gstin": {{"raw": "32AGHPR0323G1ZU", "normalized": "32AGHPR0323G1ZU", "confidence": 1.0}},
    "address": {{"raw": "MUZHAPPILANGAD MADAM, THALASSERY", "normalized": "MUZHAPPILANGAD MADAM, THALASSERY", "confidence": 1.0}},
    "phone": {{"raw": "0490 2326443", "normalized": "0490 2326443", "confidence": 1.0}},
    "state": {{"raw": "KERALA", "normalized": "KERALA", "confidence": 1.0}}
  }},
  "buyer": {{
    "name": {{"raw": "GERMAN PHARMACY", "normalized": "GERMAN PHARMACY", "confidence": 1.0}},
    "gstin": null,
    "address": null,
    "phone": null,
    "state": {{"raw": "KERALA", "normalized": "KERALA", "confidence": 1.0}}
  }},
  "items": [
    {{
      "line_number": 1,
      "product": {{
        "product_code": {{"raw": "LIFE", "normalized": "LIFE", "confidence": 1.0}},
        "description": {{"raw": "AMPICARE DS TAB", "normalized": "AMPICARE DS TAB", "confidence": 1.0}},
        "hsn_code": {{"raw": "30049099", "normalized": "30049099", "confidence": 1.0}}
      }},
      "batch": {{
        "batch_no": {{"raw": "LBT2403026", "normalized": "LBT2403026", "confidence": 1.0}},
        "expiry_date": {{"raw": "02-27", "normalized": "02-27", "confidence": 1.0}}
      }},
      "packaging": {{
        "pack_size": "1",
        "unit_count": 1,
        "unit_type": "Tablets"
      }},
      "quantity": {{
        "qty": {{"raw": "10", "normalized": 10.0, "confidence": 1.0}},
        "free_qty": {{"raw": "0", "normalized": 0.0, "confidence": 1.0}},
        "total_qty": 10.0
      }},
      "pricing": {{
        "mrp": {{"raw": "225.00", "normalized": 225.0, "confidence": 1.0}},
        "purchase_rate": {{"raw": "179.00", "normalized": 179.0, "confidence": 1.0}},
        "discount_percentage": {{"raw": "0.00", "normalized": 0.0, "confidence": 1.0}},
        "discount_amount": {{"raw": "0.00", "normalized": 0.0, "confidence": 1.0}},
        "taxable_amount": {{"raw": "1790.00", "normalized": 1790.0, "confidence": 1.0}}
      }},
      "tax": {{
        "cgst_percentage": {{"raw": "2.5", "normalized": 2.5, "confidence": 1.0}},
        "sgst_percentage": {{"raw": "2.5", "normalized": 2.5, "confidence": 1.0}},
        "igst_percentage": {{"raw": "0.0", "normalized": 0.0, "confidence": 1.0}},
        "cgst_amount": {{"raw": "44.75", "normalized": 44.75, "confidence": 1.0}},
        "sgst_amount": {{"raw": "44.75", "normalized": 44.75, "confidence": 1.0}},
        "igst_amount": {{"raw": "0.00", "normalized": 0.0, "confidence": 1.0}},
        "gst_percentage": {{"raw": "5.0", "normalized": 5.0, "confidence": 1.0}},
        "gst_amount": {{"raw": "89.50", "normalized": 89.5, "confidence": 1.0}}
      }}
    }}
  ],
  "totals": {{
    "subtotal": {{"raw": "4713.90", "normalized": 4713.90, "confidence": 1.0}},
    "discount_total": {{"raw": "0.00", "normalized": 0.0, "confidence": 1.0}},
    "tax_total": {{"raw": "235.70", "normalized": 235.70, "confidence": 1.0}},
    "grand_total": {{"raw": "4949.60", "normalized": 4949.60, "confidence": 1.0}},
    "round_off": {{"raw": "0.40", "normalized": 0.40, "confidence": 1.0}}
  }},
  "tax_summary": [
    {{
      "tax_rate": 5.0,
      "taxable_amount": 4713.90,
      "cgst_amount": 117.85,
      "sgst_amount": 117.85,
      "igst_amount": 0.0,
      "total_tax_amount": 235.70
    }}
  ]
}}

Ensure all values conform to the schema:
- If a value is missing or not present, set it to null.
- Return ONLY a valid JSON object matching the complete schema.
"""
