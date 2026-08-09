import asyncio
import io
import os
import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import HTTPException, UploadFile
from app.api.v1.endpoints.invoices import parse_invoice


async def test_scenario(name: str, filename: str, content: bytes, expected_status: int, expected_detail_snippet: str):
    print(f"\n--- Testing Scenario: {name} ---")
    file_obj = io.BytesIO(content)
    upload = UploadFile(filename=filename, file=file_obj)
    
    try:
        await parse_invoice(file=upload)
        print(f"FAILED: Expected HTTP {expected_status}, but got success.")
        return False
    except HTTPException as e:
        status_match = (e.status_code == expected_status)
        detail_match = (expected_detail_snippet.lower() in str(e.detail).lower())
        
        if status_match and detail_match:
            print(f"PASSED: HTTP {e.status_code} -> {e.detail}")
            return True
        else:
            print(f"FAILED: Expected status {expected_status} containing '{expected_detail_snippet}', got {e.status_code}: {e.detail}")
            return False
    except Exception as e:
        print(f"FAILED: Unexpected exception type: {type(e).__name__}: {e}")
        return False


async def main():
    print("==================================================")
    print("COMPREHENSIVE ERROR HANDLING TEST SUITE")
    print("==================================================")
    
    tests = [
        # 1. Missing / empty filename
        (
            "Missing/Empty Filename",
            "",
            b"test content",
            400,
            "filename"
        ),
        # 2. Empty file (0 bytes)
        (
            "Empty File (0 bytes)",
            "invoice.pdf",
            b"",
            400,
            "empty"
        ),
        # 3. Unsupported extension
        (
            "Unsupported Extension (.exe)",
            "invoice.exe",
            b"binary exe content",
            400,
            "unsupported"
        ),
        # 4. Corrupt PDF file
        (
            "Corrupt PDF (Invalid binary data)",
            "corrupt.pdf",
            b"NOT_A_REAL_PDF_HEADER_OR_BODY_CORRUPT_BYTES",
            422,
            "corrupt"
        ),
        # 5. Corrupt Excel file
        (
            "Corrupt XLSX (Invalid zip binary)",
            "corrupt.xlsx",
            b"NOT_A_VALID_EXCEL_OR_ZIP_FILE_DATA",
            422,
            "corrupt"
        ),
        # 6. Corrupt Image file
        (
            "Corrupt PNG (Invalid image header)",
            "corrupt.png",
            b"NOT_A_PNG_IMAGE_DATA_CORRUPT",
            422,
            "corrupt"
        )
    ]
    
    all_passed = True
    for name, filename, content, exp_status, exp_detail in tests:
        passed = await test_scenario(name, filename, content, exp_status, exp_detail)
        if not passed:
            all_passed = False
            
    print("\n==================================================")
    if all_passed:
        print("[SUCCESS] All error handling test scenarios PASSED!")
    else:
        print("[FAILURE] Some error handling scenarios failed.")


if __name__ == "__main__":
    asyncio.run(main())
