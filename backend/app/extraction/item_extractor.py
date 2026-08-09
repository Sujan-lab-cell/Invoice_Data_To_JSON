import re
import logging
from typing import Any, Dict, List, Optional, Union
from app.ocr.schemas import OCRResult

logger = logging.getLogger(__name__)


class ItemExtractor:
    """
    Robust extractor that scans OCR text line-by-line using regex patterns
    for digital/text invoices, and falls back to 2D spatial OCRTableReconstructor
    when flattened text returns 0 items.
    """

    LINE_PATTERN = re.compile(
        r"^(?P<prefix>.*?)"                                                      # Prefix e.g. UNSUR INSPI 298 |
        r"(?P<desc>[A-Z\d\s\.\&\-\/\+\`\'’\(\)]+?)"                              # Brand/product description
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

    LINE_PATTERN_MFG_HSN = re.compile(
        r"^(?P<mfg>[A-Z0-9]+)\s+"
        r"(?P<hsn>\d{4,8})\s+"
        r"(?P<desc>[A-Z\d\s\.\&\-\/\+\`\'’\(\)]+?)\s+"
        r"(?P<pack>\d+(?:X\d+)?(?:`|'|’)?(?:[sS]|TABS|CAPS|NOS|PCS|ML|GM|VIAL|AMPS)?)\s+"
        r"(?:(?P<scheme_billed>\d+(?:\.\d+)?)\s*\+\s*)?(?P<qty_raw>\d+(?:\.\d+)?)\s*"
        r"(?P<batch>[A-Z0-9\-]+)\s+"
        r"(?P<exp>\d{2}[/\-]\d{2,4})\s+"
        r"(?P<mrp>\d+\.\d{2})\s+"
        r"(?P<rate>\d+\.\d{2,3})\s+"
        r"(?P<dis_pct>\d+\.\d{2})\s+"
        r"(?P<dis_amt>\d+\.\d{2})\s+"
        r"(?P<sch_disc>\d+\.\d{2})\s+"
        r"(?P<cgst_pct>\d+(?:\.\d+)?)\s+(?P<cgst_amt>\d+\.\d{2})\s+"
        r"(?P<sgst_pct>\d+(?:\.\d+)?)\s+(?P<sgst_amt>\d+\.\d{2})\s+"
        r"(?P<taxable_amt>\d+\.\d{2})"
        r"(?P<suffix>.*)$",
        re.IGNORECASE | re.VERBOSE
    )

    @classmethod
    def _extract_from_structured_sheet(cls, ocr_text: str) -> Optional[List[Dict[str, Any]]]:
        """Extracts items from CSV/Excel structured text representation."""
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        is_structured = "===== SHEET:" in ocr_text or (lines and "|" in lines[0])
        if not is_structured:
            return None

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
            return None

    @classmethod
    def _extract_via_regex(cls, ocr_text: str) -> List[Dict[str, Any]]:
        """Scans lines using LINE_PATTERN."""
        items = []
        lines = ocr_text.splitlines()
        line_num = 1

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            if any(term in line_clean.upper() for term in ["TOTAL", "SUBTOTAL", "INVOICE", "DECLARATION", "BANK", "PAGE"]):
                continue

            match = cls.LINE_PATTERN.match(line_clean)
            if match:
                gd = match.groupdict()
                try:
                    product_desc = gd["desc"].strip()
                    if "|" in product_desc:
                        product_desc = product_desc.split("|")[-1].strip()
                    product_desc = re.sub(r"^[\|\s\-\:\,]+", "", product_desc).strip()

                    qty_val = float(gd["qty"])
                    mrp_val = float(gd["mrp"])
                    ptr_val = float(gd["ptr"])
                    dis_val = float(gd["dis_pct"])
                    gst_val = float(gd["gst_pct"])
                    taxable_val = float(gd["taxable_amt"])

                    discount_amount_val = round(taxable_val * (dis_val / 100.0), 2)
                    gst_amount_val = round(taxable_val * (gst_val / 100.0), 2)

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
                    elif "amps" in pack_lower:
                        unit_type = "Ampoules"
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
                    continue
                except Exception as e:
                    logger.debug(f"Failed parsing item row with LINE_PATTERN: {e}")
                    continue

            # Check secondary layout pattern: [Mfg] [HSN] [Desc] [Pack] [Qty] [Batch] [Exp] [MRP] [Rate] ...
            match_mfg = cls.LINE_PATTERN_MFG_HSN.match(line_clean)
            if match_mfg:
                gd = match_mfg.groupdict()
                try:
                    product_desc = gd["desc"].strip()
                    if gd.get("scheme_billed") is not None:
                        billed_qty = float(gd["scheme_billed"])
                        free_qty = float(gd["qty_raw"])
                    else:
                        billed_qty = float(gd["qty_raw"])
                        free_qty = 0.0

                    mrp_val = float(gd["mrp"])
                    rate_val = float(gd["rate"])
                    dis_pct = float(gd["dis_pct"])
                    dis_amt = float(gd["dis_amt"])
                    cgst_pct = float(gd["cgst_pct"])
                    cgst_amt = float(gd["cgst_amt"])
                    sgst_pct = float(gd["sgst_pct"])
                    sgst_amt = float(gd["sgst_amt"])
                    gst_pct = cgst_pct + sgst_pct
                    gst_amt = round(cgst_amt + sgst_amt, 2)
                    taxable_val = float(gd["taxable_amt"])

                    unit_count = 1
                    pack_str = gd["pack"]
                    pack_x = re.search(r"(\d+)X(\d+)", pack_str, re.IGNORECASE)
                    if pack_x:
                        unit_count = int(pack_x.group(1)) * int(pack_x.group(2))
                    else:
                        pack_match = re.match(r"^(\d+)", pack_str)
                        if pack_match:
                            unit_count = int(pack_match.group(1))

                    unit_type = "Units"
                    desc_lower = product_desc.lower()
                    if "tab" in desc_lower or "tab" in pack_str.lower():
                        unit_type = "Tablets"
                    elif "cap" in desc_lower or "cap" in pack_str.lower():
                        unit_type = "Capsules"
                    elif "syr" in desc_lower or "liq" in desc_lower or "ml" in desc_lower:
                        unit_type = "Bottles"

                    free_qty_field = {"raw": str(free_qty), "normalized": free_qty, "confidence": 0.9} if free_qty > 0 else None

                    item = {
                        "line_number": line_num,
                        "product": {
                            "product_code": {"raw": gd["mfg"], "normalized": gd["mfg"], "confidence": 0.9},
                            "description": {"raw": product_desc, "normalized": product_desc, "confidence": 0.9},
                            "hsn_code": {"raw": gd["hsn"], "normalized": gd["hsn"], "confidence": 0.9}
                        },
                        "batch": {
                            "batch_no": {"raw": gd["batch"], "normalized": gd["batch"], "confidence": 0.9},
                            "expiry_date": {"raw": gd["exp"], "normalized": gd["exp"], "confidence": 0.9}
                        },
                        "packaging": {
                            "pack_size": pack_str,
                            "unit_count": unit_count,
                            "unit_type": unit_type
                        },
                        "quantity": {
                            "qty": {"raw": str(billed_qty), "normalized": billed_qty, "confidence": 0.9},
                            "free_qty": free_qty_field,
                            "total_qty": (billed_qty + free_qty) * unit_count
                        },
                        "pricing": {
                            "mrp": {"raw": gd["mrp"], "normalized": mrp_val, "confidence": 0.9},
                            "purchase_rate": {"raw": gd["rate"], "normalized": rate_val, "confidence": 0.9},
                            "discount_percentage": {"raw": gd["dis_pct"], "normalized": dis_pct, "confidence": 0.9} if dis_pct > 0 else None,
                            "discount_amount": {"raw": gd["dis_amt"], "normalized": dis_amt, "confidence": 0.9} if dis_amt > 0 else None,
                            "taxable_amount": {"raw": gd["taxable_amt"], "normalized": taxable_val, "confidence": 0.9}
                        },
                        "tax": {
                            "cgst_percentage": {"raw": gd["cgst_pct"], "normalized": cgst_pct, "confidence": 0.9} if cgst_pct > 0 else None,
                            "sgst_percentage": {"raw": gd["sgst_pct"], "normalized": sgst_pct, "confidence": 0.9} if sgst_pct > 0 else None,
                            "igst_percentage": None,
                            "cgst_amount": {"raw": gd["cgst_amt"], "normalized": cgst_amt, "confidence": 0.9} if cgst_amt > 0 else None,
                            "sgst_amount": {"raw": gd["sgst_amt"], "normalized": sgst_amt, "confidence": 0.9} if sgst_amt > 0 else None,
                            "igst_amount": None,
                            "gst_percentage": {"raw": str(gst_pct), "normalized": gst_pct, "confidence": 0.9},
                            "gst_amount": {"raw": str(gst_amt), "normalized": gst_amt, "confidence": 0.9}
                        }
                    }
                    items.append(item)
                    line_num += 1
                    continue
                except Exception as e:
                    logger.debug(f"Failed parsing item row with LINE_PATTERN_MFG_HSN: {e}")
                    continue
        return items

    @classmethod
    def _convert_grid_to_invoice_items(cls, grid_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Converts 2D reconstructed grid dictionaries into the canonical InvoiceItem schema.
        """
        items = []
        line_num = 1

        def _parse_float(val: str, default: float = 0.0) -> float:
            if not val:
                return default
            clean = re.sub(r"[,\s₹$]", "", val)
            try:
                return float(clean)
            except ValueError:
                return default

        for row in grid_rows:
            product_desc = row.get("product_name") or row.get("items") or row.get("description", "")
            if not product_desc:
                # If no product description in this row, skip
                continue

            hsn = row.get("hsn", "")
            batch = row.get("batch_no", "")
            exp = row.get("expiry_date", "")
            pack = row.get("pack", "1 Unit")

            qty_raw = row.get("quantity", "")
            qty_val = _parse_float(qty_raw, default=1.0 if (row.get("amount") or row.get("rate")) else 0.0)

            rate_raw = row.get("rate") or row.get("rate_per_unit", "")
            rate_val = _parse_float(rate_raw, default=0.0)

            mrp_raw = row.get("mrp", "")
            mrp_val = _parse_float(mrp_raw, default=rate_val)

            amount_raw = row.get("amount", "")
            amount_val = _parse_float(amount_raw, default=0.0)

            if amount_val == 0.0 and qty_val > 0 and rate_val > 0:
                amount_val = round(qty_val * rate_val, 2)
            elif rate_val == 0.0 and amount_val > 0 and qty_val > 0:
                rate_val = round(amount_val / qty_val, 2)

            dis_raw = row.get("discount_pct", "")
            dis_val = _parse_float(dis_raw, default=0.0)

            gst_raw = row.get("gst_pct") or row.get("tax_per_unit", "")
            gst_val = _parse_float(gst_raw, default=0.0)

            taxable_val = amount_val if amount_val > 0 else round(qty_val * rate_val, 2)
            discount_amount_val = round(taxable_val * (dis_val / 100.0), 2)
            gst_amount_val = round(taxable_val * (gst_val / 100.0), 2)

            unit_count = 1
            pack_match = re.match(r"^(\d+)", pack)
            if pack_match:
                unit_count = int(pack_match.group(1))

            unit_type = "Units"
            pack_lower = pack.lower()
            if "tab" in pack_lower:
                unit_type = "Tablets"
            elif "cap" in pack_lower:
                unit_type = "Capsules"
            elif "vial" in pack_lower:
                unit_type = "Vials"
            elif "amps" in pack_lower:
                unit_type = "Ampoules"
            elif "ml" in pack_lower or "liq" in pack_lower or "syr" in pack_lower:
                unit_type = "Bottles"

            free_raw = row.get("free_qty", "")
            free_val = _parse_float(free_raw, default=0.0)
            free_qty_field = {"raw": str(free_val), "normalized": free_val, "confidence": 0.85} if free_val > 0 else None

            item = {
                "line_number": line_num,
                "product": {
                    "product_code": None,
                    "description": {"raw": product_desc, "normalized": product_desc, "confidence": 0.85},
                    "hsn_code": {"raw": hsn, "normalized": hsn, "confidence": 0.85} if hsn else None
                },
                "batch": {
                    "batch_no": {"raw": batch, "normalized": batch, "confidence": 0.85} if batch else {"raw": "", "normalized": "", "confidence": 0.0},
                    "expiry_date": {"raw": exp, "normalized": exp, "confidence": 0.85} if exp else {"raw": "", "normalized": "", "confidence": 0.0}
                },
                "packaging": {
                    "pack_size": pack,
                    "unit_count": unit_count,
                    "unit_type": unit_type
                },
                "quantity": {
                    "qty": {"raw": str(qty_val), "normalized": qty_val, "confidence": 0.85},
                    "free_qty": free_qty_field,
                    "total_qty": (qty_val + free_val) * unit_count
                },
                "pricing": {
                    "mrp": {"raw": str(mrp_val), "normalized": mrp_val, "confidence": 0.85},
                    "purchase_rate": {"raw": str(rate_val), "normalized": rate_val, "confidence": 0.85},
                    "discount_percentage": {"raw": str(dis_val), "normalized": dis_val, "confidence": 0.85} if dis_val > 0 else None,
                    "discount_amount": {"raw": str(discount_amount_val), "normalized": discount_amount_val, "confidence": 0.85} if discount_amount_val > 0 else None,
                    "taxable_amount": {"raw": str(taxable_val), "normalized": taxable_val, "confidence": 0.85}
                },
                "tax": {
                    "cgst_percentage": None,
                    "sgst_percentage": None,
                    "igst_percentage": None,
                    "cgst_amount": None,
                    "sgst_amount": None,
                    "igst_amount": None,
                    "gst_percentage": {"raw": str(gst_val), "normalized": gst_val, "confidence": 0.85},
                    "gst_amount": {"raw": str(gst_amount_val), "normalized": gst_amount_val, "confidence": 0.85}
                }
            }
            items.append(item)
            line_num += 1

        return items

    @classmethod
    def extract_items(
        cls,
        ocr_text: str,
        ocr_result: Optional[OCRResult] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts items from the invoice.
        1. Checks structured sheet (Excel/CSV).
        2. Scans line-by-line using regex (PDF / text).
        3. If 0 items found and ocr_result is provided, uses 2D spatial OCRTableReconstructor.
        """
        # 1. Check structured sheet
        structured_items = cls._extract_from_structured_sheet(ocr_text)
        if structured_items is not None:
            return structured_items

        # 2. Try line-by-line regex
        items = cls._extract_via_regex(ocr_text)
        if items:
            return items

        # 3. 2D spatial OCR reconstruction fallback for images
        if ocr_result is not None:
            try:
                from app.ocr.ocr_table_reconstructor import OCRTableReconstructor
                grid_rows = OCRTableReconstructor.reconstruct_item_rows(ocr_result, use_canonical_names=True)
                if grid_rows:
                    reconstructed_items = cls._convert_grid_to_invoice_items(grid_rows)
                    if reconstructed_items:
                        logger.info(f"Successfully extracted {len(reconstructed_items)} items via 2D OCRTableReconstructor.")
                        return reconstructed_items
            except Exception as e:
                logger.warning(f"2D OCRTableReconstructor extraction failed: {e}")

        return []
