import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HeaderExtractor:
    """
    Rule-based header extractor for pharmacy invoices.
    Uses regex patterns and heuristic scans to find known metadata fields (invoice number, date, GSTINs, names, payment type).
    """

    # Regex patterns for Invoice Number
    INVOICE_NUM_PATTERNS = [
        r"(?:tax\s+)?inv(?:oice)?\.?\s*(?:no|num|number)?\.?\s*[:\-]?\s*([a-z0-9/\-]+)",
        r"bill\s*(?:no|num|number)?\.?\s*[:\-]?\s*([a-z0-9/\-]+)",
        r"invoice\s*[:\-]?\s*([a-z0-9/\-]+)",
    ]

    # Regex patterns for Invoice Date
    INVOICE_DATE_PATTERNS = [
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})",
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{2})",
        r"\bdate\s*[:\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})\b",
    ]

    # GSTIN matches a standard 15-character Indian GSTIN
    GSTIN_PATTERN = r"\b([0-9]{2}[a-z]{5}[0-9]{4}[a-z]{1}[1-9a-z]{1}z[0-9a-z]{1})\b"

    # Payment type keywords
    PAYMENT_KEYWORDS = {
        "credit": ["credit", "cr", "due", "on account"],
        "cash": ["cash", "cod", "hand cash"],
    }

    @classmethod
    def extract(cls, ocr_text: str) -> Dict[str, Any]:
        """
        Runs regex-based rules and positional scans across raw OCR text to extract header values.

        Args:
            ocr_text (str): Raw OCR text or page text.

        Returns:
            Dict[str, Any]: Structured dictionary with raw values and field-level confidence scores.
        """
        logger.info("Starting rule-based header extraction.")
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

        extracted = {
            "invoice_number": cls._extract_field_regex(ocr_text, cls.INVOICE_NUM_PATTERNS),
            "invoice_date": cls._extract_field_regex(ocr_text, cls.INVOICE_DATE_PATTERNS),
            "supplier_gstin": {"raw": "", "confidence": 0.0},
            "buyer_gstin": {"raw": "", "confidence": 0.0},
            "supplier_name": {"raw": "", "confidence": 0.0},
            "buyer_name": {"raw": "", "confidence": 0.0},
            "payment_type": cls._extract_payment_type(ocr_text)
        }

        # Extract GSTINs and partition them to Supplier vs Buyer
        cls._extract_gstins(ocr_text, lines, extracted)

        # Extract Supplier & Buyer Names
        cls._extract_names(lines, extracted)

        return extracted

    @classmethod
    def _extract_field_regex(cls, text: str, patterns: List[str]) -> Dict[str, Any]:
        """
        Iterates over a list of regex patterns to extract a raw value.
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_val = match.group(1).strip()
                # Ignore empty matches or placeholders
                if raw_val and not raw_val.lower().startswith("order"):
                    return {"raw": raw_val, "confidence": 1.0}
        return {"raw": "", "confidence": 0.0}

    @classmethod
    def _extract_gstins(cls, text: str, lines: List[str], extracted: Dict[str, Any]):
        """
        Finds all Indian GSTIN numbers and decides which belongs to supplier vs buyer.
        """
        gstins = re.findall(cls.GSTIN_PATTERN, text, re.IGNORECASE)
        # Standardize to uppercase
        gstins = list(set([g.upper() for g in gstins]))

        if not gstins:
            return

        # If only one GSTIN is found, we map it to the Supplier by default (high probability)
        if len(gstins) == 1:
            extracted["supplier_gstin"] = {"raw": gstins[0], "confidence": 0.9}
            return

        # If two GSTINs are found, we check the line context
        # Typically, the seller's GSTIN is listed in the top supplier letterhead block,
        # whereas the buyer's is under billing details.
        gstin_positions = {}
        for gstin in gstins:
            for idx, line in enumerate(lines):
                if gstin in line.upper():
                    gstin_positions[gstin] = idx
                    break

        sorted_gstins = sorted(gstin_positions.keys(), key=lambda k: gstin_positions[k])

        # First listed is usually the Supplier, second is Buyer
        extracted["supplier_gstin"] = {"raw": sorted_gstins[0], "confidence": 1.0}
        extracted["buyer_gstin"] = {"raw": sorted_gstins[1], "confidence": 1.0}

    @classmethod
    def _extract_names(cls, lines: List[str], extracted: Dict[str, Any]):
        """
        Extracts Supplier Name and Buyer Name using line position heuristics.
        """
        if not lines:
            return

        # Supplier Heuristics:
        # The supplier is almost always on the 1st or 2nd line of the invoice letterhead.
        # Often contains words like "LTD", "DISTRIBUTORS", "AGENCY", "PHARMA", etc.
        supplier_raw = ""
        supplier_confidence = 0.0

        first_line = lines[0].upper()
        # Clean terms like "TAX INVOICE" out of the name
        cleaned_first_line = re.sub(r"\b(?:TAX\s+INVOICE|INVOICE|RETAIL|CASH\s+BILL)\b.*", "", first_line).strip()
        
        if len(cleaned_first_line) > 3:
            supplier_raw = cleaned_first_line
            supplier_confidence = 0.75

        # Refine supplier name if we see "DISTRIBUTORS" or "LTD" in the top 3 lines
        for idx in range(min(3, len(lines))):
            line = lines[idx].upper()
            if any(term in line for term in ["DISTRIBUTORS", "PVT.LTD", "LIMITED", "AGENCIES", "PHARMA"]):
                # If there is a line like "(A UNIT OF EMMARLINK DISTRIBUTORS PVT.LTD.)", get company name
                match = re.search(r"\b([A-Z\s\.\&]+(?:DISTRIBUTORS|LTD|PHARMA|AGENCIES|LIMITED))\b", line)
                if match:
                    supplier_raw = match.group(1).strip()
                    supplier_confidence = 0.9
                    break

        extracted["supplier_name"] = {"raw": supplier_raw, "confidence": supplier_confidence}

        # Buyer Heuristics:
        # Look for the buyer under keywords like "GERMAN PHARMACY", "HOSPITAL", or lines containing "PHARMACY", "MEDICAL"
        buyer_raw = ""
        buyer_confidence = 0.0

        for idx, line in enumerate(lines):
            line_up = line.upper()
            if any(term in line_up for term in ["PHARMACY", "MEDICAL STORE", "CLINIC", "HOSPITAL", "DRUGS & CO"]):
                # Filter out supplier if name matches the top line
                if supplier_raw and supplier_raw[:5] in line_up:
                    continue
                # Found a pharmacy buyer line
                # E.g. "GERMAN PHARMACY, MUPHAPPILANGAD" -> get "GERMAN PHARMACY"
                clean_buyer = line_up.split(",")[0].strip()
                # Clean prefix details
                clean_buyer = re.sub(r"^(?:TO|SOLD\s+TO|BILL\s+TO)\s*[:\-]?\s*", "", clean_buyer).strip()
                buyer_raw = clean_buyer
                buyer_confidence = 0.85
                break

        extracted["buyer_name"] = {"raw": buyer_raw, "confidence": buyer_confidence}

    @classmethod
    def _extract_payment_type(cls, text: str) -> Dict[str, Any]:
        """
        Scans for payment terms (Credit, Cash, COD).
        """
        text_lower = text.lower()
        
        # Exact keyword search
        for pay_mode, keywords in cls.PAYMENT_KEYWORDS.items():
            for word in keywords:
                pattern = r"\b" + re.escape(word) + r"\b"
                if re.search(pattern, text_lower):
                    return {"raw": pay_mode.upper(), "confidence": 0.9}

        return {"raw": "UNKNOWN", "confidence": 0.0}
