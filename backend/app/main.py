import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.exceptions import AppException
from app.schemas.common import HealthResponse

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

API_DESCRIPTION = """
## Pharmacy Invoice Data Extraction API

An automated service for ingesting, parsing, and extracting structured JSON data from pharmacy supplier invoices.

### Key Capabilities
- **Multi-Format Ingestion**: Supports PDF (native digital text & scanned pages), Images (PNG, JPG, JPEG, TIFF, BMP), and Spreadsheets (CSV, XLS, XLSX).
- **Hybrid AI Extraction**: High-accuracy structured data extraction combining Gemini LLM with deterministic regex heuristics.
- **Inventory Matching**: Fuzzy reconciliation against standardized pharmacy product catalogs.
- **Mathematical Validation**: Strict automated validation of taxes, line totals, and grand totals.

### Authentication
Secured endpoints require a Bearer token in the `Authorization` header:
`Authorization: Bearer <API_BEARER_TOKEN>`
"""

TAGS_METADATA = [
    {
        "name": "Invoices",
        "description": "Invoice document ingestion, parsing, and structured data extraction.",
    },
    {
        "name": "Health",
        "description": "API health check and availability monitoring.",
    },
]

app = FastAPI(
    title="Invoice Data to JSON API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
origins = settings.CORS_ORIGINS
allow_creds = settings.CORS_ALLOW_CREDENTIALS if "*" not in origins else False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if isinstance(origins, list) else [origins],
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Application Exception Handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"Application error processing request {request.url.path}: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.message},
    )


# Include API v1 routes
app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health status",
    description="Returns the operational status of the API server. Public endpoint requiring no authentication.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "API service is healthy and operational.",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            },
        }
    },
)
async def health_check():
    """
    Returns the health status of the API.
    """
    return {"status": "ok"}

