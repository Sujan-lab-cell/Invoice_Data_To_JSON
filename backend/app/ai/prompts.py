import json
from typing import Dict, Any
from app.schemas.invoice_schema import Invoice


class PromptBuilder:
    """
    Utility class to generate versioned, reusable prompts for extracting structured pharmacy invoice data.
    Directly injects the canonical Pydantic JSON schema to guide the LLM.
    """

    VERSION: str = "1.1.0"

    @classmethod
    def get_pharmacy_extraction_prompt(cls, ocr_text: str) -> str:
        """
        Generates the system prompt instructing the LLM to extract data from raw OCR text
        and format it to match the canonical Invoice schema.

        Args:
            ocr_text (str): The raw text extracted from the document.

        Returns:
            str: The fully compiled system prompt.
        """
        # Inject the schema JSON to guide the LLM exactly on structure
        schema_json = json.dumps(Invoice.model_json_schema(), indent=2)

        prompt = (
            f"You are an expert AI extraction agent specialized in pharmaceutical purchase invoices. (Prompt Version: {cls.VERSION})\n"
            "Your task is to analyze the raw OCR text below and extract distributor billing information into a structured JSON object matching the requested schema.\n\n"
            
            "--- RAW OCR TEXT ---\n"
            f"{ocr_text}\n"
            "---------------------\n\n"
            
            "--- EXTRACTION RULES ---\n"
            "1. Output format must be STRICTLY valid JSON conforming to the target schema. Do not write explanations.\n"
            "2. No markdown wrappers. Output the JSON block directly (do NOT wrap in ```json ... ```).\n"
            "3. For every field mapped to a 'ValuePair' model, you must provide:\n"
            "   - 'raw': The exact text fragment found on the invoice (e.g. '12/12/26', 'Rs. 250.00').\n"
            "   - 'normalized': The parsed, standardized value (e.g. date as '2026-12-12', numbers as float/int, text standard).\n"
            "   - 'confidence': Estimate a field-level confidence score from 0.0 to 1.0 based on readability.\n"
            "4. Pharmacy columns mapping instructions:\n"
            "   - Product Name: Extract description precisely (e.g. 'DOLO 650 15`S').\n"
            "   - Batch: Extract batch number exactly.\n"
            "   - Expiry Date: Normalize to ISO 'YYYY-MM-DD'. If only MM/YY is given, default day to last day of that month.\n"
            "   - Packaging: Extract pack composition detail (e.g. pack_size='15s', unit_count=15, unit_type='Tablets').\n"
            "   - Quantity: Standardize quantity counts. Check if free promotional items ('free_qty') are present.\n"
            "   - Pricing: Extract MRP, Purchase Rate, and Discount. Calculate the taxable amount.\n"
            "   - Tax: Split CGST, SGST, IGST percentages and totals.\n"
            "5. Verify mathematical aggregates: line item taxable amounts must add up to subtotal, and tax summaries must map by GST rate.\n\n"
            
            "--- TARGET JSON SCHEMA ---\n"
            f"{schema_json}\n"
        )
        return prompt
