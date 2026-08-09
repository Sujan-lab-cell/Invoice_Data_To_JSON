import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.ocr.schemas import OCRResult, OCRPage, OCRLine, OCRWord

logger = logging.getLogger(__name__)


class WordBox:
    """
    Normalized 2D bounding box and geometry container for an OCR word token.
    """

    def __init__(self, text: str, bbox: List[List[int]], confidence: float = 1.0):
        self.text = str(text).strip()
        self.confidence = float(confidence)
        self.bbox = bbox
        if bbox and len(bbox) >= 4:
            self.x_min = min(point[0] for point in bbox)
            self.x_max = max(point[0] for point in bbox)
            self.y_min = min(point[1] for point in bbox)
            self.y_max = max(point[1] for point in bbox)
        else:
            self.x_min = 0
            self.x_max = 0
            self.y_min = 0
            self.y_max = 0

        self.y_center = (self.y_min + self.y_max) / 2.0
        self.x_center = (self.x_min + self.x_max) / 2.0
        self.height = max(1, self.y_max - self.y_min)
        self.width = max(1, self.x_max - self.x_min)

    def is_same_row(self, other: "WordBox", y_tolerance_ratio: float = 0.5) -> bool:
        """
        Determines whether two word boxes belong to the same horizontal row.
        """
        avg_height = (self.height + other.height) / 2.0
        overlap = min(self.y_max, other.y_max) - max(self.y_min, other.y_min)
        if overlap > 0 and (overlap / avg_height) >= 0.3:
            return True
        return abs(self.y_center - other.y_center) <= (avg_height * y_tolerance_ratio)

    def to_ocr_word(self) -> OCRWord:
        return OCRWord(
            text=self.text,
            confidence=self.confidence,
            bbox=self.bbox
        )


class ColumnHeader:
    """
    Represents a recognized table column header with its spatial X span,
    dynamic boundaries, and canonical name.
    """
    def __init__(
        self,
        name: str,
        canonical_name: str,
        x_min: int,
        x_max: int,
        words: Optional[List[WordBox]] = None
    ):
        self.name = name.strip()
        self.canonical_name = canonical_name.strip()
        self.x_min = x_min
        self.x_max = x_max
        self.x_center = (x_min + x_max) / 2.0
        self.left_bound: float = 0.0
        self.right_bound: float = 999999.0
        self.words = words or []

    def __repr__(self):
        return f"<ColumnHeader '{self.name}' ({self.canonical_name}) span=[{self.x_min}..{self.x_max}] bounds=[{self.left_bound:.1f}..{self.right_bound:.1f}]>"


class TableLayoutProfile:
    """
    Encapsulates the dynamic column layout computed from the invoice table header.
    """
    def __init__(self, header_row_idx: int, columns: List[ColumnHeader]):
        self.header_row_idx = header_row_idx
        self.columns = columns
        self.column_map: Dict[str, ColumnHeader] = {col.canonical_name: col for col in columns}

    def find_column_for_word(self, word: WordBox) -> ColumnHeader:
        """
        Determines the appropriate column for a word box using dynamic boundaries
        and distance fallback.
        """
        # 1. Primary match: inside dynamic left/right bounds
        for col in self.columns:
            if col.left_bound <= word.x_center < col.right_bound:
                return col

        # 2. Secondary match: nearest column center
        best_col = self.columns[0]
        min_dist = float("inf")
        for col in self.columns:
            dist = abs(word.x_center - col.x_center)
            if dist < min_dist:
                min_dist = dist
                best_col = col

        return best_col


# Semantic classification of canonical columns
NUMERIC_COLUMNS = {
    "quantity", "free_qty", "mrp", "rate", "rate_per_unit",
    "discount_pct", "tax_per_unit", "gst_pct", "cgst_pct",
    "sgst_pct", "igst_pct", "tax_pct", "amount", "taxable_amount"
}

IDENTIFIER_COLUMNS = {
    "hsn", "batch_no", "expiry_date"
}

TEXT_COLUMNS = {
    "product_name", "description", "manufacturer", "pack"
}


# Header alias mapping for canonical field resolution
HEADER_ALIAS_MAP = {
    # Product / Item Name / Description
    "PRODUCT": "product_name",
    "PRODUCT NAME": "product_name",
    "ITEM": "product_name",
    "ITEMS": "product_name",
    "METS": "product_name",
    "ITEM NAME": "product_name",
    "ITEM DESCRIPTION": "product_name",
    "PRODUCT DESCRIPTION": "product_name",
    "NAME OF PRODUCT": "product_name",
    "DESCRIPTION": "product_name",
    "DESCRIPTION OF GOODS": "product_name",
    "PARTICULARS": "product_name",
    "GOODS": "product_name",

    # Quantity
    "QTY": "quantity",
    "QUANTITY": "quantity",
    "QUANTLTY": "quantity",
    "INV QTY": "quantity",
    "BILLED QTY": "quantity",
    "TOT QTY": "quantity",
    "UNITS": "quantity",
    "NOS": "quantity",
    "PCS": "quantity",

    # Rate / Price / PTR
    "RATE": "rate",
    "RALE": "rate",
    "UNIT RATE": "rate",
    "PTR": "rate",
    "PRICE": "rate",
    "UNIT PRICE": "rate",
    "PURCHASE RATE": "rate",
    "SALE RATE": "rate",
    "SALERATE": "rate",
    "RATE PER UNIT": "rate",
    "RALE PER UNLT": "rate",
    "RATE PER UNLT": "rate",

    # Amount / Total
    "AMOUNT": "amount",
    "AMOUNT (RS)": "amount",
    "AMOUNT(RS)": "amount",
    "AMOUNT (INR)": "amount",
    "AMOUNT(INR)": "amount",
    "AMOUNT (RS.)": "amount",
    "AMOUNT(RS.)": "amount",
    "AMount": "amount",
    "AMT": "amount",
    "TOTAL": "amount",
    "NET AMOUNT": "amount",
    "NET AMT": "amount",
    "TAXABLE AMOUNT": "amount",
    "TAXABLE VALUE": "amount",
    "TAXABLE AMT": "amount",
    "NMMT": "amount",
    "INV AMOUNT": "amount",
    "VALUE": "amount",

    # Batch Number
    "BATCH": "batch_no",
    "BATCH NO": "batch_no",
    "BATCH NO:": "batch_no",
    "BATCH NO_": "batch_no",
    "BATCH NUMBER": "batch_no",
    "BATCHNO": "batch_no",
    "LOT": "batch_no",
    "LOT NO": "batch_no",
    "LOT NUMBER": "batch_no",
    "B.NO": "batch_no",
    "B.NO.": "batch_no",

    # Expiry Date
    "EXPIRY": "expiry_date",
    "EXP DT": "expiry_date",
    "EXP. DT": "expiry_date",
    "EXP. DT.": "expiry_date",
    "EXP DATE": "expiry_date",
    "EXP. DATE": "expiry_date",
    "EXPIRY DATE": "expiry_date",
    "EXP": "expiry_date",
    "EXPDATE": "expiry_date",

    # GST / Tax Percentage
    "GST": "gst_pct",
    "GST%": "gst_pct",
    "GST %": "gst_pct",
    "TAX": "gst_pct",
    "TAX%": "gst_pct",
    "TAX %": "gst_pct",
    "VAT%": "gst_pct",
    "VAT %": "gst_pct",
    "TAX RATE": "gst_pct",
    "TAX PER UNIT": "gst_pct",
    "TAX PER UNLT": "gst_pct",

    # CGST / SGST / IGST
    "CGST": "cgst_pct",
    "CGST%": "cgst_pct",
    "CGST %": "cgst_pct",
    "CGST PER": "cgst_pct",
    "CGSTPER": "cgst_pct",
    "SGST": "sgst_pct",
    "SGST%": "sgst_pct",
    "SGST %": "sgst_pct",
    "SGST PER": "sgst_pct",
    "SGSTPER": "sgst_pct",
    "IGST": "igst_pct",
    "IGST%": "igst_pct",
    "IGST %": "igst_pct",
    "IGST PER": "igst_pct",
    "IGSTPER": "igst_pct",

    # MRP
    "MRP": "mrp",
    "M.R.P": "mrp",
    "M.R.P.": "mrp",
    "ITEM MRP": "mrp",
    "ITEMMRP": "mrp",
    "MAX RETAIL PRICE": "mrp",

    # HSN / SAC Code
    "HSN": "hsn",
    "HSN CODE": "hsn",
    "HSN/SAC": "hsn",
    "HSN / SAC": "hsn",
    "SAC": "hsn",
    "SAC CODE": "hsn",
    "HSN/SAC CODE": "hsn",
    "HSNSACCODE": "hsn",
    "HSNCODE": "hsn",

    # Pack / Packaging
    "PACK": "pack",
    "PACKING": "pack",
    "PKG": "pack",
    "PACK SIZE": "pack",
    "PACK NAME": "pack",
    "PACKNAME": "pack",

    # Discount
    "DIS": "discount_pct",
    "DIS %": "discount_pct",
    "DISC": "discount_pct",
    "DISC %": "discount_pct",
    "DISCOUNT": "discount_pct",
    "DISCOUNT %": "discount_pct",
    "INV DISC": "discount_pct",
    "INVDISC": "discount_pct",
    "TRADE DISC": "discount_pct",

    # Free Quantity / Scheme
    "FREE": "free_qty",
    "FREE QTY": "free_qty",
    "FREE QUANTITY": "free_qty",
    "SCHEME": "free_qty",
    "SCM": "free_qty",
    "INV SC QTY": "free_qty",
    "INVSCQTY": "free_qty",

    # Manufacturer / Brand
    "MF": "manufacturer",
    "MFG": "manufacturer",
    "MFR": "manufacturer",
    "MANUFACTURER": "manufacturer",
    "COMPANY": "manufacturer",
    "MAKE": "manufacturer"
}


def is_valid_numeric_token(text: str) -> bool:
    """Checks whether a string token represents a valid numeric value."""
    if not text:
        return False
    clean = re.sub(r"[,\s₹$]", "", text)
    return bool(re.match(r"^-?\d+(?:\.\d+)?$", clean))


def normalize_numeric_token(text: str) -> Optional[str]:
    """
    Attempts to sanitize and normalize an OCR numeric token.
    Corrects safe OCR digit confusions (e.g. 1C0 -> 100, 579. -> 579.00),
    or returns None if the token contains non-numeric text.
    """
    if not text:
        return None

    s = clean_cell_text(text)
    if not s:
        return None

    # Strip trailing dot e.g. "579." -> "579.00"
    if s.endswith(".") and s[:-1].isdigit():
        s = f"{s[:-1]}.00"

    if is_valid_numeric_token(s):
        return s

    # Handle OCR 0 / O / C / l digit confusions if word is short (<= 4 chars) and mostly numeric
    sub_text = s.replace("O", "0").replace("o", "0").replace("C", "0").replace("l", "1").replace("I", "1")
    if is_valid_numeric_token(sub_text):
        return sub_text

    return None


def clean_cell_text(text: str) -> str:
    """
    Cleans OCR currency artifacts, bracket noise, and normalizes numeric values.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Clean common OCR currency and bracket artifacts at boundaries
    s = re.sub(r"^[<\{\[\(\>₹`~]+", "", s)
    s = re.sub(r"[>\}\]\)]+$", "", s)

    # 2. Handle zero tax with percentage or bracket noise
    s = re.sub(r"^(\d+\.\d{2})\s*(?:\(0|\{0|0\b|\(0%\)).*$", r"\1", s)

    # 3. Clean trailing OCR noise chars like '0Q' or punctuation
    s = re.sub(r"\s+0[Qq]$", ".00", s)
    s = s.strip(" ,;:-_")

    # 4. Normalize Indian OCR numbers where decimal point was read as comma
    if re.search(r"\d+,\d{2}$", s) and "." not in s:
        s = re.sub(r",(\d{2})$", r".\1", s)
    elif re.search(r"^\d+,\d{3},\d{2}$", s):
        parts = s.split(",")
        s = f"{parts[0]},{parts[1]}.{parts[2]}"

    return s.strip()


class OCRTableReconstructor:
    """
    2D spatial table reconstruction layer for image-based OCR tokens.
    Dynamically computes each column's X-span and boundary intervals from the
    invoice header bounding boxes, allowing robust extraction across any column ordering.
    """

    KNOWN_HEADER_KEYWORDS = [
        "ITEM", "ITEMS", "METS", "PRODUCT", "DESCRIPTION", "PARTICULARS", "GOODS",
        "HSN", "SAC", "CODE", "PACK", "PACKING", "QTY", "QUANTITY", "QUANTLTY",
        "RATE", "RALE", "PRICE", "PTR", "MRP", "M.R.P", "BATCH", "LOT", "EXP", "EXPIRY",
        "DISC", "DIS", "DISCOUNT", "TAX", "CGST", "SGST", "IGST", "GST", "GST%",
        "AMOUNT", "AMT", "NMMT", "TOTAL", "NET", "FREE", "SCHEME", "SCM", "MF", "MFG"
    ]

    VALID_COMPOUND_HEADERS = {
        "RATE PER UNIT": "rate",
        "RALE PER UNLT": "rate",
        "RATE PER UNLT": "rate",
        "UNIT RATE": "rate",
        "PURCHASE RATE": "rate",
        "SALE RATE": "rate",
        "TAX PER UNIT": "gst_pct",
        "TAX PER UNLT": "gst_pct",
        "PRODUCT NAME": "product_name",
        "ITEM NAME": "product_name",
        "DESCRIPTION OF GOODS": "product_name",
        "NAME OF PRODUCT": "product_name",
        "BATCH NO": "batch_no",
        "BATCH NO:": "batch_no",
        "BATCH NO_": "batch_no",
        "BATCH NUMBER": "batch_no",
        "LOT NO": "batch_no",
        "LOT NUMBER": "batch_no",
        "EXP DT": "expiry_date",
        "EXP. DT": "expiry_date",
        "EXP DATE": "expiry_date",
        "EXP. DATE": "expiry_date",
        "EXPIRY DATE": "expiry_date",
        "DIS %": "discount_pct",
        "DISC %": "discount_pct",
        "DISCOUNT %": "discount_pct",
        "GST %": "gst_pct",
        "TAX %": "gst_pct",
        "TAX RATE": "gst_pct",
        "HSN / SAC": "hsn",
        "HSN/SAC": "hsn",
        "HSN CODE": "hsn",
        "SAC CODE": "hsn",
        "HSN/SAC CODE": "hsn",
        "NET AMOUNT": "amount",
        "NET AMT": "amount",
        "TAXABLE AMOUNT": "amount",
        "TAXABLE VALUE": "amount",
        "FREE QTY": "free_qty",
        "FREE QUANTITY": "free_qty",
        "PACK SIZE": "pack",
        "PACK NAME": "pack"
    }

    @classmethod
    def normalize_header_name(cls, header_str: str) -> str:
        """
        Normalizes a raw header string and maps it to the canonical column name.
        """
        if not header_str:
            return "unknown"

        cleaned = re.sub(r"[\t\r\n]+", " ", str(header_str)).strip()
        cleaned_upper = cleaned.upper()

        if cleaned_upper in cls.VALID_COMPOUND_HEADERS:
            return cls.VALID_COMPOUND_HEADERS[cleaned_upper]

        if cleaned_upper in HEADER_ALIAS_MAP:
            return HEADER_ALIAS_MAP[cleaned_upper]

        no_punct = re.sub(r"[^\w\s%]", "", cleaned_upper).strip()
        if no_punct in HEADER_ALIAS_MAP:
            return HEADER_ALIAS_MAP[no_punct]

        return cleaned.lower()

    @classmethod
    def extract_word_boxes(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]]
    ) -> List[WordBox]:
        """
        Extracts all WordBox instances from an OCRResult, OCRPage, line list, or WordBox list.
        """
        words: List[WordBox] = []
        if isinstance(ocr_data, OCRResult):
            for page in ocr_data.pages:
                for line in page.lines:
                    if line.words:
                        for w in line.words:
                            words.append(WordBox(w.text, w.bbox, w.confidence))
                    elif line.text:
                        dummy_box = [[0, 0], [0, 0], [0, 0], [0, 0]]
                        words.append(WordBox(line.text, dummy_box, line.confidence))
        elif isinstance(ocr_data, OCRPage):
            for line in ocr_data.lines:
                if line.words:
                    for w in line.words:
                        words.append(WordBox(w.text, w.bbox, w.confidence))
                elif line.text:
                    dummy_box = [[0, 0], [0, 0], [0, 0], [0, 0]]
                    words.append(WordBox(line.text, dummy_box, line.confidence))
        elif isinstance(ocr_data, list):
            for item in ocr_data:
                if isinstance(item, WordBox):
                    words.append(item)
                elif isinstance(item, OCRWord):
                    words.append(WordBox(item.text, item.bbox, item.confidence))
                elif isinstance(item, OCRLine):
                    if item.words:
                        for w in item.words:
                            words.append(WordBox(w.text, w.bbox, w.confidence))
                    elif item.text:
                        dummy_box = [[0, 0], [0, 0], [0, 0], [0, 0]]
                        words.append(WordBox(item.text, dummy_box, item.confidence))

        return words

    @classmethod
    def group_words_into_rows(
        cls,
        words: List[WordBox],
        y_tolerance_ratio: float = 0.5
    ) -> List[List[WordBox]]:
        """
        Groups words into horizontal rows based on Y-coordinate proximity and overlap.
        Sorts words within each row from left to right (by x_min).
        """
        if not words:
            return []

        sorted_words = sorted(words, key=lambda w: (w.y_center, w.x_min))
        rows: List[List[WordBox]] = []

        for word in sorted_words:
            if not word.text.strip():
                continue

            matched_row = None
            for row in rows:
                row_y_center = sum(w.y_center for w in row) / len(row)
                avg_height = sum(w.height for w in row) / len(row)
                min_y = min(w.y_min for w in row)
                max_y = max(w.y_max for w in row)

                overlap = min(word.y_max, max_y) - max(word.y_min, min_y)
                if overlap > 0 and (overlap / avg_height) >= 0.3:
                    matched_row = row
                    break
                if abs(word.y_center - row_y_center) <= (avg_height * y_tolerance_ratio):
                    matched_row = row
                    break

            if matched_row is not None:
                matched_row.append(word)
            else:
                rows.append([word])

        for row in rows:
            row.sort(key=lambda w: w.x_min)

        rows.sort(key=lambda r: sum(w.y_center for w in r) / len(r))
        return rows

    @classmethod
    def detect_table_header(cls, rows: List[List[WordBox]]) -> Tuple[int, List[ColumnHeader]]:
        """
        Scans rows to find the table header row and constructs ColumnHeader objects with spatial X spans
        and normalized canonical names.
        """
        best_header_idx = -1
        best_header_score = 0

        for idx, row in enumerate(rows):
            row_text = " ".join(w.text.upper() for w in row)
            score = sum(1 for kw in cls.KNOWN_HEADER_KEYWORDS if kw in row_text)
            if score >= 2 and score > best_header_score:
                best_header_score = score
                best_header_idx = idx

        if best_header_idx == -1:
            return -1, []

        header_words = rows[best_header_idx]
        columns: List[ColumnHeader] = []

        i = 0
        while i < len(header_words):
            matched = False

            # Check 3-word compound headers (e.g. "Rate Per Unit", "Tax Per Unit")
            if i + 2 < len(header_words):
                phrase_3 = f"{header_words[i].text} {header_words[i+1].text} {header_words[i+2].text}".upper()
                if phrase_3 in cls.VALID_COMPOUND_HEADERS:
                    raw_name = f"{header_words[i].text} {header_words[i+1].text} {header_words[i+2].text}"
                    canonical = cls.VALID_COMPOUND_HEADERS[phrase_3]
                    col = ColumnHeader(raw_name, canonical, header_words[i].x_min, header_words[i+2].x_max, header_words[i:i+3])
                    columns.append(col)
                    i += 3
                    matched = True

            # Check 2-word compound headers (e.g. "Product Name", "Batch No", "Exp Dt", "Dis %")
            if not matched and i + 1 < len(header_words):
                phrase_2 = f"{header_words[i].text} {header_words[i+1].text}".upper()
                if phrase_2 in cls.VALID_COMPOUND_HEADERS:
                    raw_name = f"{header_words[i].text} {header_words[i+1].text}"
                    canonical = cls.VALID_COMPOUND_HEADERS[phrase_2]
                    col = ColumnHeader(raw_name, canonical, header_words[i].x_min, header_words[i+1].x_max, header_words[i:i+2])
                    columns.append(col)
                    i += 2
                    matched = True

            # Single-word column header
            if not matched:
                raw_name = header_words[i].text
                canonical = cls.normalize_header_name(raw_name)
                col = ColumnHeader(raw_name, canonical, header_words[i].x_min, header_words[i].x_max, [header_words[i]])
                columns.append(col)
                i += 1

        return best_header_idx, columns

    @classmethod
    def build_table_layout_profile(cls, rows: List[List[WordBox]]) -> Optional[TableLayoutProfile]:
        """
        Dynamically computes the TableLayoutProfile from detected header bounding boxes.
        Calculates dynamic boundary intervals for each column based on its actual position.
        """
        header_idx, columns = cls.detect_table_header(rows)
        if header_idx == -1 or not columns:
            return None

        # Sort columns strictly left-to-right by x_min
        columns.sort(key=lambda c: c.x_min)

        # Compute dynamic boundaries between consecutive columns
        for i in range(len(columns)):
            if i == 0:
                columns[i].left_bound = 0.0
            else:
                mid = (columns[i-1].x_max + columns[i].x_min) / 2.0
                columns[i-1].right_bound = mid
                columns[i].left_bound = mid

            if i == len(columns) - 1:
                columns[i].right_bound = 999999.0

        return TableLayoutProfile(header_idx, columns)

    @classmethod
    def reconstruct_item_rows(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]],
        use_canonical_names: bool = True
    ) -> List[Dict[str, str]]:
        """
        Reconstructs invoice line-item table rows dynamically:
        1. Groups word boxes into horizontal rows by Y-proximity.
        2. Detects table header and builds dynamic column layout profile.
        3. For each word in each data row, determines its dynamic column assignment.
        4. Semantically cleans and places each value into its canonical field.
        """
        words = cls.extract_word_boxes(ocr_data)
        rows = cls.group_words_into_rows(words)

        if not rows:
            return []

        layout = cls.build_table_layout_profile(rows)
        if layout is None:
            return []

        header_idx = layout.header_row_idx
        columns = layout.columns

        # Detect table end boundary (totals, remarks, bank details)
        end_idx = len(rows)
        for idx in range(header_idx + 1, len(rows)):
            row_text = " ".join(w.text.upper() for w in rows[idx])
            if any(
                k in row_text for k in [
                    "SUB TOTAL", "SUBTOTAL", "TAXABLE AMOUNT", "TOTAL AMOUNT",
                    "RECEIVED AMOUNT", "BALANCE", "ROUND OFF", "BANK DETAILS",
                    "TERMS & CONDITIONS", "TERMS AND CONDITIONS", "FOR "
                ]
            ):
                end_idx = idx
                break

        grid_rows: List[Dict[str, str]] = []

        for r_idx in range(header_idx + 1, end_idx):
            row_words = rows[r_idx]
            if not row_words:
                continue

            row_text = " ".join(w.text.upper() for w in row_words)
            if any(k in row_text for k in ["SUB TOTAL", "SUBTOTAL", "TAXABLE AMOUNT", "BALANCE", "TOTAL AMOUNT"]):
                break

            # Map cell tokens to columns using dynamic layout profile
            row_cells: Dict[ColumnHeader, List[str]] = {col: [] for col in columns}

            for word in row_words:
                target_col = layout.find_column_for_word(word)
                cleaned_text = clean_cell_text(word.text)
                if cleaned_text:
                    row_cells[target_col].append(cleaned_text)

            row_dict: Dict[str, str] = {}
            for col in columns:
                key = col.canonical_name if use_canonical_names else col.name
                cell_val = " ".join(row_cells[col]).strip()

                # Semantic Column Validation
                if col.canonical_name in NUMERIC_COLUMNS:
                    num_val = normalize_numeric_token(cell_val)
                    cell_val = num_val if num_val is not None else ""
                elif col.canonical_name == "hsn":
                    if any(w in cell_val.upper() for w in ["TOTAL", "SUBTOTAL", "BANK"]):
                        cell_val = ""

                row_dict[key] = cell_val

            if any(v for v in row_dict.values()):
                grid_rows.append(row_dict)

        return grid_rows

    @classmethod
    def reconstruct_grid(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]],
        use_canonical_names: bool = True
    ) -> List[Dict[str, str]]:
        """
        Alias for reconstruct_item_rows.
        """
        return cls.reconstruct_item_rows(ocr_data, use_canonical_names=use_canonical_names)

    @classmethod
    def reconstruct_text_lines(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]]
    ) -> List[str]:
        """
        Reconstructs 2D OCR words into full horizontal lines of text.
        """
        words = cls.extract_word_boxes(ocr_data)
        rows = cls.group_words_into_rows(words)
        return [" ".join(w.text for w in row) for row in rows]

    @classmethod
    def reconstruct_full_text(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]]
    ) -> str:
        """
        Returns a single newline-separated text representation where 2D spatial
        horizontal alignment is restored.
        """
        lines = cls.reconstruct_text_lines(ocr_data)
        return "\n".join(lines)

    @classmethod
    def reconstruct_table_rows(
        cls,
        ocr_data: Union[OCRResult, OCRPage, List[OCRLine], List[OCRWord], List[WordBox]],
        delimiter: str = " | "
    ) -> List[str]:
        """
        Detects invoice line-item table boundaries from 2D spatial layout and returns
        reconstructed, delimited table rows (header + line items).
        """
        grid = cls.reconstruct_item_rows(ocr_data, use_canonical_names=False)
        if not grid:
            words = cls.extract_word_boxes(ocr_data)
            rows = cls.group_words_into_rows(words)
            return [delimiter.join(w.text for w in row) for row in rows]

        col_names = list(grid[0].keys())
        formatted_rows = [delimiter.join(col_names)]
        for row in grid:
            formatted_rows.append(delimiter.join(row[c] for c in col_names))

        return formatted_rows
