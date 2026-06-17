from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Dict, Optional

from app.ocr.schemas import OCRResult
from app.schemas.invoice_schema import Invoice

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers (e.g. OpenAI, Anthropic, Qwen, Gemma, local Ollama).
    """

    @abstractmethod
    def generate(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a text response from the model.

        Args:
            prompt (str): The prompt text sent to the model.
            response_schema (Optional[Dict[str, Any]]): Optional JSON Schema to enforce structured output.

        Returns:
            str: Raw model response (typically expected to be JSON).
        """
        pass


class InvoiceExtractor:
    """
    Service to extract structured canonical invoice data from OCRResult using LLMs.
    """

    def __init__(self, provider: LLMProvider):
        """
        Initialize with a specific LLM provider.

        Args:
            provider (LLMProvider): The LLM client implementation to use.
        """
        self.provider = provider

    def build_prompt(self, ocr_text: str) -> str:
        """
        Constructs the extraction prompt instructing the LLM to extract fields from the OCR text.
        
        Args:
            ocr_text (str): The raw text extracted from the invoice file.

        Returns:
            str: Structured prompt text.
        """
        prompt = (
            "You are an expert OCR Invoice processing assistant specialized in Indian Pharmacy purchase invoices.\n"
            "Analyze the raw OCR text provided below and extract the information into the exact JSON schema requested.\n\n"
            
            "RULES FOR EXTRACTION:\n"
            "1. For each value field, extract a ValuePair containing:\n"
            "   - 'raw': The exact text fragment found on the invoice (do not change spelling/symbols).\n"
            "   - 'normalized': The cleaned version of the data. E.g.:\n"
            "       - Dates: ISO format 'YYYY-MM-DD'\n"
            "       - Numbers: float or integer (remove commas, currency symbols)\n"
            "       - Text: trimmed and standardized strings\n"
            "   - 'confidence': Estimate a confidence score from 0.0 to 1.0 based on clarity.\n"
            "2. Extract pharmacy specific columns: HSN Code, Batch Number, Expiry Date, Quantity, Free Quantity, MRP, Purchase Rate, and GST/Tax breakdown (CGST, SGST, IGST).\n"
            "3. Ensure mathematical consistency: taxable_amount should equal (qty * purchase_rate) minus any discount, and total gst_amount should align with cgst + sgst + igst.\n\n"
            
            "RAW OCR TEXT:\n"
            f"\"\"\"\n{ocr_text}\n\"\"\"\n\n"
            
            "OUTPUT FORMAT:\n"
            "Provide ONLY a valid JSON object matching the requested schema. No explanations, no markdown wrappers (like ```json)."
        )
        return prompt

    def parse_response(self, raw_response: str) -> Invoice:
        """
        Parses the raw JSON string from the LLM and validates it against the Invoice schema.
        Raises ValueError or Pydantic ValidationError if parsing or schema validation fails.

        Args:
            raw_response (str): The raw text/JSON returned by the LLM.

        Returns:
            Invoice: The validated canonical Invoice model.
        
        Raises:
            ValueError: If the raw response is not valid JSON.
            ValidationError: If the parsed dictionary fails validation against the Invoice schema.
        """
        # Clean markdown wrappers if returned by the LLM
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            parsed_dict = json.loads(clean_json)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to decode LLM response JSON: {raw_response}")
            raise ValueError(f"LLM response was not valid JSON: {je}") from je
            
        # Instantiate Pydantic model for validation.
        # This will automatically raise pydantic.ValidationError if schema fails.
        invoice_model = Invoice.model_validate(parsed_dict)
        return invoice_model

    def extract(self, ocr_result: OCRResult) -> Invoice:
        """
        Execute the full extraction pipeline: extract full_text -> build prompt -> call LLM -> parse & validate.

        Args:
            ocr_result (OCRResult): Structured OCR results containing the text.

        Returns:
            Invoice: The parsed and validated canonical Invoice.
        """
        # Extract full_text from OCRResult
        ocr_text = ocr_result.full_text
        
        # Build prompt
        prompt = self.build_prompt(ocr_text)
        
        # Query provider
        schema_dict = Invoice.model_json_schema()
        raw_output = self.provider.generate(prompt, response_schema=schema_dict)
        
        # Parse and validate response
        return self.parse_response(raw_output)
