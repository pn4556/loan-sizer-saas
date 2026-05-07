# LoanSizer PDF Parser Service

Production-grade PDF parsing for loan applications with OCR fallback.

## Architecture

```
PDF Upload
   ↓
Detect PDF Type (text/image/mixed)
   ↓
Text PDF? → PyMuPDF extraction
   ↓ No
OCR Pipeline → pdf2image + Tesseract
   ↓
Text Normalization
   ↓
Lender Detection (JotForm, Bridge Capital, etc.)
   ↓
Template-Based Extraction
   ↓
Confidence Scoring
   ↓
Structured JSON Response
```

## Deploy to Render

### 1. Create New Web Service

- Go to https://dashboard.render.com
- Click "New +" → "Web Service"
- Connect your GitHub repo

### 2. Configuration

- **Name**: `loan-sizer-parser`
- **Root Directory**: `backend`
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn pdf_api:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables (if using Redis)

```
REDIS_URL=redis://default:password@host:port
```

### 4. Deploy

Click "Create Web Service"

## API Endpoints

### Upload PDF
```bash
POST /api/v1/parse
Content-Type: multipart/form-data

file: <PDF file>
```

Response:
```json
{
  "job_id": "job_20240115...",
  "status": "pending",
  "message": "PDF upload successful, processing started"
}
```

### Check Status
```bash
GET /api/v1/parse/{job_id}/status
```

Response:
```json
{
  "job_id": "job_20240115...",
  "status": "completed",
  "progress": 100,
  "result": {...},
  "errors": []
}
```

### Get Result
```bash
GET /api/v1/parse/{job_id}/result
```

Response:
```json
{
  "job_id": "...",
  "status": "completed",
  "filename": "loan.pdf",
  "ocr_used": false,
  "lender_detected": "jotform",
  "parsing_time_ms": 450,
  "fields": {
    "purchase_price": 260000,
    "as_is_value": 269000,
    "arv": 405000,
    ...
  },
  "errors": []
}
```

## Supported Lenders

- **JotForm**: Bridge Loan Application forms
- **Bridge Capital**: Bridge Capital Partners forms
- **Eastview**: Eastview Funding forms
- **Generic**: Fallback for unknown lenders

## OCR Capabilities

- Scanned PDFs
- Image-based PDFs
- Mixed content PDFs
- Handwritten text (limited)
- Multi-page documents

## Confidence Scoring

Each extracted field includes confidence score:

- `0.9+`: High confidence (exact regex match)
- `0.7-0.9`: Medium confidence (fuzzy match)
- `< 0.7`: Low confidence (manual review recommended)

## Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install tesseract poppler

# Run server
uvicorn pdf_api:app --reload
```

## Testing

```bash
# Upload PDF
curl -X POST -F "file=@loan.pdf" http://localhost:8000/api/v1/parse

# Check status
curl http://localhost:8000/api/v1/parse/{job_id}/status

# Get result
curl http://localhost:8000/api/v1/parse/{job_id}/result
```