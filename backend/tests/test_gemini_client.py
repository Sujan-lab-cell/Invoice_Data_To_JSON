import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend folder to sys.path to enable direct app module imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.ai.gemini_client import generate_json, GeminiAPIError


class TestGeminiClientMock(unittest.TestCase):
    """Unit tests for Gemini client using Mock objects."""

    @patch("google.generativeai.GenerativeModel")
    @patch("app.ai.gemini_client.settings")
    def test_generate_json_success(self, mock_settings, mock_model_class):
        # Set up settings mock
        mock_settings.GEMINI_API_KEY = "dummy_key"

        # Mock the model and response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = '{"status": "ok", "message": "hello"}'
        mock_model.generate_content.return_value = mock_response

        # Execute
        result = generate_json("Hello mock model")

        # Verify
        self.assertEqual(result, {"status": "ok", "message": "hello"})
        mock_model.generate_content.assert_called_once_with(
            "Hello mock model",
            generation_config={"response_mime_type": "application/json"}
        )

    @patch("app.ai.gemini_client.settings")
    def test_generate_json_missing_api_key(self, mock_settings):
        mock_settings.GEMINI_API_KEY = None

        with self.assertRaises(ValueError) as ctx:
            generate_json("Should fail")
        
        self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))

    @patch("google.generativeai.GenerativeModel")
    @patch("app.ai.gemini_client.settings")
    def test_generate_json_api_failure(self, mock_settings, mock_model_class):
        mock_settings.GEMINI_API_KEY = "dummy_key"

        # Mock API exception
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("API connection timeout")

        with self.assertRaises(GeminiAPIError) as ctx:
            generate_json("Should fail")

        self.assertIn("Gemini API invocation failed", str(ctx.exception))

    @patch("google.generativeai.GenerativeModel")
    @patch("app.ai.gemini_client.settings")
    def test_generate_json_invalid_json_returned(self, mock_settings, mock_model_class):
        mock_settings.GEMINI_API_KEY = "dummy_key"

        # Mock invalid JSON response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_model.generate_content.return_value = mock_response

        with self.assertRaises(GeminiAPIError) as ctx:
            generate_json("Should fail parsing")

        self.assertIn("Gemini API returned invalid JSON", str(ctx.exception))


def run_integration_test():
    """Performs a live test call if a real Gemini API Key is configured."""
    print("\n--- Running Live Integration Test ---")
    if not settings.GEMINI_API_KEY:
        print("[SKIP] No GEMINI_API_KEY found in configuration. Skipping live integration test.")
        return True

    print(f"API Key found (starts with: {settings.GEMINI_API_KEY[:4]}...). Sending live request...")
    prompt = "Return a JSON object containing a field 'test' with value 'success' and 'message' with value 'hello from Gemini'."
    try:
        result = generate_json(prompt)
        print("Success! Live response:")
        print(result)
        if result.get("test") == "success":
            print("Integration verification PASSED.")
            return True
        else:
            print("Integration verification FAILED (unexpected structure).")
            return False
    except Exception as e:
        print(f"Integration verification FAILED with error: {e}")
        return False


def main():
    # Run the unittest suite
    print("--- Running Unit Tests with Mocks ---")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGeminiClientMock)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    unit_success = result.wasSuccessful()
    
    # Run the integration test if key is provided
    integration_success = run_integration_test()

    if not unit_success or not integration_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
