import asyncio
import io
import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import HTTPException, UploadFile
from app.api.v1.endpoints.invoices import parse_invoice, SUPPORTED_EXTENSIONS


async def test_invalid_extension(filename: str):
    file_obj = io.BytesIO(b"dummy data")
    upload = UploadFile(filename=filename, file=file_obj)
    try:
        await parse_invoice(file=upload)
        print(f"FAILED: Expected HTTP 400 for '{filename}' but request succeeded.")
        return False
    except HTTPException as e:
        if e.status_code == 400:
            print(f"PASSED: '{filename}' -> HTTP 400: {e.detail}")
            return True
        else:
            print(f"FAILED: '{filename}' -> Unexpected status code: {e.status_code}")
            return False
    except Exception as e:
        print(f"FAILED: '{filename}' -> Unexpected exception: {type(e).__name__}: {e}")
        return False


async def main():
    print("==================================================")
    print("Testing Unsupported File Types (Expect HTTP 400)")
    print("==================================================")
    
    invalid_files = [
        "invoice.txt",
        "document.docx",
        "script.py",
        "data.json",
        "archive.zip",
        "executable.exe",
        "no_extension"
    ]
    
    all_passed = True
    for fname in invalid_files:
        passed = await test_invalid_extension(fname)
        if not passed:
            all_passed = False
            
    print("\n==================================================")
    print("Supported Extensions Configured:")
    print("==================================================")
    print(sorted(list(SUPPORTED_EXTENSIONS)))
    
    if all_passed:
        print("\n[SUCCESS] All extension validation tests passed!")
    else:
        print("\n[FAILURE] Some extension validation tests failed.")


if __name__ == "__main__":
    asyncio.run(main())
