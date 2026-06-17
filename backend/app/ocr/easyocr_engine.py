import logging
from statistics import mean
from typing import List
import easyocr

from app.core.config import settings
from app.ocr.base import OCREngine
from app.ocr.schemas import OCRResult, OCRPage, OCRLine, OCRWord

logger = logging.getLogger(__name__)


class EasyOCREngine(OCREngine):
    """
    EasyOCR implementation of the OCREngine interface.
    """

    def __init__(self):
        """
        Initialize the EasyOCR Reader once to reuse it across OCR tasks.
        """
        try:
            logger.info("Initializing EasyOCR Reader...")
            self.reader = easyocr.Reader(
                lang_list=settings.OCR_LANGUAGES,
                gpu=settings.OCR_GPU
            )
            logger.info("EasyOCR Reader successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR Reader: {e}")
            raise RuntimeError(f"OCR Engine initialization failed: {e}") from e

    def extract_text(self, file_path: str) -> OCRResult:
        """
        Run OCR on the given image path and build a structured OCRResult.
        """
        try:
            logger.info(f"Running OCR on file: {file_path}")
            # Each entry in results is: (bbox, text, confidence)
            results = self.reader.readtext(file_path)
            
            lines: List[OCRLine] = []
            text_lines: List[str] = []

            for bbox, text, confidence in results:
                text_str = str(text).strip()
                conf_val = float(confidence)
                text_lines.append(text_str)

                # Ensure coordinates are integers
                box_coords = [[int(point[0]), int(point[1])] for point in bbox]

                # Segment line box into word-level boxes proportionally
                words = self._split_line_into_words(box_coords, text_str, conf_val)

                lines.append(
                    OCRLine(
                        text=text_str,
                        confidence=conf_val,
                        words=words
                    )
                )

            # EasyOCR processes a single image, representing Page 1
            page = OCRPage(
                page_number=1,
                lines=lines
            )

            full_text = "\n".join(text_lines)

            return OCRResult(
                pages=[page],
                full_text=full_text
            )

        except Exception as e:
            logger.error(f"Error during EasyOCR text extraction: {e}")
            raise RuntimeError(f"OCR text extraction failed: {e}") from e

    def _split_line_into_words(self, bbox: List[List[int]], text: str, confidence: float) -> List[OCRWord]:
        """
        Proportionally segment a line bounding box into word bounding boxes using vector interpolation.
        
        Args:
            bbox: Bounding box of the line as 4 points: [top-left, top-right, bottom-right, bottom-left].
            text: Text content of the line.
            confidence: Confidence value of the line extraction.
        """
        words = text.split()
        if not words:
            return []

        # If there's only 1 word, the line's bbox is the word's bbox
        if len(words) == 1:
            return [OCRWord(text=text, confidence=confidence, bbox=bbox)]

        p1, p2, p3, p4 = bbox
        
        # Calculate direction vectors for the top and bottom borders
        v_top = [p2[0] - p1[0], p2[1] - p1[1]]
        v_bottom = [p3[0] - p4[0], p3[1] - p4[1]]
        
        num_words = len(words)
        ocr_words: List[OCRWord] = []

        for i, word in enumerate(words):
            # Proportional bounds for this word
            t_start = i / num_words
            t_end = (i + 1) / num_words

            # Interpolate points along the top and bottom edge vectors
            w_p1 = [int(p1[0] + t_start * v_top[0]), int(p1[1] + t_start * v_top[1])]
            w_p2 = [int(p1[0] + t_end * v_top[0]), int(p1[1] + t_end * v_top[1])]
            w_p3 = [int(p4[0] + t_end * v_bottom[0]), int(p4[1] + t_end * v_bottom[1])]
            w_p4 = [int(p4[0] + t_start * v_bottom[0]), int(p4[1] + t_start * v_bottom[1])]

            ocr_words.append(
                OCRWord(
                    text=word,
                    confidence=confidence,
                    bbox=[w_p1, w_p2, w_p3, w_p4]
                )
            )

        return ocr_words
