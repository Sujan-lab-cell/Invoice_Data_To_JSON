import sys
import time
from pathlib import Path
import json

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.ocr.schemas import OCRResult

# Configurable constants
TEST_DATA_DIR = Path(__file__).parent / "sample_invoices"
SAMPLE_FILE_NAME = "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"


def main():
    # Measure the actual end-to-end pipeline execution time externally
    t_external_start = time.perf_counter()

    sample_file = TEST_DATA_DIR / SAMPLE_FILE_NAME
    if not sample_file.exists():
        print(f"\n[ERROR] Sample invoice file not found at: {sample_file}\n")
        return

    # 1. Parse using ParserService
    print(f"\n--- 1. Parsing Sample Invoice: {sample_file.name} ---")
    
    try:
        parser_service = ParserService()
        t_parse_start = time.perf_counter()
        parse_result = parser_service.parse(str(sample_file))
        t_parse = time.perf_counter() - t_parse_start
    except Exception as e:
        print(f"\n[ERROR] ParserService failed to parse the document: {e}\n")
        return

    if not parse_result or "source_file_type" not in parse_result:
        print("\n[ERROR] Invalid parser service output data structure.\n")
        return

    if parse_result["source_file_type"] in ["csv", "excel"]:
        if "text" not in parse_result:
            print("\n[ERROR] Missing parsed text field in Excel/CSV result.\n")
            return
        ocr_result = OCRResult(full_text=parse_result["text"])
    else:
        if "raw_data" not in parse_result or not parse_result["raw_data"]:
            print("\n[ERROR] Missing raw OCR data in PDF/Image result.\n")
            return
        ocr_result = parse_result["raw_data"]
        
    print(f"Successfully extracted text (length: {len(ocr_result.full_text)} characters).")

    # 2. Instantiate HybridInvoiceExtractor
    print("\n--- 2. Initializing Hybrid Invoice Extractor ---")
    try:
        extractor = HybridInvoiceExtractor()
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize HybridInvoiceExtractor: {e}\n")
        return

    # 3. Perform Extraction
    print("\n--- 3. Running Hybrid Extraction Pipeline ---")
    try:
        document = extractor.extract(
            ocr_result,
            file_name=sample_file.name,
            file_type=parse_result["source_file_type"]
        )
        print("Pipeline run completed successfully.")
    except Exception as e:
        print(f"\n[ERROR] Extraction pipeline failed: {e}\n")
        return

    if not document:
        print("\n[ERROR] No document wrapper returned from extraction pipeline.\n")
        return

    # 4. Print results
    invoice = document.invoice_data
    validation = document.validation
    review = document.review

    print("\n" + "=" * 80)
    print("=== HYBRID EXTRACTOR PIPELINE RESULTS ===")
    print("=" * 80)
    if invoice:
        print(f"Invoice Number: {invoice.invoice_number.normalized}")
        print(f"Invoice Date:   {invoice.invoice_date.normalized}")
        print(f"Supplier Name:  {invoice.supplier.name.normalized}")
        print(f"Buyer Name:     {invoice.buyer.name.normalized}")
        
        print("\n--- Extracted Line Items ---")
        print(f"Total items found: {len(invoice.items)}")
        for item in invoice.items:
            prod = item.product.description.normalized
            qty = item.quantity.qty.normalized
            rate = item.pricing.purchase_rate.normalized
            taxable = item.pricing.taxable_amount.normalized
            batch = item.batch.batch_no.normalized
            exp = item.batch.expiry_date.normalized
            print(f" - [{batch} | Exp: {exp}] {prod[:30]:<30} Qty: {qty:<3} Rate: {rate:<6} Taxable: {taxable}")
            
        print("\n--- Totals ---")
        print(f"Subtotal:    {invoice.totals.subtotal.normalized}")
        print(f"Tax Total:   {invoice.totals.tax_total.normalized}")
        print(f"Grand Total: {invoice.totals.grand_total.normalized}")
    else:
        print("[ERROR] No invoice data returned.")

    print("\n--- Validation & Review Status ---")
    print(f"Is Valid:        {validation.is_valid}")
    print(f"Requires Review: {review.requires_review}")
    if review.reason:
        print(f"Review Reason:   {review.reason}")
    if validation.issues:
        print("\nValidation Issues:")
        for idx, issue in enumerate(validation.issues, 1):
            print(f" {idx}. [{issue.severity.upper()}] {issue.field}: {issue.message}")
    print("=" * 80 + "\n")

    t_external_end = time.perf_counter() - t_external_start

    # 5. Print profiling details
    print("=" * 80)
    print("=== PIPELINE STAGE TIMING PROFILES ===")
    print("=" * 80)
    print(f"ParserService time:               {t_parse:.4f}s")
    if parse_result["source_file_type"] in ["excel", "csv"]:
        print(f"Excel/CSV Parser time:            {t_parse:.4f}s")
    else:
        print(f"Excel/CSV Parser time:            N/A (using OCR)")
        
    print(f"OCR Initialized:                  {parser_service.ocr_initialized}")
    print(f"OCR Initialization time:          {parser_service.ocr_init_duration:.4f}s")
    
    raw_fields = document.raw_extraction.raw_fields if document.raw_extraction else {}
    print(f"Preprocessing / NLP Clean:        {raw_fields.get('duration_preprocessing', '0.0000s')}")
    print(f"RuleBasedExtractor time:          {raw_fields.get('duration_rules', '0.0000s')}")
    print(f"Gemini API call time:             {raw_fields.get('duration_gemini', '0.0000s')}")
    print(f"Validation time:                  {raw_fields.get('duration_validation', '0.0000s')}")
    print(f"Internal Pipeline time:           {raw_fields.get('duration_pipeline', '0.0000s')}")
    print(f"External End-to-End time:         {t_external_end:.4f}s")
    print(f"Gemini Fallback Triggered:        {raw_fields.get('fallback_triggered', 'False')}")
    print("=" * 80 + "\n")

    # 6. Convert Document model to JSON and save/print
    json_data = document.model_dump(mode="json")
    
    print("=" * 80)
    print("=== FINAL COMPLETE JSON OUTPUT ===")
    print("=" * 80)
    print(json.dumps(json_data, indent=2))
    print("=" * 80 + "\n")
    
    # Save the output JSON using the input invoice filename
    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{sample_file.stem}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"Successfully saved final JSON output to: {output_file}\n")


if __name__ == "__main__":
    main()
