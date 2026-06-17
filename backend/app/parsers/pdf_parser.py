import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
import pdfplumber
from pdf2image import convert_from_path

from app.ocr.base import OCREngine
from app.ocr.schemas import OCRResult, OCRPage, OCRLine, OCRWord
from app.utils.image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Parser for PDF invoices.
    Detects if a PDF contains digital text or is scanned, and extracts content accordingly.
    """

    def __init__(self, ocr_engine: OCREngine):
        """
        Dependency inject the OCR engine.

        Args:
            ocr_engine (OCREngine): OCR engine implementing the OCREngine interface.
        """
        self.ocr_engine = ocr_engine

    def parse(self, file_path: str) -> OCRResult:
        """
        Parse a PDF file. Direct text extraction is attempted first. If the file is scanned
        or contains insufficient text, it falls back to pdf2image + OCR.

        Args:
            file_path (str): Path to the PDF file.

        Returns:
            OCRResult: Structured Pydantic model containing pages, lines, and words.
        """
        logger.info(f"Parsing PDF file: {file_path}")
        
        # 1. Attempt direct text extraction using pdfplumber
        digital_pages = self._extract_text_pdf(file_path)
        
        # Calculate total characters extracted directly
        total_text = "\n".join([page.full_text for page in [
            OCRResult(pages=[dp], full_text="\n".join([line.text for line in dp.lines]))
            for dp in digital_pages
        ]])
        
        # Heuristic: If more than 50 characters are found, treat it as a digital text PDF
        if len(total_text.strip()) > 50:
            logger.info("Sufficient digital text detected. Using pdfplumber extraction.")
            return OCRResult(
                pages=digital_pages,
                full_text="\n".join([line.text for dp in digital_pages for line in dp.lines])
            )
            
        # 2. Fall back to converting PDF to images and running OCR
        logger.info("Insufficient digital text. Falling back to OCR extraction.")
        return self._extract_scanned_pdf(file_path)

    def _extract_text_pdf(self, file_path: str) -> List[OCRPage]:
        """
        Extract text directly from a digital PDF file page-by-page.
        """
        ocr_pages: List[OCRPage] = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if not page_text:
                        continue
                    
                    lines: List[OCRLine] = []
                    for line_text in page_text.splitlines():
                        line_str = line_text.strip()
                        if not line_str:
                            continue
                        
                        # Generate word tokens with 1.0 confidence (since digital text is exact)
                        words = [
                            OCRWord(text=w, confidence=1.0, bbox=[])
                            for w in line_str.split()
                        ]
                        
                        lines.append(
                            OCRLine(
                                text=line_str,
                                confidence=1.0,
                                words=words
                            )
                        )
                        
                    ocr_pages.append(
                        OCRPage(
                            page_number=idx + 1,
                            lines=lines
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed direct PDF text extraction: {e}. Falling back to OCR.")
            
        return ocr_pages

    def _extract_scanned_pdf(self, file_path: str) -> OCRResult:
        """
        Convert scanned PDF pages to images and run OCR on each page.
        """
        ocr_pages: List[OCRPage] = []
        full_text_blocks: List[str] = []

        try:
            with TemporaryDirectory() as temp_dir:
                # Convert PDF pages to list of PIL Images
                # Note: Requires system-level 'poppler' package installed
                pages = convert_from_path(file_path, dpi=300)
                
                for idx, page in enumerate(pages):
                    image_path = Path(temp_dir) / f"page_{idx + 1}.jpg"
                    page.save(str(image_path), "JPEG")

                    # Preprocess page image
                    raw_image = ImagePreprocessor.load_image(str(image_path))
                    processed_image = ImagePreprocessor.deskew(
                        ImagePreprocessor.grayscale(raw_image)
                    )
                    
                    # Run OCR on preprocessed page
                    page_result = self.ocr_engine.extract_text(processed_image)
                    
                    # Merge page structure and override to PDF page index (1-indexed)
                    for ocr_page in page_result.pages:
                        ocr_page.page_number = idx + 1
                        ocr_pages.append(ocr_page)
                        
                    full_text_blocks.append(page_result.full_text)
                    
            return OCRResult(
                pages=ocr_pages,
                full_text="\n".join(full_text_blocks)
            )
        except Exception as e:
            logger.error(f"Failed scanned PDF extraction: {e}")
            raise RuntimeError(f"Scanned PDF extraction failed: {e}") from e
