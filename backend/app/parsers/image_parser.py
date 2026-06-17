from app.ocr.base import OCREngine
from app.ocr.schemas import OCRResult
from app.utils.image_preprocessor import ImagePreprocessor


class ImageParser:
    """
    Parser for image-based invoices.
    Applies image preprocessing and utilizes an injected OCR engine to extract structured text.
    """

    def __init__(self, ocr_engine: OCREngine):
        """
        Dependency inject the OCR engine.

        Args:
            ocr_engine (OCREngine): OCR engine implementing the OCREngine interface.
        """
        self.ocr_engine = ocr_engine

    def parse(self, image_path: str) -> OCRResult:
        """
        Preprocess the image and execute the OCR engine to extract text.

        Args:
            image_path (str): File path to the invoice image.

        Returns:
            OCRResult: Structured Pydantic model containing the OCR extraction results.
        """
        # 1. Load the raw image
        raw_image = ImagePreprocessor.load_image(image_path)

        # 2. Run preprocessing (Convert to grayscale and correct skew)
        processed_image = ImagePreprocessor.deskew(
            ImagePreprocessor.grayscale(raw_image)
        )

        # 3. Perform OCR using the injected engine
        ocr_result = self.ocr_engine.extract_text(processed_image)

        return ocr_result