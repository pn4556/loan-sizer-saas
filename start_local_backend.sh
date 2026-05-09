#!/bin/bash
# Start Loan Sizer Backend Locally
# This runs the PDF API server on your local machine

cd "$(dirname "$0")/backend"

echo "🚀 Starting Loan Sizer Backend..."
echo "================================"
echo ""
echo "API will be available at:"
echo "  http://localhost:8000/api/v1/health"
echo "  http://localhost:8000/api/v1/demo/parse-pdf"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the server
uvicorn pdf_api:app --host 0.0.0.0 --port 8000 --reload
