import sys
from pathlib import Path

# Add backend folder to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.main import app


def test_openapi_schema():
    print("==================================================")
    print("TESTING FASTAPI OPENAPI / SWAGGER DOCUMENTATION")
    print("==================================================")

    schema = app.openapi()
    assert schema is not None, "Failed to generate OpenAPI schema"

    # 1. Verify API metadata
    print("\n1. Verifying API Metadata...")
    assert schema["info"]["title"] == "Invoice Data to JSON API"
    assert schema["info"]["version"] == "1.0.0"
    assert "Pharmacy Invoice Data Extraction API" in schema["info"]["description"]
    assert "Multi-Format Ingestion" in schema["info"]["description"]
    assert "Bearer" in schema["info"]["description"]
    print("PASSED: API title, version, and overview description verified.")

    # 2. Verify OpenAPI Tags
    print("\n2. Verifying OpenAPI Tags...")
    tag_names = [t["name"] for t in schema.get("tags", [])]
    assert "Invoices" in tag_names, "Tag 'Invoices' missing in OpenAPI tags"
    assert "Health" in tag_names, "Tag 'Health' missing in OpenAPI tags"
    print(f"PASSED: OpenAPI tags verified -> {tag_names}")

    # 3. Verify GET /health endpoint documentation
    print("\n3. Verifying GET /health Documentation...")
    paths = schema["paths"]
    assert "/health" in paths, "Endpoint /health missing from OpenAPI paths"
    health_op = paths["/health"]["get"]
    assert health_op["summary"] == "Check API health status"
    assert "Health" in health_op["tags"]
    assert "200" in health_op["responses"]
    health_200 = health_op["responses"]["200"]
    assert "HealthResponse" in str(health_200) or "status" in str(health_200)
    print("PASSED: GET /health documentation verified.")

    # 4. Verify POST /api/v1/invoices/parse endpoint documentation
    print("\n4. Verifying POST /api/v1/invoices/parse Documentation...")
    assert "/api/v1/invoices/parse" in paths, "Endpoint /api/v1/invoices/parse missing from OpenAPI paths"
    parse_op = paths["/api/v1/invoices/parse"]["post"]
    assert parse_op["summary"] == "Parse and extract structured data from an invoice file"
    assert "Invoices" in parse_op["tags"]

    desc = parse_op["description"]
    # Check documented supported formats
    for ext in [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".csv", ".xls", ".xlsx"]:
        assert ext in desc, f"Extension {ext} not mentioned in /parse description"
    print("PASSED: All 9 supported file formats documented in /parse description.")

    # Check documented security
    assert "Bearer" in desc, "Bearer authentication not mentioned in /parse description"

    # Check responses documented
    responses = parse_op["responses"]
    for code in ["200", "400", "401", "422", "500"]:
        assert code in responses, f"Response code {code} missing in /parse responses"
    print("PASSED: All response status codes (200, 400, 401, 422, 500) documented.")

    # Check request body / file upload documentation
    request_body = parse_op.get("requestBody", {})
    assert "multipart/form-data" in request_body.get("content", {})
    form_schema = request_body["content"]["multipart/form-data"]["schema"]
    if "$ref" in form_schema:
        ref_name = form_schema["$ref"].split("/")[-1]
        form_props = schema["components"]["schemas"][ref_name]["properties"]
    else:
        form_props = form_schema.get("properties", {})
    assert "file" in form_props
    assert "description" in form_props["file"]
    print("PASSED: Request body multipart/form-data file parameter documented.")

    # 5. Verify Bearer Security Scheme in components
    print("\n5. Verifying Bearer Authentication Security Scheme...")
    components = schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    assert "BearerAuth" in security_schemes or "HTTPBearer" in security_schemes, "Bearer security scheme missing in components"
    print(f"PASSED: Security scheme registered -> {list(security_schemes.keys())}")

    # 6. Verify Response Schemas in components
    schemas = components.get("schemas", {})
    assert "Document" in schemas, "Document schema missing in OpenAPI components"
    assert "HealthResponse" in schemas, "HealthResponse schema missing in OpenAPI components"
    assert "ErrorResponse" in schemas, "ErrorResponse schema missing in OpenAPI components"
    print(f"PASSED: Core schemas registered (Document, HealthResponse, ErrorResponse).")

    print("\n==================================================")
    print("[SUCCESS] All OpenAPI/Swagger documentation tests PASSED!")
    print("==================================================")
    return True


if __name__ == "__main__":
    test_openapi_schema()
