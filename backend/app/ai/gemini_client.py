import json
import logging
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the Gemini API client once.
# This configures google-generativeai globally.
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

    Args:
        prompt (str): The prompt text to send to Gemini.
        model_name (str): The name of the Gemini model to use (default: gemini-1.5-flash).

    Returns:
        dict: The parsed JSON dictionary.

    Raises:
        ValueError: If the GEMINI_API_KEY is not configured.
        GeminiAPIError: If the API call fails or if the output is not valid JSON.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in settings.")

    try:
        model = genai.GenerativeModel(model_name)
        # Using response_mime_type="application/json" to prompt Gemini to output valid JSON.
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
    except Exception as e:
        logger.error(f"Gemini API invocation failed: {e}", exc_info=True)
        raise GeminiAPIError(f"Gemini API invocation failed: {e}") from e

    if not response or not response.text:
        raise GeminiAPIError("Gemini API returned an empty or invalid response.")

    text = response.text.strip()

    # In case the response is wrapped in markdown formatting blocks, clean it.
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON. Response text: {response.text}", exc_info=True)
        raise GeminiAPIError(f"Gemini API returned invalid JSON: {e}") from e
