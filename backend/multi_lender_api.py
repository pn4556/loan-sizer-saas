"""
Multi-Lender Pricing API Endpoints
Provides 3-lender comparison for 1-4 unit properties
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from multi_lender_logic import (
    MultiLenderPricingEngine, MultiLenderRequest, MultiLenderResponse,
    format_currency, format_percent, LoanProgram
)

router = APIRouter(prefix="/api/multi-lender", tags=["multi-lender"])

# Initialize pricing engine
pricing_engine = MultiLenderPricingEngine()


class LenderComparisonRequest(BaseModel):
    as_is_value: float = Field(..., gt=0, description="As-is property value")
    arv: float = Field(..., gt=0, description="After repair value")
    purchase_price: float = Field(..., gt=0, description="Purchase price")
    rehab_budget: float = Field(..., ge=0, description="Rehabilitation budget")
    fico: int = Field(..., ge=300, le=850, description="Borrower FICO score")
    experience: int = Field(default=5, ge=0, description="Years of experience")
    loan_purpose: str = Field(default="purchase", description="Loan purpose")
    property_type: str = Field(default="SFR", description="Property type")


class LenderResult(BaseModel):
    lender: str
    program: str
    rate: float
    rate_formatted: str
    points: float
    points_formatted: str
    max_loan_amount: float
    max_loan_formatted: str
    ltv: float
    ltv_formatted: str
    ltc: float
    ltc_formatted: str
    ltarv: Optional[float]
    ltarv_formatted: Optional[str]
    monthly_payment: float
    monthly_payment_formatted: str
    total_cost: float
    total_cost_formatted: str
    approval_confidence: str
    ranking: int


class LenderComparisonResponse(BaseModel):
    results: List[LenderResult]
    best_rate_lender: str
    best_rate: float
    best_rate_formatted: str
    best_overall_lender: str
    comparison_summary: str
    input_summary: dict


def pricing_result_to_dict(result, ranking: int) -> dict:
    """Convert PricingResult to dictionary with formatted values"""
    return {
        "lender": result.lender.value,
        "program": result.program,
        "rate": result.rate,
        "rate_formatted": format_percent(result.rate),
        "points": result.points,
        "points_formatted": format_percent(result.points),
        "max_loan_amount": result.max_loan_amount,
        "max_loan_formatted": format_currency(result.max_loan_amount),
        "ltv": result.ltv,
        "ltv_formatted": format_percent(result.ltv),
        "ltc": result.ltc,
        "ltc_formatted": format_percent(result.ltc),
        "ltarv": result.ltarv,
        "ltarv_formatted": format_percent(result.ltarv) if result.ltarv else None,
        "monthly_payment": result.monthly_payment,
        "monthly_payment_formatted": format_currency(result.monthly_payment),
        "total_cost": result.total_cost,
        "total_cost_formatted": format_currency(result.total_cost),
        "approval_confidence": result.approval_confidence,
        "ranking": ranking
    }


@router.post("/compare", response_model=LenderComparisonResponse)
async def compare_lenders(request: LenderComparisonRequest):
    """
    Compare pricing from all 3 lenders (IFC, ICE, Eastview)
    Returns side-by-side comparison with best options highlighted
    """
    try:
        # Get pricing from all lenders
        results = pricing_engine.compare_all_lenders(
            as_is_value=request.as_is_value,
            arv=request.arv,
            purchase_price=request.purchase_price,
            rehab_budget=request.rehab_budget,
            fico=request.fico,
            experience=request.experience,
            loan_purpose=request.loan_purpose
        )
        
        if not results:
            raise HTTPException(status_code=400, detail="No lenders available for this scenario")
        
        # Format results
        formatted_results = [
            pricing_result_to_dict(result, i + 1)
            for i, result in enumerate(results)
        ]
        
        # Get best options
        best_rate_result = pricing_engine.get_best_rate(results)
        best_overall_result = pricing_engine.get_best_overall(results)
        
        # Generate comparison summary
        summary = generate_comparison_summary(results, request)
        
        return LenderComparisonResponse(
            results=formatted_results,
            best_rate_lender=best_rate_result.lender.value if best_rate_result else "N/A",
            best_rate=best_rate_result.rate if best_rate_result else 0,
            best_rate_formatted=format_percent(best_rate_result.rate) if best_rate_result else "N/A",
            best_overall_lender=best_overall_result.lender.value if best_overall_result else "N/A",
            comparison_summary=summary,
            input_summary={
                "as_is_value": format_currency(request.as_is_value),
                "arv": format_currency(request.arv),
                "purchase_price": format_currency(request.purchase_price),
                "rehab_budget": format_currency(request.rehab_budget),
                "fico": request.fico,
                "experience": request.experience,
                "loan_purpose": request.loan_purpose
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating pricing: {str(e)}")


@router.post("/scenario/{lender}")
async def get_lender_specific_scenario(
    lender: str,
    request: LenderComparisonRequest
):
    """
    Get detailed pricing scenario for a specific lender
    """
    try:
        lender_name = lender.upper()
        
        if lender_name == "IFC":
            result = pricing_engine.calculate_ifc_pricing(
                request.as_is_value, request.arv, request.purchase_price,
                request.rehab_budget, request.fico, LoanProgram.RENOVATION,
                request.loan_purpose
            )
        elif lender_name == "ICE":
            result = pricing_engine.calculate_ice_pricing(
                request.as_is_value, request.arv, request.purchase_price,
                request.rehab_budget, request.fico, LoanProgram.LIGHT_REHAB,
                request.experience, request.loan_purpose
            )
        elif lender_name == "EASTVIEW":
            result = pricing_engine.calculate_eastview_pricing(
                request.as_is_value, request.arv, request.purchase_price,
                request.rehab_budget, request.fico, LoanProgram.FIX_FLIP,
                request.experience, request.loan_purpose
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown lender: {lender}")
        
        if not result:
            raise HTTPException(status_code=400, detail=f"No pricing available from {lender}")
        
        return pricing_result_to_dict(result, 1)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def generate_comparison_summary(results, request) -> str:
    """Generate a human-readable comparison summary"""
    if not results:
        return "No lenders available for this scenario."
    
    best = results[0]
    savings_vs_worst = ""
    
    if len(results) > 1:
        worst_rate = max(r.rate for r in results)
        rate_diff = worst_rate - best.rate
        savings_vs_worst = f" Choosing {best.lender.value} saves {format_percent(rate_diff)} compared to the highest rate."
    
    summary = (
        f"Best Rate: {best.lender.value} at {format_percent(best.rate)} "
        f"with {format_percent(best.points)} points. "
        f"Max loan: {format_currency(best.max_loan_amount)} "
        f"({format_percent(best.ltv)} LTV).{savings_vs_worst}"
    )
    
    return summary


@router.get("/programs")
async def get_available_programs():
    """Get list of available loan programs by lender"""
    return {
        "IFC": ["Bridge", "Renovation"],
        "ICE": ["Light Rehab", "Bridge", "Heavy Rehab"],
        "Eastview": ["Fix & Flip", "Bridge"]
    }


@router.get("/lender-info")
async def get_lender_info():
    """Get detailed information about each lender's programs"""
    return {
        "IFC": {
            "name": "IFC",
            "programs": {
                "Bridge": {
                    "ltv_range": "55-80%",
                    "rate_range": "7.50% - 8.00%",
                    "points": "1.5%",
                    "min_fico": 680
                },
                "Renovation": {
                    "ltv_range": "65-90%",
                    "rate_range": "7.75% - 8.50%",
                    "points": "2.0%",
                    "min_fico": 660,
                    "ltarv_max": "75%"
                }
            },
            "fico_tiers": ["740+", "700-739", "680-699", "660-679"]
        },
        "ICE": {
            "name": "ICE/Guides",
            "programs": {
                "Light Rehab": {
                    "ltv_max": "90%",
                    "ltc_max": "90%",
                    "ltarv_max": "75%",
                    "base_rate": "8.75%",
                    "points": "0.5%",
                    "min_fico": 680
                },
                "Bridge": {
                    "ltv_max": "85%",
                    "ltc_max": "85%",
                    "base_rate": "8.75%",
                    "points": "0.75%",
                    "min_fico": 680
                },
                "Heavy Rehab": {
                    "ltv_max": "85%",
                    "ltc_max": "85%",
                    "ltarv_max": "70%",
                    "base_rate": "9.00%",
                    "points": "0.75%",
                    "min_fico": 700
                }
            }
        },
        "Eastview": {
            "name": "Eastview",
            "programs": {
                "Fix & Flip": {
                    "A+": {"ltv": "90%", "ltc": "90%", "ltarv": "75%", "min_rate": "9.25%"},
                    "A": {"ltv": "85%", "ltc": "85%", "ltarv": "70%", "min_rate": "9.50%"},
                    "B": {"ltv": "82.5%", "ltc": "82.5%", "ltarv": "65%", "min_rate": "9.75%"},
                    "C": {"ltv": "75%", "ltc": "75%", "ltarv": "60%", "min_rate": "10.25%"},
                    "points": "1.5%",
                    "min_fico": 660
                },
                "Bridge": {
                    "A+": {"ltv": "82.5%", "ltc": "82.5%", "min_rate": "9.25%"},
                    "A": {"ltv": "80%", "ltc": "80%", "min_rate": "9.50%"},
                    "B": {"ltv": "80%", "ltc": "80%", "min_rate": "9.75%"},
                    "C": {"ltv": "75%", "ltc": "75%", "min_rate": "10.25%"},
                    "points": "1.5%",
                    "min_fico": 660
                }
            },
            "grade_calculation": "Based on FICO score + Experience"
        }
    }
