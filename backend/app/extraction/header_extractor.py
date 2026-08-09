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
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}\s+[a-zA-Z]{3,9}[;,]?\s+\d{2,4}(?:\s+\d{1,2}[:.]\d{2}\s*[APMapm]{2})?)",
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        r"(?:inv(?:oice)?\.?\s*date|bill\s*date|date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})",
        r"\bdate\s*[:\-]?\s*(\d{1,2}\s+[a-zA-Z]{3,9}[;,]?\s+\d{2,4})",
        r"\bdate\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b",
        r"\bdate\s*[:\-]?\s*(\d{1,2}[/\-][a-zA-Z]{3,9}[/\-]\d{2,4})\b",
        r"inv\s*dt\.?\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"inv\s*dt\.?\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}\s*[APMapm]{2})",
        r"\bdated\s*[:\-]?\s*(\d{1,2}\s+[a-zA-Z]{3,9}\s+\d{2,4})",
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

    # Noise phrases and document labels to strip from names
    NAME_NOISE_PATTERNS = [
        r"\*[A-Za-z0-9\-_]+\*",                                                     # Barcodes / invoice numbers in asterisks e.g. *1758*, *MCRB-25-26-8898*
        r"(?:TAX\s+)?INVOICE\s+COPY(?:\s*\(\d+\))?",                              # INVOICE COPY (1)
        r"(?:ORIGINAL|DUPLICATE|TRIPLICATE)\s+COPY(?:\s*\(\d+\))?",                # ORIGINAL COPY
        r"\b(?:ORIGINAL|DUPLICATE|TRIPLICATE|ORIGINALFOR)\s*(?:FOR)?\s*(?:RECIPIENT|BUYER|TRANSPORTER|SUPPLIER)\b", # Recipient / Buyer copy banners e.g. ORIGINALFOR RECIPIENT
        r"\bSUBJECT\s+TO\s+.*?(?:JURISDICTION|JURIDUCTION)\b",                      # Legal jurisdiction headers
        r"\bCOPY\s*\(\d+\)",                                                       # Copy (1)
        r"PAGE\s*\d+(?:\s*OF\s*\d+)?",                                             # PAGE 1 OF 1
        r"\b(?:GST\s+)?(?:TAX\s+INVOICE|RETAIL\s+INVOICE|SALES\s+INVOICE|TAX\s+INV|BILL\s+OF\s+SUPPLY)\b", # Document titles
        r"\b(?:DRUG\s+LIC(?:ENCE)?\s*(?:NO)?\.?|D\.L\.?\s*(?:NO)?\.?|DL\s*NO)\b[:\-]?\s*[A-Za-z0-9/,_\- ]*", # Drug license lines
        r"\bFSSAI(?:\s*(?:LIC|NO)\.?)?\b[:\-]?\s*[A-Za-z0-9/,_\- ]*",              # FSSAI numbers
        r"\bCIN(?:\s*NO\.?)?\b[:\-]?\s*[A-Za-z0-9/,_\- ]*",                        # CIN numbers
        r"\bPAN(?:\s*NO\.?)?\b[:\-]?\s*[A-Za-z0-9/,_\- ]*",                        # PAN numbers
        r"\b(?:GSTIN|GST)\b[:\-]?\s*[A-Za-z0-9/,_\- ]*",                           # GST numbers
        r"\b(?:PH|PHONE|TEL|MOBILE|FAX|MOB)\b[:\-]?\s*[0-9\-\+/, ]*",               # Phone numbers
        r"\bCODE\s*[:\-]?\s*\d+\b",                                                # Code 902859
        r"\bE\-?MAIL\s*[:\-]?\s*[\w\.\@\-]+",                                       # Email addresses
        r"\bSTATE\s*CODE\b",                                                        # State Code headers
    ]

    # Supplier corporate entity indicators
    COMPANY_KEYWORDS = [
        "ENTERPRISES", "PHARMA", "PHARMACY", "DISTRIBUTORS", "DISTRIBUTOR", "AGENCIES", "AGENCY",
        "DRUG HOUSE", "DRUG STORES", "ASSOCIATES", "HEALTHCARE", "LABORATORIES", "LABS",
        "PHARMACEUTICALS", "PHARMACEUTICAL", "MEDICALS", "MEDICAL", "SURGICALS",
        "SURGICAL", "TRADERS", "TRADING", "TRADELINK", "PVT.LTD", "PVT LTD", "LIMITED",
        "LTD", "CO-OP", "CORPORATION", "MEDICINES", "DRUGS", "CHEMISTS", "ENTERPRISE",
        "SURGICALS & PHARMACEUTICALS", "WHOLESALE DRUGGISTS"
    ]

    # Buyer label patterns
    BUYER_LABEL_PATTERNS = [
        r"(?:billed\s*to|bill\s*to|buyer\s*name|buyer|customer\s*name|customer|consignee|receiver(?:\s*details)?|party\s*name)\s*[:\-]?\s*(.*)",
    ]

    # Address label patterns
    ADDRESS_LABEL_PATTERNS = [
        r"(?:regd\.?\s*|registered\s*|head\s*|corp(?:orate)?\s*|office\s*|branch\s*)?address\s*[:\-]\s*(.*)",
        r"(?:regd\.?\s*|registered\s*)?office\s*[:\-]\s*(.*)",
        r"\bpremises\s*[:\-]\s*(.*)",
    ]

    # Address keyword indicators
    ADDRESS_KEYWORDS = [
        "DOOR", "BUILDING", "BLDG", "FLOOR", "ROAD", "STREET", "NAGAR", "COMPLEX",
        "ESTATE", "PLOT", "SECTOR", "CROSS", "MAIN", "NEAR", "OPP", "OPPOSITE",
        "BEHIND", "POST", "DIST", "DISTT", "PIN", "PINCODE", "AVENUE", "LANE",
        "MARG", "CHOWK", "CITY", "VILLAGE", "TALUK", "TOWN", "INDUSTRIAL", "PHASE",
        "GIDC", "MIDC", "FORT", "KERALA", "MAHARASHTRA", "MUMBAI", "KANNUR", "PAYYANUR",
        "PILATHARA", "GROUND", "1ST", "2ND", "3RD", "SHOP", "ROOM", "NO."
    ]

    # Phone label patterns
    PHONE_LABEL_PATTERNS = [
        r"(?:(?:^|[\s,;|])(?:PH|PHONE|TEL|TELEPHONE|MOBILE|MOB|CONTACT|CELL)\.?\s*[:\-]?\s*)([0-9\+\(\)\s\-\,/]{6,})",
    ]

    @classmethod
    def clean_name(cls, name_str: str) -> str:
        """
        Cleans name strings by removing embedded GSTINs, postal codes, noise labels,
        document headers, barcode numbers, and trailing/leading punctuation.
        """
        if not name_str:
            return ""

        cleaned = name_str

        # Remove GSTINs
        cleaned = re.sub(cls.GSTIN_PATTERN, "", cleaned, flags=re.IGNORECASE)
        # Remove postal codes (6 digits)
        cleaned = re.sub(r"\b\d{6}\b", "", cleaned)

        # Remove noise patterns
        for pat in cls.NAME_NOISE_PATTERNS:
            cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)

        # Remove remaining noise words
        cleaned = re.sub(r"\b(?:GSTIN|GST|PAN|DL|D\.L\.?No|CODE|MOBILE|PH|PHONE|TAX|INV|NO|BILL|PAGE|COPY)\b[:\-]?\s*", " ", cleaned, flags=re.IGNORECASE)

        # Remove isolated standalone single/double digits (e.g. "TRADELINK 2 TRADELINK" -> "TRADELINK TRADELINK")
        cleaned = re.sub(r"\b\d{1,2}\b", " ", cleaned)

        # Clean leading/trailing punctuation and spaces
        cleaned = re.sub(r"^[\s\-\:\,\.\/\(\)\*\#]+|[\s\-\:\,\.\/\(\)\*\#]+$", "", cleaned)
        # Clean multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Word deduplication (e.g. "TRADELINK TRADELINK" -> "TRADELINK")
        parts = [p.strip() for p in cleaned.split() if p.strip()]
        if len(parts) >= 2:
            half = len(parts) // 2
            if parts[:half] == parts[half:]:
                cleaned = " ".join(parts[:half])
            elif len(parts) == 2 and parts[0] == parts[1]:
                cleaned = parts[0]

        return cleaned

    @classmethod
    def clean_buyer_name(cls, candidate: str, supplier_raw: str = "") -> str:
        """
        Cleans candidate buyer name strings.
        """
        if not candidate:
            return ""
        cleaned = cls.clean_name(candidate)
        if supplier_raw and supplier_raw.upper() in cleaned.upper():
            return ""
        return cleaned

    @classmethod
    def normalize_date(cls, date_str: str) -> Optional[str]:
        """
        Normalizes various date formats (DD/MM/YYYY, DD-MM-YY, DD-MMM-YY, DD MMM YYYY, etc.) into ISO YYYY-MM-DD.
        Handles OCR noise (semicolons, commas, timestamps).
        """
        if not date_str:
            return None

        # Strip timestamps e.g. "03.23 PM", "03:22 PM", "10:21:00 AM"
        cleaned = re.sub(r"\s+\d{1,2}[:.]\d{2}(?::\d{2})?\s*[APMapm]{2}", "", date_str).strip()
        # Clean noisy punctuation e.g. "13 Apr; 2026" -> "13 Apr 2026"
        cleaned = re.sub(r"[;,]", " ", cleaned).strip()

        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "api": 4, "apl": 4, "apt": 4, "aprl": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }

        # 1. Try space-separated alphanumeric: DD MMM YYYY (e.g. 13 Apr 2026, 20 Mar 2020)
        match = re.match(r"^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{2,4})$", cleaned)
        if match:
            day_str, month_name, year_str = match.groups()
            day = int(day_str)
            month = months_map.get(month_name.lower())
            year = int(year_str)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            if month and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # Clean non-alphanumeric except / and -
        cleaned_punct = re.sub(r"[^\w/\-]", "", cleaned).strip()

        # 2. Try DD/MM/YYYY or DD-MM-YYYY
        match = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", cleaned_punct)
        if match:
            day_str, month_str, year_str = match.groups()
            day = int(day_str)
            month = int(month_str)
            year = int(year_str)
            if year < 100:
                year = 2000 + year if year < 50 else 1900 + year
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # 3. Try YYYY-MM-DD or YYYY/MM/DD
        match = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", cleaned_punct)
        if match:
            year_str, month_str, day_str = match.groups()
            year = int(year_str)
            month = int(month_str)
            day = int(day_str)
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-{day:02d}"

        # 4. Try hyphen/slash alphanumeric: DD-MMM-YYYY or DD-MMM-YY (e.g. 07-May-26)
        match = re.match(r"^(\d{1,2})[/\-]([a-zA-Z]+)[/\-](\d{2,4})$", cleaned_punct)
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

        # 4b. Extract Supplier Address
        supplier_address = cls._extract_supplier_address(lines, supplier_name["raw"])

        # 4c. Extract Supplier Phone
        supplier_phone = cls._extract_supplier_phone(lines)

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
                "address": {
                    "raw": supplier_address["raw"],
                    "normalized": supplier_address["normalized"],
                    "confidence": supplier_address["confidence"]
                },
                "phone": {
                    "raw": supplier_phone["raw"],
                    "normalized": supplier_phone["normalized"],
                    "confidence": supplier_phone["confidence"]
                },
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

        # Single GSTIN: Most likely Supplier, unless the surrounding/preceding lines indicate Buyer details
        if len(gstins) == 1:
            gstin = gstins[0]
            found_buyer_keyword = False
            gstin_idx = -1
            for idx, line in enumerate(lines):
                if gstin in line.upper():
                    gstin_idx = idx
                    break
            if gstin_idx != -1:
                preceding = lines[max(0, gstin_idx - 4): gstin_idx + 1]
                if any(any(kw in l.upper() for kw in ["BILLED TO", "BILL TO", "BUYER", "CUSTOMER", "RECEIVER", "SHIP TO", "CONSIGNEE"]) for l in preceding):
                    found_buyer_keyword = True

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

    # Buyer label patterns
    BUYER_LABEL_PATTERNS = [
        r"\b(?:BUYER(?:\s*NAME)?|BILLED\s*TO|BILL\s*TO|CUSTOMER(?:\s*NAME)?|PARTY(?:\s*NAME)?|CONSIGNEE|RECEIVER(?:\s*DETAILS)?|MESSRS\.?|M/S\.?)\s*[:\-]?(?:\s+([A-Za-z0-9&.,()\- ]+))?",
    ]

    @classmethod
    def clean_buyer_name(cls, name_str: str, supplier_name: str = "") -> str:
        """
        Cleans buyer candidate names by stripping merged invoice numbers, parent company tags,
        trailing route/customer numbers, and trailing addresses.
        """
        if not name_str:
            return ""
        cleaned = name_str

        # If line has parent company banner or invoice number e.g. "(A UNIT OF ...) Tax Inv. No. : TL-26-4220 GERMAN PHARMACY"
        m = re.search(r"(?:(?:Tax\s+)?Inv(?:oice)?\.?\s*(?:No|Num|Number|#)?\.?\s*[:\-]?\s*[A-Za-z0-9\-_/]+\s+|Code\s*\d+\s+)(.*)", cleaned, re.IGNORECASE)
        if m:
            cleaned = m.group(1)

        # Strip "(A UNIT OF ...)" parent phrases
        cleaned = re.sub(r"^\s*\(?\s*A\s+UNIT\s+OF\s+.*?\)?\s*", " ", cleaned, flags=re.IGNORECASE)
        if supplier_name and supplier_name.upper() in cleaned.upper():
            cleaned = re.sub(re.escape(supplier_name), " ", cleaned, flags=re.IGNORECASE)

        # Clean standard noise
        cleaned = cls.clean_name(cleaned)

        # Split at comma if following part is location/code e.g. "GERMAN PHARMACY,KANNUR 779504" -> "GERMAN PHARMACY"
        if "," in cleaned:
            parts = [p.strip() for p in cleaned.split(",") if p.strip()]
            if len(parts[0]) >= 3:
                cleaned = parts[0]

        # Strip trailing isolated numbers/routes/pincodes e.g. "M M C PHARMACY 144" -> "M M C PHARMACY"
        cleaned = re.sub(r"\s+\d+$", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

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

        # 1. Supplier Extraction:
        # Scan header boundary (before buyer/item sections)
        header_limit = min(12, len(lines))
        for idx in range(min(12, len(lines))):
            line_upper = lines[idx].upper()
            if re.search(r"\b(?:ORIGINAL|DUPLICATE|TRIPLICATE)\s+FOR\b", line_upper):
                continue
            if any(marker in line_upper for marker in ["BUYER:", "BUYER /", "BUYER NAME", "BILLED TO", "BILL TO", "SHIP TO", "CONSIGNEE", "CUSTOMER", "ITEM NAME", "PRODUCT DESCRIPTION"]):
                header_limit = max(idx, 2)
                break
            if re.search(r"\b\d{4,8}\s*-\s*[A-Z]", line_upper):
                header_limit = max(idx, 2)
                break

        header_lines = lines[:header_limit]

        # First pass: Look for lines containing corporate/pharma/business terms
        for line in header_lines:
            line_up = line.upper()

            # Skip lines explicitly designated as buyer/customer (ignoring copy banners)
            if not re.search(r"\b(?:ORIGINAL|DUPLICATE|TRIPLICATE)\s+FOR\b", line_up):
                if any(kw in line_up for kw in ["BUYER:", "BUYER /", "BILLED TO", "BILL TO", "SHIP TO", "CUSTOMER", "CONSIGNEE"]):
                    continue

            # Check if line contains company keyword
            if any(term in line_up for term in cls.COMPANY_KEYWORDS):
                cleaned = cls.clean_name(line)
                # Ensure it has sufficient alphabetic length
                if len(re.sub(r"[^A-Za-z]", "", cleaned)) >= 3:
                    supplier_raw = cleaned
                    supplier_confidence = 0.95
                    break

        # Second pass: If no explicit corporate term matched, find the first clean candidate line
        if not supplier_raw:
            for line in header_lines:
                line_up = line.upper()
                # Skip noise labels
                if any(kw in line_up for kw in ["BUYER", "BILLED TO", "SHIP TO", "CUSTOMER", "INVOICE", "DATE", "GSTIN", "PHONE"]):
                    continue
                cleaned = cls.clean_name(line)
                letters_only = re.sub(r"[^A-Za-z]", "", cleaned)
                # Ignore lines that are purely numbers or too short
                if len(letters_only) >= 4:
                    supplier_raw = cleaned
                    supplier_confidence = 0.8
                    break

        supplier_norm = supplier_raw.upper().strip()

        # 2. Buyer Extraction:
        # Step 2a: Check explicit Buyer labels (e.g. "BUYER: ...", "BILLED TO: ...", "Customer: ...")
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            for pat in cls.BUYER_LABEL_PATTERNS:
                match = re.search(pat, line_clean, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip() if match.group(1) else ""
                    if not candidate and idx + 1 < len(lines):
                        candidate = lines[idx + 1].strip()
                    clean_buyer = cls.clean_buyer_name(candidate, supplier_raw)
                    if clean_buyer and len(re.sub(r"[^A-Za-z]", "", clean_buyer)) >= 3:
                        if not supplier_norm or supplier_norm[:6] not in clean_buyer.upper():
                            buyer_raw = clean_buyer
                            buyer_confidence = 0.95
                            break
            if buyer_raw:
                break

        # Step 2b: Check for customer code pattern e.g., "12345 - BUYER NAME" (targeting 4-to-8 digit customer codes)
        if not buyer_raw:
            for line in lines:
                line_up = line.upper()
                pattern_match = re.search(r"\b\d{4,8}\b\s*-\s*([A-Z0-9&.,()\- ]+)", line_up)
                if pattern_match:
                    buyer_candidate = pattern_match.group(1).strip()
                    clean_buyer = cls.clean_buyer_name(buyer_candidate, supplier_raw)
                    if clean_buyer and len(re.sub(r"[^A-Za-z]", "", clean_buyer)) >= 3:
                        if not supplier_norm or supplier_norm[:6] not in clean_buyer.upper():
                            buyer_raw = clean_buyer
                            buyer_confidence = 0.9
                            break

        # Step 2c: Check for "Code 902859 ... BUYER NAME" pattern
        if not buyer_raw:
            for line in lines:
                line_up = line.upper()
                code_match = re.search(r"Code\s*\d+\s+([A-Z0-9&.,()\- ]+)", line_up, re.IGNORECASE)
                if code_match:
                    candidate = code_match.group(1).strip()
                    clean_buyer = cls.clean_buyer_name(candidate, supplier_raw)
                    if clean_buyer and len(re.sub(r"[^A-Za-z]", "", clean_buyer)) >= 3:
                        if not supplier_norm or supplier_norm[:6] not in clean_buyer.upper():
                            buyer_raw = clean_buyer
                            buyer_confidence = 0.85
                            break

        # Step 2d: Check pharmacy/hospital/medical entity keywords
        if not buyer_raw:
            for line in lines:
                line_up = line.upper()
                if any(term in line_up for term in ["PHARMACY", "MEDICAL STORE", "MEDICALS", "CLINIC", "HOSPITAL", "DRUGS & CO"]):
                    clean_buyer = cls.clean_buyer_name(line_up, supplier_raw)
                    if clean_buyer and len(re.sub(r"[^A-Za-z]", "", clean_buyer)) >= 3:
                        if not supplier_norm or supplier_norm[:6] not in clean_buyer.upper():
                            buyer_raw = clean_buyer
                            buyer_confidence = 0.85
                            break

        return {"raw": supplier_raw, "confidence": supplier_confidence}, {"raw": buyer_raw, "confidence": buyer_confidence}

    @classmethod
    def clean_address_line(cls, line: str) -> str:
        """
        Strips statutory labels, GSTINs, phone numbers, emails, and document titles
        from an address line.
        """
        if not line:
            return ""

        cleaned = line

        # If line contains split tokens like "Tax Inv. No." or "Inv. Date" or "Inv No:", take text before it
        for boundary in [r"\bTax\s+Inv(?:oice)?\.?\s*No\.?", r"\bInv\.?\s*(?:No\.?|Date)", r"\bDue\s+Date\b", r"\bOrder\s+No\.?", r"\bPay\s+Type\b"]:
            m = re.search(boundary, cleaned, re.IGNORECASE)
            if m and m.start() > 5:
                cleaned = cleaned[:m.start()]

        # Remove GSTINs
        cleaned = re.sub(cls.GSTIN_PATTERN, "", cleaned, flags=re.IGNORECASE)
        # Remove invoice number, order number, and dates
        cleaned = re.sub(r"\b(?:Tax\s+)?Inv(?:\.|\s*oice)?(?:\s*No\.?)?\s*[:\-]?\s*[A-Za-z0-9\-_/]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bOrder\s*No\.?\s*[:\-]?\s*[A-Za-z0-9\-_/]*", " ", cleaned, flags=re.IGNORECASE)
        # Remove statutory/contact fields and values
        cleaned = re.sub(r"\b(?:GSTIN|GST|PAN|FSSAI|CIN|DL|D\.L\.?|DRUG\s+LIC(?:ENCE)?|MSME)\s*(?:NO\.?)?\s*[:\-]?\s*[^,\n\|]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:PH|PHONE|TEL|MOBILE|FAX|MOB)\s*[:\-]?\s*[0-9\-\+/, ]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bE\-?MAIL\s*[:\-]?\s*[\w\.\@\-]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:TAX\s+INVOICE|RETAIL\s+INVOICE|SALES\s+INVOICE|INVOICE\s+COPY|ORIGINAL\s+COPY|DUPLICATE\s+COPY)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\*[A-Za-z0-9\-_]+\*", " ", cleaned)
        cleaned = re.sub(r"PAGE\s*\d+(?:\s*OF\s*\d+)?", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:WLF\w+|RLF\w+)\b", " ", cleaned, flags=re.IGNORECASE)

        # Strip remaining isolated statutory tags
        cleaned = re.sub(r"\b(?:GSTIN|GST|PAN|FSSAI|DL\s*NO|CIN|MSME(?:\s*NO\.?)?)\b[:\-]?\s*", " ", cleaned, flags=re.IGNORECASE)

        # Clean punctuation and spacing
        cleaned = re.sub(r"^[\s\-\:\,\.\/\(\)\*\#\|\;]+|[\s\-\:\,\.\/\(\)\*\#\|\;]+$", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def _extract_supplier_address(cls, lines: List[str], supplier_name: str) -> Dict[str, Any]:
        """
        Extracts Supplier Address from header lines using explicit labels (Address:, Office:)
        or positional heuristics directly below the supplier name.
        """
        if not lines:
            return {"raw": "", "normalized": None, "confidence": 1.0}

        # Determine header boundary (before buyer/item sections)
        header_limit = min(12, len(lines))
        for idx in range(min(12, len(lines))):
            line_upper = lines[idx].upper()
            if re.search(r"\b(?:ORIGINAL|DUPLICATE|TRIPLICATE)\s+FOR\b", line_upper):
                continue
            if any(marker in line_upper for marker in ["BUYER:", "BUYER /", "BUYER NAME", "BILLED TO", "BILL TO", "SHIP TO", "CONSIGNEE", "CUSTOMER", "ITEM NAME", "PRODUCT DESCRIPTION"]):
                header_limit = max(idx, 2)
                break
            if re.search(r"\b\d{4,8}\s*-\s*[A-Z]", line_upper):
                header_limit = max(idx, 2)
                break

        header_lines = lines[:header_limit]

        # 1. Look for explicit Address label
        for idx, line in enumerate(header_lines):
            line_clean = line.strip()
            for pat in cls.ADDRESS_LABEL_PATTERNS:
                match = re.search(pat, line_clean, re.IGNORECASE)
                if match:
                    addr_candidate = match.group(1).strip()
                    cleaned_addr = cls.clean_address_line(addr_candidate)

                    # Check if address continues on next line(s)
                    parts = [cleaned_addr] if cleaned_addr else []
                    for next_idx in range(idx + 1, min(idx + 3, len(header_lines))):
                        next_line = header_lines[next_idx]
                        if any(marker in next_line.upper() for marker in ["BUYER", "BILLED TO", "SHIP TO", "PHONE", "GSTIN"]):
                            break
                        cleaned_next = cls.clean_address_line(next_line)
                        if cleaned_next and (any(kw in cleaned_next.upper() for kw in cls.ADDRESS_KEYWORDS) or re.search(r"\b[1-9]\d{5}\b", cleaned_next)):
                            parts.append(cleaned_next)

                    full_addr = ", ".join(p for p in parts if p)
                    full_addr = re.sub(r",\s*,+", ", ", full_addr).strip(", ")
                    if len(full_addr) >= 4:
                        return {"raw": full_addr, "normalized": full_addr, "confidence": 0.95}

        # 2. Positional / Keyword-based Address Extraction below Supplier Name
        supplier_idx = -1
        supplier_norm = supplier_name.upper().strip()
        if supplier_norm:
            for idx, line in enumerate(header_lines):
                if supplier_norm in line.upper():
                    supplier_idx = idx
                    break

        start_idx = supplier_idx + 1 if supplier_idx != -1 else 0
        address_parts = []

        for idx in range(start_idx, len(header_lines)):
            line = header_lines[idx]
            line_up = line.upper()

            # Stop if reaching customer code or buyer/invoice markers
            if re.search(r"\b\d{4,8}\s*-\s*[A-Z]", line_up):
                break
            if any(marker in line_up for marker in ["BUYER", "BILLED TO", "SHIP TO", "CONSIGNEE", "INV NO:", "INVOICE NO:"]):
                break
            if re.search(r"^(?:PH|PHONE|TEL|MOBILE)\s*[:\-]\s*[0-9\+]", line_up.strip()):
                break

            # Skip if this line is just the supplier name or company keyword header
            if supplier_norm and supplier_norm in line_up:
                continue

            cleaned_line = cls.clean_address_line(line)
            if not cleaned_line:
                continue

            # Check if line contains address indicators, pincode, or district/city names
            has_addr_kw = any(kw in cleaned_line.upper() for kw in cls.ADDRESS_KEYWORDS)
            has_pincode = bool(re.search(r"\b[1-9]\d{5}\b", cleaned_line) or re.search(r"PIN\s*[\-:]?\s*\d{6}", cleaned_line, re.IGNORECASE))
            has_comma_structure = "," in cleaned_line and len(cleaned_line.split()) >= 2

            if has_addr_kw or has_pincode or has_comma_structure:
                # Ensure line is not a buyer pharmacy name
                if not any(pharm in cleaned_line.upper() for pharm in ["GERMAN PHARMACY", "APOLLO PHARMACY", "MEDICAL STORE"]):
                    address_parts.append(cleaned_line)

        if address_parts:
            # Deduplicate similar phrases
            unique_parts = []
            for p in address_parts:
                if p not in unique_parts:
                    unique_parts.append(p)
            full_address = ", ".join(unique_parts)
            full_address = re.sub(r",\s*,+", ", ", full_address).strip(", ")
            if len(full_address) >= 4:
                return {"raw": full_address, "normalized": full_address, "confidence": 0.85}

        return {"raw": "", "normalized": None, "confidence": 1.0}

    @classmethod
    def _extract_supplier_phone(cls, lines: List[str]) -> Dict[str, Any]:
        """
        Extracts supplier phone number(s) from invoice header lines strictly before buyer sections.
        """
        if not lines:
            return {"raw": "", "normalized": None, "confidence": 1.0}

        # Determine header boundary (before buyer/item sections)
        header_limit = min(12, len(lines))
        for idx in range(min(12, len(lines))):
            line_upper = lines[idx].upper()
            if any(marker in line_upper for marker in ["BUYER", "BILLED TO", "SHIP TO", "CONSIGNEE", "CUSTOMER", "ITEM NAME", "PRODUCT DESCRIPTION"]):
                header_limit = max(idx, 2)
                break
            if re.search(r"\b\d{4,8}\s*-\s*[A-Z]", line_upper):
                header_limit = max(idx, 2)
                break

        header_lines = lines[:header_limit]

        # Scan for phone labels in the supplier header region
        for idx, line in enumerate(header_lines):
            # 1. Single-line match e.g. "Phone: 9876543210" or "PH : 04985202475"
            for pat in cls.PHONE_LABEL_PATTERNS:
                match = re.search(pat, line, re.IGNORECASE)
                if match:
                    phone_match = match.group(1).strip()
                    cleaned_match = re.split(r"\b(?:Kerala|Email|E\-Mail|Mail|State|District|FSSAI|DL|MSME|Route|Order|GSTIN|Code)\b", phone_match, flags=re.IGNORECASE)[0].strip()
                    cleaned_match = re.sub(r"^[\s\-\:\,\.\/\|]+|[\s\-\:\,\.\/\|]+$", "", cleaned_match)

                    digits = re.sub(r"\D", "", cleaned_match)
                    if len(digits) >= 6:
                        return {
                            "raw": cleaned_match,
                            "normalized": cleaned_match,
                            "confidence": 0.95
                        }

            # 2. Multiline match e.g. line is "Phone" and next line is "9508399874"
            if re.match(r"^\s*(?:PH|PHONE|TEL|TELEPHONE|MOBILE|MOB|CONTACT|CELL)\b[:\-\.]?\s*$", line.strip(), re.IGNORECASE):
                if idx + 1 < len(header_lines):
                    next_line = header_lines[idx + 1].strip()
                    cleaned_next = re.split(r"\b(?:Kerala|Email|E\-Mail|Mail|State|District|FSSAI|DL|MSME|Route|Order|GSTIN|Code)\b", next_line, flags=re.IGNORECASE)[0].strip()
                    cleaned_next = re.sub(r"^[\s\-\:\,\.\/\|]+|[\s\-\:\,\.\/\|]+$", "", cleaned_next)
                    digits = re.sub(r"\D", "", cleaned_next)
                    if len(digits) >= 6:
                        return {
                            "raw": cleaned_next,
                            "normalized": cleaned_next,
                            "confidence": 0.95
                        }

        return {"raw": "", "normalized": None, "confidence": 1.0}

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
