"""
EV RTL (Fix & Flip / Rehab) Loan Sizer Logic
Based on: EV RTL Sizer_Jan 26
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RehabType(str, Enum):
    LIGHT = "Light Rehab"
    HEAVY = "Heavy Rehab"


class LoanPurpose(str, Enum):
    PURCHASE = "Purchase"
    REFINANCE = "Refinance"


class BorrowerClassification(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


@dataclass
class Guarantor:
    name: str
    credit_score: int
    is_guarantor: bool = True
    ownership_pct: float = 0.0


@dataclass
class RTLProperty:
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str  # SFR, Condo, Townhome, etc.
    square_footage: Optional[float] = None


@dataclass
class RTLInputs:
    # Loan Purpose (required)
    loan_purpose: LoanPurpose
    expected_closing_date: str
    first_payment_date: str
    maturity_date: str
    entity_name: str
    num_owners: int
    guarantors: List[Guarantor]
    property: RTLProperty
    purchase_price: float
    borrower_cost_basis: float
    as_is_value: float
    after_repair_value: float
    total_rehab_budget: float
    loan_amount: float
    
    # Optional fields with defaults
    seasoning_days: int = 0
    rehabs_completed_and_sold: int = 0
    rehabs_completed_refinanced: int = 0
    rentals_acquired: int = 0
    gc_rehabs_completed: int = 0
    sqft_expansion: float = 0.0
    change_of_use: bool = False
    conversion_of_structure: bool = False
    rehab_severity: RehabType = RehabType.LIGHT
    loan_term_months: int = 12
    interest_accrual_type: str = "Non-Dutch / Multiple Draws"


@dataclass
class RTLResults:
    # Borrower Classification
    borrower_classification: BorrowerClassification
    total_score: int
    
    # LTV/LTC Limits
    max_ltv: float
    max_ltc: float
    max_ltarv: Optional[float]
    
    # Leverage Reductions
    leverage_reductions: Dict[str, float]
    
    # Liquidity Requirement
    liquidity_requirement: float
    
    # ROI
    roi_ratio: float
    min_roi_required: float
    roi_check_passed: bool
    
    # Decision
    overall_pass: bool
    failures: List[str]


def calculate_borrower_classification(guarantors: List[Guarantor], 
                                       total_experience: int) -> Tuple[BorrowerClassification, int]:
    """
    Calculate borrower classification based on credit scores and experience.
    
    Scoring:
    - Credit Decision Score:
      >=700: 3 points
      680-699: 1 point
      <680: 0 points
    
    - # of Verified Experience:
      10+: 7 points
      3-9: 5 points
      0-2: 1 point
    
    Classification:
    - A+: >=7 points
    - A: 5-6 points
    - B: 2-4 points
    - C: <2 points
    """
    # Get primary guarantor credit score
    primary_guarantor = next((g for g in guarantors if g.is_guarantor), None)
    if not primary_guarantor:
        return BorrowerClassification.C, 0
    
    credit_score = primary_guarantor.credit_score
    
    # Credit score points
    if credit_score >= 700:
        credit_points = 3
    elif credit_score >= 680:
        credit_points = 1
    else:
        credit_points = 0
    
    # Experience points
    if total_experience >= 10:
        exp_points = 7
    elif total_experience >= 3:
        exp_points = 5
    else:
        exp_points = 1
    
    total_score = credit_points + exp_points
    
    # Classification
    if total_score >= 7:
        classification = BorrowerClassification.A_PLUS
    elif total_score >= 5:
        classification = BorrowerClassification.A
    elif total_score >= 2:
        classification = BorrowerClassification.B
    else:
        classification = BorrowerClassification.C
    
    return classification, total_score


def calculate_experience(inputs: RTLInputs) -> int:
    """Calculate total qualifying experience."""
    # Qualifying experience = rehabs completed and sold + rentals acquired
    # (GC work counts at reduced rate typically)
    experience = (inputs.rehabs_completed_and_sold + 
                  inputs.rehabs_completed_refinanced +
                  inputs.rentals_acquired)
    return max(experience, 0)


def get_ltv_limits(borrower_class: BorrowerClassification, 
                   rehab_type: RehabType,
                   loan_purpose: LoanPurpose) -> Tuple[float, float, Optional[float]]:
    """
    Get LTV/LTC limits based on borrower classification and rehab type.
    
    Returns: (max_ltv, max_ltc, max_ltarv)
    """
    # Professional/Established Borrowers
    if borrower_class in [BorrowerClassification.A_PLUS, BorrowerClassification.A]:
        if rehab_type == RehabType.LIGHT:
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.90, 0.90, 0.75
            else:  # Refinance
                return 0.75, 0.75, 0.70
        elif rehab_type == RehabType.HEAVY:
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.85, 0.85, 0.70
            else:  # Refinance
                return 0.70, 0.70, 0.65
    
    # B Classification
    elif borrower_class == BorrowerClassification.B:
        if rehab_type == RehabType.LIGHT:
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.85, 0.85, 0.70
            else:
                return 0.70, 0.70, 0.65
        elif rehab_type == RehabType.HEAVY:
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.80, 0.80, 0.65
            else:
                return 0.65, 0.65, 0.60
    
    # C Classification
    else:  # C
        if rehab_type == RehabType.LIGHT:
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.80, 0.80, 0.65
            else:
                return 0.65, 0.65, 0.60
        else:  # Heavy
            if loan_purpose == LoanPurpose.PURCHASE:
                return 0.75, 0.75, 0.60
            else:
                return 0.60, 0.60, 0.55
    
    return 0.80, 0.80, 0.65  # Default


def calculate_leverage_reductions(hpa_decline: float = 0.0,
                                   zhvi_multiplier: float = 1.0) -> Dict[str, float]:
    """
    Calculate leverage reductions based on market conditions.
    
    Heavy Rehab Projects: Reduction varies by class
    HPA Decline 0-10%: Reduction
    HPA Decline >10%: Larger reduction
    ZHVI Multiplier >200%: Reduction
    ZHVI Multiplier >300%: Larger reduction
    """
    reductions = {
        'hpa_decline_0_10': 0.0,
        'hpa_decline_10_plus': 0.0,
        'zhvi_200_300': 0.0,
        'zhvi_300_plus': 0.0,
    }
    
    # HPA decline reductions
    if hpa_decline > 0.10:
        reductions['hpa_decline_10_plus'] = min(hpa_decline, 0.15)
    elif hpa_decline > 0:
        reductions['hpa_decline_0_10'] = hpa_decline * 0.5
    
    # ZHVI multiplier reductions
    if zhvi_multiplier > 3.0:
        reductions['zhvi_300_plus'] = 0.10
    elif zhvi_multiplier > 2.0:
        reductions['zhvi_200_300'] = 0.05
    
    return reductions


def calculate_liquidity_requirement(interest_payments: float,
                                     non_financed_rehab: float,
                                     down_payment: float,
                                     closing_costs: float) -> float:
    """
    Calculate liquidity requirement.
    
    Components:
    - Number of Interest Payments Required (typically 3-6 months)
    - Non-Financed Rehab Portion
    - Down Payment for Purchase Loans
    - Closing Costs (typically 5% of purchase price)
    """
    return interest_payments + non_financed_rehab + down_payment + closing_costs


def calculate_roi(cost_basis: float, arv: float, 
                  closing_costs_pct: float = 0.05,
                  experience_level: str = "experienced") -> Tuple[float, float, bool]:
    """
    Calculate ROI for Fix & Flip profitability.
    
    Returns: (roi_ratio, min_roi_required, passed)
    """
    # Estimated closing costs
    closing_costs = cost_basis * closing_costs_pct
    
    # Net profit estimate (simplified)
    net_profit = arv - cost_basis - closing_costs
    
    # ROI ratio
    if cost_basis > 0:
        roi_ratio = net_profit / cost_basis
    else:
        roi_ratio = 0.0
    
    # Minimum ROI based on experience
    if experience_level == "experienced":
        min_roi = 0.10  # 10%
    elif experience_level == "intermediate":
        min_roi = 0.15  # 15%
    else:  # beginner
        min_roi = 0.20  # 20%
    
    passed = roi_ratio >= min_roi
    
    return roi_ratio, min_roi, passed


def run_rtl_sizer(inputs: RTLInputs) -> RTLResults:
    """Run the complete RTL (Fix & Flip) loan sizer."""
    
    failures = []
    
    # 1. Calculate Experience
    total_experience = calculate_experience(inputs)
    
    # 2. Calculate Borrower Classification
    borrower_class, total_score = calculate_borrower_classification(
        inputs.guarantors, total_experience
    )
    
    # 3. Get LTV/LTC Limits
    max_ltv, max_ltc, max_ltarv = get_ltv_limits(
        borrower_class, inputs.rehab_severity, inputs.loan_purpose
    )
    
    # 4. Calculate Leverage Reductions
    leverage_reductions = calculate_leverage_reductions()
    
    # 5. Calculate Liquidity Requirement
    # Estimate 3-6 months of interest payments
    estimated_rate = 0.10  # 10% annual
    monthly_interest = inputs.loan_amount * estimated_rate / 12
    interest_payments_required = monthly_interest * 3  # 3 months
    
    # Down payment (for purchase)
    down_payment = 0.0
    if inputs.loan_purpose == LoanPurpose.PURCHASE:
        down_payment = inputs.purchase_price * (1 - max_ltv)
    
    closing_costs = inputs.purchase_price * 0.05
    
    liquidity_requirement = calculate_liquidity_requirement(
        interest_payments_required, 0.0, down_payment, closing_costs
    )
    
    # 6. Calculate ROI
    experience_level = "experienced" if total_experience >= 5 else "intermediate" if total_experience >= 2 else "beginner"
    roi_ratio, min_roi, roi_passed = calculate_roi(
        inputs.borrower_cost_basis, 
        inputs.after_repair_value,
        experience_level=experience_level
    )
    
    if not roi_passed:
        failures.append(f"ROI check failed: {roi_ratio:.1%} < {min_roi:.1%} minimum")
    
    # 7. Calculate actual ratios
    actual_ltv = inputs.loan_amount / inputs.as_is_value if inputs.as_is_value > 0 else 1.0
    actual_ltc = inputs.loan_amount / inputs.borrower_cost_basis if inputs.borrower_cost_basis > 0 else 1.0
    actual_ltarv = inputs.loan_amount / inputs.after_repair_value if inputs.after_repair_value > 0 else None
    
    # 8. Check leverage limits
    if actual_ltv > max_ltv:
        failures.append(f"LTV {actual_ltv:.1%} exceeds maximum {max_ltv:.1%}")
    
    if actual_ltc > max_ltc:
        failures.append(f"LTC {actual_ltc:.1%} exceeds maximum {max_ltc:.1%}")
    
    if actual_ltarv and max_ltarv and actual_ltarv > max_ltarv:
        failures.append(f"LTARV {actual_ltarv:.1%} exceeds maximum {max_ltarv:.1%}")
    
    # 9. Check term requirements
    if inputs.loan_term_months > 18 and inputs.rehab_severity == RehabType.HEAVY:
        failures.append("Heavy rehab limited to 18 months")
    
    # Overall decision
    overall_pass = len(failures) == 0
    
    return RTLResults(
        borrower_classification=borrower_class,
        total_score=total_score,
        max_ltv=max_ltv,
        max_ltc=max_ltc,
        max_ltarv=max_ltarv,
        leverage_reductions=leverage_reductions,
        liquidity_requirement=liquidity_requirement,
        roi_ratio=roi_ratio,
        min_roi_required=min_roi,
        roi_check_passed=roi_passed,
        overall_pass=overall_pass,
        failures=failures
    )


def get_rtl_programs() -> List[Dict]:
    """Get available RTL (Fix & Flip) loan programs."""
    return [
        {
            "name": "Fix & Flip - Light Rehab",
            "description": "Up to 90% LTC for experienced borrowers on light cosmetic rehabs",
            "max_ltv": 0.90,
            "max_ltc": 0.90,
            "max_ltarv": 0.75,
            "max_term": 12,
            "min_experience": 0,
        },
        {
            "name": "Fix & Flip - Heavy Rehab",
            "description": "Up to 85% LTC for structural renovations and major rehabs",
            "max_ltv": 0.85,
            "max_ltc": 0.85,
            "max_ltarv": 0.70,
            "max_term": 18,
            "min_experience": 2,
        },
        {
            "name": "Bridge Plus",
            "description": "Extended 36-month term for complex projects",
            "max_ltv": 0.80,
            "max_ltc": 0.80,
            "max_ltarv": 0.70,
            "max_term": 36,
            "min_experience": 5,
        }
    ]
