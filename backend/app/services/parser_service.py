import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.ocr.easyocr_engine import EasyOCREngine
from app.ocr.base import OCREngine
from app.parsers.csv_parser import CSVParser
from app.parsers.excel_parser import ExcelParser
from app.parsers.image_parser import ImageParser
from app.parsers.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class UnsupportedFileTypeError(Exception):
    """
    Custom exception raised when a file format is not supported by the parser service.
    """
    pass


class ParserService:
    """
    Service coordinating the parsing pipeline.
    Detects file types and routes to the appropriate parser implementation.
    """

    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
        image_parser: Optional[ImageParser] = None,
        pdf_parser: Optional[PDFParser] = None,
        excel_parser: Optional[ExcelParser] = None,
        csv_parser: Optional[CSVParser] = None
    ):
        """
        Initialize the ParserService with dependency injection.
        If no dependencies are provided, defaults will be instantiated lazily.
        """
        self._ocr_engine = ocr_engine
        self._image_parser = image_parser
        self._pdf_parser = pdf_parser
        self.excel_parser = excel_parser or ExcelParser()
        self.csv_parser = csv_parser or CSVParser()
        self.ocr_initialized = False
        self.ocr_init_duration = 0.0

    @property
    def ocr_engine(self) -> OCREngine:
        if self._ocr_engine is None:
            import time
            logger.info("Initializing EasyOCREngine (Lazy Load)...")
            t0 = time.perf_counter()
            self._ocr_engine = EasyOCREngine()
            self.ocr_init_duration = time.perf_counter() - t0
            self.ocr_initialized = True
        return self._ocr_engine

    @property
    def image_parser(self) -> ImageParser:
        if self._image_parser is None:
            self._image_parser = ImageParser(ocr_engine=self.ocr_engine)
        return self._image_parser

    @property
    def pdf_parser(self) -> PDFParser:
        if self._pdf_parser is None:
            self._pdf_parser = PDFParser(ocr_engine=self.ocr_engine)
        return self._pdf_parser

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Detects the file extension, routes to the correct parser, and normalizes the output.

        Args:
            file_path (str): Path to the invoice file.

        Returns:
            Dict[str, Any]: A unified dictionary containing raw text, structured data,
                            and file metadata.
        
        Raises:
            UnsupportedFileTypeError: If the file extension is not supported.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()
        logger.info(f"Routing file with extension '{extension}' to appropriate parser.")

        if extension in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            ocr_result = self.image_parser.parse(str(path))
            return {
                "text": ocr_result.full_text,
                "raw_data": ocr_result,
                "source_file_name": path.name,
                "source_file_type": "image"
            }

        if extension == ".pdf":
            ocr_result = self.pdf_parser.parse(str(path))
            return {
                "text": ocr_result.full_text,
                "raw_data": ocr_result,
                "source_file_name": path.name,
                "source_file_type": "pdf"
            }

        if extension == ".csv":
            csv_result = self.csv_parser.parse(str(path))
            return {
                "text": csv_result["text"],
                "raw_data": csv_result,
                "source_file_name": path.name,
                "source_file_type": "csv"
            }

        if extension in [".xlsx", ".xls"]:
            excel_result = self.excel_parser.parse(str(path))
            return {
                "text": excel_result["text"],
                "raw_data": excel_result,
                "source_file_name": path.name,
                "source_file_type": "excel"
            }

        # Raise custom exception for unsupported formats
        raise UnsupportedFileTypeError(
            f"Unsupported file format '{extension}'. Supported formats: PDF, Images (JPG/PNG/BMP/TIFF), CSV, Excel (XLS/XLSX)."
        )
