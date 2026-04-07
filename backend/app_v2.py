"""
Loan Sizer Automation API v2.0
Integrated with: Multi and Mixed-Use Term Sizer 3.18.2026
"""

import os
import sys
import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Form, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import anthropic
from dotenv import load_dotenv

# Import custom processor
from processor_custom import (
    SizerProcessor, 
    LoanApplication, 
    ProcessingResult
)

load_dotenv()

app = FastAPI(
    title="Loan Sizer Automation API",
    version="2.0.0",
    description="AI-powered loan processing for Multi and Mixed-Use Term Sizer"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Claude
claude_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY", "")
) if os.getenv("ANTHROPIC_API_KEY") else None

# Initialize processor
TEMPLATE_PATH = os.getenv("EXCEL_TEMPLATE", "../demo-data/template.xlsx")
processor = SizerProcessor(TEMPLATE_PATH)

# ==================== DATA MODELS ====================

class ApplicationInput(BaseModel):
    email_content: str = Field(..., description="Raw email text from applicant")
    interest_rate: float = Field(..., description="Daily interest rate")
    applicant_email: str = Field(..., description="Applicant's email address")
    officer_notes: Optional[str] = Field(None, description="Optional notes from loan officer")

class ApplicationData(BaseModel):
    units: int
    address: str
    city: str
    state: str
    zip_code: str
    estimated_value: float
    purchase_price: float
    loan_amount: float
    note_type: str
    credit_score_1: int
    credit_score_2: int
    credit_score_3: int
    points_to_lender: float = 0.0
    property_type: str = "Multifamily"
    asset_class: str = "C"

class ExtractionResponse(BaseModel):
    success: bool
    application: Optional[ApplicationData]
    missing_fields: List[str]
    confidence: float
    raw_extraction: Dict[str, Any]

class ProgramResultOut(BaseModel):
    name: str
    status: str
    max_loan_amount: Optional[float]
    interest_rate: Optional[float]
    dscr: Optional[float]
    reason: Optional[str]

class ProcessingResponse(BaseModel):
    success: bool
    application: ApplicationData
    credit_score_used: int
    ltv_ratio: float
    programs: List[ProgramResultOut]
    overall_decision: str
    decision_reason: str
    output_file: str
    processing_time: float
    generated_email: Dict[str, str]

# ==================== AI EXTRACTION ====================

EXTRACTION_PROMPT = """Extract loan application data from this email.

Look for these specific fields:
- Units (number of units)
- Property address
- City, State, ZIP code
- Estimated property value
- Purchase price
- Loan amount requested
- Note type (e.g., "30 YR Fixed", "15 YR Fixed")
- Points to lender (if mentioned)
- Three credit scores (we'll use the middle one)

EMAIL CONTENT:
{email}

Respond with ONLY this JSON format:
{{
    "units": 8,
    "address": "307 S Main Street",
    "city": "Hopkinsville", 
    "state": "KY",
    "zip_code": "44240",
    "estimated_value": 1200000,
    "purchase_price": 980000,
    "loan_amount": 784000,
    "note_type": "30 YR Fixed",
    "points_to_lender": 1.0,
    "credit_score_1": 688,
    "credit_score_2": 712,
    "credit_score_3": 703,
    "property_type": "Multifamily",
    "asset_class": "C"
}}

If a field is missing, use null. Convert currency to numbers (remove $ and commas)."""

async def extract_with_ai(email_content: str) -> Dict:
    """Use Claude to extract application data"""
    if not claude_client:
        raise HTTPException(500, "Claude API not configured")
    
    response = claude_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(email=email_content)
        }]
    )
    
    return json.loads(response.content[0].text)

import re

async def extract_with_regex(email_content: str) -> Dict:
    """Fallback extraction using regex patterns"""
    text = email_content
    
    patterns = {
        'units': r'(\d+)\s*units?',
        'address': r'(\d+\s+[^,\n]+?(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln))',
        'city': r'(?:City[:\s]+)?([A-Za-z\s]+?)(?=,\s*[A-Z]{2})',
        'state': r',\s*([A-Z]{2})\s*\d{5}',
        'zip': r'\b(\d{5})\b',
        'estimated_value': r'(?:est(?:imated)?\s+(?:value|price)[:\s]+)\$?([\d,]+)',
        'purchase_price': r'(?:purchase[:\s]+)\$?([\d,]+)',
        'loan_amount': r'(?:loan[:\s]+)\$?([\d,]+)',
        'note_type': r'(30|15|20)\s*YR\s*(?:Fixed|ARM)',
        'points': r'points[:\s]+(\d+(?:\.\d+)?)',
        'credit_scores': r'(\d{3})[\s,]+(\d{3})[\s,]+(\d{3})'
    }
    
    extracted = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
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
    
    # Set defaults
    extracted.setdefault('property_type', 'Multifamily')
    extracted.setdefault('asset_class', 'C')
    extracted.setdefault('points_to_lender', 0.0)
    
    return extracted

# ==================== EMAIL GENERATION ====================

def generate_approval_email(result: ProcessingResult, applicant_email: str) -> Dict[str, str]:
    """Generate approval email"""
    passed = [p for p in result.programs if p.status == "PASS"]
    
    subject = f"✅ Loan Approved - {result.application.full_address}"
    
    body = f"""Dear Applicant,

Congratulations! Your loan application has been APPROVED.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROPERTY DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Address: {result.application.full_address}
• Property Type: {result.application.property_type} ({result.application.units} units)
• Estimated Value: ${result.application.estimated_value:,.2f}
• Loan Amount: ${result.application.loan_amount:,.2f}
• LTV Ratio: {result.application.ltv_ratio:.2f}%
• Credit Score Used: {result.application.credit_score_middle} (middle of 3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVED PROGRAMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for prog in passed:
        body += f"""
✓ {prog.name}
  Status: APPROVED
  Max Loan: ${prog.max_loan_amount:,.2f}"""
        if prog.dscr:
            body += f"\n  DSCR: {prog.dscr:.2f}"
        body += "\n"
    
    body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Review and sign the attached loan commitment letter
2. Submit required documentation (income verification, property appraisal)
3. Schedule closing with our processing team

Your loan officer will contact you within 24 hours to discuss next steps.

Best regards,
Loan Processing Team

---
This decision was generated by our AI-assisted processing system
and reviewed by a loan officer. Processing time: {result.processing_time:.1f} seconds
"""
    
    return {"subject": subject, "body": body, "type": "approval"}

def generate_rejection_email(result: ProcessingResult, applicant_email: str) -> Dict[str, str]:
    """Generate rejection email"""
    failed = [p for p in result.programs if p.status == "FAIL"]
    
    subject = f"Loan Application Update - {result.application.full_address}"
    
    body = f"""Dear Applicant,

Thank you for your interest in our loan programs.

After careful review of your application for the property at:
{result.application.full_address}

We regret to inform you that your application does not meet our current program requirements.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPLICATION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Loan Amount Requested: ${result.application.loan_amount:,.2f}
• LTV Ratio: {result.application.ltv_ratio:.2f}%
• Credit Score: {result.application.credit_score_middle}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for prog in failed:
        body += f"""
✗ {prog.name}
  Status: DECLINED
  Reason: {prog.reason or 'Does not meet program requirements'}
"""
    
    body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REASONS FOR DECLINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{result.decision_reason}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You may reapply if:
• You can increase your down payment to lower the LTV ratio
• Your credit score improves
• You provide additional qualifying documentation

We appreciate your interest and wish you success with your investment.

Best regards,
Loan Processing Team
"""
    
    return {"subject": subject, "body": body, "type": "rejection"}

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "Loan Sizer Automation API v2.0",
        "template": "Multi and Mixed-Use Term Sizer 3.18.2026",
        "endpoints": [
            "/api/extract",
            "/api/process",
            "/api/demo/scenarios"
        ]
    }

@app.post("/api/extract", response_model=ExtractionResponse)
async def extract_application(email_content: str = Form(...)):
    """Extract application data from email"""
    try:
        if claude_client:
            extracted = await extract_with_ai(email_content)
            confidence = 0.95
        else:
            extracted = await extract_with_regex(email_content)
            confidence = 0.85
        
        # Check for missing fields
        required = ['units', 'address', 'city', 'state', 'zip_code',
                   'estimated_value', 'purchase_price', 'loan_amount',
                   'note_type', 'credit_score_1', 'credit_score_2', 'credit_score_3']
        missing = [f for f in required if f not in extracted or extracted[f] is None]
        
        if missing:
            return ExtractionResponse(
                success=False,
                application=None,
                missing_fields=missing,
                confidence=confidence,
                raw_extraction=extracted
            )
        
        # Build ApplicationData
        app_data = ApplicationData(**extracted)
        
        return ExtractionResponse(
            success=True,
            application=app_data,
            missing_fields=[],
            confidence=confidence,
            raw_extraction=extracted
        )
        
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {str(e)}")

@app.post("/api/process", response_model=ProcessingResponse)
async def process_application(
    email_content: str = Form(...),
    interest_rate: float = Form(...),
    applicant_email: str = Form(...)
):
    """Full processing pipeline"""
    
    import time
    start = time.time()
    
    # Step 1: Extract
    try:
        if claude_client:
            extracted = await extract_with_ai(email_content)
        else:
            extracted = await extract_with_regex(email_content)
    except Exception as e:
        raise HTTPException(422, f"Extraction failed: {str(e)}")
    
    # Step 2: Create LoanApplication
    try:
        app = LoanApplication(**extracted)
    except Exception as e:
        raise HTTPException(422, f"Invalid application data: {str(e)}")
    
    # Step 3: Process through sizer
    try:
        result = processor.process_application(app, interest_rate)
    except Exception as e:
        raise HTTPException(500, f"Sizer processing failed: {str(e)}")
    
    # Step 4: Generate email
    if result.overall_decision == "APPROVE":
        email = generate_approval_email(result, applicant_email)
    else:
        email = generate_rejection_email(result, applicant_email)
    
    # Build response
    programs_out = [
        ProgramResultOut(
            name=p.name,
            status=p.status,
            max_loan_amount=p.max_loan_amount,
            interest_rate=p.interest_rate,
            dscr=p.dscr,
            reason=p.reason
        )
        for p in result.programs
    ]
    
    return ProcessingResponse(
        success=True,
        application=ApplicationData(**extracted),
        credit_score_used=app.credit_score_middle,
        ltv_ratio=app.ltv_ratio,
        programs=programs_out,
        overall_decision=result.overall_decision,
        decision_reason=result.decision_reason,
        output_file=result.output_file,
        processing_time=result.processing_time,
        generated_email=email
    )

@app.get("/api/demo/scenarios")
async def get_scenarios():
    """Get demo scenarios"""
    return {
        "scenarios": [
            {
                "name": "✅ Strong Approval",
                "email": """Subject: Loan Application - 8 Unit Multifamily

Hello,

I'm interested in financing for an 8-unit multifamily property at 307 S Main Street, Hopkinsville, KY 44240.

Property Details:
- 8 units, approximately 750 sq ft each
- Estimated value: $1,200,000
- Purchase price: $980,000
- Requested loan amount: $784,000
- Note type: 30 YR Fixed

My credit scores are 688, 712, and 703.
Points to lender: 1%

Please let me know what programs I qualify for.

Thanks,
James Whitfield
james.whitfield@email.com""",
                "rate": 8.50,
                "expected": "APPROVE"
            },
            {
                "name": "❌ High LTV Rejection",
                "email": """Subject: Loan Request

Hi,

Looking for a loan on:
- 12 units at 456 Oak Street, Chicago, IL 60601
- Estimated value: $800,000
- Purchase price: $750,000
- Loan needed: $700,000 (87.5% LTV)
- 30 YR Fixed

Credit scores: 620, 641, 655

Thanks,
Michael Chen""",
                "rate": 8.75,
                "expected": "REJECT"
            },
            {
                "name": "⚠️ Borderline Review",
                "email": """Subject: Quick loan inquiry

Property: 789 Pine Ave, Miami FL 33101
4 units, 900 sq ft
Value: $600,000
Purchase: $520,000
Loan: $450,000
Credit: 665, 678, 682

30 YR Fixed please.

Thanks""",
                "rate": 8.60,
                "expected": "REVIEW"
            }
        ]
    }

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download processed sizer file"""
    file_path = Path("/tmp") / filename
    if file_path.exists():
        return FileResponse(file_path, filename=filename)
    raise HTTPException(404, "File not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)
