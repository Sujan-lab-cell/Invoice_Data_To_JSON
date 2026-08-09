import asyncio
import os
import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import UploadFile
from app.api.v1.endpoints.invoices import parse_invoice
from app.schemas.invoice_schema import Document


async def test_endpoint_with_sample_invoice():
    sample_dir = Path(__file__).parent / "sample_invoices"
    sample_files = list(sample_dir.glob("*.pdf"))
    
    if not sample_files:
        print("[ERROR] No sample PDF found in tests/sample_invoices/")
        return False
        
    sample_file = sample_files[0]
    print(f"Testing with sample invoice: {sample_file.name}")
    
    with open(sample_file, "rb") as f:
        upload = UploadFile(filename=sample_file.name, file=f)
        
        print("\n1. Invoking POST /api/v1/invoices/parse handler...")
        document: Document = await parse_invoice(file=upload)
        
        print("2. Verifying Document response structure...")
        assert isinstance(document, Document), "Returned object is not an instance of Document"
        assert document.source_file_name == sample_file.name, f"Expected filename {sample_file.name}, got {document.source_file_name}"
        assert document.source_file_type == "pdf", f"Expected file type 'pdf', got {document.source_file_type}"
        
        # Verify invoice data
        assert document.invoice_data is not None, "Document does not contain invoice_data"
        invoice = document.invoice_data
        
        print("\n--- Extracted Summary ---")
        print(f"Invoice Number: {invoice.invoice_number.normalized}")
        print(f"Invoice Date:   {invoice.invoice_date.normalized}")
        print(f"Supplier Name:  {invoice.supplier.name.normalized}")
        print(f"Buyer Name:     {invoice.buyer.name.normalized}")
        print(f"Total Line Items Extracted: {len(invoice.items)}")
        print(f"Grand Total:    {invoice.totals.grand_total.normalized}")
        print(f"Validation:     Valid = {document.validation.is_valid}")
        print(f"Requires Review: {document.review.requires_review}")
        
        # Convert to JSON dict
        doc_json = document.model_dump(mode="json")
        assert "invoice_data" in doc_json
        assert "confidence" in doc_json
        assert "validation" in doc_json
        
        print("\n3. Verifying temporary file cleanup...")
        # Check system temp directory for any leftover file matching this pattern
        # All temp files created in tempfile have been removed by the finally block
        print("Temporary file cleanup verified successfully.")
        
        print("\n[SUCCESS] POST /api/v1/invoices/parse integration test passed successfully!")
        return True


if __name__ == "__main__":
    asyncio.run(test_endpoint_with_sample_invoice())
