import logging
import os
import shutil
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.ai.hybrid_extractor import HybridInvoiceExtractor
from app.core.config import settings
from app.core.security import verify_bearer_token
from app.ocr.schemas import OCRResult
from app.schemas.common import ErrorResponse
from app.schemas.invoice_schema import Document
from app.services.parser_service import ParserService, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

router = APIRouter()


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".csv",
    ".xls",
    ".xlsx",
}

PARSE_ENDPOINT_DESCRIPTION = """
Uploads and parses a pharmacy invoice file, returning structured canonical Document JSON.

### Supported File Formats
- **PDF Documents**: Native digital text & scanned document OCR (`.pdf`)
- **Image Files**: Scanned or photographed invoice images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`)
- **Spreadsheets / Tabular**: Excel workbooks and flat CSV files (`.xlsx`, `.xls`, `.csv`)

### Processing Flow
1. **Parser Ingestion**: Extracts text, tabular cells, or invokes EasyOCR on image areas.
2. **Hybrid Extraction**: Merges Gemini LLM structured outputs with deterministic regex heuristics.
3. **Inventory Reconciliation**: Performs fuzzy matching of extracted items against the master inventory catalog.
4. **Validation & Integrity**: Executes mathematical checks across taxes, discounts, line totals, and grand total.

### Security
Secured endpoint requiring a valid Bearer token in the `Authorization` header.
"""


@router.post(
    "/parse",
    response_model=Document,
    status_code=status.HTTP_200_OK,
    summary="Parse and extract structured data from an invoice file",
    description=PARSE_ENDPOINT_DESCRIPTION,
    responses={
        200: {
            "description": "Successfully parsed and extracted structured invoice document.",
            "model": Document,
        },
        400: {
            "description": "Bad Request - Missing filename, empty file (0 bytes), or unsupported file format.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "unsupported_format": {
                            "summary": "Unsupported File Format",
                            "value": {
                                "detail": "Unsupported file format '.docx'. Supported formats: .bmp, .csv, .jpeg, .jpg, .pdf, .png, .tiff, .xls, .xlsx"
                            },
                        },
                        "empty_file": {
                            "summary": "Empty File (0 Bytes)",
                            "value": {
                                "detail": "The uploaded file is empty (0 bytes). Please upload a valid invoice document."
                            },
                        },
                        "missing_filename": {
                            "summary": "Missing Filename",
                            "value": {
                                "detail": "Uploaded file must have a valid filename."
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid Bearer authentication token.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "missing_token": {
                            "summary": "Missing Authorization Token",
                            "value": {
                                "detail": "Missing authentication token. Please provide a valid Bearer token in the Authorization header."
                            },
                        },
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid authentication token."
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Unprocessable Entity - Corrupt document or failure during AI extraction.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "corrupt_file": {
                            "summary": "Corrupt or Unreadable Document",
                            "value": {
                                "detail": "The uploaded file is corrupt or could not be parsed as a valid document."
                            },
                        },
                        "extraction_failure": {
                            "summary": "Structured Extraction Failure",
                            "value": {
                                "detail": "Failed to extract structured invoice data from the document."
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - Unexpected server error during processing.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An unexpected error occurred while processing the invoice. Please try again later."
                    }
                }
            },
        },
    },
)
async def parse_invoice(
    file: UploadFile = File(
        ...,
        description="Pharmacy invoice file (.pdf, .png, .jpg, .jpeg, .tiff, .bmp, .csv, .xls, .xlsx)"
    ),
    token: str = Depends(verify_bearer_token),
) -> Document:
    """
    Receives an uploaded invoice file, saves it to a temporary file, routes it through
    ParserService and HybridInvoiceExtractor, and returns the canonical Document model.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename."
        )

    file_extension = Path(file.filename).suffix.lower()
    if not file_extension or file_extension not in SUPPORTED_EXTENSIONS:
        supported_str = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_extension}'. Supported formats: {supported_str}"
        )

    temp_file_path = None
    try:
        # Create a named temporary file preserving the original extension
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_written = 0
        chunk_size = 64 * 1024  # 64 KB chunks

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                temp_file.write(chunk)

        # Check if the uploaded file is empty (0 bytes)
        if bytes_written == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty (0 bytes). Please upload a valid invoice document."
            )

        logger.info(f"Received file '{file.filename}' ({bytes_written} bytes), saved temporarily to '{temp_file_path}'")

        # 1. Parse using ParserService
        parser_service = ParserService()
        try:
            parse_result = parser_service.parse(temp_file_path)
        except UnsupportedFileTypeError as e:
            logger.warning(f"Unsupported file format rejected: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as parse_err:
            logger.error(f"Parser failed on file '{file.filename}': {parse_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded file is corrupt or could not be parsed as a valid document."
            )

        # Ensure original file name is used in output
        original_file_name = file.filename
        source_file_type = parse_result.get("source_file_type", "pdf")

        # 2. Normalize OCR payload
        if source_file_type in ["csv", "excel"]:
            ocr_result = OCRResult(full_text=parse_result.get("text", ""))
        else:
            ocr_result = parse_result.get("raw_data")
            if ocr_result is None:
                ocr_result = OCRResult(full_text=parse_result.get("text", ""))

        # 3. Extract and Validate using Hybrid Extractor
        try:
            extractor = HybridInvoiceExtractor()
            document = extractor.extract(
                ocr_result=ocr_result,
                file_name=original_file_name,
                file_type=source_file_type
            )
        except Exception as extract_err:
            logger.error(f"Extraction failed for file '{file.filename}': {extract_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Failed to extract structured invoice data from the document."
            )

        return document

    except HTTPException:
        # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Unexpected server error processing invoice '{file.filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the invoice. Please try again later."
        )
    finally:
        # Close uploaded file handle
        try:
            await file.close()
        except Exception as close_err:
            logger.warning(f"Failed to close upload file handle: {close_err}")

        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_err:
                logger.warning(f"Failed to remove temp file '{temp_file_path}': {cleanup_err}")
