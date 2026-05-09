"""
FastAPI endpoints for PDF parsing with job-based async processing
"""

import os
import json
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import hashlib

from pdf_parser_service import parse_loan_application, convert_to_frontend_format

app = FastAPI(title="LoanSizer PDF Parser API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (use Redis in production)
job_store = {}

# Redis connection (optional - for production)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()
    USE_REDIS = True
except:
    USE_REDIS = False
    redis_client = None


class ParseJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ParseStatusResponse(BaseModel):
    job_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: int  # 0-100
    result: Optional[dict] = None
    errors: list = []


class ParseResult(BaseModel):
    job_id: str
    status: str
    filename: str
    ocr_used: bool
    lender_detected: Optional[str]
    parsing_time_ms: int
    fields: dict
    errors: list


def get_cache_key(file_content: bytes) -> str:
    """Generate cache key from file content"""
    return hashlib.md5(file_content).hexdigest()


def store_job(job_id: str, data: dict):
    """Store job data"""
    if USE_REDIS and redis_client:
        redis_client.setex(
            f"parse_job:{job_id}",
            timedelta(hours=1),
            json.dumps(data, default=str)
        )
    else:
        job_store[job_id] = data


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve job data"""
    if USE_REDIS and redis_client:
        data = redis_client.get(f"parse_job:{job_id}")
        if data:
            return json.loads(data)
        return None
    else:
        return job_store.get(job_id)


async def process_pdf_async(job_id: str, file_path: str, filename: str):
    """Background task to process PDF"""
    try:
        # Update status to processing
        store_job(job_id, {
            "status": "processing",
            "progress": 10,
            "filename": filename,
            "started_at": datetime.now().isoformat()
        })
        
        # Run parsing
        store_job(job_id, {
            "status": "processing",
            "progress": 50,
            "filename": filename,
        })
        
        result = parse_loan_application(file_path, filename)
        
        # Convert to frontend format
        frontend_data = convert_to_frontend_format(result)
        
        # Store result
        store_job(job_id, {
            "status": result.status,
            "progress": 100,
            "filename": filename,
            "result": frontend_data,
            "errors": result.errors,
            "completed_at": datetime.now().isoformat()
        })
        
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        store_job(job_id, {
            "status": "failed",
            "progress": 0,
            "filename": filename,
            "errors": [str(e)],
            "failed_at": datetime.now().isoformat()
        })
        
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/api/v1/parse", response_model=ParseJobResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a PDF for parsing. Returns a job ID to poll for results.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate job ID
    job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}"
    
    # Read file content
    content = await file.read()
    
    # Check cache
    cache_key = get_cache_key(content)
    if USE_REDIS and redis_client:
        cached = redis_client.get(f"parse_cache:{cache_key}")
        if cached:
            cached_data = json.loads(cached)
            return ParseJobResponse(
                job_id=cached_data.get("job_id", job_id),
                status="completed",
                message="Retrieved from cache"
            )
    
    # Save to temp file
    temp_dir = "/tmp/loan_sizer_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{job_id}.pdf")
    
    with open(temp_path, "wb") as f:
        f.write(content)
    
    # Store initial job status
    store_job(job_id, {
        "status": "pending",
        "progress": 0,
        "filename": file.filename,
        "uploaded_at": datetime.now().isoformat()
    })
    
    # Start background processing
    background_tasks.add_task(
        process_pdf_async,
        job_id,
        temp_path,
        file.filename
    )
    
    return ParseJobResponse(
        job_id=job_id,
        status="pending",
        message="PDF upload successful, processing started"
    )


@app.get("/api/v1/parse/{job_id}/status", response_model=ParseStatusResponse)
async def get_parse_status(job_id: str):
    """
    Get the status of a parsing job
    """
    job_data = get_job(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return ParseStatusResponse(
        job_id=job_id,
        status=job_data.get("status", "unknown"),
        progress=job_data.get("progress", 0),
        result=job_data.get("result"),
        errors=job_data.get("errors", [])
    )


@app.get("/api/v1/parse/{job_id}/result", response_model=ParseResult)
async def get_parse_result(job_id: str):
    """
    Get the final parsing result
    """
    job_data = get_job(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Parsing not yet complete")
    
    result = job_data.get("result", {})
    
    return ParseResult(
        job_id=job_id,
        status=job_data.get("status"),
        filename=job_data.get("filename", ""),
        ocr_used=result.get("ocr_used", False),
        lender_detected=result.get("lender_detected"),
        parsing_time_ms=result.get("parsing_time_ms", 0),
        fields={k: v for k, v in result.items() if not k.endswith('_confidence') and k not in ['job_id', 'status', 'filename', 'ocr_used', 'lender_detected', 'parsing_time_ms', 'errors']},
        errors=job_data.get("errors", [])
    )


@app.delete("/api/v1/parse/{job_id}")
async def delete_parse_job(job_id: str):
    """
    Delete a parsing job
    """
    if USE_REDIS and redis_client:
        redis_client.delete(f"parse_job:{job_id}")
    else:
        job_store.pop(job_id, None)
    
    return {"message": "Job deleted"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "redis": USE_REDIS,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/demo/parse-pdf")
async def demo_parse_pdf(file: UploadFile = File(...)):
    """
    Synchronous demo endpoint for parsing PDF without authentication
    Returns results immediately (no polling required)
    """
    from fastapi.responses import JSONResponse
    import tempfile
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Parse synchronously
            result = parse_loan_application(tmp_path, file.filename)
            
            if result.status == "completed":
                # Convert to frontend format
                frontend_data = convert_to_frontend_format(result)
                return JSONResponse(content={
                    "success": True,
                    "fields": frontend_data,
                    "filename": file.filename,
                    "ocr_used": result.fields.get("ocr_used", False),
                    "lender_detected": result.fields.get("lender_detected"),
                    "parsing_time_ms": result.fields.get("parsing_time_ms", 0)
                })
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "Failed to parse PDF",
                        "errors": result.errors
                    }
                )
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)