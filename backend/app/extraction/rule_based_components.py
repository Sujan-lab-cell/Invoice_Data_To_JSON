import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


from .item_extractor import ItemExtractor


class PricingExtractor:
    """
    Extracts pricing details from a text line.
    """
    @classmethod
    def extract_pricing(cls, line_parts: List[str]) -> Dict[str, Any]:
        return {
            "mrp": {"raw": "0.0", "normalized": 0.0, "confidence": 0.0},
            "purchase_rate": {"raw": "0.0", "normalized": 0.0, "confidence": 0.0},
            "discount_percentage": None,
            "discount_amount": None,
            "taxable_amount": {"raw": "0.0", "normalized": 0.0, "confidence": 0.0}
        }


class TaxExtractor:
    """
    Extracts tax rates and totals from line segments.
    """
    @classmethod
    def extract_tax(cls, line_parts: List[str]) -> Dict[str, Any]:
        return {
            "cgst_percentage": None,
            "sgst_percentage": None,
            "igst_percentage": None,
            "cgst_amount": None,
            "sgst_amount": None,
            "igst_amount": None,
            "gst_percentage": {"raw": "0.0", "normalized": 0.0, "confidence": 0.0},
            "gst_amount": {"raw": "0.0", "normalized": 0.0, "confidence": 0.0}
        }


class TotalsCalculator:
    """
    Extracts invoice-level subtotal, tax_total, and grand_total.
    """

    @classmethod
    def extract_totals(cls, ocr_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        is_structured = "===== SHEET:" in ocr_text or (lines and "|" in lines[0])

        # Check if structured sheet
        if is_structured:
            try:
                from app.extraction.header_extractor import HeaderExtractor
                rows = HeaderExtractor.parse_csv_string(ocr_text)
                if rows:
                    first_row = rows[0]
                    # invamt column contains the grand total
                    inv_amt = float(first_row.get("invamt", "0.0")) if first_row.get("invamt") else 0.0
                    
                    # Sum taxable amounts and gst amounts
                    subtotal = 0.0
                    tax_total = 0.0
                    for row in rows:
                        qty = float(row.get("invqty", "0.0")) if row.get("invqty") else 0.0
                        rate = float(row.get("salerate", "0.0")) if row.get("salerate") else 0.0
                        cgst = float(row.get("cgstper", "0.0")) if row.get("cgstper") else 0.0
                        sgst = float(row.get("sgstper", "0.0")) if row.get("sgstper") else 0.0
                        igst = float(row.get("igstper", "0.0")) if row.get("igstper") else 0.0
                        
                        taxable = qty * rate
                        gst_pct = cgst + sgst + igst
                        tax = taxable * (gst_pct / 100.0)
                        
                        subtotal += taxable
                        tax_total += tax
                        
                    return {
                        "subtotal": {"raw": f"{subtotal:.2f}", "normalized": round(subtotal, 2), "confidence": 1.0},
                        "discount_total": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0},
                        "tax_total": {"raw": f"{tax_total:.2f}", "normalized": round(tax_total, 2), "confidence": 1.0},
                        "grand_total": {"raw": f"{inv_amt:.2f}", "normalized": inv_amt, "confidence": 1.0},
                        "round_off": {"raw": "0.00", "normalized": 0.0, "confidence": 1.0}
                    }
            except Exception as e:
                logger.error(f"Failed to parse totals from structured Excel text: {e}")

        subtotal = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        tax_total = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        grand_total = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        discount_val = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        round_off_val = {"raw": "", "normalized": 0.0, "confidence": 0.0}

        # 1. Grand Total (Net Payable / Net Amount / Grand Total / Invoice Total / Total :)
        gt_match = re.search(r"(?:net\s+(?:payable|amount)|grand\s+total|invoice\s+total)\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not gt_match:
            gt_match = re.search(r"(?<!sub\s)(?<!taxable\s)(?<!gst\s)(?<!items\s)(?<!qty\s)(?<!bills\s)(?<!outstanding\s)\btotal\s*[:\-]\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if gt_match:
            raw_val = gt_match.group(1)
            val = raw_val.replace(",", "")
            grand_total = {"raw": raw_val, "normalized": float(val), "confidence": 0.85}

        # 2. Subtotal (Taxable Amount / Taxable Value / Gross Amount / Gross Amt / Sale Value / Sub Total / Subtotal)
        sub_match = re.search(r"(?:taxable\s+(?:amount|value)|gross\s+amt(?:ount)?|sale\s+value|sub\s*total|subtotal)\s*(?:before\s+tax)?\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if sub_match:
            raw_val = sub_match.group(1)
            val = raw_val.replace(",", "")
            subtotal = {"raw": raw_val, "normalized": float(val), "confidence": 0.85}

        # 3. Tax Total (Tax Amount / GST Amount / GST Amt / Total GST / GST (xx%) / Tax Tot)
        tax_match = re.search(r"(?:tax\s+amount|gst\s+amt(?:ount)?|total\s+gst|gst\s*(?:\([^\)]+\))?)\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not tax_match:
            tax_match = re.search(r"tax\s+tot\s*[:;\-]?\s*(?:[0-9,]+\.[0-9]{2}\s+){2}([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if tax_match:
            raw_val = tax_match.group(1)
            val = raw_val.replace(",", "")
            tax_total = {"raw": raw_val, "normalized": float(val), "confidence": 0.85}

        # 4. Discount Amount (Discount Amount / Dis Amt / Cash Disc / Local Bill Disc)
        disc_match = re.search(r"(?:dis(?:count)?\s*amt(?:ount)?|cash\s+disc(?:ount)?|local\s+bill\s+disc(?:ount)?)\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if disc_match:
            raw_val = disc_match.group(1)
            val = raw_val.replace(",", "")
            discount_val = {"raw": raw_val, "normalized": float(val), "confidence": 0.85}

        # 5. Round Off (Write Off / Round Off / R.Off)
        ro_match = re.search(r"(?:write\s*off|round\s*off|r\.off)\s*[:\-]?\s*([+\-]?\s*[0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if ro_match:
            raw_str = ro_match.group(1).strip()
            val = raw_str.replace(" ", "").replace(",", "")
            round_off_val = {"raw": raw_str, "normalized": float(val), "confidence": 0.85}

        return {
            "subtotal": subtotal,
            "discount_total": discount_val,
            "tax_total": tax_total,
            "grand_total": grand_total,
            "round_off": round_off_val
        }
