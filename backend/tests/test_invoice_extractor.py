import os
import sys
from pathlib import Path

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.ai.gemini_client import GeminiClient
from app.ai.invoice_extractor import InvoiceExtractor
from app.ai.json_parser import JSONParser
from app.schemas.invoice_schema import Invoice


def main():
    # 0. Check for API configuration
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY or GOOGLE_API_KEY is not set.")
        print("Please configure your API key in your terminal before running:")
        print("PowerShell: $env:GEMINI_API_KEY=\"your_key_here\"\n")
        return

    sample_pdf = Path(__file__).parent / "4220 (1).pdf"
    if not sample_pdf.exists():
        print(f"\n❌ Error: Sample PDF invoice not found at: {sample_pdf}\n")
        return

    # 1. Load OCR Text from the sample PDF file
    print("\n--- 1. Parsing Sample PDF Invoice ---")
    parser_service = ParserService()
    parse_result = parser_service.parse(str(sample_pdf))
    ocr_result = parse_result["raw_data"]
    print(f"Successfully extracted OCR text from PDF (length: {len(ocr_result.full_text)} characters).")

    # 2. Instantiate GeminiClient & InvoiceExtractor
    print("\n--- 2. Initializing Gemini Client & Extractor ---")
    provider = GeminiClient()
    extractor = InvoiceExtractor(provider=provider)

    # 3. Build the extraction prompt
    print("\n--- 3. Building Extraction Prompt ---")
    prompt = extractor.build_prompt(ocr_result.full_text)
    print("Extraction prompt constructed successfully.")

    # 4. Call GeminiClient and retrieve response
    print("\n--- 4. Sending Request to Gemini Client ---")
    raw_response = provider.generate(prompt, response_schema=Invoice.model_json_schema())
    print("Received raw response text from Gemini.")

    # 5. Parse JSON using JSONParser
    print("\n--- 5. Parsing & Cleaning Response with JSONParser ---")
    parsed_json = JSONParser.parse(raw_response)
    print("JSON parsed, cleaned, and repaired successfully.")

    # 6. Validate against Invoice Schema
    print("\n--- 6. Validating JSON against Canonical Invoice Schema ---")
    invoice = Invoice.model_validate(parsed_json)
    print("Schema validation successful! Matches canonical structure.")

    # 7. Print extracted details
    print("\n" + "=" * 80)
    print("🎉 EXTRACTED INVOICE SUMMARY 🎉")
    print(f"Invoice Number (Raw):        {invoice.invoice_number.raw}")
    print(f"Invoice Number (Normalized): {invoice.invoice_number.normalized}")
    print(f"Invoice Date (Raw):          {invoice.invoice_date.raw}")
    print(f"Invoice Date (Normalized):   {invoice.invoice_date.normalized}")
    print(f"Supplier Name (Raw):         {invoice.supplier.name.raw}")
    print(f"Supplier Name (Normalized):   {invoice.supplier.name.normalized}")
    print(f"Supplier GSTIN (Raw):        {invoice.supplier.gstin.raw if invoice.supplier.gstin else 'N/A'}")
    print(f"Grand Total (Raw):           {invoice.totals.grand_total.raw}")
    print(f"Grand Total (Normalized):    {invoice.totals.grand_total.normalized}")
    print(f"Line Items Extracted:        {len(invoice.items)}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
