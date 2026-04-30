"""
API Endpoints for RTL (Fix & Flip) and Bridge Loan Sizers
Integrates with existing Loan Sizer SaaS backend
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from rtl_sizer_logic import (
    RTLInputs, RTLProperty, Guarantor, RTLResults, run_rtl_sizer,
    LoanPurpose as RTLLoanPurpose, RehabType as RTLRehabType,
    get_rtl_programs
)
from bridge_sizer_logic import (
    BridgeInputs, BridgeProperty, BridgeBorrower, BridgeValuation,
    BridgeLoanRequest, BridgeCashFlow, BridgeMarketData, BridgeResults,
    run_bridge_sizer, LoanPurpose, RehabType, TransactionType,
    Citizenship, PropertyType, get_bridge_programs
)

router = APIRouter(prefix="/sizers", tags=["loan-sizers"])


# ==================== RTL (FIX & FLIP) MODELS ====================

class RTLGuarantorInput(BaseModel):
    name: str
    credit_score: int = Field(..., ge=300, le=850)
    is_guarantor: bool = True
    ownership_pct: float = Field(default=0.0, ge=0, le=100)


class RTLPropertyInput(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str = "SFR"
    square_footage: Optional[float] = None


class RTLRequest(BaseModel):
    # Loan Purpose
    loan_purpose: str  # Purchase, Refinance
    expected_closing_date: str
    first_payment_date: str
    maturity_date: str
    seasoning_days: int = 0
    
    # Entity/Borrower
    entity_name: str
    num_owners: int = Field(..., ge=1)
    guarantors: List[RTLGuarantorInput]
    
    # Experience
    rehabs_completed_and_sold: int = 0
    rehabs_completed_refinanced: int = 0
    rentals_acquired: int = 0
    gc_rehabs_completed: int = 0
    
    # Property
    property: RTLPropertyInput
    
    # Valuation
    purchase_price: float = Field(..., gt=0)
    borrower_cost_basis: float = Field(..., gt=0)
    as_is_value: float = Field(..., gt=0)
    after_repair_value: float = Field(..., gt=0)
    total_rehab_budget: float = Field(default=0, ge=0)
    sqft_expansion: float = 0.0
    
    # Flags
    change_of_use: bool = False
    conversion_of_structure: bool = False
    rehab_severity: str = "Light Rehab"  # Light Rehab, Heavy Rehab
    
    # Loan Request
    loan_amount: float = Field(..., gt=0)
    loan_term_months: int = Field(default=12, ge=1, le=36)
    interest_accrual_type: str = "Non-Dutch / Multiple Draws"


class RTLResponse(BaseModel):
    borrower_classification: str
    total_score: int
    max_ltv: float
    max_ltc: float
    max_ltarv: Optional[float]
    
    liquidity_requirement: float
    
    roi_ratio: float
    min_roi_required: float
    roi_check_passed: bool
    
    overall_pass: bool
    failures: List[str]
    
    # Calculated limits
    max_loan_ltv: float
    max_loan_ltc: float
    max_loan_ltarv: Optional[float]
    recommended_loan_amount: float
    
    processed_at: datetime


# ==================== BRIDGE LOAN MODELS ====================

class BridgePropertyInput(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str = "SFR"  # SFR, Condo, Townhome, 2 Unit, 3 Unit, 4 Unit, 5+ Unit
    units: int = Field(..., ge=1)
    square_footage: float = Field(..., gt=0)
    occupancy_pct: float = Field(default=1.0, ge=0, le=1)


class BridgeBorrowerInput(BaseModel):
    name: str
    fico: int = Field(..., ge=300, le=850)
    citizenship: str = "US Citizen"  # US Citizen, Permanent Resident, Foreign National
    bridge_experience: int = 0
    guc_experience: int = 0
    is_institutional: bool = False


class BridgeValuationInput(BaseModel):
    as_is_value: float = Field(..., gt=0)
    purchase_price: float = Field(..., gt=0)
    as_repaired_value: float = Field(..., gt=0)
    verified_hard_soft_costs: float = 0.0
    initial_cost_basis: float = 0.0
    condo_conversion: bool = False
    change_of_use: bool = False
    property_expansion_20pct: bool = False
    midstream_financing: bool = False
    arv_3x_multiplier: bool = False


class BridgeLoanInput(BaseModel):
    initial_loan_amount: float = Field(..., gt=0)
    rehab_amount: float = Field(default=0, ge=0)
    assignment_fees: float = Field(default=0, ge=0)
    current_debt: float = Field(default=0, ge=0)
    seasoning: str = ">12 Months"
    exit_strategy: str = "Rehab to Rent"


class BridgeCashFlowInput(BaseModel):
    annual_resi_rent: float = 0.0
    annual_comm_rent: float = 0.0
    annual_other_income: float = 0.0
    annual_property_taxes: float = 0.0
    annual_insurance: float = 0.0
    replacement_reserves: float = 0.0
    operating_expenses_pct: float = 0.12


class BridgeMarketInput(BaseModel):
    msa: str
    zhvi: float
    hpa: float
    dom: int


class BridgeRequest(BaseModel):
    property: BridgePropertyInput
    borrower: BridgeBorrowerInput
    valuation: BridgeValuationInput
    loan: BridgeLoanInput
    cash_flow: BridgeCashFlowInput = BridgeCashFlowInput()
    market: BridgeMarketInput
    
    loan_purpose: str = "Purchase"  # Purchase, Refinance
    transaction_type: str = "No Cash Out"  # No Cash Out, Cash Out
    rehab_type: str = "Light Rehab"  # Light Rehab, Heavy Rehab, Bridge (No Rehab)
    stabilized_property: bool = False


class BridgeEligibilityResult(BaseModel):
    test_name: str
    passed: bool
    details: Optional[str]


class BridgeLeverageResult(BaseModel):
    category: str
    loan_amount: float
    max_starting: float
    max_adjusted: float
    adjustment: float
    passed: bool


class BridgeResponse(BaseModel):
    ice_loan_type: str
    
    # Profitability
    profitability_ratio: float
    profitability_passed: bool
    
    # Cash Flow
    annual_ncf: float
    stabilized_dscr: float
    dscr_passed: bool
    
    # Leverage Tests
    ltv_test: BridgeLeverageResult
    ltc_test: BridgeLeverageResult
    ltarv_test: BridgeLeverageResult
    
    # Max Loan Amounts
    max_loan_ltv: float
    max_loan_ltc: float
    max_loan_ltarv: float
    max_loan_overall: float
    
    # Recommended Structure
    senior_loan: float
    junior_loan: float
    total_loan: float
    construction_budget: float
    
    # Eligibility
    eligibility_tests: List[BridgeEligibilityResult]
    
    # Pricing
    base_rate: float
    points: float
    final_rate: float
    
    # Decision
    overall_pass: bool
    failures: List[str]
    warnings: List[str]
    
    processed_at: datetime


# ==================== API ENDPOINTS ====================

@router.post("/rtl/analyze", response_model=RTLResponse)
async def analyze_rtl_loan(request: RTLRequest):
    """
    Analyze a Fix & Flip / RTL (Rehab-to-Live) loan application.
    
    This endpoint evaluates:
    - Borrower classification based on credit and experience
    - LTV/LTC/LTARV limits
    - ROI calculations
    - Liquidity requirements
    """
    try:
        # Convert request to internal format
        guarantors = [
            Guarantor(
                name=g.name,
                credit_score=g.credit_score,
                is_guarantor=g.is_guarantor,
                ownership_pct=g.ownership_pct
            )
            for g in request.guarantors
        ]
        
        property_info = RTLProperty(
            address=request.property.address,
            city=request.property.city,
            state=request.property.state,
            zip_code=request.property.zip_code,
            property_type=request.property.property_type,
            square_footage=request.property.square_footage
        )
        
        inputs = RTLInputs(
            loan_purpose=RTLLoanPurpose.PURCHASE if request.loan_purpose == "Purchase" else RTLLoanPurpose.REFINANCE,
            expected_closing_date=request.expected_closing_date,
            first_payment_date=request.first_payment_date,
            maturity_date=request.maturity_date,
            seasoning_days=request.seasoning_days,
            entity_name=request.entity_name,
            num_owners=request.num_owners,
            guarantors=guarantors,
            rehabs_completed_and_sold=request.rehabs_completed_and_sold,
            rehabs_completed_refinanced=request.rehabs_completed_refinanced,
            rentals_acquired=request.rentals_acquired,
            gc_rehabs_completed=request.gc_rehabs_completed,
            property=property_info,
            purchase_price=request.purchase_price,
            borrower_cost_basis=request.borrower_cost_basis,
            as_is_value=request.as_is_value,
            after_repair_value=request.after_repair_value,
            total_rehab_budget=request.total_rehab_budget,
            sqft_expansion=request.sqft_expansion,
            change_of_use=request.change_of_use,
            conversion_of_structure=request.conversion_of_structure,
            rehab_severity=RTLRehabType.LIGHT if request.rehab_severity == "Light Rehab" else RTLRehabType.HEAVY,
            loan_amount=request.loan_amount,
            loan_term_months=request.loan_term_months,
            interest_accrual_type=request.interest_accrual_type
        )
        
        # Run sizer
        result = run_rtl_sizer(inputs)
        
        # Calculate max loan amounts
        max_loan_ltv = inputs.as_is_value * result.max_ltv
        max_loan_ltc = inputs.borrower_cost_basis * result.max_ltc
        max_loan_ltarv = inputs.after_repair_value * result.max_ltarv if result.max_ltarv else None
        
        recommended_loan = min(
            max_loan_ltv, 
            max_loan_ltc, 
            max_loan_ltarv or float('inf'),
            request.loan_amount
        )
        
        return RTLResponse(
            borrower_classification=result.borrower_classification.value,
            total_score=result.total_score,
            max_ltv=result.max_ltv,
            max_ltc=result.max_ltc,
            max_ltarv=result.max_ltarv,
            liquidity_requirement=result.liquidity_requirement,
            roi_ratio=result.roi_ratio,
            min_roi_required=result.min_roi_required,
            roi_check_passed=result.roi_check_passed,
            overall_pass=result.overall_pass,
            failures=result.failures,
            max_loan_ltv=max_loan_ltv,
            max_loan_ltc=max_loan_ltc,
            max_loan_ltarv=max_loan_ltarv,
            recommended_loan_amount=recommended_loan,
            processed_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RTL analysis failed: {str(e)}")


@router.post("/bridge/analyze", response_model=BridgeResponse)
async def analyze_bridge_loan(request: BridgeRequest):
    """
    Analyze a Bridge loan application.
    
    Supports:
    - Internal 1-4 Bridge
    - Multi Bridge (5+ units)
    - 1-4 GUC (Ground Up Construction)
    
    Evaluates eligibility tests, leverage limits, and pricing.
    """
    try:
        # Convert request to internal format
        property_info = BridgeProperty(
            address=request.property.address,
            city=request.property.city,
            state=request.property.state,
            zip_code=request.property.zip_code,
            property_type=PropertyType(request.property.property_type.replace("+", "_PLUS")),
            units=request.property.units,
            square_footage=request.property.square_footage,
            occupancy_pct=request.property.occupancy_pct
        )
        
        borrower = BridgeBorrower(
            name=request.borrower.name,
            fico=request.borrower.fico,
            citizenship=Citizenship(request.borrower.citizenship),
            bridge_experience=request.borrower.bridge_experience,
            guc_experience=request.borrower.guc_experience,
            is_institutional=request.borrower.is_institutional
        )
        
        valuation = BridgeValuation(
            as_is_value=request.valuation.as_is_value,
            purchase_price=request.valuation.purchase_price,
            as_repaired_value=request.valuation.as_repaired_value,
            verified_hard_soft_costs=request.valuation.verified_hard_soft_costs,
            initial_cost_basis=request.valuation.initial_cost_basis,
            condo_conversion=request.valuation.condo_conversion,
            change_of_use=request.valuation.change_of_use,
            property_expansion_20pct=request.valuation.property_expansion_20pct,
            midstream_financing=request.valuation.midstream_financing,
            arv_3x_multiplier=request.valuation.arv_3x_multiplier
        )
        
        loan = BridgeLoanRequest(
            initial_loan_amount=request.loan.initial_loan_amount,
            rehab_amount=request.loan.rehab_amount,
            assignment_fees=request.loan.assignment_fees,
            current_debt=request.loan.current_debt,
            seasoning=request.loan.seasoning,
            exit_strategy=request.loan.exit_strategy
        )
        
        cash_flow = BridgeCashFlow(
            annual_resi_rent=request.cash_flow.annual_resi_rent,
            annual_comm_rent=request.cash_flow.annual_comm_rent,
            annual_other_income=request.cash_flow.annual_other_income,
            annual_property_taxes=request.cash_flow.annual_property_taxes,
            annual_insurance=request.cash_flow.annual_insurance,
            replacement_reserves=request.cash_flow.replacement_reserves,
            operating_expenses_pct=request.cash_flow.operating_expenses_pct
        )
        
        market = BridgeMarketData(
            msa=request.market.msa,
            zhvi=request.market.zhvi,
            hpa=request.market.hpa,
            dom=request.market.dom
        )
        
        inputs = BridgeInputs(
            property=property_info,
            borrower=borrower,
            valuation=valuation,
            loan=loan,
            cash_flow=cash_flow,
            market=market,
            loan_purpose=LoanPurpose(request.loan_purpose),
            transaction_type=TransactionType(request.transaction_type),
            rehab_type=RehabType(request.rehab_type),
            stabilized_property=request.stabilized_property
        )
        
        # Run sizer
        result = run_bridge_sizer(inputs)
        
        # Convert to response format
        return BridgeResponse(
            ice_loan_type=result.ice_loan_type,
            profitability_ratio=result.profitability_ratio,
            profitability_passed=result.profitability_passed,
            annual_ncf=result.annual_ncf,
            stabilized_dscr=result.stabilized_dscr,
            dscr_passed=result.dscr_passed,
            ltv_test=BridgeLeverageResult(**result.ltv_test.__dict__),
            ltc_test=BridgeLeverageResult(**result.ltc_test.__dict__),
            ltarv_test=BridgeLeverageResult(**result.ltarv_test.__dict__),
            max_loan_ltv=result.max_loan_ltv,
            max_loan_ltc=result.max_loan_ltc,
            max_loan_ltarv=result.max_loan_ltarv,
            max_loan_overall=result.max_loan_overall,
            senior_loan=result.senior_loan,
            junior_loan=result.junior_loan,
            total_loan=result.total_loan,
            construction_budget=result.construction_budget,
            eligibility_tests=[
                BridgeEligibilityResult(**t.__dict__) 
                for t in result.eligibility_tests
            ],
            base_rate=result.base_rate,
            points=result.points,
            final_rate=result.final_rate,
            overall_pass=result.overall_pass,
            failures=result.failures,
            warnings=result.warnings,
            processed_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge analysis failed: {str(e)}")


@router.get("/rtl/programs")
async def get_rtl_loan_programs():
    """Get available RTL (Fix & Flip) loan programs."""
    return get_rtl_programs()


@router.get("/bridge/programs")
async def get_bridge_loan_programs():
    """Get available Bridge loan programs."""
    return get_bridge_programs()


@router.post("/rtl/quick-check")
async def rtl_quick_check(
    loan_amount: float,
    as_is_value: float,
    arv: float,
    rehab_budget: float,
    credit_score: int,
    experience: int = 0
):
    """
    Quick eligibility check for RTL loans.
    Returns pass/fail with basic limits.
    """
    # Simplified check
    ltv = loan_amount / as_is_value if as_is_value > 0 else 1.0
    ltc = loan_amount / (as_is_value + rehab_budget) if (as_is_value + rehab_budget) > 0 else 1.0
    ltarv = loan_amount / arv if arv > 0 else 1.0
    
    # Determine max leverage based on experience
    if experience >= 10:
        max_ltv, max_ltc, max_ltarv = 0.90, 0.90, 0.75
    elif experience >= 3:
        max_ltv, max_ltc, max_ltarv = 0.85, 0.85, 0.70
    else:
        max_ltv, max_ltc, max_ltarv = 0.80, 0.80, 0.65
    
    passed = (ltv <= max_ltv and ltc <= max_ltc and ltarv <= max_ltarv and credit_score >= 680)
    
    return {
        "passed": passed,
        "ltv": f"{ltv:.1%}",
        "max_ltv": f"{max_ltv:.1%}",
        "ltc": f"{ltc:.1%}",
        "max_ltc": f"{max_ltc:.1%}",
        "ltarv": f"{ltarv:.1%}",
        "max_ltarv": f"{max_ltarv:.1%}",
        "credit_check": credit_score >= 680
    }


@router.post("/bridge/quick-check")
async def bridge_quick_check(
    loan_amount: float,
    as_is_value: float,
    arv: float,
    rehab_budget: float,
    fico: int,
    experience: int = 0,
    units: int = 1
):
    """
    Quick eligibility check for Bridge loans.
    Returns pass/fail with basic limits.
    """
    ltv = loan_amount / as_is_value if as_is_value > 0 else 1.0
    ltarv = loan_amount / arv if arv > 0 else 1.0
    total_cost = as_is_value + rehab_budget
    ltc = loan_amount / total_cost if total_cost > 0 else 1.0
    
    # Determine max leverage
    is_multi = units >= 5
    
    if experience >= 10:
        max_ltv = 0.80 if is_multi else 0.90
        max_ltarv = 0.70 if is_multi else 0.75
    elif experience >= 3:
        max_ltv = 0.75 if is_multi else 0.85
        max_ltarv = 0.65 if is_multi else 0.70
    else:
        max_ltv = 0.70 if is_multi else 0.80
        max_ltarv = 0.60 if is_multi else 0.65
    
    max_ltc = max_ltv  # Same as LTV typically
    
    profitability = arv / total_cost if total_cost > 0 else 0
    
    passed = (
        ltv <= max_ltv and 
        ltc <= max_ltc and 
        ltarv <= max_ltarv and 
        fico >= 680 and
        profitability >= 1.15
    )
    
    return {
        "passed": passed,
        "ltv": f"{ltv:.1%}",
        "max_ltv": f"{max_ltv:.1%}",
        "ltc": f"{ltc:.1%}",
        "max_ltc": f"{max_ltc:.1%}",
        "ltarv": f"{ltarv:.1%}",
        "max_ltarv": f"{max_ltarv:.1%}",
        "profitability": f"{profitability:.2f}x",
        "min_profitability": "1.15x",
        "credit_check": fico >= 680
    }
