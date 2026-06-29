import json
import logging
from typing import Any, Dict, Optional
from app.ocr.schemas import OCRResult
from app.schemas.invoice_schema import (
    Invoice, Document, Confidence, RawExtraction, Review, ValuePair
)
from app.extraction.header_extractor import HeaderExtractor
from app.extraction.rule_based_components import ItemExtractor, TotalsCalculator
from app.ai.gemini_client import generate_json
from app.ai.validator import validate_invoice

logger = logging.getLogger(__name__)


class HybridInvoiceExtractor:
    """
    Orchestrates the hybrid invoice extraction pipeline.
    Runs rule-based extractors, validates the results, and triggers Gemini fallback
    if critical fields or items are missing, merging and re-validating the final output.
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
        import time
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
        partial_data["items"] = ItemExtractor.extract_items(cleaned_text)
        partial_data["totals"] = TotalsCalculator.extract_totals(cleaned_text)
        t_rules = time.perf_counter() - t_rules_start

        # Instantiate a partial Invoice object
        try:
            invoice = Invoice.model_validate(partial_data)
        except Exception as e:
            logger.warning(f"Failed to instantiate partial Invoice model directly: {e}. Falling back to default initial structure.")
            # Fallback to empty shell model if validation fails
            invoice = Invoice(
                invoice_number=ValuePair(raw="", confidence=0.0),
                invoice_date=ValuePair(raw="", confidence=0.0),
                supplier=partial_data["supplier"],
                buyer=partial_data["buyer"],
                items=[],
                totals=partial_data["totals"]
            )

        # 2. Validation Checks
        logger.info("Step 2: Checking schema and math validation on partial JSON.")
        t_val1_start = time.perf_counter()
        validation = validate_invoice(invoice)
        t_val1 = time.perf_counter() - t_val1_start

        # 3. Decision Point: Missing Fields?
        # Only call Gemini if item pricing fields (mrp, purchase_rate, taxable_amount) are missing/zero after rule-based extraction
        item_pricing_missing = False
        if not invoice.items:
            item_pricing_missing = True
        else:
            for item in invoice.items:
                pricing = item.pricing
                if (not pricing or
                    not pricing.mrp or pricing.mrp.normalized == 0.0 or
                    not pricing.purchase_rate or pricing.purchase_rate.normalized == 0.0 or
                    not pricing.taxable_amount or pricing.taxable_amount.normalized == 0.0):
                    item_pricing_missing = True
                    break

        gemini_raw_json = None
        t_gemini = 0.0
        if item_pricing_missing:
            logger.info("Step 3: Item pricing fields are missing. Triggering Gemini Fallback for missing items.")
            
            # Formulate the prompt for Gemini, sending only raw text and missing fields instructions
            prompt = self._build_gemini_prompt(raw_text)

            try:
                # Call Gemini client
                t_gemini_start = time.perf_counter()
                gemini_data = generate_json(prompt)
                
                # Sanitize value pairs to ensure 'raw' is always a string
                gemini_data = self._sanitize_value_pairs(gemini_data)
                gemini_raw_json = json.dumps(gemini_data, default=str)
                
                # Extract and merge the items list
                if "items" in gemini_data and isinstance(gemini_data["items"], list):
                    from app.schemas.invoice_schema import InvoiceItem
                    validated_items = []
                    for idx, raw_item in enumerate(gemini_data["items"]):
                        # Ensure line_number is set
                        if "line_number" not in raw_item:
                            raw_item["line_number"] = idx + 1
                        validated_items.append(InvoiceItem.model_validate(raw_item))
                    
                    # Merge items back into invoice
                    invoice.items = validated_items
                    logger.info(f"Successfully merged {len(validated_items)} line items from Gemini.")
                    
                    # Recalculate totals based on merged items
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
                    grand_val = subtotal_val + tax_val
                    
                    invoice.totals.subtotal.normalized = subtotal_val
                    invoice.totals.subtotal.raw = f"{subtotal_val:.2f}"
                    invoice.totals.tax_total.normalized = tax_val
                    invoice.totals.tax_total.raw = f"{tax_val:.2f}"
                    invoice.totals.grand_total.normalized = grand_val
                    invoice.totals.grand_total.raw = f"{grand_val:.2f}"
                t_gemini = time.perf_counter() - t_gemini_start
                
            except Exception as e:
                t_gemini = time.perf_counter() - t_gemini_start
                logger.error(f"Gemini fallback extraction or validation failed: {e}", exc_info=True)
                # Keep the rule-based partial invoice as-is if Gemini fails
        else:
            logger.info("Step 3: All item pricing fields successfully parsed via rules. Skipping Gemini fallback.")

        # 5. Final Validation Check
        t_val2_start = time.perf_counter()
        final_validation = validate_invoice(invoice)
        t_val2 = time.perf_counter() - t_val2_start

        # Total pipeline time
        t_total = time.perf_counter() - t_start

        # 6. Build the Audit Payloads & Document wrapper
        raw_extraction = RawExtraction(
            ocr_text_snippet=raw_text[:2000],
            raw_json=gemini_raw_json,
            raw_fields={
                "fallback_triggered": str(item_pricing_missing),
                "duration_preprocessing": f"{t_prep:.4f}s",
                "duration_rules": f"{t_rules:.4f}s",
                "duration_gemini": f"{t_gemini:.4f}s",
                "duration_validation": f"{(t_val1 + t_val2):.4f}s",
                "duration_pipeline": f"{t_total:.4f}s"
            }
        )

        review = Review(
            requires_review=not final_validation.is_valid,
            reason="Validation errors present" if not final_validation.is_valid else "Fuzzy matching required"
        )

        # Determine confidence metrics
        extraction_confidence = 1.0 if final_validation.is_valid else 0.7
        confidence = Confidence(
            ocr=0.9, # EasyOCR baseline
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

    def _build_gemini_prompt(self, ocr_text: str) -> str:
        """
        Builds the prompt instructing Gemini on what missing fields to extract.
        """
        return f"""You are an expert invoice data extraction assistant.
Analyze the following raw OCR text extracted from a pharmacy tax invoice and extract ONLY the missing line items table ("items") with pricing details.

--- RAW OCR TEXT ---
{ocr_text}

--- SCHEMA STRUCTURAL GUIDELINES ---
Every value in the JSON must conform to the following rules:

1. Fields that MUST be wrapped in a ValuePair structure: {{"raw": "extracted_string", "normalized": typed_value_or_null, "confidence": 1.0}}
   - items[].product.product_code, items[].product.description, items[].product.hsn_code
   - items[].batch.batch_no, items[].batch.expiry_date
   - items[].quantity.qty (normalized value as float), items[].quantity.free_qty (normalized value as float or null)
   - items[].pricing.mrp, items[].pricing.purchase_rate, items[].pricing.discount_percentage, items[].pricing.discount_amount, items[].pricing.taxable_amount (all normalized values as float)
   - items[].tax.cgst_percentage, items[].tax.sgst_percentage, items[].tax.igst_percentage, items[].tax.cgst_amount, items[].tax.sgst_amount, items[].tax.igst_amount, items[].tax.gst_percentage, items[].tax.gst_amount (all normalized values as float)

2. Fields that MUST NOT be wrapped in a ValuePair (they must be direct raw values):
   - items[].line_number: integer (e.g. 1, 2, 3...)
   - items[].packaging.pack_size: string (e.g. "10s", "15'S")
   - items[].packaging.unit_count: integer (e.g. 10, 15)
   - items[].packaging.unit_type: string (e.g. "Capsules", "Tablets", "Syrup")
   - items[].quantity.total_qty: float (total units, e.g., qty * unit_count)

Ensure all values conform to the schema:
- If a value is missing or not present, set it to null.
- Return ONLY a valid JSON object matching the schema containing the "items" list, like:
{{
  "items": [
     ...
  ]
}}
Do not output any markdown formatting other than the JSON itself.
"""

    def _merge_invoice_data(self, rule_invoice: Invoice, gemini_invoice: Invoice) -> Invoice:
        """
        Merges rule-based extracted data with Gemini fallback extracted data.
        Prioritizes high-confidence rule-based header fields and uses Gemini for tables/totals.
        """
        merged_dict = gemini_invoice.model_dump()
        rule_dict = rule_invoice.model_dump()

        # Let's preserve rule-based header fields if they were extracted with high confidence.
        # Confidence score >= 0.75 is considered high confidence.
        for field in ["invoice_number", "invoice_date", "due_date", "order_number", "payment_type"]:
            if rule_dict[field] and rule_dict[field].get("confidence", 0.0) >= 0.75:
                if rule_dict[field].get("raw"):
                    merged_dict[field] = rule_dict[field]

        # Supplier merge
        for field in ["name", "gstin", "state"]:
            rule_field = rule_dict["supplier"].get(field)
            if rule_field and rule_field.get("confidence", 0.0) >= 0.75:
                if rule_field.get("raw"):
                    merged_dict["supplier"][field] = rule_field

        # Buyer merge
        for field in ["name", "gstin", "state"]:
            rule_field = rule_dict["buyer"].get(field)
            if rule_field and rule_field.get("confidence", 0.0) >= 0.75:
                if rule_field.get("raw"):
                    merged_dict["buyer"][field] = rule_field

        return Invoice.model_validate(merged_dict)
