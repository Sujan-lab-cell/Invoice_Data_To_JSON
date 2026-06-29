import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ItemExtractor:
    """
    Robust, rule-based extractor that scans OCR text line-by-line and uses regex
    patterns to extract detailed line items conforming to the InvoiceItem schema.
    """

    # Regex matching the standard pharmacy line layout:
    # [Description] [Pack] [Qty] [Batch] [Exp] [MRP] [PTR] [Scm%] [Dis%] [GST%] [HSN] [Taxable]
    # Example line:
    # UNSUR INSPI 298 | SILGO 8MG CAPS 10S 3 AFSOE-2503 11/27 279.38 212.86 0.00 2.00 5 30049099 638.58
    LINE_PATTERN = re.compile(
        r"^(?P<prefix>.*?)"                                                      # Prefix e.g. UNSUR INSPI 298 |
        r"(?P<desc>[A-Z\d\s\.\&\-\/\+\`\'’\(\)]+?)"                              # Brand/product description (with parentheses)
        r"\s+(?P<pack>\d+(?:`|'|’)?(?:[sS]|TABS|CAPS|NOS|PCS|ML|GM|VIAL|AMPS)\b)" # Pack size (10S, 10`S, 15's, etc.)
        r"\s+(?P<qty>\d+)(?:\s*\+\s*\d+)?"                                       # Quantity (supporting scheme e.g. 30 +6)
        r"\s+(?P<batch>[A-Z0-9\-]+)"                                             # Batch No
        r"\s+(?P<exp>\d{2}[/\-]\d{2,4})"                                         # Expiry Date (MM/YY or MM/YYYY)
        r"\s+(?P<mrp>\d+\.\d{2})"                                                # MRP
        r"\s+(?P<ptr>\d+\.\d{2})"                                                # Purchase Rate (PTR / Trade Price)
        r"\s+(?P<scm_pct>\d+\.\d{2})"                                            # Scheme/Discount 1 %
        r"\s+(?P<dis_pct>\d+\.\d{2})"                                            # Discount %
        r"\s+(?P<gst_pct>\d{1,2})"                                               # GST %
        r"\s+(?P<hsn>\d{6,8})"                                                   # HSN Code
        r"\s+(?P<taxable_amt>\d+\.\d{2})"                                        # Taxable Amount
        r"(?P<suffix>.*)$",                                                      # Suffix e.g. extra dates/numbers
        re.IGNORECASE | re.VERBOSE
    )

    @classmethod
    def extract_items(cls, ocr_text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        is_structured = "===== SHEET:" in ocr_text or (lines and "|" in lines[0])
        
        # Check if structured sheet
        if is_structured:
            try:
                from app.extraction.header_extractor import HeaderExtractor
                rows = HeaderExtractor.parse_csv_string(ocr_text)
                items = []
                line_num = 1
                for row in rows:
                    desc = row.get("itemname", "")
                    if not desc:
                        continue
                    pack = row.get("packname", "10'S")
                    batch = row.get("batchno", "")
                    exp = row.get("expdate", "")
                    qty_val = float(row.get("invqty", "0.0")) if row.get("invqty") else 0.0
                    ptr_val = float(row.get("salerate", "0.0")) if row.get("salerate") else 0.0
                    mrp_val = float(row.get("itemmrp", "0.0")) if row.get("itemmrp") else 0.0
                    dis_val = float(row.get("invdisc", "0.0")) if row.get("invdisc") else 0.0
                    
                    cgst = float(row.get("cgstper", "0.0")) if row.get("cgstper") else 0.0
                    sgst = float(row.get("sgstper", "0.0")) if row.get("sgstper") else 0.0
                    igst = float(row.get("igstper", "0.0")) if row.get("igstper") else 0.0
                    gst_val = cgst + sgst + igst
                    
                    hsn = row.get("hsnsaccode", "")
                    taxable_val = qty_val * ptr_val
                    
                    discount_amount_val = round(taxable_val * (dis_val / 100.0), 2)
                    gst_amount_val = round(taxable_val * (gst_val / 100.0), 2)
                    
                    # Extract unit count from pack
                    unit_count = 1
                    pack_match = re.match(r"^(\d+)", pack)
                    if pack_match:
                        unit_count = int(pack_match.group(1))

                    unit_type = "Tablets"
                    pack_lower = pack.lower()
                    if "cap" in pack_lower:
                        unit_type = "Capsules"
                    elif "vial" in pack_lower:
                        unit_type = "Vials"
                    elif "amps" in pack_lower:
                        unit_type = "Ampoules"
                    elif "ml" in pack_lower or "liq" in pack_lower or "syr" in pack_lower:
                        unit_type = "Bottles"

                    free_val = float(row.get("invscqty", "0.0")) if row.get("invscqty") else 0.0
                    free_qty_field = {"raw": str(free_val), "normalized": free_val, "confidence": 1.0} if free_val > 0 else None

                    item = {
                        "line_number": line_num,
                        "product": {
                            "product_code": {"raw": str(row.get("itemcode")), "normalized": row.get("itemcode"), "confidence": 1.0} if row.get("itemcode") else None,
                            "description": {"raw": desc, "normalized": desc, "confidence": 1.0},
                            "hsn_code": {"raw": hsn, "normalized": hsn, "confidence": 1.0}
                        },
                        "batch": {
                            "batch_no": {"raw": batch, "normalized": batch, "confidence": 1.0},
                            "expiry_date": {"raw": exp, "normalized": exp, "confidence": 1.0}
                        },
                        "packaging": {
                            "pack_size": pack,
                            "unit_count": unit_count,
                            "unit_type": unit_type
                        },
                        "quantity": {
                            "qty": {"raw": str(qty_val), "normalized": qty_val, "confidence": 1.0},
                            "free_qty": free_qty_field,
                            "total_qty": (qty_val + free_val) * unit_count
                        },
                        "pricing": {
                            "mrp": {"raw": str(mrp_val), "normalized": mrp_val, "confidence": 1.0},
                            "purchase_rate": {"raw": str(ptr_val), "normalized": ptr_val, "confidence": 1.0},
                            "discount_percentage": {"raw": str(dis_val), "normalized": dis_val, "confidence": 1.0},
                            "discount_amount": {"raw": str(discount_amount_val), "normalized": discount_amount_val, "confidence": 1.0},
                            "taxable_amount": {"raw": f"{taxable_val:.2f}", "normalized": round(taxable_val, 2), "confidence": 1.0}
                        },
                        "tax": {
                            "cgst_percentage": {"raw": str(cgst), "normalized": cgst, "confidence": 1.0} if cgst > 0 else None,
                            "sgst_percentage": {"raw": str(sgst), "normalized": sgst, "confidence": 1.0} if sgst > 0 else None,
                            "igst_percentage": {"raw": str(igst), "normalized": igst, "confidence": 1.0} if igst > 0 else None,
                            "cgst_amount": {"raw": f"{round(taxable_val * (cgst / 100.0), 2):.2f}", "normalized": round(taxable_val * (cgst / 100.0), 2), "confidence": 1.0} if cgst > 0 else None,
                            "sgst_amount": {"raw": f"{round(taxable_val * (sgst / 100.0), 2):.2f}", "normalized": round(taxable_val * (sgst / 100.0), 2), "confidence": 1.0} if sgst > 0 else None,
                            "igst_amount": {"raw": f"{round(taxable_val * (igst / 100.0), 2):.2f}", "normalized": round(taxable_val * (igst / 100.0), 2), "confidence": 1.0} if igst > 0 else None,
                            "gst_percentage": {"raw": str(gst_val), "normalized": gst_val, "confidence": 1.0},
                            "gst_amount": {"raw": str(gst_amount_val), "normalized": gst_amount_val, "confidence": 1.0}
                        }
                    }
                    items.append(item)
                    line_num += 1
                return items
            except Exception as e:
                logger.error(f"Failed parsing items from Excel sheet: {e}")

        items = []
        lines = ocr_text.splitlines()
        line_num = 1

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            # Ignore lines containing total/subtotal keywords
            if any(term in line_clean.upper() for term in ["TOTAL", "SUBTOTAL", "INVOICE", "DECLARATION", "BANK", "PAGE"]):
                continue

            match = cls.LINE_PATTERN.match(line_clean)
            if match:
                gd = match.groupdict()
                try:
                    product_desc = gd["desc"].strip()
                    # Clean prefix/suffix from description if needed
                    # If description has vertical bar |, take the part after it
                    if "|" in product_desc:
                        product_desc = product_desc.split("|")[-1].strip()
                    
                    product_desc = re.sub(r"^[\|\s\-\:\,]+", "", product_desc).strip()

                    qty_val = float(gd["qty"])
                    mrp_val = float(gd["mrp"])
                    ptr_val = float(gd["ptr"])
                    dis_val = float(gd["dis_pct"])
                    gst_val = float(gd["gst_pct"])
                    taxable_val = float(gd["taxable_amt"])

                    # Calculate discount amount: Taxable Amount * dis_val / 100
                    discount_amount_val = round(taxable_val * (dis_val / 100.0), 2)

                    # Calculate gst_amount = taxable_val * (gst_val / 100.0)
                    gst_amount_val = round(taxable_val * (gst_val / 100.0), 2)

                    # Extract unit count from pack (e.g. "10S" -> 10)
                    unit_count = 1
                    pack_match = re.match(r"^(\d+)", gd["pack"])
                    if pack_match:
                        unit_count = int(pack_match.group(1))

                    unit_type = "Tablets"
                    pack_lower = gd["pack"].lower()
                    if "cap" in pack_lower:
                        unit_type = "Capsules"
                    elif "vial" in pack_lower:
                        unit_type = "Vials"
                    elif "ml" in pack_lower or "liq" in pack_lower or "syr" in pack_lower:
                        unit_type = "Bottles"

                    item = {
                        "line_number": line_num,
                        "product": {
                            "product_code": None,
                            "description": {"raw": product_desc, "normalized": product_desc, "confidence": 0.8},
                            "hsn_code": {"raw": gd["hsn"], "normalized": gd["hsn"], "confidence": 0.8}
                        },
                        "batch": {
                            "batch_no": {"raw": gd["batch"], "normalized": gd["batch"], "confidence": 0.8},
                            "expiry_date": {"raw": gd["exp"], "normalized": gd["exp"], "confidence": 0.8}
                        },
                        "packaging": {
                            "pack_size": gd["pack"],
                            "unit_count": unit_count,
                            "unit_type": unit_type
                        },
                        "quantity": {
                            "qty": {"raw": gd["qty"], "normalized": qty_val, "confidence": 0.8},
                            "free_qty": None,
                            "total_qty": qty_val * unit_count
                        },
                        "pricing": {
                            "mrp": {"raw": gd["mrp"], "normalized": mrp_val, "confidence": 0.8},
                            "purchase_rate": {"raw": gd["ptr"], "normalized": ptr_val, "confidence": 0.8},
                            "discount_percentage": {"raw": gd["dis_pct"], "normalized": dis_val, "confidence": 0.8},
                            "discount_amount": {"raw": str(discount_amount_val), "normalized": discount_amount_val, "confidence": 0.8},
                            "taxable_amount": {"raw": gd["taxable_amt"], "normalized": taxable_val, "confidence": 0.8}
                        },
                        "tax": {
                            "cgst_percentage": None,
                            "sgst_percentage": None,
                            "igst_percentage": None,
                            "cgst_amount": None,
                            "sgst_amount": None,
                            "igst_amount": None,
                            "gst_percentage": {"raw": gd["gst_pct"], "normalized": gst_val, "confidence": 0.8},
                            "gst_amount": {"raw": str(gst_amount_val), "normalized": gst_amount_val, "confidence": 0.8}
                        }
                    }
                    items.append(item)
                    line_num += 1
                except Exception as e:
                    logger.debug(f"Failed parsing item row with rules: {e}")
                    continue
        return items
