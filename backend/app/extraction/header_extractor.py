import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Indian GSTIN state code mapping
STATE_CODES = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh"
}


class HeaderExtractor:
    """
    Robust, rule-based header extractor for pharmacy invoices using regex and positional heuristics.
    Extracts 9 fields and formats the output into a dictionary conforming to the Invoice schema.
    """

    # Regex patterns for Invoice Number - Prioritize explicit label matches
    INVOICE_NUM_PATTERNS = [
        r"(?:tax\s+)?inv(?:oice)?\.?\s*(?:no|num|number|#)\.?\s*[:\-]?\s*([a-zA-Z0-9/\-_]+)",
        r"bill\s*(?:no|num|number|#)\.?\s*[:\-]?\s*([a-zA-Z0-9/\-_]+)",
        r"invoice\s*[:\-]\s*([a-zA-Z0-9/\-_]+)",
        r"invoice\s+([a-zA-Z0-9/\-_]{3,})",
        r"tax\s*inv(?:oice)?\s*no\.?\s*[:\-]?\s*([A-Za-z0-9/_-]+)",
        r"inv\s*no\.?\s*[:\-]?\s*([A-Za-z0-9/_-]+)",
        r"tax\s*inv\s*no\.?\s*[:\-]?\s*([A-Za-z0-9/_-]+)",
    ]

    # Regex patterns for Invoice Date
    INVOICE_DATE_PATTERNS = [
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})",
        r"\bdate\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b",
        r"\bdate\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})\b",
        r"inv\s*dt\.?\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"inv\s*dt\.?\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}\s*[APMapm]{2})",
    ]

    # Regex patterns for Due Date
    DUE_DATE_PATTERNS = [
        r"(?:due\s*date|due\s*by|pay\s*by|due\s*on)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        r"(?:due\s*date|due\s*by|pay\s*by|due\s*on)\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})",
        r"\bdue\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b",
        r"\bdue\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})\b",
    ]

    # Regex patterns for Order Number - Ensure we don't match labels like "No" as value
    ORDER_NUM_PATTERNS = [
        r"(?:order|p\.?o)\.?\s*(?:no|num|number|#)?\.?\s*[:\-]\s*([a-zA-Z0-9/\-_]+)",
        r"(?:order|p\.?o)\.?\s*(?:no|num|number|#)\.?\s+([a-zA-Z0-9/\-_]{3,})",
        r"order\s*no\s*&\s*dt\.?\s*[:\-]?\s*([A-Za-z0-9/_-]*)",
    ]

    # Regex patterns for Indian GSTIN (15 characters)
    GSTIN_PATTERN = r"\b([0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}z[0-9a-zA-Z]{1})\b"

    # Regex patterns for direct State extraction from text
    STATE_PATTERNS = [
        r"state\s*(?:name)?\s*[:\-]\s*([a-zA-Z\s]{3,20})",
        r"state\s*code\s*[:\-]\s*(\d{2})",
        r"state\s*:\s*\d+\s*[-:]\s*([A-Za-z ]+)",
        r"state\s*code\s*:\s*\d+\s*state\s*:\s*([A-Za-z ]+)",
        r"([A-Za-z]+)-\d{2}",
    ]

    # Payment type keywords
    PAYMENT_KEYWORDS = {
        "CREDIT SALE": ["credit sale"],
        "CASH SALE": ["cash sale"],
        "CREDIT": ["credit", "cr", "due", "on account"],
        "CASH": ["cash", "cod", "hand cash", "cash/bill"],
    }

    @classmethod
    def clean_name(cls, name_str: str) -> str:
        """
        Cleans name strings by removing embedded GSTINs, postal codes, noise labels,
        and trailing/leading punctuation.
        """
        if not name_str:
            return ""
            
        # Remove GSTINs
        name_str = re.sub(cls.GSTIN_PATTERN, "", name_str, flags=re.IGNORECASE)
        # Remove postal codes (6 digits)
        name_str = re.sub(r"\b\d{6}\b", "", name_str)
        # Remove words like GSTIN, GST, PAN, DL, D.L.No, Code, Mobile, Ph, Phone, Tax Inv
        name_str = re.sub(r"\b(?:GSTIN|GST|PAN|DL|D\.L\.?No|CODE|MOBILE|PH|PHONE|TAX|INV|NO|BILL)\b[:\-]?\s*", "", name_str, flags=re.IGNORECASE)
        # Clean up leading/trailing punctuation and spaces
        name_str = re.sub(r"^[\s\-\:\,\.\/]+|[\s\-\:\,\.\/]+$", "", name_str)
        # Clean multiple spaces
        name_str = re.sub(r"\s+", " ", name_str).strip()
        
        # Simple word deduplication (e.g. "TRADELINK TRADELINK" -> "TRADELINK")
        parts = [p.strip() for p in name_str.split() if p.strip()]
        if len(parts) >= 2:
            half = len(parts) // 2
            if parts[:half] == parts[half:]:
                name_str = " ".join(parts[:half])
                
        return name_str

    @classmethod
    def normalize_date(cls, date_str: str) -> Optional[str]:
        """
        Normalizes various date formats (DD/MM/YYYY, DD-MM-YY, DD-MMM-YY, etc.) into ISO YYYY-MM-DD.
        """
        if not date_str:
            return None
        cleaned = re.sub(r"[^\w/\-]", "", date_str).strip()

        # 1. Try DD/MM/YYYY or DD-MM-YYYY
        match = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", cleaned)
        if match:
            day_str, month_str, year_str = match.groups()
            day = int(day_str)
            month = int(month_str)
            year = int(year_str)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # 2. Try YYYY-MM-DD or YYYY/MM/DD
        match = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", cleaned)
        if match:
            year_str, month_str, day_str = match.groups()
            year = int(year_str)
            month = int(month_str)
            day = int(day_str)
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # 3. Try alphanumeric: DD-MMM-YYYY or DD-MMM-YY (e.g. 07-May-26)
        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        match = re.match(r"^(\d{1,2})[/\-]([a-zA-Z]+)[/\-](\d{2,4})$", cleaned)
        if match:
            day_str, month_name, year_str = match.groups()
            day = int(day_str)
            month = months_map.get(month_name.lower())
            year = int(year_str)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            if month and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"

        return None

    @classmethod
    def resolve_state(cls, state_raw: str) -> Optional[str]:
        """
        Attempts to resolve the full state name from either a state code or name string.
        """
        if not state_raw:
            return None
        cleaned = state_raw.strip().upper()
        
        # If it's a numeric code, look up directly
        if cleaned.isdigit() and cleaned in STATE_CODES:
            return STATE_CODES[cleaned]
            
        # Try matching state names from keys/values of STATE_CODES
        for code, name in STATE_CODES.items():
            if cleaned == name.upper() or cleaned == code:
                return name
                
        return state_raw.title()

    @classmethod
    def parse_csv_string(cls, text: str) -> List[Dict[str, str]]:
        """
        Parses a pipe-delimited CSV string into a list of row dictionaries.
        """
        import csv
        import io
        rows = []
        lines = []
        for line in text.splitlines():
            if line.strip().startswith("=====") or not line.strip():
                continue
            lines.append(line.strip())
            
        if not lines:
            return rows
            
        csv_file = io.StringIO("\n".join(lines))
        reader = csv.DictReader(csv_file, delimiter="|")
        for row in reader:
            row_clean = {}
            for k, v in row.items():
                if k is None:
                    continue
                v_str = str(v).strip()
                if v_str == "nan" or v_str == "NaN" or not v_str:
                    v_str = ""
                row_clean[k.strip().lower()] = v_str
            rows.append(row_clean)
        return rows

    @classmethod
    def extract(cls, ocr_text: str) -> Dict[str, Any]:
        """
        Runs regex-based rules and positional scans across raw OCR text to extract header values.
        Returns a structured dictionary conforming to the updated Invoice schema.
        """
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        is_structured = "===== SHEET:" in ocr_text or (lines and "|" in lines[0])

        # Check if the text is structured spreadsheet
        if is_structured:
            try:
                rows = cls.parse_csv_string(ocr_text)
                if rows:
                    first_row = rows[0]
                    # Extract fields
                    inv_num = first_row.get("invno", "")
                    inv_date_raw = first_row.get("invdate", "")
                    inv_date_norm = cls.normalize_date(inv_date_raw)
                    
                    # Try to get supplier name from sheet name
                    sheet_name = ""
                    for line in ocr_text.splitlines():
                        if "===== SHEET:" in line:
                            match = re.search(r"===== SHEET:\s*(.*?)\s*=====", line)
                            if match:
                                sheet_name = match.group(1).strip()
                            break
                    supplier_name = sheet_name or "Spreadsheet Supplier"
                    
                    # Resolve state
                    state_raw = first_row.get("state", "") or "Kerala"
                    state_resolved = cls.resolve_state(state_raw)
                    
                    return {
                        "invoice_number": {"raw": inv_num, "normalized": inv_num, "confidence": 1.0},
                        "invoice_date": {"raw": inv_date_raw, "normalized": inv_date_norm, "confidence": 1.0},
                        "due_date": {"raw": "", "normalized": None, "confidence": 0.0},
                        "order_number": {"raw": first_row.get("refordno", ""), "normalized": first_row.get("refordno", ""), "confidence": 1.0},
                        "payment_type": {"raw": "CREDIT", "normalized": "CREDIT", "confidence": 1.0},
                        "supplier": {
                            "name": {"raw": supplier_name, "normalized": supplier_name, "confidence": 1.0},
                            "gstin": {"raw": "", "normalized": "", "confidence": 0.0},
                            "address": {"raw": "", "normalized": None, "confidence": 1.0},
                            "phone": {"raw": "", "normalized": None, "confidence": 1.0},
                            "state": {"raw": state_raw, "normalized": state_resolved, "confidence": 1.0}
                        },
                        "buyer": {
                            "name": {"raw": "Unknown Buyer", "normalized": "Unknown Buyer", "confidence": 0.5},
                            "gstin": {"raw": "", "normalized": "", "confidence": 0.0},
                            "address": {"raw": "", "normalized": None, "confidence": 1.0},
                            "state": {"raw": state_raw, "normalized": state_resolved, "confidence": 1.0}
                        },
                        "items": [],
                        "totals": {
                            "subtotal": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                            "discount_total": None,
                            "tax_total": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                            "grand_total": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                            "round_off": None
                        },
                        "tax_summary": {"items": []}
                    }
            except Exception as e:
                logger.error(f"Failed to parse structured Excel text in header extraction: {e}")

        logger.info("Starting improved header extraction.")
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

        # 1. Extract flat fields
        inv_num_data = cls._extract_field_regex(ocr_text, cls.INVOICE_NUM_PATTERNS)
        inv_date_data = cls._extract_field_regex(ocr_text, cls.INVOICE_DATE_PATTERNS)
        due_date_data = cls._extract_field_regex(ocr_text, cls.DUE_DATE_PATTERNS)
        order_num_data = cls._extract_field_regex(ocr_text, cls.ORDER_NUM_PATTERNS)
        payment_type_data = cls._extract_payment_type(ocr_text)

        # Normalize dates
        inv_date_data["normalized"] = cls.normalize_date(inv_date_data["raw"]) if inv_date_data["raw"] else None
        due_date_data["normalized"] = cls.normalize_date(due_date_data["raw"]) if due_date_data["raw"] else None

        # 2. Extract GSTINs and classify them
        supplier_gstin, buyer_gstin = cls._extract_and_classify_gstins(ocr_text, lines)

        # 3. Extract States (Supplier and Buyer)
        supplier_state, buyer_state = cls._extract_and_resolve_states(lines, supplier_gstin, buyer_gstin)

        # 4. Extract Names
        supplier_name, buyer_name = cls._extract_names(lines)

        # 5. Build and return structured Invoice schema dictionary
        return {
            "invoice_number": {
                "raw": inv_num_data["raw"],
                "normalized": inv_num_data["raw"],
                "confidence": inv_num_data["confidence"]
            },
            "invoice_date": {
                "raw": inv_date_data["raw"],
                "normalized": inv_date_data["normalized"],
                "confidence": inv_date_data["confidence"]
            },
            "due_date": {
                "raw": due_date_data["raw"],
                "normalized": due_date_data["normalized"],
                "confidence": due_date_data["confidence"]
            },
            "order_number": {
                "raw": order_num_data["raw"],
                "normalized": order_num_data["raw"],
                "confidence": order_num_data["confidence"]
            },
            "payment_type": {
                "raw": payment_type_data["raw"],
                "normalized": payment_type_data["raw"],
                "confidence": payment_type_data["confidence"]
            },
            "supplier": {
                "name": {
                    "raw": supplier_name["raw"],
                    "normalized": supplier_name["raw"],
                    "confidence": supplier_name["confidence"]
                },
                "gstin": {
                    "raw": supplier_gstin["raw"],
                    "normalized": supplier_gstin["raw"],
                    "confidence": supplier_gstin["confidence"]
                },
                "address": {"raw": "", "normalized": None, "confidence": 1.0},
                "phone": {"raw": "", "normalized": None, "confidence": 1.0},
                "state": {
                    "raw": supplier_state["raw"],
                    "normalized": supplier_state["normalized"],
                    "confidence": supplier_state["confidence"]
                }
            },
            "buyer": {
                "name": {
                    "raw": buyer_name["raw"],
                    "normalized": buyer_name["raw"],
                    "confidence": buyer_name["confidence"]
                },
                "gstin": {
                    "raw": buyer_gstin["raw"],
                    "normalized": buyer_gstin["raw"],
                    "confidence": buyer_gstin["confidence"]
                },
                "address": {"raw": "", "normalized": None, "confidence": 1.0},
                "state": {
                    "raw": buyer_state["raw"],
                    "normalized": buyer_state["normalized"],
                    "confidence": buyer_state["confidence"]
                }
            },
            "items": [],
            "totals": {
                "subtotal": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                "discount_total": None,
                "tax_total": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                "grand_total": {"raw": "", "normalized": 0.0, "confidence": 1.0},
                "round_off": None
            },
            "tax_summary": {"items": []}
        }

    @classmethod
    def _extract_field_regex(cls, text: str, patterns: List[str]) -> Dict[str, Any]:
        """
        Helper method to match first valid occurrences of patterns line-by-line.
        """
        for pattern in patterns:
            for line in text.splitlines():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    raw_val = match.group(1).strip()
                    if raw_val:
                        return {"raw": raw_val, "confidence": 1.0}
        return {"raw": "", "confidence": 0.0}

    @classmethod
    def _extract_and_classify_gstins(cls, text: str, lines: List[str]) -> tuple:
        """
        Locates all GSTIN numbers and uses positional/label heuristics to map Supplier vs Buyer.
        """
        gstins = re.findall(cls.GSTIN_PATTERN, text, re.IGNORECASE)
        # Unique values in uppercase
        gstins = list(set([g.upper() for g in gstins]))

        supplier_gstin = {"raw": "", "confidence": 0.0}
        buyer_gstin = {"raw": "", "confidence": 0.0}

        if not gstins:
            return supplier_gstin, buyer_gstin

        # Single GSTIN: Most likely Supplier, unless the surrounding line indicates Buyer details
        if len(gstins) == 1:
            gstin = gstins[0]
            found_buyer_keyword = False
            for line in lines:
                if gstin in line.upper() and any(kw in line.upper() for kw in ["BUYER", "TO", "CUSTOMER", "RECEIVER", "SHIP TO"]):
                    found_buyer_keyword = True
                    break
            if found_buyer_keyword:
                buyer_gstin = {"raw": gstin, "confidence": 0.9}
            else:
                supplier_gstin = {"raw": gstin, "confidence": 0.9}
            return supplier_gstin, buyer_gstin

        # Multiple GSTINs: Map by line position index
        gstin_positions = {}
        for gstin in gstins:
            for idx, line in enumerate(lines):
                if gstin in line.upper():
                    gstin_positions[gstin] = idx
                    break

        sorted_gstins = sorted(gstin_positions.keys(), key=lambda k: gstin_positions[k])

        # Supplier is usually first, Buyer is second
        supplier_gstin = {"raw": sorted_gstins[0], "confidence": 1.0}
        buyer_gstin = {"raw": sorted_gstins[1], "confidence": 1.0}

        return supplier_gstin, buyer_gstin

    @classmethod
    def _extract_and_resolve_states(cls, lines: List[str], supplier_gstin: dict, buyer_gstin: dict) -> tuple:
        """
        Resolves states for Supplier and Buyer using GSTIN code mapping as primary,
        and falling back to regex patterns found in text lines.
        """
        supplier_state = {"raw": "", "normalized": None, "confidence": 0.0}
        buyer_state = {"raw": "", "normalized": None, "confidence": 0.0}

        # 1. Resolve from GSTIN if available
        if supplier_gstin["raw"]:
            state_code = supplier_gstin["raw"][:2]
            if state_code in STATE_CODES:
                state_name = STATE_CODES[state_code]
                supplier_state = {"raw": state_name, "normalized": state_name, "confidence": 1.0}

        if buyer_gstin["raw"]:
            state_code = buyer_gstin["raw"][:2]
            if state_code in STATE_CODES:
                state_name = STATE_CODES[state_code]
                buyer_state = {"raw": state_name, "normalized": state_name, "confidence": 1.0}

        # 2. Fall back to regex state searches in text if needed
        if not supplier_state["raw"] or not buyer_state["raw"]:
            state_matches = []
            for idx, line in enumerate(lines):
                for pattern in cls.STATE_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        raw_state = match.group(1).strip()
                        state_matches.append((idx, raw_state))

            for pos, state_val in state_matches:
                resolved = cls.resolve_state(state_val)
                # Heuristic: Earlier state matches belong to Supplier, later to Buyer
                if pos < len(lines) // 2 and not supplier_state["raw"]:
                    supplier_state = {"raw": state_val, "normalized": resolved, "confidence": 0.8}
                elif not buyer_state["raw"]:
                    buyer_state = {"raw": state_val, "normalized": resolved, "confidence": 0.8}

        return supplier_state, buyer_state

    @classmethod
    def _extract_names(cls, lines: List[str]) -> tuple:
        """
        Extracts Supplier Name and Buyer Name using line position heuristics and sanitization.
        """
        supplier_raw = ""
        supplier_confidence = 0.0
        buyer_raw = ""
        buyer_confidence = 0.0

        if not lines:
            return {"raw": "", "confidence": 0.0}, {"raw": "", "confidence": 0.0}

        # 1. Supplier Heuristics (usually top line, company indicators)
        first_line = lines[0].upper()
        cleaned_first_line = cls.clean_name(first_line)
        
        if len(cleaned_first_line) > 3:
            supplier_raw = cleaned_first_line
            supplier_confidence = 0.75

        # Check top 4 lines for corporate terms
        for idx in range(min(4, len(lines))):
            line = lines[idx].upper()
            if any(term in line for term in ["DISTRIBUTORS", "PVT.LTD", "LIMITED", "LTD", "AGENCIES", "PHARMA"]):
                match = re.search(r"\b([A-Z\s\.\&]+(?:DISTRIBUTORS|LTD|PHARMA|AGENCIES|LIMITED))\b", line)
                if match:
                    supplier_raw = cls.clean_name(match.group(1))
                    supplier_confidence = 0.9
                    break

        # 2. Buyer Heuristics (matches tags, pharmacy/hospital keywords, or numeric customer code format)
        for idx, line in enumerate(lines):
            line_up = line.upper()
            
            # Check for customer code pattern e.g., "12345 - BUYER NAME" (targeting 4-to-8 digit customer codes)
            pattern_match = re.search(r"\b\d{4,8}\b\s*-\s*([A-Z0-9&.,()\- ]+)", line_up)
            if pattern_match:
                buyer_candidate = pattern_match.group(1).strip()
                # Split at comma/separator to get the name portion
                clean_buyer = buyer_candidate.split(",")[0].strip()
                clean_buyer = cls.clean_name(clean_buyer)
                # Ensure it doesn't overlap with Supplier name
                if supplier_raw and supplier_raw[:6] in clean_buyer:
                    continue
                if clean_buyer:
                    buyer_raw = clean_buyer
                    buyer_confidence = 0.9
                    break

            if any(term in line_up for term in ["PHARMACY", "MEDICAL STORE", "CLINIC", "HOSPITAL", "DRUGS & CO"]):
                # Ensure it doesn't overlap with Supplier name
                if supplier_raw and supplier_raw[:6] in line_up:
                    continue
                # Split at comma/separator to get the name portion
                clean_buyer = line_up.split(",")[0].strip()
                clean_buyer = cls.clean_name(clean_buyer)
                if clean_buyer:
                    buyer_raw = clean_buyer
                    buyer_confidence = 0.85
                    break

        return {"raw": supplier_raw, "confidence": supplier_confidence}, {"raw": buyer_raw, "confidence": buyer_confidence}

    @classmethod
    def _extract_payment_type(cls, text: str) -> Dict[str, Any]:
        """
        Scans for payment terms (CREDIT, CASH, COD).
        """
        text_lower = text.lower()
        for pay_mode, keywords in cls.PAYMENT_KEYWORDS.items():
            for word in keywords:
                pattern = r"\b" + re.escape(word) + r"\b"
                if re.search(pattern, text_lower):
                    return {"raw": pay_mode, "confidence": 0.9}

        return {"raw": "UNKNOWN", "confidence": 0.0}
