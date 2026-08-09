import logging
from app.ocr.schemas import OCRResult
from app.schemas.invoice_schema import Invoice
from app.extraction.header_extractor import HeaderExtractor

logger = logging.getLogger(__name__)


class RuleBasedInvoiceExtractor:
    """
    Rule-based extractor that runs regex-based extraction to populate
    the header information of an invoice and returns a validated Invoice model.
    """

    def extract(self, ocr_result: OCRResult) -> Invoice:
        """
        Extract method using HeaderExtractor to retrieve structured invoice details.

        Args:
            ocr_result (OCRResult): The raw text and details parsed from document pages.

        Returns:
            Invoice: Structured model matching the canonical Invoice schema.
        """
        logger.info("Executing rule-based invoice extraction pipeline.")
        
        # Preprocess text
        from app.extraction.text_preprocessor import TextPreprocessor
        _, cleaned_text = TextPreprocessor.preprocess(ocr_result.full_text)
        
        # Run header extraction rules using cleaned text
        extracted_data = HeaderExtractor.extract(cleaned_text)
        
        # Run item extraction rules using cleaned text and ocr_result
        from app.extraction.item_extractor import ItemExtractor
        extracted_data["items"] = ItemExtractor.extract_items(cleaned_text, ocr_result=ocr_result)
        
        # Load and validate using Pydantic model
        return Invoice.model_validate(extracted_data)
