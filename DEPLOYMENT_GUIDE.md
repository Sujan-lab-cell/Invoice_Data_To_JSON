# Deployment & AyusLab API Integration Guide

This guide provides step-by-step instructions for hosting the **Invoice Data Extraction API** on **Render** (or any Docker container platform) and connecting it to AyusLab.

---

## 1. Hosting Architecture Overview

```
AyusLab Web / App
       │
       ▼
AyusLab Backend (Node.js / Java / Python / PHP)
       │
       ▼  (HTTPS POST multipart/form-data + Bearer Token)
Render Web Service (FastAPI / Uvicorn in Docker Container)
       │
       ▼  (JSON Response)
AyusLab Purchase Module (Creates Draft Purchase Entry)
```

> **Note**: Only the FastAPI backend container is hosted. AyusLab interacts with our service exclusively via REST API calls.

---

## 2. Deploying to Render in 5 Minutes

### Step 1: Push Code to GitHub / GitLab
Ensure the latest code (including `Dockerfile` and `render.yaml`) is pushed to your Git repository:
```bash
git add .
git commit -m "Add production Dockerfile and Render deployment blueprint"
git push origin main
```

### Step 2: Create Web Service on Render
1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your Git repository.
4. Select **Docker** as the Runtime environment (Render will automatically detect the root `Dockerfile`).
5. Choose your region (e.g., `Oregon (US West)` or `Singapore`).
6. Select your instance tier (e.g., **Starter** or higher for OCR memory).

### Step 3: Configure Environment Variables
In the Render Service **Environment** tab, set the following variables:

| Variable Name | Required | Recommended Value / Description |
|---|---|---|
| `API_BEARER_TOKEN` | **YES** | A strong secret token (e.g. generate via `openssl rand -hex 32`). This is the key AyusLab will send in their headers. |
| `GEMINI_API_KEY` | Optional | Your Google Gemini API Key for AI fallback extraction. |
| `PORT` | Auto | `8000` (Render binds this automatically). |
| `MAX_UPLOAD_SIZE_MB` | Optional | `25` |
| `LOG_LEVEL` | Optional | `INFO` |
| `OCR_GPU` | Optional | `false` |
| `CORS_ORIGINS` | Optional | `https://app.ayuslab.com,http://localhost:3000` |

### Step 4: Deploy
Click **Create Web Service**. Render will build the container, install system dependencies (`poppler-utils`, `libglib`), pre-cache OCR models, and launch Uvicorn.

Your live API will be available at:
```text
https://<your-service-name>.onrender.com
```

---

## 3. Verifying Your Live API

### Health Check (No Auth Required)
```bash
curl -X GET https://<your-service-name>.onrender.com/health
```
**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Invoice Data to JSON API"
}
```

### Interactive API Documentation
Visit the interactive Swagger UI in your browser:
```text
https://<your-service-name>.onrender.com/docs
```

---

## 4. How AyusLab Calls the API

### Endpoint Details
- **URL**: `POST https://<your-service-name>.onrender.com/api/v1/invoices/parse`
- **Authentication**: `Authorization: Bearer <API_BEARER_TOKEN>`
- **Content-Type**: `multipart/form-data`
- **Body Field Name**: `file`

### cURL Example for Testing
```bash
curl -X POST "https://<your-service-name>.onrender.com/api/v1/invoices/parse" \
  -H "Authorization: Bearer <YOUR_API_BEARER_TOKEN>" \
  -F "file=@sample_invoice.pdf"
```

### Python Integration Example (for AyusLab Backend)
```python
import requests

API_URL = "https://<your-service-name>.onrender.com/api/v1/invoices/parse"
BEARER_TOKEN = "<YOUR_API_BEARER_TOKEN>"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

with open("invoice.pdf", "rb") as f:
    files = {"file": ("invoice.pdf", f, "application/pdf")}
    response = requests.post(API_URL, headers=headers, files=files)

invoice_data = response.json()
print("Extracted Invoice:", invoice_data["invoice_data"]["invoice_number"])
```

### Node.js Integration Example (for AyusLab Backend)
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function parseInvoice() {
  const form = new FormData();
  form.append('file', fs.createReadStream('invoice.pdf'));

  const response = await axios.post('https://<your-service-name>.onrender.com/api/v1/invoices/parse', form, {
    headers: {
      ...form.getHeaders(),
      'Authorization': 'Bearer <YOUR_API_BEARER_TOKEN>'
    }
  });

  console.log('Parsed Invoice Items:', response.data.invoice_data.items);
}
```

---

## 5. Information to Hand Over to AyusLab (Vishnu & Olivia)

Once deployed, provide AyusLab with:
1. **API Base URL**: `https://<your-service-name>.onrender.com`
2. **Endpoint**: `POST /api/v1/invoices/parse`
3. **Their Bearer Token**: `<YOUR_API_BEARER_TOKEN>`
4. **API Documentation Link**: `https://<your-service-name>.onrender.com/docs`
