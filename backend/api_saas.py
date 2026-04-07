"""
Loan Sizer SaaS API
Multi-tenant API with authentication, file uploads, and PDF parsing
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
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
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
from pdf_parser import PDFLoanParser

# Initialize app
app = FastAPI(
    title="Loan Sizer SaaS Platform",
    version="2.0.0",
    description="Multi-tenant loan processing platform"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR = UPLOAD_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
PDFS_DIR = UPLOAD_DIR / "pdfs"
PDFS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR = UPLOAD_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# ==================== AUTH SCHEMAS ====================

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class RegisterRequest(BaseModel):
    company_name: str
    email: str
    password: str
    first_name: str
    last_name: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = "loan_officer"

# ==================== AUTH ROUTES ====================

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return tokens"""
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "client_id": user.client_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "client_id": user.client_id}
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "client": {
                "id": user.client.id,
                "company_name": user.client.company_name,
                "slug": user.client.slug
            }
        }
    )

@app.post("/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new client"""
    # Check if email exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    # Create client and admin user
    client, admin = register_client(
        db=db,
        company_name=request.company_name,
        email=request.email,
        password=request.password,
        admin_first_name=request.first_name,
        admin_last_name=request.last_name
    )
    
    return {
        "message": "Registration successful",
        "client_id": client.id,
        "client_slug": client.slug,
        "trial_ends": client.trial_ends_at
    }

@app.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "client": {
            "id": current_user.client.id,
            "company_name": current_user.client.company_name,
            "slug": current_user.client.slug,
            "plan": current_user.client.plan,
            "trial_ends": current_user.client.trial_ends_at
        }
    }

# ==================== USER MANAGEMENT (Admin) ====================

@app.post("/admin/users")
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user in the organization (Admin only)"""
    
    # Check email uniqueness within client
    existing = db.query(User).filter(
        User.email == request.email,
        User.client_id == current_user.client_id
    ).first()
    if existing:
        raise HTTPException(400, "Email already exists in your organization")
    
    user = User(
        client_id=current_user.client_id,
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role
    )
    user.set_password(request.password)
    
    db.add(user)
    db.commit()
    
    return {"id": user.id, "email": user.email, "message": "User created"}

@app.get("/admin/users")
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users in organization (Admin only)"""
    users = db.query(User).filter(User.client_id == current_user.client_id).all()
    return [{
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "role": u.role,
        "is_active": u.is_active,
        "last_login": u.last_login
    } for u in users]

# ==================== TEMPLATE MANAGEMENT ====================

@app.post("/templates/upload")
async def upload_template(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Upload Excel template (Admin only)"""
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xlsm', '.xls')):
        raise HTTPException(400, "Only Excel files (.xlsx, .xlsm, .xls) allowed")
    
    # Read file content
    content = await file.read()
    
    # Calculate hash for deduplication
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Save file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.client_id}_{timestamp}_{file.filename}"
    file_path = TEMPLATES_DIR / filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Analyze template (extract cell mappings)
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=False)
        
        # Find input cells (simplified analysis)
        cell_mappings = {}
        if 'SIZER' in wb.sheetnames:
            sheet = wb['SIZER']
            # This would be expanded with full analysis
            cell_mappings = {
                "C8": "units",
                "E5": "address",
                "E6": "city",
                "E7": "state",
                "E8": "zip_code",
                "G5": "estimated_value",
                "G6": "purchase_price",
                "J4": "loan_amount",
                "I8": "note_type",
                "I10": "points_to_lender",
                "M7": "credit_score",
            }
        wb.close()
    except Exception as e:
        # Delete file if analysis fails
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not analyze Excel file: {str(e)}")
    
    # Create template record
    template = ExcelTemplate(
        client_id=current_user.client_id,
        name=name,
        description=description,
        file_path=str(file_path),
        file_size=len(content),
        file_hash=file_hash,
        cell_mappings=cell_mappings
    )
    
    # If first template, make it default
    existing = db.query(ExcelTemplate).filter(
        ExcelTemplate.client_id == current_user.client_id
    ).first()
    if not existing:
        template.is_default = True
    
    db.add(template)
    db.commit()
    
    return {
        "id": template.id,
        "name": template.name,
        "cell_mappings": template.cell_mappings,
        "message": "Template uploaded successfully"
    }

@app.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all templates for the organization"""
    templates = db.query(ExcelTemplate).filter(
        ExcelTemplate.client_id == current_user.client_id
    ).all()
    
    return [{
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "is_default": t.is_default,
        "is_active": t.is_active,
        "file_size": t.file_size,
        "created_at": t.created_at,
        "cell_count": len(t.cell_mappings) if t.cell_mappings else 0
    } for t in templates]

@app.post("/templates/{template_id}/set-default")
async def set_default_template(
    template_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Set template as default (Admin only)"""
    
    # Unset current default
    db.query(ExcelTemplate).filter(
        ExcelTemplate.client_id == current_user.client_id
    ).update({"is_default": False})
    
    # Set new default
    template = db.query(ExcelTemplate).filter(
        ExcelTemplate.id == template_id,
        ExcelTemplate.client_id == current_user.client_id
    ).first()
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    template.is_default = True
    db.commit()
    
    return {"message": "Default template updated"}

# ==================== APPLICATION PROCESSING ====================

class ProcessFromEmailRequest(BaseModel):
    email_content: str
    interest_rate: float
    applicant_email: str
    template_id: Optional[int] = None

@app.post("/applications/process/email")
async def process_from_email(
    request: ProcessFromEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process loan application from email text"""
    
    # Get template
    if request.template_id:
        template = db.query(ExcelTemplate).filter(
            ExcelTemplate.id == request.template_id,
            ExcelTemplate.client_id == current_user.client_id
        ).first()
    else:
        template = db.query(ExcelTemplate).filter(
            ExcelTemplate.client_id == current_user.client_id,
            ExcelTemplate.is_default == True
        ).first()
    
    if not template:
        raise HTTPException(400, "No template available. Please upload an Excel template first.")
    
    # Create application record
    app_record = LoanApplication(
        client_id=current_user.client_id,
        template_id=template.id,
        processed_by_id=current_user.id,
        source_type="email",
        source_email=request.email_content,
        applicant_email=request.applicant_email,
        interest_rate=request.interest_rate,
        status="processing"
    )
    db.add(app_record)
    db.commit()
    
    try:
        # Extract data (use AI if available, else regex)
        import anthropic
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            # AI extraction would go here
            extracted = _extract_with_regex(request.email_content)  # Fallback for now
            app_record.extraction_method = "regex"
        except:
            extracted = _extract_with_regex(request.email_content)
            app_record.extraction_method = "regex"
        
        # Validate extraction
        required = ['units', 'address', 'city', 'state', 'zip_code',
                   'estimated_value', 'purchase_price', 'loan_amount',
                   'credit_score_1', 'credit_score_2', 'credit_score_3']
        missing = [f for f in required if f not in extracted]
        app_record.missing_fields = missing
        
        if missing:
            app_record.status = "review"
            app_record.officer_notes = f"Missing fields: {', '.join(missing)}"
            db.commit()
            return {
                "application_id": app_record.id,
                "status": "review",
                "message": f"Missing required fields: {', '.join(missing)}",
                "extracted_data": extracted
            }
        
        # Create loan application model
        loan_app = LoanAppModel(**extracted)
        
        # Process through sizer
        processor = SizerProcessor(template.file_path)
        result = processor.process_application(loan_app, request.interest_rate)
        
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
        app_record.extraction_confidence = 0.85
        app_record.programs_results = [{
            "name": p.name,
            "status": p.status,
            "max_loan": p.max_loan_amount,
            "dscr": p.dscr,
            "reason": p.reason
        } for p in result.programs]
        app_record.overall_decision = result.overall_decision
        app_record.decision_reason = result.decision_reason
        app_record.output_excel_path = result.output_file
        app_record.processing_time_seconds = result.processing_time
        app_record.status = "review"  # Awaiting officer approval
        
        db.commit()
        
        return {
            "application_id": app_record.id,
            "status": "success",
            "decision": result.overall_decision,
            "decision_reason": result.decision_reason,
            "processing_time": result.processing_time,
            "programs": app_record.programs_results,
            "output_file": result.output_file,
            "application": {
                "units": loan_app.units,
                "address": loan_app.full_address,
                "loan_amount": loan_app.loan_amount,
                "ltv_ratio": loan_app.ltv_ratio,
                "credit_score": loan_app.credit_score_middle
            }
        }
        
    except Exception as e:
        app_record.status = "error"
        app_record.officer_notes = str(e)
        db.commit()
        raise HTTPException(500, f"Processing failed: {str(e)}")


@app.post("/applications/process/pdf")
async def process_from_pdf(
    interest_rate: float = Form(...),
    applicant_email: str = Form(...),
    file: UploadFile = File(...),
    template_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process loan application from PDF file"""
    
    # Validate file
    if not file.content_type == "application/pdf":
        raise HTTPException(400, "Only PDF files allowed")
    
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
        raise HTTPException(400, "No template available")
    
    # Save PDF
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{current_user.client_id}_{timestamp}_{file.filename}"
    pdf_path = PDFS_DIR / pdf_filename
    
    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)
    
    # Create application record
    app_record = LoanApplication(
        client_id=current_user.client_id,
        template_id=template.id,
        processed_by_id=current_user.id,
        source_type="pdf",
        source_pdf_path=str(pdf_path),
        applicant_email=applicant_email,
        interest_rate=interest_rate,
        status="processing"
    )
    db.add(app_record)
    db.commit()
    
    try:
        # Parse PDF
        parser = PDFLoanParser()
        pdf_result = parser.parse_pdf(content)
        
        if not pdf_result.success:
            app_record.status = "review"
            app_record.officer_notes = f"PDF parsing failed: {pdf_result.error_message}"
            db.commit()
            raise HTTPException(400, f"Could not parse PDF: {pdf_result.error_message}")
        
        # Convert extracted fields to loan application
        extracted = pdf_result.fields
        extracted['points_to_lender'] = extracted.get('points', 0.0)
        
        # Create and process
        loan_app = LoanAppModel(**extracted)
        processor = SizerProcessor(template.file_path)
        result = processor.process_application(loan_app, interest_rate)
        
        # Update record
        app_record.extraction_method = "pdf"
        app_record.extraction_confidence = pdf_result.confidence
        app_record.status = "review"
        db.commit()
        
        return {
            "application_id": app_record.id,
            "status": "success",
            "pdf_confidence": pdf_result.confidence,
            "decision": result.overall_decision,
            "extracted_fields": list(pdf_result.fields.keys())
        }
        
    except Exception as e:
        app_record.status = "error"
        app_record.officer_notes = str(e)
        db.commit()
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ==================== DASHBOARD ROUTES ====================

@app.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for the organization"""
    
    # Total applications
    total_apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == current_user.client_id
    ).count()
    
    # This month's applications
    from datetime import datetime, timedelta
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    month_apps = db.query(LoanApplication).filter(
        LoanApplication.client_id == current_user.client_id,
        LoanApplication.created_at >= month_start
    ).count()
    
    # Decision breakdown
    decisions = db.query(LoanApplication.overall_decision, 
                        db.func.count(LoanApplication.id)).filter(
        LoanApplication.client_id == current_user.client_id
    ).group_by(LoanApplication.overall_decision).all()
    
    # Average processing time
    avg_time = db.query(db.func.avg(LoanApplication.processing_time_seconds)).filter(
        LoanApplication.client_id == current_user.client_id,
        LoanApplication.processing_time_seconds != None
    ).scalar()
    
    # Time saved calculation
    time_saved_minutes = total_apps * 23  # 23 min saved per app
    
    return {
        "total_applications": total_apps,
        "this_month": month_apps,
        "decisions": {d[0] or "pending": d[1] for d in decisions},
        "average_processing_time": round(avg_time, 2) if avg_time else 0,
        "time_saved_minutes": time_saved_minutes,
        "time_saved_hours": round(time_saved_minutes / 60, 1)
    }


@app.get("/applications")
async def list_applications(
    status: Optional[str] = None,
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
            "loan_amount": a.loan_amount,
            "decision": a.overall_decision,
            "status": a.status,
            "processing_time": a.processing_time_seconds,
            "created_at": a.created_at,
            "processed_by": a.processed_by.full_name if a.processed_by else None
        } for a in apps]
    }


# ==================== HELPER FUNCTIONS ====================

def _extract_with_regex(email_content: str) -> dict:
    """Simple regex extraction (fallback)"""
    import re
    
    patterns = {
        'units': r'(\d+)\s*units?',
        'address': r'(\d+\s+[^,\n]+?(?:Street|St|Avenue|Ave|Road|Rd))',
        'city': r'(?:City[:\s]+)?([A-Za-z\s]+?)(?=,\s*[A-Z]{2})',
        'state': r',\s*([A-Z]{2})\s*\d{5}',
        'zip': r'\b(\d{5})\b',
        'estimated_value': r'(?:value|price)[:\s]+\$?([\d,]+)',
        'purchase_price': r'(?:purchase|buy)[:\s]+\$?([\d,]+)',
        'loan_amount': r'(?:loan|requested)[:\s]+\$?([\d,]+)',
        'note_type': r'(30|15|20)\s*YR',
        'points': r'points[:\s]+(\d+(?:\.\d+)?)',
        'credit_scores': r'(\d{3})[\s,]+(\d{3})[\s,]+(\d{3})',
    }
    
    extracted = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, email_content, re.IGNORECASE)
        if match:
            if field == 'credit_scores':
                extracted['credit_score_1'] = int(match.group(1))
                extracted['credit_score_2'] = int(match.group(2))
                extracted['credit_score_3'] = int(match.group(3))
            elif field == 'units':
                extracted[field] = int(match.group(1))
            elif field == 'points':
                extracted[field] = float(match.group(1))
            elif field == 'note_type':
                extracted[field] = f"{match.group(1)} YR Fixed"
            elif field in ['estimated_value', 'purchase_price', 'loan_amount']:
                extracted[field] = float(match.group(1).replace(',', ''))
            else:
                extracted[field] = match.group(1).strip()
    
    extracted.setdefault('property_type', 'Multifamily')
    extracted.setdefault('asset_class', 'C')
    extracted.setdefault('points_to_lender', 0.0)
    
    return extracted


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "service": "loan-sizer-api",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== INITIALIZATION ====================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    init_database()
    print("✅ Loan Sizer SaaS Platform initialized")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)
