import asyncio
import io
import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import UploadFile
from app.api.v1.endpoints.invoices import parse_invoice
from app.schemas.invoice_schema import Document


async def test_format(name: str, filename: str, file_bytes: bytes):
    print(f"\n==================================================")
    print(f"Testing Format: {name} ({filename})")
    print(f"==================================================")
    try:
        file_obj = io.BytesIO(file_bytes)
        upload = UploadFile(filename=filename, file=file_obj)
        
        doc: Document = await parse_invoice(file=upload)
        
        assert isinstance(doc, Document), "Output is not a Document"
        assert doc.source_file_name == filename
        
        inv = doc.invoice_data
        inv_num = inv.invoice_number.normalized if inv else "N/A"
        supp = inv.supplier.name.normalized if inv else "N/A"
        item_count = len(inv.items) if inv else 0
        grand_total = inv.totals.grand_total.normalized if inv else 0.0
        
        print(f"-> Status: PASS")
        print(f"-> Source File Type: {doc.source_file_type}")
        print(f"-> Invoice Number: {inv_num}")
        print(f"-> Supplier: {supp}")
        print(f"-> Line Items: {item_count}")
        print(f"-> Grand Total: {grand_total}")
        return True, None
    except Exception as e:
        print(f"-> Status: FAIL")
        print(f"-> Error: {e}")
        return False, str(e)


async def main():
    sample_dir = Path(__file__).parent / "sample_invoices"
    
    results = {}

    # 1. Test PDF
    pdf_path = sample_dir / "VINAYAKA ENTERPRISES PAYYANUR, KANNUR DISTT Sales Invoice 1758 (1).pdf"
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        passed, err = await test_format("PDF", pdf_path.name, pdf_bytes)
        results["PDF"] = ("PASS" if passed else "FAIL", err)
    else:
        results["PDF"] = ("FAIL", "Sample PDF file not found")

    # 2. Test XLS
    xls_path = sample_dir / "MCRB PHARMA PILATHARA Sales Invoice 8898.xls"
    if xls_path.exists():
        with open(xls_path, "rb") as f:
            xls_bytes = f.read()
        passed, err = await test_format("XLS", xls_path.name, xls_bytes)
        results["XLS"] = ("PASS" if passed else "FAIL", err)
    else:
        results["XLS"] = ("FAIL", "Sample XLS file not found")

    # 3. Test XLSX
    xlsx_path = sample_dir / "INV_11424.xlsx"
    if xls_path.exists():
        with open(xlsx_path, "rb") as f:
            xlsx_bytes = f.read()
        passed, err = await test_format("XLSX", xlsx_path.name, xlsx_bytes)
        results["XLSX"] = ("PASS" if passed else "FAIL", err)
    else:
        results["XLSX"] = ("FAIL", "Sample XLSX file not found")

    # 4. Test CSV
    # Create sample CSV content from structured pharmacy invoice data
    csv_content = """Invoice No,Invoice Date,Supplier Name,Buyer Name,Product Description,Batch No,Expiry Date,Qty,MRP,Rate,GST%,Total
1758,2026-05-08,VINAYAKA ENTERPRISES,GERMAN PHARMACY,EASODAY 40 MG 10X15,APGT250937G,05/27,5,121.78,91.85,5,450.07
1758,2026-05-08,VINAYAKA ENTERPRISES,GERMAN PHARMACY,KEFTRUM 500MG TABS 10S,CT250310,02/27,5,540.00,407.31,5,1995.82
"""
    passed, err = await test_format("CSV", "sample_invoice.csv", csv_content.encode("utf-8"))
    results["CSV"] = ("PASS" if passed else "FAIL", err)

    # 5. Test PNG / JPG using an image created via Pillow
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "TAX INVOICE", fill=(0, 0, 0))
    draw.text((20, 50), "Supplier: VINAYAKA ENTERPRISES", fill=(0, 0, 0))
    draw.text((20, 80), "Buyer: GERMAN PHARMACY", fill=(0, 0, 0))
    draw.text((20, 110), "Invoice No: 1758 Date: 08-05-2026", fill=(0, 0, 0))
    draw.text((20, 150), "Item: EASODAY 40 MG Qty: 5 Rate: 91.85 MRP: 121.78", fill=(0, 0, 0))
    draw.text((20, 190), "Grand Total: 2568.00", fill=(0, 0, 0))

    # Test PNG
    png_io = io.BytesIO()
    img.save(png_io, format="PNG")
    passed, err = await test_format("PNG", "sample_invoice.png", png_io.getvalue())
    results["PNG"] = ("PASS" if passed else "FAIL", err)

    # Test JPG
    jpg_io = io.BytesIO()
    img.save(jpg_io, format="JPEG")
    passed, err = await test_format("JPG", "sample_invoice.jpg", jpg_io.getvalue())
    results["JPG"] = ("PASS" if passed else "FAIL", err)

    print("\n" + "=" * 60)
    print("FORMAT TEST MATRIX SUMMARY")
    print("=" * 60)
    for fmt, (res, err) in results.items():
        err_msg = f" (Error: {err})" if err else ""
        print(f"[{res}] {fmt:<10}{err_msg}")


if __name__ == "__main__":
    asyncio.run(main())
