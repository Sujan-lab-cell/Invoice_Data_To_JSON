from abc import ABC, abstractmethod
from app.ocr.schemas import OCRResult


class OCREngine(ABC):
    """
    Abstract Base Class representing a generic OCR Engine interface.
    Any OCR implementation (such as EasyOCR, Tesseract, or cloud APIs) must inherit from this class.
    """

    @abstractmethod
    def extract_text(self, file_path: str) -> OCRResult:
        """
        Extract text from the given file and return a structured OCRResult.

        Args:
            file_path (str): The path to the image or document file to process.

        Returns:
            OCRResult: A structured Pydantic model containing pages, lines, words, and aggregated text.
        """
        pass
