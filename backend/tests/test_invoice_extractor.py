import sys
from pathlib import Path

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.ai.rule_based_extractor import RuleBasedInvoiceExtractor
from app.schemas.invoice_schema import Invoice


from app.ocr.schemas import OCRResult


# Configurable constants
TEST_DATA_DIR = Path(__file__).parent / "sample_invoices"
SAMPLE_FILE_NAME = "MCRB PHARMA PILATHARA Sales Invoice 8898.pdf"


def main():
    sample_file = TEST_DATA_DIR / SAMPLE_FILE_NAME
    if not sample_file.exists():
        print(f"\n[ERROR] Sample invoice file not found at: {sample_file}\n")
        return

    # 1. Load Text from the sample file
    print(f"\n--- 1. Parsing Sample Invoice: {sample_file.name} ---")
    parser_service = ParserService()
    parse_result = parser_service.parse(str(sample_file))
    
    if parse_result["source_file_type"] in ["csv", "excel"]:
        ocr_result = OCRResult(full_text=parse_result["text"])
    else:
        ocr_result = parse_result["raw_data"]
        
    print(f"Successfully extracted text (length: {len(ocr_result.full_text)} characters).")

    # 2. Instantiate RuleBasedInvoiceExtractor
    print("\n--- 2. Initializing Rule-Based Extractor ---")
    extractor = RuleBasedInvoiceExtractor()

    # 3. Perform Extraction
    print("\n--- 3. Extracting structured invoice JSON matching schema ---")
    invoice = extractor.extract(ocr_result)
    print("Extraction completed successfully.")

    # 4. Print extracted details to verify they conform to the schema
    print("\n" + "=" * 80)
    print("=== EXTRACTED INVOICE SUMMARY (IMPROVED RULE-BASED EXTRACTOR) ===")
    print(f"Invoice Number (Raw):        {invoice.invoice_number.raw!r}")
    print(f"Invoice Date (Raw):          {invoice.invoice_date.raw!r}")
    print(f"Invoice Date (Normalized):   {invoice.invoice_date.normalized!r}")
    print(f"Due Date (Raw):              {(invoice.due_date.raw if invoice.due_date else None)!r}")
    print(f"Due Date (Normalized):       {(invoice.due_date.normalized if invoice.due_date else None)!r}")
    print(f"Order Number (Raw):          {(invoice.order_number.raw if invoice.order_number else None)!r}")
    print(f"Payment Type (Raw):          {(invoice.payment_type.raw if invoice.payment_type else None)!r}")
    
    print("-" * 40)
    print(f"Supplier Name (Raw):         {invoice.supplier.name.raw!r}")
    print(f"Supplier GSTIN (Raw):        {(invoice.supplier.gstin.raw if invoice.supplier.gstin else None)!r}")
    print(f"Supplier State (Raw):        {(invoice.supplier.state.raw if invoice.supplier.state else None)!r}")
    print(f"Supplier State (Normalized): {(invoice.supplier.state.normalized if invoice.supplier.state else None)!r}")
    
    print("-" * 40)
    print(f"Buyer Name (Raw):            {invoice.buyer.name.raw!r}")
    print(f"Buyer GSTIN (Raw):           {(invoice.buyer.gstin.raw if invoice.buyer.gstin else None)!r}")
    print(f"Buyer State (Raw):           {(invoice.buyer.state.raw if invoice.buyer.state else None)!r}")
    print(f"Buyer State (Normalized):    {(invoice.buyer.state.normalized if invoice.buyer.state else None)!r}")
    print("=" * 80 + "\n")

    # 5. Convert Invoice model to JSON and optionally save/print
    import json
    json_data = invoice.model_dump(mode="json")
    
    print("=" * 80)
    print("=== FINAL COMPLETE JSON OUTPUT (RULE-BASED EXTRACTOR) ===")
    print("=" * 80)
    print(json.dumps(json_data, indent=2))
    print("=" * 80 + "\n")
    
    # Save the output JSON
    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "invoice.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"Successfully saved final JSON output to: {output_file}\n")


if __name__ == "__main__":
    main()
