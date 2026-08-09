import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

TEST_BEARER_TOKEN = "test_api_bearer_token_xyz987"
os.environ["API_BEARER_TOKEN"] = TEST_BEARER_TOKEN

from fastapi import HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.security import verify_bearer_token
from app.api.v1.endpoints.invoices import parse_invoice, SUPPORTED_EXTENSIONS
from app.main import app, health_check
from app.schemas.invoice_schema import Document


class TestAPIEndpoints(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive API test suite covering:
    1. GET /health
    2. Valid authenticated PDF upload
    3. Missing file / empty file
    4. Unsupported file formats
    5. Missing authentication
    6. Invalid authentication
    7. Parser and extraction failure
    """

    async def asyncSetUp(self) -> None:
        settings.API_BEARER_TOKEN = TEST_BEARER_TOKEN
        self.valid_token = TEST_BEARER_TOKEN
        self.sample_dir = Path(__file__).parent / "sample_invoices"

    # =========================================================================
    # 1. GET /health
    # =========================================================================
    async def test_01_get_health_endpoint(self) -> None:
        """Test GET /health returns status 200 and {'status': 'ok'} without authentication."""
        # 1. Test direct handler execution
        response = await health_check()
        self.assertEqual(response, {"status": "ok"})

        # 2. Verify route registration in FastAPI app
        health_route = next(
            (r for r in app.routes if getattr(r, "path", None) == "/health"),
            None
        )
        self.assertIsNotNone(health_route, "Route '/health' is not registered in FastAPI app.")
        self.assertIn("GET", health_route.methods, "Route '/health' does not support GET.")

    # =========================================================================
    # 2. Valid authenticated PDF upload
    # =========================================================================
    async def test_02_valid_authenticated_pdf_upload(self) -> None:
        """Test POST /api/v1/invoices/parse with a valid PDF and valid Bearer token."""
        sample_pdfs = list(self.sample_dir.glob("*.pdf"))
        self.assertTrue(len(sample_pdfs) > 0, "No sample PDF files found in tests/sample_invoices/")

        sample_pdf = sample_pdfs[0]
        with open(sample_pdf, "rb") as f:
            pdf_bytes = f.read()

        file_obj = io.BytesIO(pdf_bytes)
        upload = UploadFile(filename=sample_pdf.name, file=file_obj)

        document = await parse_invoice(file=upload, token=self.valid_token)

        self.assertIsInstance(document, Document, "Expected response to be an instance of Document schema.")
        self.assertEqual(document.source_file_name, sample_pdf.name)
        self.assertEqual(document.source_file_type, "pdf")
        self.assertIsNotNone(document.invoice_data, "Document missing invoice_data.")

        invoice = document.invoice_data
        self.assertIsNotNone(invoice.invoice_number.normalized or invoice.invoice_number.raw)
        self.assertIsNotNone(invoice.supplier.name.normalized or invoice.supplier.name.raw)
        self.assertIsNotNone(invoice.buyer.name.normalized or invoice.buyer.name.raw)
        self.assertTrue(len(invoice.items) > 0, "Line items list should not be empty for sample invoice.")
        self.assertIsNotNone(invoice.totals.grand_total.normalized or invoice.totals.grand_total.raw)

    # =========================================================================
    # 3. Missing file / Empty file
    # =========================================================================
    async def test_03_missing_filename(self) -> None:
        """Test POST /api/v1/invoices/parse with empty/missing filename raises HTTP 400."""
        upload = UploadFile(filename="", file=io.BytesIO(b"some binary content"))
        with self.assertRaises(HTTPException) as ctx:
            await parse_invoice(file=upload, token=self.valid_token)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("filename", ctx.exception.detail.lower())

    async def test_03_empty_file_zero_bytes(self) -> None:
        """Test POST /api/v1/invoices/parse with 0-byte file raises HTTP 400."""
        upload = UploadFile(filename="invoice.pdf", file=io.BytesIO(b""))
        with self.assertRaises(HTTPException) as ctx:
            await parse_invoice(file=upload, token=self.valid_token)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("empty", ctx.exception.detail.lower())

    # =========================================================================
    # 4. Unsupported file formats
    # =========================================================================
    async def test_04_unsupported_file_formats(self) -> None:
        """Test POST /api/v1/invoices/parse with unsupported formats raises HTTP 400."""
        unsupported_extensions = [
            "invoice.txt",
            "invoice.docx",
            "invoice.exe",
            "invoice.zip",
            "invoice.json",
            "invoice.py",
            "invoice.html",
            "invoice_without_ext"
        ]

        for fname in unsupported_extensions:
            upload = UploadFile(filename=fname, file=io.BytesIO(b"dummy payload"))
            with self.assertRaises(HTTPException, msg=f"Expected HTTP 400 for '{fname}'") as ctx:
                await parse_invoice(file=upload, token=self.valid_token)
            self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("unsupported", ctx.exception.detail.lower())

    # =========================================================================
    # 5. Missing authentication
    # =========================================================================
    async def test_05_missing_authentication_token(self) -> None:
        """Test verify_bearer_token with missing credentials raises HTTP 401."""
        with self.assertRaises(HTTPException) as ctx:
            await verify_bearer_token(credentials=None)
        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("missing", ctx.exception.detail.lower())
        self.assertEqual(ctx.exception.headers.get("WWW-Authenticate"), "Bearer")

    async def test_05_empty_bearer_credentials(self) -> None:
        """Test verify_bearer_token with empty credentials string raises HTTP 401."""
        empty_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        with self.assertRaises(HTTPException) as ctx:
            await verify_bearer_token(credentials=empty_creds)
        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("missing", ctx.exception.detail.lower())

    # =========================================================================
    # 6. Invalid authentication
    # =========================================================================
    async def test_06_invalid_authentication_token(self) -> None:
        """Test verify_bearer_token with invalid credentials raises HTTP 401."""
        invalid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_secret_token_123")
        with self.assertRaises(HTTPException) as ctx:
            await verify_bearer_token(credentials=invalid_creds)
        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("invalid", ctx.exception.detail.lower())

    async def test_06_valid_authentication_success(self) -> None:
        """Test verify_bearer_token with correct credentials succeeds."""
        valid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=self.valid_token)
        result = await verify_bearer_token(credentials=valid_creds)
        self.assertEqual(result, self.valid_token)

    # =========================================================================
    # 7. Parser and extraction failure
    # =========================================================================
    async def test_07_parser_failure_corrupt_file(self) -> None:
        """Test POST /api/v1/invoices/parse with corrupt binary data raises HTTP 422."""
        corrupt_upload = UploadFile(
            filename="corrupt_invoice.pdf",
            file=io.BytesIO(b"NOT_A_VALID_PDF_BINARY_HEADER_OR_BODY")
        )
        with self.assertRaises(HTTPException) as ctx:
            await parse_invoice(file=corrupt_upload, token=self.valid_token)
        self.assertEqual(ctx.exception.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("corrupt", ctx.exception.detail.lower())

    async def test_07_parser_service_exception_handling(self) -> None:
        """Test POST /api/v1/invoices/parse raises HTTP 422 when ParserService raises exception."""
        upload = UploadFile(
            filename="invoice.pdf",
            file=io.BytesIO(b"%PDF-1.4 dummy valid-looking header with corrupt body")
        )
        with patch("app.api.v1.endpoints.invoices.ParserService.parse", side_effect=RuntimeError("Engine failure")):
            with self.assertRaises(HTTPException) as ctx:
                await parse_invoice(file=upload, token=self.valid_token)
            self.assertEqual(ctx.exception.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
            self.assertIn("corrupt", ctx.exception.detail.lower())

    async def test_07_extractor_failure_handling(self) -> None:
        """Test POST /api/v1/invoices/parse raises HTTP 422 when HybridInvoiceExtractor fails."""
        upload = UploadFile(
            filename="invoice.pdf",
            file=io.BytesIO(b"%PDF-1.4 dummy header")
        )
        mock_parse_result = {
            "source_file_type": "pdf",
            "text": "sample text",
            "raw_data": None
        }
        with patch("app.api.v1.endpoints.invoices.ParserService.parse", return_value=mock_parse_result):
            with patch("app.api.v1.endpoints.invoices.HybridInvoiceExtractor.extract", side_effect=Exception("LLM extraction failed")):
                with self.assertRaises(HTTPException) as ctx:
                    await parse_invoice(file=upload, token=self.valid_token)
                self.assertEqual(ctx.exception.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
                self.assertIn("failed to extract", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
