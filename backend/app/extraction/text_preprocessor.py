import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    Lightweight, offline NLP preprocessing layer for invoice text normalization.
    """

    # Common OCR mistakes correction dictionary
    OCR_CORRECTIONS = {
        "lnvoice": "Invoice",
        "GSTlN": "GSTIN",
        "lNV": "INV",
        "1nvoice": "Invoice",
        "Gst1n": "GstIn",
    }

    @classmethod
    def preprocess(cls, text: str) -> Tuple[str, str]:
        """
        Normalizes the input text and corrects common OCR mistakes.

        Args:
            text (str): The raw text extracted from the document.

        Returns:
            Tuple[str, str]: A tuple containing:
                - The original unchanged raw text.
                - The cleaned/preprocessed text.
        """
        if not text:
            return "", ""

        # Normalize line breaks
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize punctuation (smart quotes to standard quotes)
        cleaned = cleaned.replace("‘", "'").replace("’", "'").replace("`", "'")
        cleaned = cleaned.replace("“", '"').replace("”", '"')

        # Correct common OCR mistakes using dictionary replacement (word boundaries)
        for typo, correction in cls.OCR_CORRECTIONS.items():
            pattern = r"\b" + re.escape(typo) + r"\b"
            cleaned = re.sub(pattern, correction, cleaned, flags=re.IGNORECASE)

        # Normalize extra spaces within each line
        lines = []
        for line in cleaned.splitlines():
            line_clean = re.sub(r"[ \t]+", " ", line).strip()
            lines.append(line_clean)
        
        cleaned = "\n".join(lines)

        logger.debug("Text preprocessing completed successfully.")
        return text, cleaned
