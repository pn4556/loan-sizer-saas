"""
Fixed Public API Endpoint for File Parsing
No authentication required, supports all file types
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from universal_parser import get_parser, ParseResult
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Loan Sizer File Parser", version="2.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/parse")
async def parse_file_public(file: UploadFile = File(...)):
    """
    Public endpoint for parsing loan application files
    Supports: PDF, CSV, Excel, TXT, Images
    """
    try:
        logger.info(f"Received file: {file.filename}, content-type: {file.content_type}")
        
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        # Parse file
        parser = get_parser()
        result = await parser.parse(content, file.filename)
        
        if result.success:
            return {
                "success": True,
                "file_type": result.file_type,
                "filename": file.filename,
                "extracted_data": result.structured_data,
                "confidence": result.confidence,
                "ocr_used": result.ocr_used,
                "text_preview": result.text[:500] if result.text else None
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
                "file_type": result.file_type,
                "filename": file.filename
            }
            
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Loan Sizer Parser",
        "version": "2.0.0",
        "supported_types": ["pdf", "csv", "excel", "text", "image"]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
