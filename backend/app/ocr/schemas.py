from pydantic import BaseModel, Field
from typing import List


class OCRWord(BaseModel):
    """
    Represents a single recognized word with its bounding box and confidence score.
    """
    text: str = Field(..., description="The recognized word text.")
    confidence: float = Field(..., description="Confidence score of the recognized word (typically 0.0 to 1.0).")
    bbox: List[List[int]] = Field(
        ..., 
        description="Bounding box coordinates of the word as a list of points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]."
    )


class OCRLine(BaseModel):
    """
    Represents a reconstructed line of text composed of individual words.
    """
    text: str = Field(..., description="The complete text of the line.")
    confidence: float = Field(..., description="The average confidence score for this line of text.")
    words: List[OCRWord] = Field(default_factory=list, description="The individual words making up the line.")


class OCRPage(BaseModel):
    """
    Represents a single page in a document containing lines of recognized text.
    """
    page_number: int = Field(..., description="The page number (1-indexed).")
    lines: List[OCRLine] = Field(default_factory=list, description="Lines of text detected on this page.")


class OCRResult(BaseModel):
    """
    The top-level OCR output containing processed pages and the aggregated full text.
    """
    pages: List[OCRPage] = Field(default_factory=list, description="List of pages processed by the OCR engine.")
    full_text: str = Field(..., description="The full combined text across all pages in the document.")
