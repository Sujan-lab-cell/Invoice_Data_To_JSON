import json
import logging
from typing import Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the Gemini API client once globally.
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set in configuration settings.")


class GeminiAPIError(Exception):
    """Exception raised when a Gemini API call or response parsing fails."""
    pass


def generate_json(prompt: str, model_name: str = "gemini-2.5-flash") -> dict:
    """
    Sends a prompt to the Gemini API and parses the response to return a JSON dictionary.
    Includes automatic fallback across available Gemini models (2.5-flash, 1.5-flash, 2.0-flash).

    Args:
        prompt (str): The prompt text to send to Gemini.
        model_name (str): The preferred Gemini model name to try first.

    Returns:
        dict: The parsed JSON dictionary.

    Raises:
        ValueError: If the GEMINI_API_KEY is not configured.
        GeminiAPIError: If all API calls fail or if the output is not valid JSON.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in settings.")

    models_to_try = [model_name]
    for alt in ["gemini-1.5-flash", "gemini-2.0-flash"]:
        if alt not in models_to_try:
            models_to_try.append(alt)

    last_error: Optional[Exception] = None

    for m_name in models_to_try:
        try:
            logger.info(f"Requesting structured JSON extraction from Gemini using model '{m_name}'")
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            if not response or not response.text:
                continue

            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError as json_err:
                logger.error(f"Gemini API returned invalid JSON from model '{m_name}': {json_err}")
                raise GeminiAPIError(f"Gemini API returned invalid JSON: {json_err}") from json_err

        except GeminiAPIError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini API model '{m_name}' call failed: {e}. Attempting next fallback model...")

    logger.error(f"All Gemini models failed: {last_error}", exc_info=True)
    raise GeminiAPIError(f"Gemini API invocation failed: {last_error}") from last_error
