from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint.
    """
    status: str = Field(
        default="ok",
        description="Current operational status of the API server.",
        json_schema_extra={"example": "ok"}
    )


class ErrorResponse(BaseModel):
    """
    Standard error response model returned when request processing fails.
    """
    detail: str = Field(
        ...,
        description="Detailed explanation of the error.",
        json_schema_extra={"example": "Unsupported file format '.txt'. Supported formats: .bmp, .csv, .jpeg, .jpg, .pdf, .png, .tiff, .xls, .xlsx"}
    )
