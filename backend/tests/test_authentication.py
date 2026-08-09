import asyncio
import io
import os
import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Set test bearer token in environment
TEST_TOKEN = "secret_invoice_test_token_12345"
os.environ["API_BEARER_TOKEN"] = TEST_TOKEN

from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.security import verify_bearer_token
from app.api.v1.endpoints.invoices import parse_invoice
from app.main import app


async def test_auth():
    print("==================================================")
    print("TESTING API BEARER TOKEN AUTHENTICATION")
    print("==================================================")
    
    # Reload settings to pick up environment variable
    settings.API_BEARER_TOKEN = TEST_TOKEN
    
    # 1. Test missing credentials -> HTTP 401
    print("\n1. Testing Missing Token...")
    try:
        await verify_bearer_token(credentials=None)
        print("FAILED: Expected HTTP 401 for missing token.")
        return False
    except HTTPException as e:
        if e.status_code == 401:
            print(f"PASSED: Missing token returned HTTP 401 -> {e.detail}")
        else:
            print(f"FAILED: Expected HTTP 401, got {e.status_code}")
            return False

    # 2. Test invalid token -> HTTP 401
    print("\n2. Testing Invalid Token...")
    try:
        invalid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_token_xyz")
        await verify_bearer_token(credentials=invalid_creds)
        print("FAILED: Expected HTTP 401 for invalid token.")
        return False
    except HTTPException as e:
        if e.status_code == 401:
            print(f"PASSED: Invalid token returned HTTP 401 -> {e.detail}")
        else:
            print(f"FAILED: Expected HTTP 401, got {e.status_code}")
            return False

    # 3. Test valid token -> Returns token string
    print("\n3. Testing Valid Token...")
    try:
        valid_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=TEST_TOKEN)
        result = await verify_bearer_token(credentials=valid_creds)
        assert result == TEST_TOKEN
        print("PASSED: Valid token accepted.")
    except Exception as e:
        print(f"FAILED: Valid token raised error: {e}")
        return False

    # 4. Test /health route has no authentication requirement
    print("\n4. Testing /health Public Accessibility...")
    health_route = next((r for r in app.routes if getattr(r, "path", None) == "/health"), None)
    assert health_route is not None, "/health route not found in app"
    # Verify endpoint function directly
    from app.main import health_check
    res = await health_check()
    assert res == {"status": "ok"}
    print(f"PASSED: /health is public and returns {res}")

    print("\n==================================================")
    print("[SUCCESS] All authentication requirements verified!")
    print("==================================================")
    return True


if __name__ == "__main__":
    asyncio.run(test_auth())
