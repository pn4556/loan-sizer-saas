"""
Minimal Loan Sizer API - Reliable Backend for Render
No heavy dependencies, fast startup, all core functionality
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Loan Sizer API", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ DATA MODELS ============

class LenderCompareRequest(BaseModel):
    as_is_value: float
    purchase_price: float
    arv: float
    rehab_budget: float
    fico: int
    experience: int
    property_type: str = "SFR"
    loan_purpose: str = "purchase"

class LenderResult(BaseModel):
    lender: str
    program: str
    rate: float
    points: float
    max_loan_amount: float
    ltv: float
    ltc: float
    ltarv: Optional[float]
    monthly_payment: float
    approval_confidence: str
    ranking: int

# ============ LENDER LOGIC ============

def calculate_bridge_loan(
    as_is_value: float,
    arv: float,
    purchase_price: float,
    rehab_budget: float,
    fico: int,
    experience: int,
    lender: str
) -> dict:
    """Calculate bridge loan terms for a specific lender"""
    
    # Base rates by lender
    base_rates = {
        "IFC": 10.49,
        "ICE": 9.99,
        "Eastview": 10.75
    }
    
    # Points by lender
    base_points = {
        "IFC": 2.0,
        "ICE": 1.5,
        "Eastview": 2.5
    }
    
    # LTV/LTC limits
    max_ltv = {
        "IFC": 75,
        "ICE": 80,
        "Eastview": 70
    }
    
    max_ltc = {
        "IFC": 85,
        "ICE": 90,
        "Eastview": 80
    }
    
    # Calculate max loan
    ltv_limit = as_is_value * (max_ltv[lender] / 100)
    ltc_limit = purchase_price * (max_ltc[lender] / 100)
    max_loan = min(ltv_limit, ltc_limit)
    
    # Add rehab if applicable
    total_cost = purchase_price + rehab_budget
    if rehab_budget > 0:
        rehab_limit = arv * 0.70  # 70% ARV cap
        max_loan = min(max_loan + rehab_budget, rehab_limit)
    
    # Interest rate adjustment based on FICO
    rate = base_rates[lender]
    if fico >= 740:
        rate -= 0.25
    elif fico < 660:
        rate += 0.50
    elif fico < 700:
        rate += 0.25
    
    # Experience adjustment
    if experience >= 10:
        rate -= 0.25
        points = max(0.5, base_points[lender] - 0.5)
    elif experience >= 5:
        points = base_points[lender]
    else:
        rate += 0.25
        points = base_points[lender] + 0.5
    
    # Monthly payment (interest-only)
    monthly_payment = (max_loan * (rate / 100)) / 12
    
    # Calculate ratios
    ltv_actual = (max_loan / as_is_value) * 100 if as_is_value > 0 else 0
    ltc_actual = (max_loan / total_cost) * 100 if total_cost > 0 else 0
    ltarv_actual = (max_loan / arv) * 100 if arv > 0 else 0
    
    # Approval confidence
    if fico >= 720 and experience >= 5:
        confidence = "High"
    elif fico >= 680 and experience >= 2:
        confidence = "Good"
    elif fico >= 640:
        confidence = "Moderate"
    else:
        confidence = "Review Required"
    
    return {
        "lender": lender,
        "program": f"Bridge Loan - {lender}",
        "rate": round(rate, 2),
        "points": round(points, 2),
        "max_loan_amount": round(max_loan, 2),
        "ltv": round(ltv_actual, 1),
        "ltc": round(ltc_actual, 1),
        "ltarv": round(ltarv_actual, 1) if ltarv_actual > 0 else None,
        "monthly_payment": round(monthly_payment, 2),
        "approval_confidence": confidence,
        "total_cost": round(max_loan * (points / 100), 2)
    }

# ============ API ROUTES ============

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Loan Sizer API",
        "version": "3.1.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/api/multi-lender/compare",
            "/sizers/rtl/analyze",
            "/sizers/bridge/analyze"
        ]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "loan-sizer-api",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/multi-lender/compare")
async def compare_lenders(request: LenderCompareRequest):
    """
    Compare bridge loan offers from 3 lenders
    """
    try:
        # Calculate for all 3 lenders
        lenders = ["IFC", "ICE", "Eastview"]
        results = []
        
        for lender in lenders:
            result = calculate_bridge_loan(
                as_is_value=request.as_is_value,
                arv=request.arv,
                purchase_price=request.purchase_price,
                rehab_budget=request.rehab_budget,
                fico=request.fico,
                experience=request.experience,
                lender=lender
            )
            results.append(result)
        
        # Sort by rate for ranking
        sorted_results = sorted(results, key=lambda x: x["rate"])
        for i, result in enumerate(sorted_results, 1):
            result["ranking"] = i
        
        # Find best rate
        best = min(results, key=lambda x: x["rate"])
        
        return {
            "results": results,
            "best_rate_lender": best["lender"],
            "best_rate": best["rate"],
            "best_overall_lender": sorted_results[0]["lender"],
            "comparison_summary": f"{sorted_results[0]['lender']} offers the best rate at {sorted_results[0]['rate']}%",
            "input_summary": {
                "as_is_value": request.as_is_value,
                "purchase_price": request.purchase_price,
                "arv": request.arv,
                "rehab_budget": request.rehab_budget,
                "fico": request.fico,
                "experience": request.experience
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ RTL (Fix & Flip) SIZER MODELS ============

class RTLGuarantor(BaseModel):
    name: str
    credit_score: int
    is_guarantor: bool = True
    ownership_pct: float

class RTLProperty(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str = "SFR"

class RTLAnalyzeRequest(BaseModel):
    loan_purpose: str = "purchase"
    rehab_severity: str = "light"
    loan_term_months: int = 12
    entity_name: str
    num_owners: int = 1
    guarantors: List[RTLGuarantor]
    rehabs_completed_and_sold: int = 0
    rehabs_completed_refinanced: int = 0
    rentals_acquired: int = 0
    gc_rehabs_completed: int = 0
    property: RTLProperty
    purchase_price: float
    borrower_cost_basis: float
    as_is_value: float
    after_repair_value: float
    total_rehab_budget: float
    loan_amount: float
    expected_closing_date: str
    first_payment_date: str
    maturity_date: str

class RTLAnalyzeResult(BaseModel):
    overall_pass: bool
    borrower_classification: str
    max_ltv: float
    max_ltc: float
    ltv_approved: bool
    ltc_approved: bool
    fico_approved: bool
    experience_approved: bool
    rehab_budget_approved: bool
    loan_limits: Dict[str, Any]
    messages: List[str]

# ============ BRIDGE SIZER MODELS ============

class BridgeAnalyzeRequest(BaseModel):
    loan_purpose: str = "purchase"
    property_type: str = "SFR"
    occupancy: str = "non_owner"
    as_is_value: float
    purchase_price: float
    after_repair_value: float
    total_rehab_budget: float
    loan_amount: float
    fico_score: int
    liquidity: float
    experience_years: int
    exit_strategy: str = "sale"
    expected_hold_months: int = 6

class BridgeAnalyzeResult(BaseModel):
    overall_pass: bool
    lender: str
    program: str
    rate: float
    points: float
    max_loan_amount: float
    recommended_loan_amount: float
    ltv: float
    ltc: float
    ltarv: float
    monthly_payment: float
    approval_confidence: str
    messages: List[str]
    checks: Dict[str, Any]

# ============ RTL (FIX & FLIP) SIZER LOGIC ============

def calculate_rtl_loan(data: RTLAnalyzeRequest) -> RTLAnalyzeResult:
    """Calculate RTL (Fix & Flip) loan analysis"""
    
    messages = []
    
    # Get primary guarantor credit score
    primary_guarantor = data.guarantors[0] if data.guarantors else None
    fico = primary_guarantor.credit_score if primary_guarantor else 680
    
    # Calculate experience metrics
    total_rehabs = data.rehabs_completed_and_sold + data.rehabs_completed_refinanced
    total_deals = total_rehabs + data.rentals_acquired + data.gc_rehabs_completed
    
    # Borrower classification
    if total_deals >= 10 and fico >= 720:
        borrower_class = "Tier 1 - Elite"
        max_ltv = 0.90
        max_ltc = 0.90
    elif total_deals >= 5 and fico >= 680:
        borrower_class = "Tier 2 - Experienced"
        max_ltv = 0.85
        max_ltc = 0.90
    elif total_deals >= 2 and fico >= 660:
        borrower_class = "Tier 3 - Growing"
        max_ltv = 0.80
        max_ltc = 0.85
    else:
        borrower_class = "Tier 4 - New Investor"
        max_ltv = 0.75
        max_ltc = 0.80
    
    # Check approvals
    ltv_actual = data.loan_amount / data.after_repair_value if data.after_repair_value > 0 else 0
    ltc_actual = data.loan_amount / (data.purchase_price + data.total_rehab_budget) if (data.purchase_price + data.total_rehab_budget) > 0 else 0
    
    ltv_approved = ltv_actual <= max_ltv
    ltc_approved = ltc_actual <= max_ltc
    fico_approved = fico >= 620
    experience_approved = total_deals >= 0  # No minimum for new investors
    
    # Rehab budget check (max 25% of ARV for light, 40% for heavy)
    rehab_ratio = data.total_rehab_budget / data.after_repair_value if data.after_repair_value > 0 else 0
    if data.rehab_severity == "light":
        rehab_budget_approved = rehab_ratio <= 0.25
    elif data.rehab_severity == "heavy":
        rehab_budget_approved = rehab_ratio <= 0.50
    else:
        rehab_budget_approved = rehab_ratio <= 0.35
    
    # Build messages
    if not ltv_approved:
        messages.append(f"LTV {ltv_actual*100:.1f}% exceeds max {max_ltv*100:.0f}%")
    if not ltc_approved:
        messages.append(f"LTC {ltc_actual*100:.1f}% exceeds max {max_ltc*100:.0f}%")
    if not fico_approved:
        messages.append(f"FICO {fico} below minimum 620")
    if not rehab_budget_approved:
        messages.append(f"Rehab ratio {rehab_ratio*100:.1f}% too high for {data.rehab_severity} rehab")
    
    if not messages:
        messages.append("Loan approved within all parameters")
    
    overall_pass = ltv_approved and ltc_approved and fico_approved and rehab_budget_approved
    
    # Calculate loan limits
    arv_limit = data.after_repair_value * max_ltv
    cost_limit = (data.purchase_price + data.total_rehab_budget) * max_ltc
    max_loan = min(arv_limit, cost_limit)
    
    return RTLAnalyzeResult(
        overall_pass=overall_pass,
        borrower_classification=borrower_class,
        max_ltv=max_ltv,
        max_ltc=max_ltc,
        ltv_approved=ltv_approved,
        ltc_approved=ltc_approved,
        fico_approved=fico_approved,
        experience_approved=experience_approved,
        rehab_budget_approved=rehab_budget_approved,
        loan_limits={
            "max_loan_amount": round(max_loan, 2),
            "requested_loan": data.loan_amount,
            "arv_based_max": round(arv_limit, 2),
            "cost_based_max": round(cost_limit, 2)
        },
        messages=messages
    )

# ============ BRIDGE SIZER LOGIC ============

def calculate_bridge_analysis(data: BridgeAnalyzeRequest) -> BridgeAnalyzeResult:
    """Calculate Bridge loan analysis for individual sizer"""
    
    messages = []
    checks = {}
    
    # Base rates (Bridge Capital as primary)
    base_rate = 9.5
    base_points = 1.5
    
    # Rate adjustments
    rate = base_rate
    points = base_points
    
    # FICO adjustments
    if data.fico_score >= 740:
        rate -= 0.25
    elif data.fico_score < 660:
        rate += 0.50
    elif data.fico_score < 700:
        rate += 0.25
    
    # Experience adjustments
    if data.experience_years >= 5:
        rate -= 0.25
        points = max(1.0, points - 0.5)
    elif data.experience_years < 2:
        rate += 0.25
        points += 0.5
    
    # Max LTV/LTC
    if data.fico_score >= 720 and data.experience_years >= 3:
        max_ltv = 0.80
        max_ltc = 0.85
    elif data.fico_score >= 680:
        max_ltv = 0.75
        max_ltc = 0.80
    else:
        max_ltv = 0.70
        max_ltc = 0.75
    
    # Calculate max loan
    ltv_limit = data.as_is_value * max_ltv
    total_cost = data.purchase_price + data.total_rehab_budget
    ltc_limit = total_cost * max_ltc
    
    # ARV cap for rehab deals
    if data.total_rehab_budget > 0 and data.after_repair_value > 0:
        arv_cap = data.after_repair_value * 0.70
        max_loan = min(ltv_limit, ltc_limit, arv_cap)
    else:
        max_loan = min(ltv_limit, ltc_limit)
    
    # Check approvals
    ltv_actual = data.loan_amount / data.as_is_value if data.as_is_value > 0 else 0
    ltc_actual = data.loan_amount / total_cost if total_cost > 0 else 0
    ltarv_actual = data.loan_amount / data.after_repair_value if data.after_repair_value > 0 else 0
    
    ltv_approved = ltv_actual <= max_ltv
    ltc_approved = ltc_actual <= max_ltc
    fico_approved = data.fico_score >= 620
    liquidity_approved = data.liquidity >= data.loan_amount * 0.10  # 10% liquidity
    
    checks = {
        "ltv_check": {"actual": round(ltv_actual * 100, 1), "max": max_ltv * 100, "approved": ltv_approved},
        "ltc_check": {"actual": round(ltc_actual * 100, 1), "max": max_ltc * 100, "approved": ltc_approved},
        "fico_check": {"actual": data.fico_score, "min": 620, "approved": fico_approved},
        "liquidity_check": {"actual": data.liquidity, "required": data.loan_amount * 0.10, "approved": liquidity_approved}
    }
    
    # Messages
    if not ltv_approved:
        messages.append(f"LTV {ltv_actual*100:.1f}% exceeds {max_ltv*100:.0f}%")
    if not ltc_approved:
        messages.append(f"LTC {ltc_actual*100:.1f}% exceeds {max_ltc*100:.0f}%")
    if not fico_approved:
        messages.append(f"FICO {data.fico_score} below minimum 620")
    if not liquidity_approved:
        messages.append(f"Liquidity ${data.liquidity:,.0f} below required ${data.loan_amount*0.10:,.0f}")
    
    if not messages:
        messages.append("Bridge loan approved")
    
    overall_pass = ltv_approved and ltc_approved and fico_approved and liquidity_approved
    
    # Monthly payment (interest-only)
    monthly_payment = (data.loan_amount * (rate / 100)) / 12
    
    # Approval confidence
    if data.fico_score >= 720 and data.experience_years >= 5 and ltv_actual <= 0.70:
        confidence = "High"
    elif data.fico_score >= 680 and data.experience_years >= 2:
        confidence = "Good"
    elif data.fico_score >= 640:
        confidence = "Moderate"
    else:
        confidence = "Review Required"
    
    return BridgeAnalyzeResult(
        overall_pass=overall_pass,
        lender="Bridge Capital",
        program="Bridge Loan - Bridge Capital",
        rate=round(rate, 2),
        points=round(points, 2),
        max_loan_amount=round(max_loan, 2),
        recommended_loan_amount=round(min(data.loan_amount, max_loan), 2),
        ltv=round(ltv_actual * 100, 1),
        ltc=round(ltc_actual * 100, 1),
        ltarv=round(ltarv_actual * 100, 1),
        monthly_payment=round(monthly_payment, 2),
        approval_confidence=confidence,
        messages=messages,
        checks=checks
    )

# ============ API ROUTES ============

@app.post("/sizers/rtl/analyze")
async def analyze_rtl(request: RTLAnalyzeRequest):
    """
    Analyze RTL (Fix & Flip) loan application
    """
    try:
        result = calculate_rtl_loan(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sizers/bridge/analyze")
async def analyze_bridge(request: BridgeAnalyzeRequest):
    """
    Analyze Bridge loan application
    """
    try:
        result = calculate_bridge_analysis(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse-file")
async def parse_file():
    """
    File parsing endpoint - returns mock data for now
    Frontend handles actual file parsing client-side
    """
    return {
        "success": True,
        "message": "File parsing is handled client-side",
        "fields": {}
    }

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
