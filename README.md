# Invoice Data to JSON - Backend Workflow

## Overview

This project extracts structured information from pharmaceutical purchase invoices in **PDF, Image, Excel, and CSV** formats and converts them into a standardized JSON schema for inventory management.

The extraction pipeline combines:

- Rule-Based Information Extraction
- Lightweight NLP Preprocessing
- OCR (EasyOCR)
- Gemini AI Fallback
- Validation Layer
- Structured JSON Generation

---

# Complete Workflow

```text
                ┌─────────────────────────────┐
                │     Invoice Upload          │
                │ PDF / Image / Excel / CSV   │
                └──────────────┬──────────────┘
                               │
                               ▼
                   ┌─────────────────────┐
                   │    Parser Service   │
                   └─────────┬───────────┘
                             │
          ┌──────────────────┴───────────────────┐
          │                                      │
          ▼                                      ▼
 ┌───────────────────┐                 ┌────────────────────┐
 │ Excel / CSV Parser│                 │ OCR (EasyOCR)      │
 │ (Pandas)          │                 │ PDF / Images        │
 └─────────┬─────────┘                 └─────────┬──────────┘
           │                                     │
           └───────────────┬─────────────────────┘
                           ▼
              ┌────────────────────────┐
              │ NLP Preprocessing      │
              │ • Text Cleaning        │
              │ • Line Normalization   │
              │ • Whitespace Cleanup   │
              │ • OCR Correction       │
              │ • Punctuation Cleanup  │
              └─────────────┬──────────┘
                            ▼
             ┌──────────────────────────┐
             │ Rule-Based Extraction    │
             │ (Regex + Header + Items) │
             └─────────────┬────────────┘
                           ▼
         ┌──────────────────────────────────┐
         │ Structured Invoice Object        │
         └───────────────┬──────────────────┘
                         ▼
          ┌────────────────────────────────┐
          │ Validation Layer               │
          │ • Required Fields              │
          │ • Math Verification            │
          │ • Totals Consistency           │
          └──────────────┬─────────────────┘
                         ▼
       ┌─────────────────────────────────────┐
       │ Missing Critical Fields ?           │
       └──────────────┬──────────────────────┘
                      │
         ┌────────────┴─────────────┐
         │                          │
         ▼                          ▼
      NO Missing              YES Missing
         │                          │
         │                          ▼
         │               ┌────────────────────┐
         │               │ Gemini AI Fallback │
         │               └─────────┬──────────┘
         │                         │
         └──────────────┬──────────┘
                        ▼
          ┌────────────────────────────┐
          │ Merge Rule + AI Extraction │
          └─────────────┬──────────────┘
                        ▼
          ┌────────────────────────────┐
          │ Pydantic Schema Validation │
          └─────────────┬──────────────┘
                        ▼
         ┌──────────────────────────────┐
         │ Structured JSON Output        │
         └─────────────┬────────────────┘
                       ▼
          outputs/<invoice_name>.json
```

---
## Running the Project

Navigate to the backend directory:

```bash
cd backend
```

### Run Parser Service

```bash
python -m tests.test_parser_service
```

### Run Rule-Based Extractor

```bash
python -m tests.test_invoice_extractor
```

### Run Hybrid Extractor

```bash
python -m tests.test_hybrid_extractor
```

### Run Inventory Matcher

```bash
python -m tests.test_inventory_matcher
```
# NLP Preprocessing Pipeline

The project uses a lightweight offline NLP preprocessing layer before extraction.

### Operations

- Text Cleaning
- Line Break Normalization
- Whitespace Normalization
- Punctuation Normalization
- Dictionary-Based OCR Error Correction
- Case Normalization (Matching Only)
- Rule-Based Pattern Matching (Regex)

> Stemming and Lemmatization are intentionally **not used** because they may alter medicine names, invoice numbers, product codes, and batch numbers.

---

# Rule-Based Extraction

The rule engine extracts:

## Invoice Header

- Invoice Number
- Invoice Date
- Due Date
- Supplier Details
- Buyer Details
- GSTIN
- Payment Type
- State

## Line Items

- Product Name
- Product Code
- Batch Number
- Expiry Date
- Quantity
- Free Quantity
- PTR
- Purchase Rate
- MRP
- Discount
- GST
- Taxable Amount
- Net Amount

## Totals

- Subtotal
- Discount Total
- Tax Total
- Grand Total

---

# Validation

The validation layer verifies:

- Required Header Fields
- Required Line Item Fields
- Invoice Total Consistency
- Tax Calculation
- Mathematical Verification
- Human Review Requirement

---

# AI Fallback

Gemini AI is **not executed for every invoice**.

It is called only when:

- Invoice Number is missing
- Invoice Date is missing
- Buyer Information is missing
- Critical pricing information is missing

Otherwise, the entire extraction is completed locally.

---

# JSON Output

The final output contains:

- Document Metadata
- Invoice Information
- Supplier Details
- Buyer Details
- Line Items
- Pricing
- Tax Information
- Totals
- Validation
- Review Status
- Raw Extraction Information

The JSON is generated using **Pydantic v2** and saved as:

```

outputs/<invoice_name>.json

```

---

# Current Architecture

```

backend/
│
├── app/
│ ├── ai/
│ ├── extraction/
│ ├── inventory/
│ ├── ocr/
│ ├── parsers/
│ ├── schemas/
│ ├── services/
│ ├── utils/
│ └── core/
│
├── outputs/
├── tests/
│ └── sample_invoices/
│
└── requirements.txt

```

---

# Technologies Used

- Python
- FastAPI (Backend)
- EasyOCR
- Pandas
- Pydantic v2
- OpenCV
- RapidFuzz (Future Inventory Matching)
- Google Gemini API
- Regular Expressions (Regex)

---

# Features that are left

- Inventory Master Integration
- Product Mapping (Exact & Fuzzy)
- Purchase Entry API Integration
- FastAPI REST Endpoints
- Frontend Review Dashboard
- Automated Inventory Updates