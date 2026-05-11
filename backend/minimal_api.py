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
        "version": "3.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/api/multi-lender/compare"
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
