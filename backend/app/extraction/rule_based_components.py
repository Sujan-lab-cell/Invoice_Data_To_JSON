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

        # 1. Grand Total (final invoice amount)
        gt_match = re.search(r"grand\s+total\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not gt_match:
            gt_match = re.search(r"total\s*[:\-]\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if gt_match:
            val = gt_match.group(1).replace(",", "")
            grand_total = {"raw": val, "normalized": float(val), "confidence": 0.8}

        # 2. Subtotal (Gross Amount / Taxable Amount)
        sub_match = re.search(r"gross\s+amt\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not sub_match:
            sub_match = re.search(r"sale\s+value\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not sub_match:
            sub_match = re.search(r"(?:sub\s*)?total\s*(?:before\s+tax)\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if sub_match:
            val = sub_match.group(1).replace(",", "")
            subtotal = {"raw": val, "normalized": float(val), "confidence": 0.8}

        # 3. GST Amount (tax total)
        tax_match = re.search(r"gst\s+amt\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not tax_match:
            tax_match = re.search(r"total\s+gst\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if tax_match:
            val = tax_match.group(1).replace(",", "")
            tax_total = {"raw": val, "normalized": float(val), "confidence": 0.8}

        # 4. Discount Amount
        discount_val = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        disc_match = re.search(r"dis(?:count)?\s*amt\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not disc_match:
            disc_match = re.search(r"cash\s+disc\s*[:\-]?\s*([0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if disc_match:
            val = disc_match.group(1).replace(",", "")
            discount_val = {"raw": val, "normalized": float(val), "confidence": 0.8}

        # 5. Round Off
        round_off_val = {"raw": "", "normalized": 0.0, "confidence": 0.0}
        ro_match = re.search(r"r\.off\s*([+\-]?\s*[0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if not ro_match:
            ro_match = re.search(r"round\s*off\s*([+\-]?\s*[0-9,]+\.[0-9]{2})", ocr_text, re.IGNORECASE)
        if ro_match:
            raw_str = ro_match.group(1).strip()
            val = raw_str.replace(" ", "").replace(",", "")
            round_off_val = {"raw": raw_str, "normalized": float(val), "confidence": 0.8}

        return {
            "subtotal": subtotal,
            "discount_total": discount_val,
            "tax_total": tax_total,
            "grand_total": grand_total,
            "round_off": round_off_val
        }
