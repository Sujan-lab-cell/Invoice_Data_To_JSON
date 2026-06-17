from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional
from pydantic import ValidationError

from app.ocr.schemas import OCRResult
from app.schemas.invoice_schema import Invoice
from app.ai.prompts import PromptBuilder
from app.ai.json_parser import JSONParser
from app.exceptions import ValidationException

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
    Service coordinating the extraction of structured pharmacy invoice data from OCRResult.
    Delegates prompt engineering, JSON repairing, and schema validation to specialized utilities.
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
        Delegates prompt creation to the PromptBuilder utility.

        Args:
            ocr_text (str): The raw text extracted from the invoice file.

        Returns:
            str: Structured prompt text.
        """
        return PromptBuilder.get_pharmacy_extraction_prompt(ocr_text)

    def parse_response(self, raw_response: str) -> Invoice:
        """
        Parses raw text using JSONParser and validates it against the Invoice schema.

        Args:
            raw_response (str): The raw text/JSON returned by the LLM.

        Returns:
            Invoice: The validated canonical Invoice model.

        Raises:
            ValidationException: If parsing fails or the schema validation check fails.
        """
        try:
            # Parse and repair raw text using the JSONParser utility
            parsed_dict = JSONParser.parse(raw_response)
            
            # Validate against canonical Invoice schema
            return Invoice.model_validate(parsed_dict)
            
        except ValidationError as ve:
            logger.error(f"Invoice schema validation failed: {ve}")
            raise ValidationException(
                message="Extracted data did not conform to the canonical Invoice schema structure.",
                details=str(ve)
            ) from ve
        except Exception as e:
            logger.error(f"JSON parsing or extraction cleaning failed: {e}")
            raise ValidationException(
                message=f"Failed to process and validate LLM extraction response: {e}"
            ) from e

    def extract(self, ocr_result: OCRResult) -> Invoice:
        """
        Execute the full extraction pipeline: build prompt -> call LLM -> parse, repair & validate.

        Args:
            ocr_result (OCRResult): Structured OCR results.

        Returns:
            Invoice: The parsed and validated canonical Invoice.
        
        Raises:
            ValidationException: If schema validation fails.
            LLMProviderException: If generative AI provider fails.
        """
        logger.info("Executing structured AI invoice extraction pipeline.")
        try:
            # 1. Build extraction prompt from OCRResult text using PromptBuilder
            prompt = self.build_prompt(ocr_result.full_text)
            
            # 2. Query LLM provider with target JSON schema constraints
            schema_dict = Invoice.model_json_schema()
            raw_output = self.provider.generate(prompt, response_schema=schema_dict)
            
            # 3. Parse, repair, and validate response
            return self.parse_response(raw_output)
            
        except Exception as e:
            logger.error(f"Extraction pipeline execution failed: {e}")
            raise
