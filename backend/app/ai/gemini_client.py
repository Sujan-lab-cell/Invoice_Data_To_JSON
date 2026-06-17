import json
import logging
import os
from typing import Any, Dict, Optional
import google.generativeai as genai

from app.ai.invoice_extractor import LLMProvider

logger = logging.getLogger(__name__)


class GeminiExtractionError(Exception):
    """
    Custom exception raised when extraction using the Gemini API fails repeatedly.
    """
    pass


class GeminiClient(LLMProvider):
    """
    Gemini implementation of the LLMProvider interface.
    Isolates Gemini configuration, client calls, and safety parsing logic.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        """
        Configure the Gemini SDK and initialize the model using environment credentials.
        """
        # Load API key from env (checking common aliases)
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API Key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY in your environment."
            )

        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"GeminiClient initialized successfully with model: {model_name}")

    def generate(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates content from the Gemini model matching the LLMProvider interface.

        Args:
            prompt (str): Prompt text.
            response_schema (Optional[Dict[str, Any]]): JSON Schema dictionary.

        Returns:
            str: Raw JSON string output.
        """
        generation_config = {}
        if response_schema:
            # Force JSON-only outputs using configuration
            generation_config["response_mime_type"] = "application/json"
            # Some versions of google-generativeai support direct schema enforcement via:
            # generation_config["response_schema"] = response_schema
            
        try:
            config = genai.GenerationConfig(**generation_config)
            response = self.model.generate_content(
                prompt,
                generation_config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generate API call failed: {e}")
            raise RuntimeError(f"Gemini API failure: {e}") from e

    def extract(self, text: str, prompt: str) -> dict:
        """
        Extracts structured data from raw OCR text using a prompt.
        Attempts extraction with a retry hook if JSON parsing fails.

        Args:
            text (str): Raw OCR/document text.
            prompt (str): Extraction prompt guidelines.

        Returns:
            dict: Structured parsed dictionary of extracted data.

        Raises:
            GeminiExtractionError: If extraction fails twice consecutively due to API or JSON errors.
        """
        combined_prompt = f"{prompt}\n\n[INPUT DATA]:\n{text}"
        
        # Implement a retry-once policy (2 attempts max)
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                logger.info(f"Gemini extraction attempt {attempt + 1}/{max_attempts}")
                
                # Configure generation to force JSON-only responses
                config = genai.GenerationConfig(
                    response_mime_type="application/json"
                )
                
                response = self.model.generate_content(
                    combined_prompt,
                    generation_config=config
                )
                
                raw_response = response.text.strip()
                
                # Parse JSON safely (removing potential markdown brackets)
                clean_json = self._clean_json_formatting(raw_response)
                parsed_dict = json.loads(clean_json)
                
                return parsed_dict

            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Gemini extraction attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    # Raise custom exception on repeated failure
                    raise GeminiExtractionError(
                        f"Gemini extraction failed after {max_attempts} attempts. Final error: {e}"
                    ) from e

    def _clean_json_formatting(self, raw_text: str) -> str:
        """
        Cleans any markdown notation wrappers (like ```json ... ```) from the LLM text.
        """
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return clean_text.strip()
