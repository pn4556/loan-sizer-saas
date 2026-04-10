"""
Loan Sizer SaaS API - Enhanced Version
Multi-tenant API with authentication, universal file parsing, and Excel export
"""

import os
import json
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

# Import our modules
from database import get_db, init_database
from models import (
    Client, User, ExcelTemplate, LoanApplication, 
    ApiKey, AuditLog
)
from auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_current_user, require_admin, register_client,
    get_password_hash, verify_password
)
from processor_custom import SizerProcessor, LoanApplication as LoanAppModel
from file_parser import UniversalFileParser, parse_loan_file

# Initialize app
app = FastAPI(
    title="Loan Sizer SaaS Platform - Enhanced",
    version="2.1.0",
    description="Multi-tenant loan processing with universal file support and Excel export"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR = UPLOAD_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
FILES_DIR = UPLOAD_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR = UPLOAD_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# Initialize file parser
file_parser = UniversalFileParser()

# Startup event
@app.on_event("startup")
async def startup_event():
    print("🚀 Loan Sizer API Enhanced starting up...")
    print(f"📍 Supported formats: {', '.join(file_parser.get_supported_formats())}")
    print(f"📍 API docs: /docs")

# ==================== ROOT ROUTE ====================

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "service": "Loan Sizer SaaS Platform - Enhanced",
        "version": "2.1.0",
        "status": "running",
        "features": [
            "universal_file_parsing",
            "excel_export",
            "real_dashboard_metrics",
            "ocr_support"
        ],
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "loan-sizer-api-enhanced",
        "version": "2.1.0"
    }

# ==================== DASHBOARD ROUTES ====================

@app.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get real dashboard statistics for the organization"""
    
    client_id = current_user.client_id
    
    # Total applications
    total_apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == client_id
    ).count()
    
    # This month's applications
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == client_id,
        LoanApplication.created_at >= month_start
    ).count()
    
    # Last month's applications (for comparison)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == client_id,
        LoanApplication.created_at >= last_month_start,
        LoanApplication.created_at < month_start
    ).count()
    
    # Decision breakdown
    decisions = db.query(LoanApplication.overall_decision, 
                        func.count(LoanApplication.id)).filter(
        LoanApplication.client_id == client_id
    ).group_by(LoanApplication.overall_decision).all()
    
    decision_counts = {d[0] or "pending": d[1] for d in decisions}
    approved_count = decision_counts.get("APPROVE", 0) + decision_counts.get("approve", 0)
    rejected_count = decision_counts.get("REJECT", 0) + decision_counts.get("reject", 0)
    pending_count = decision_counts.get("REVIEW", 0) + decision_counts.get("review", 0) + decision_counts.get("pending", 0)
    
    # Average processing time
    avg_time = db.query(func.avg(LoanApplication.processing_time_seconds)).filter(
        LoanApplication.client_id == client_id,
        LoanApplication.processing_time_seconds != None
    ).scalar()
    
    # Time saved calculation (23 min saved per app vs manual)
    time_saved_minutes = total_apps * 23
    time_saved_hours = round(time_saved_minutes / 60, 1)
    
    # Calculate month-over-month change
    month_change = 0
    if last_month_apps > 0:
        month_change = round(((month_apps - last_month_apps) / last_month_apps) * 100)
    elif month_apps > 0:
        month_change = 100
    
    return {
        "total_applications": total_apps,
        "this_month": month_apps,
        "last_month": last_month_apps,
        "month_change_percent": month_change,
        "decisions": decision_counts,
        "approved": approved_count,
        "rejected": rejected_count,
        "pending_review": pending_count,
        "average_processing_time": round(avg_time, 2) if avg_time else 0,
        "time_saved_minutes": time_saved_minutes,
        "time_saved_hours": time_saved_hours,
        "efficiency_gain": 93  # Percentage
    }


@app.get("/dashboard/activity")
async def get_recent_activity(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent activity for the dashboard"""
    
    client_id = current_user.client_id
    
    apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == client_id
    ).order_by(LoanApplication.created_at.desc()).limit(limit).all()
    
    activities = []
    for app in apps:
        # Determine icon and status based on decision
        if app.overall_decision == "APPROVE":
            icon = "success"
            title = "Application Approved"
        elif app.overall_decision == "REJECT":
            icon = "error"
            title = "Application Rejected"
        elif app.status == "processing":
            icon = "pending"
            title = "Processing Started"
        else:
            icon = "pending"
            title = "Under Review"
        
        # Format time ago
        time_diff = datetime.utcnow() - app.created_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} min ago"
        else:
            time_ago = "Just now"
        
        activities.append({
            "id": app.id,
            "icon": icon,
            "title": title,
            "meta": f"{app.program_type or 'Loan'} • ${app.loan_amount:,.0f}" if app.loan_amount else f"{app.program_type or 'Loan'}",
            "time": time_ago,
            "timestamp": app.created_at.isoformat()
        })
    
    return {"activities": activities}


@app.get("/applications")
async def list_applications(
    status: Optional[str] = None,
    decision: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List applications for the organization"""
    
    query = db.query(LoanApplication).filter(
        LoanApplication.client_id == current_user.client_id
    )
    
    if status:
        query = query.filter(LoanApplication.status == status)
    
    if decision:
        query = query.filter(LoanApplication.overall_decision == decision)
    
    total = query.count()
    apps = query.order_by(LoanApplication.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "applications": [{
            "id": a.id,
            "applicant_email": a.applicant_email,
            "property_address": a.property_address,
            "property_city": a.property_city,
            "property_state": a.property_state,
            "loan_amount": a.loan_amount,
            "estimated_value": a.estimated_value,
            "ltv_ratio": round((a.loan_amount / a.estimated_value * 100), 2) if a.estimated_value else None,
            "credit_score_middle": a.credit_score_middle,
            "decision": a.overall_decision,
            "status": a.status,
            "processing_time": a.processing_time_seconds,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "processed_by": a.processed_by.full_name if a.processed_by else None,
            "programs_results": a.programs_results
        } for a in apps]
    }


@app.get("/applications/{application_id}")
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single application details"""
    
    app = db.query(LoanApplication).filter(
        LoanApplication.id == application_id,
        LoanApplication.client_id == current_user.client_id
    ).first()
    
    if not app:
        raise HTTPException(404, "Application not found")
    
    return {
        "id": app.id,
        "applicant_email": app.applicant_email,
        "property_address": app.property_address,
        "property_city": app.property_city,
        "property_state": app.property_state,
        "property_zip": app.property_zip,
        "units": app.units,
        "loan_amount": app.loan_amount,
        "estimated_value": app.estimated_value,
        "purchase_price": app.purchase_price,
        "note_type": app.note_type,
        "points_to_lender": app.points_to_lender,
        "credit_score_1": app.credit_score_1,
        "credit_score_2": app.credit_score_2,
        "credit_score_3": app.credit_score_3,
        "credit_score_middle": app.credit_score_middle,
        "ltv_ratio": app.ltv_ratio,
        "interest_rate": app.interest_rate,
        "decision": app.overall_decision,
        "decision_reason": app.decision_reason,
        "status": app.status,
        "programs_results": app.programs_results,
        "officer_notes": app.officer_notes,
        "processing_time": app.processing_time_seconds,
        "output_excel_path": app.output_excel_path,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "extraction_confidence": app.extraction_confidence
    }


# ==================== FILE PROCESSING ROUTES ====================

@app.post("/applications/process-file")
async def process_application_file(
    interest_rate: float = Form(...),
    applicant_email: str = Form(...),
    file: UploadFile = File(...),
    template_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process loan application from ANY supported file format
    Supports: PDF, DOCX, TXT, EML, MSG, PNG, JPG, TIFF, CSV, XLSX, XLS
    """
    
    # Get template
    if template_id:
        template = db.query(ExcelTemplate).filter(
            ExcelTemplate.id == template_id,
            ExcelTemplate.client_id == current_user.client_id
        ).first()
    else:
        template = db.query(ExcelTemplate).filter(
            ExcelTemplate.client_id == current_user.client_id,
            ExcelTemplate.is_default == True
        ).first()
    
    if not template:
        raise HTTPException(400, "No Excel template available. Please upload a template first.")
    
    # Save file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_ext = Path(file.filename).suffix
    saved_filename = f"{current_user.client_id}_{timestamp}_{file.filename}"
    file_path = FILES_DIR / saved_filename
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create application record
    app_record = LoanApplication(
        client_id=current_user.client_id,
        template_id=template.id,
        processed_by_id=current_user.id,
        source_type="file",
        source_pdf_path=str(file_path),
        applicant_email=applicant_email,
        interest_rate=interest_rate,
        status="processing"
    )
    db.add(app_record)
    db.commit()
    
    try:
        # Parse file using universal parser
        parse_result = file_parser.parse_file(content, file.filename)
        
        if not parse_result.success:
            app_record.status = "review"
            app_record.officer_notes = f"File parsing failed: {parse_result.error_message}"
            db.commit()
            raise HTTPException(400, f"Could not parse file: {parse_result.error_message}")
        
        # Get extracted fields
        extracted = parse_result.fields.copy()
        
        # Add default values for missing required fields
        if 'estimated_value' not in extracted and 'purchase_price' in extracted:
            extracted['estimated_value'] = extracted['purchase_price']
        
        if 'purchase_price' not in extracted and 'estimated_value' in extracted:
            extracted['purchase_price'] = extracted['estimated_value']
        
        if 'note_type' not in extracted:
            extracted['note_type'] = '30 Year Fixed'
        
        if 'points_to_lender' not in extracted:
            extracted['points_to_lender'] = 0.0
        
        # Validate extraction
        required = ['units', 'address', 'city', 'state', 'zip',
                   'estimated_value', 'purchase_price', 'loan_amount',
                   'credit_score_1', 'credit_score_2', 'credit_score_3']
        missing = [f for f in required if f not in extracted]
        
        # Update record
        app_record.extraction_method = parse_result.file_type
        app_record.extraction_confidence = parse_result.confidence
        app_record.missing_fields = missing
        
        if missing:
            app_record.status = "review"
            app_record.officer_notes = f"Missing fields: {', '.join(missing)}"
            db.commit()
            
            return {
                "application_id": app_record.id,
                "status": "review",
                "message": f"Missing required fields: {', '.join(missing)}",
                "extracted_data": extracted,
                "confidence": parse_result.confidence,
                "file_type": parse_result.file_type
            }
        
        # Create loan application model
        loan_app = LoanAppModel(**extracted)
        
        # Process through sizer
        processor = SizerProcessor(template.file_path)
        result = processor.process_application(loan_app, interest_rate)
        
        # Update record with results
        app_record.units = loan_app.units
        app_record.property_address = loan_app.address
        app_record.property_city = loan_app.city
        app_record.property_state = loan_app.state
        app_record.property_zip = loan_app.zip_code
        app_record.estimated_value = loan_app.estimated_value
        app_record.purchase_price = loan_app.purchase_price
        app_record.loan_amount = loan_app.loan_amount
        app_record.note_type = loan_app.note_type
        app_record.points_to_lender = loan_app.points_to_lender
        app_record.credit_score_1 = loan_app.credit_score_1
        app_record.credit_score_2 = loan_app.credit_score_2
        app_record.credit_score_3 = loan_app.credit_score_3
        app_record.credit_score_middle = loan_app.credit_score_middle
        app_record.ltv_ratio = loan_app.ltv_ratio
        app_record.programs_results = [{
            "program_name": p.program_name,
            "status": p.status,
            "max_loan": p.max_loan_amount,
            "dscr": p.dscr,
            "reason": p.reason
        } for p in result.programs]
        app_record.overall_decision = result.overall_decision
        app_record.decision_reason = result.decision_reason
        app_record.output_excel_path = result.output_file
        app_record.processing_time_seconds = result.processing_time
        app_record.status = "review"
        
        db.commit()
        
        return {
            "application_id": app_record.id,
            "status": "success",
            "decision": result.overall_decision,
            "decision_reason": result.decision_reason,
            "processing_time": result.processing_time,
            "programs": app_record.programs_results,
            "output_file": result.output_file,
            "confidence": parse_result.confidence,
            "file_type": parse_result.file_type,
            "application": {
                "id": app_record.id,
                "units": loan_app.units,
                "address": loan_app.full_address,
                "loan_amount": loan_app.loan_amount,
                "ltv_ratio": loan_app.ltv_ratio,
                "credit_score": loan_app.credit_score_middle
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_record.status = "error"
        app_record.officer_notes = str(e)
        db.commit()
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ==================== EXCEL EXPORT ROUTES ====================

@app.get("/applications/{application_id}/export")
async def export_application_excel(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export application as Excel file using the original sizer template
    """
    
    app = db.query(LoanApplication).filter(
        LoanApplication.id == application_id,
        LoanApplication.client_id == current_user.client_id
    ).first()
    
    if not app:
        raise HTTPException(404, "Application not found")
    
    # Check if output file exists
    if app.output_excel_path and Path(app.output_excel_path).exists():
        # Return existing processed file
        return FileResponse(
            app.output_excel_path,
            filename=f"loan_application_{application_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Otherwise, generate from template
    template = db.query(ExcelTemplate).filter(
        ExcelTemplate.id == app.template_id
    ).first()
    
    if not template:
        raise HTTPException(400, "Template not found for this application")
    
    try:
        # Create loan application model from stored data
        loan_data = {
            'units': app.units or 1,
            'address': app.property_address or '',
            'city': app.property_city or '',
            'state': app.property_state or '',
            'zip_code': app.property_zip or '',
            'estimated_value': app.estimated_value or 0,
            'purchase_price': app.purchase_price or 0,
            'loan_amount': app.loan_amount or 0,
            'note_type': app.note_type or '30 Year Fixed',
            'credit_score_1': app.credit_score_1 or 700,
            'credit_score_2': app.credit_score_2 or 700,
            'credit_score_3': app.credit_score_3 or 700,
            'points_to_lender': app.points_to_lender or 0,
        }
        
        loan_app = LoanAppModel(**loan_data)
        
        # Process through sizer
        processor = SizerProcessor(template.file_path)
        result = processor.process_application(loan_app, app.interest_rate or 7.5)
        
        # Update record
        app.output_excel_path = result.output_file
        db.commit()
        
        return FileResponse(
            result.output_file,
            filename=f"loan_application_{application_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


# ==================== TEMPLATES ROUTES ====================

@app.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Excel templates for the organization"""
    
    templates = db.query(ExcelTemplate).filter(
        ExcelTemplate.client_id == current_user.client_id
    ).all()
    
    return {
        "templates": [{
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_default": t.is_default,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in templates]
    }


@app.post("/templates/upload")
async def upload_template(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    is_default: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new Excel template"""
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Only Excel files (.xlsx, .xls) are allowed")
    
    # Save file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.client_id}_{timestamp}_{file.filename}"
    file_path = TEMPLATES_DIR / filename
n    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # If setting as default, unset other defaults
    if is_default:
        db.query(ExcelTemplate).filter(
            ExcelTemplate.client_id == current_user.client_id
        ).update({"is_default": False})
    
    # Create template record
    template = ExcelTemplate(
        client_id=current_user.client_id,
        name=name,
        description=description,
        file_path=str(file_path),
        original_filename=file.filename,
        is_default=is_default,
        uploaded_by_id=current_user.id
    )
    db.add(template)
    db.commit()
    
    return {
        "id": template.id,
        "name": template.name,
        "message": "Template uploaded successfully"
    }


# ==================== SUPPORTED FORMATS ====================

@app.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": file_parser.SUPPORTED_FORMATS,
        "all_extensions": file_parser.get_supported_formats()
    }


# Import and include email router
from email_api import router as email_router
app.include_router(email_router, prefix="/email")
