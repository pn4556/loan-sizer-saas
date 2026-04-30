"""
Bridge Loan Sizer Logic
Based on: Guides Updated Bridge Sizer
Supports: Internal 1-4 Bridge, Multi Bridge, and 1-4 GUC programs
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RehabType(str, Enum):
    NONE = "Bridge (No Rehab)"
    LIGHT = "Light Rehab"
    HEAVY = "Heavy Rehab"


class LoanPurpose(str, Enum):
    PURCHASE = "Purchase"
    REFINANCE = "Refinance"
    CASH_OUT = "Cash Out"


class TransactionType(str, Enum):
    NO_CASH_OUT = "No Cash Out"
    CASH_OUT = "Cash Out"


class PropertyType(str, Enum):
    SFR = "SFR"
    CONDO = "Condo"
    TOWNHOME = "Townhome"
    PUD = "PUD"
    MULTI_2 = "2 Unit"
    MULTI_3 = "3 Unit"
    MULTI_4 = "4 Unit"
    MULTI_5_PLUS = "5+ Unit"


class ExperienceLevel(str, Enum):
    PROFESSIONAL = "Professional"  # 10+ bridge/GUC experience
    ESTABLISHED = "Established"    # 3-9 experience
    EXPERIENCED = "Experienced"    # Multi bridge experienced
    INEXPERIENCED = "Inexperienced"  # 0-2 experience


class Citizenship(str, Enum):
    US_CITIZEN = "US Citizen"
    PERMANENT_RESIDENT = "Permanent Resident"
    FOREIGN_NATIONAL = "Foreign National"


@dataclass
class BridgeProperty:
    address: str
    city: str
    state: str
    zip_code: str
    property_type: PropertyType
    units: int
    square_footage: float
    occupancy_pct: float = 1.0  # 1.0 = 100%


@dataclass
class BridgeBorrower:
    name: str
    fico: int
    citizenship: Citizenship
    bridge_experience: int  # Number of bridge loans completed
    guc_experience: int  # Ground up construction experience
    is_institutional: bool = False


@dataclass
class BridgeValuation:
    as_is_value: float
    purchase_price: float
    as_repaired_value: float
    verified_hard_soft_costs: float = 0.0
    initial_cost_basis: float = 0.0
    condo_conversion: bool = False
    change_of_use: bool = False
    property_expansion_20pct: bool = False
    midstream_financing: bool = False
    arv_3x_multiplier: bool = False


@dataclass
class BridgeLoanRequest:
    initial_loan_amount: float
    rehab_amount: float
    assignment_fees: float = 0.0
    current_debt: float = 0.0
    seasoning: str = ">12 Months"  # <6 Months, 6-12 Months, >12 Months
    exit_strategy: str = "Rehab to Rent"  # Rehab to Sell, Refinance, etc.


@dataclass
class BridgeCashFlow:
    annual_resi_rent: float = 0.0
    annual_comm_rent: float = 0.0
    annual_other_income: float = 0.0
    annual_property_taxes: float = 0.0
    annual_insurance: float = 0.0
    replacement_reserves: float = 0.0
    operating_expenses_pct: float = 0.12  # 12% default


@dataclass
class BridgeMarketData:
    msa: str
    zhvi: float  # Zillow Home Value Index
    hpa: float  # Home Price Appreciation
    dom: int  # Days on Market


@dataclass
class BridgeInputs:
    property: BridgeProperty
    borrower: BridgeBorrower
    valuation: BridgeValuation
    loan: BridgeLoanRequest
    cash_flow: BridgeCashFlow
    market: BridgeMarketData
    loan_purpose: LoanPurpose
    transaction_type: TransactionType
    rehab_type: RehabType
    stabilized_property: bool = False


@dataclass
class LeverageTest:
    category: str
    loan_amount: float
    max_starting: float
    max_adjusted: float
    adjustment: float
    passed: bool


@dataclass
class EligibilityTest:
    test_name: str
    passed: bool
    details: Optional[str] = None


@dataclass
class BridgeResults:
    # Program Selection (required)
    ice_loan_type: str
    profitability_ratio: float
    profitability_passed: bool
    annual_ncf: float
    stabilized_dscr: float
    dscr_passed: bool
    ltv_test: LeverageTest
    ltc_test: LeverageTest
    ltarv_test: LeverageTest
    max_loan_ltv: float
    max_loan_ltc: float
    max_loan_ltarv: float
    max_loan_overall: float
    senior_loan: float
    junior_loan: float
    total_loan: float
    construction_budget: float
    eligibility_tests: List[EligibilityTest]
    base_rate: float
    points: float
    rate_adjustments: Dict[str, float]
    final_rate: float
    overall_pass: bool
    failures: List[str]
    warnings: List[str]
    
    # Optional with defaults
    debt_yield_test: Optional[LeverageTest] = None
    min_profitability_required: float = 1.15
    min_dscr_required: float = 1.20


def get_fico_categorization(fico: int) -> str:
    """Categorize FICO score."""
    if fico >= 780:
        return "780+"
    elif fico >= 760:
        return "760-779"
    elif fico >= 740:
        return "740-759"
    elif fico >= 720:
        return "720-739"
    elif fico >= 700:
        return "700-719"
    elif fico >= 680:
        return "680-699"
    else:
        return "<680"


def get_experience_categorization(bridge_exp: int, guc_exp: int = 0) -> str:
    """Categorize borrower experience."""
    total_exp = bridge_exp + guc_exp
    if total_exp >= 10:
        return "10+ Experience"
    elif total_exp >= 5:
        return "5-9 Experience"
    elif total_exp >= 3:
        return "3-4 Experience"
    else:
        return "0-2 Experience"


def get_guc_categorization(guc_exp: int) -> str:
    """Categorize GUC experience."""
    if guc_exp >= 5:
        return "5+ GUC Experience"
    elif guc_exp >= 2:
        return "2-4 GUC Experience"
    else:
        return "<2 GUC Experience"


def get_ice_loan_type(borrower: BridgeBorrower, rehab_type: RehabType,
                      loan_purpose: LoanPurpose, transaction_type: TransactionType) -> str:
    """
    Generate ICE loan characterization.
    Format: "Experience / Rehab Type / Purpose / Transaction Type"
    """
    # Experience level
    if borrower.bridge_experience >= 10 or borrower.guc_experience >= 10:
        exp_level = "Professional"
    elif borrower.bridge_experience >= 3 or borrower.guc_experience >= 3:
        exp_level = "Established"
    else:
        exp_level = "Inexperienced"
    
    # Stabilized vs Rehab
    if rehab_type == RehabType.NONE:
        rehab_desc = "Stabilized"
    else:
        rehab_desc = rehab_type.value
    
    # Purpose
    purpose_desc = "Purchase" if loan_purpose == LoanPurpose.PURCHASE else "Refinance"
    
    # Transaction type
    trans_desc = "No Cash Out" if transaction_type == TransactionType.NO_CASH_OUT else "Cash Out"
    
    return f"{exp_level} / {rehab_desc} / {purpose_desc} / {trans_desc}"


def calculate_profitability_ratio(arv: float, cost_basis: float) -> float:
    """Calculate ARV/Cost Basis profitability ratio."""
    if cost_basis > 0:
        return arv / cost_basis
    return 0.0


def calculate_cash_flow(cash_flow: BridgeCashFlow) -> Tuple[float, float]:
    """
    Calculate net cash flow and DSCR.
    
    Returns: (annual_ncf, dscr)
    """
    # Gross potential revenue
    gpr = (cash_flow.annual_resi_rent + 
           cash_flow.annual_comm_rent + 
           cash_flow.annual_other_income)
    
    # Operating expenses
    operating_expenses = gpr * cash_flow.operating_expenses_pct
    
    # Effective gross income
    egi = gpr - operating_expenses
    
    # Net operating income
    noi = egi - cash_flow.annual_property_taxes - cash_flow.annual_insurance
    
    # Net cash flow
    ncf = noi - cash_flow.replacement_reserves
    
    # DSCR (simplified - would need actual debt service)
    # Assuming 7% interest, interest-only
    # This is a placeholder - real calc would use actual loan terms
    dscr = 1.25  # Placeholder
    
    return ncf, dscr


def get_program_maximums(borrower: BridgeBorrower, rehab_type: RehabType,
                         loan_purpose: LoanPurpose, transaction_type: TransactionType,
                         property_type: PropertyType, is_multi: bool = False) -> Dict:
    """
    Get program maximums based on borrower profile and loan characteristics.
    
    Returns dict with:
    - max_ltv_as_is
    - max_ltc
    - max_ltarv
    - additional_requirements
    """
    
    # Determine experience level
    if borrower.bridge_experience >= 10:
        exp_level = "Professional"
    elif borrower.bridge_experience >= 3:
        exp_level = "Established"
    else:
        exp_level = "Inexperienced"
    
    # Multi-family / Mixed-use programs
    if is_multi:
        return get_multi_bridge_maximums(exp_level, rehab_type, loan_purpose, transaction_type)
    
    # Internal 1-4 Bridge Program
    if rehab_type == RehabType.NONE:
        # Stabilized
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.80, "max_ltc": 0.80, "max_ltarv": None, "notes": ""}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.70, "max_ltc": None, "max_ltarv": None, "notes": ""}
        else:  # Cash out
            return {"max_ltv": 0.65, "max_ltc": None, "max_ltarv": None, "notes": ""}
    
    elif rehab_type == RehabType.LIGHT:
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.90, "max_ltc": 0.90, "max_ltarv": 0.75, "notes": ""}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.75, "max_ltc": None, "max_ltarv": 0.70, "notes": ""}
        else:  # Cash out
            return {"max_ltv": 0.65, "max_ltc": None, "max_ltarv": 0.60, "notes": ""}
    
    elif rehab_type == RehabType.HEAVY:
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.85, "max_ltc": 0.85, "max_ltarv": 0.70, "notes": ""}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.70, "max_ltc": None, "max_ltarv": 0.65, "notes": ""}
        else:  # Cash out - not allowed for heavy rehab
            return {"max_ltv": None, "max_ltc": None, "max_ltarv": None, "notes": "Cash out not allowed for heavy rehab"}
    
    return {"max_ltv": 0.80, "max_ltc": 0.80, "max_ltarv": 0.70, "notes": ""}


def get_multi_bridge_maximums(exp_level: str, rehab_type: RehabType,
                               loan_purpose: LoanPurpose, transaction_type: TransactionType) -> Dict:
    """Get maximums for multi-family bridge loans."""
    
    is_exp = exp_level in ["Professional", "Established"]
    
    if rehab_type == RehabType.NONE:
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.75, "max_ltc": 0.75, "max_ltarv": None, "notes": ""}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.70, "max_ltc": None, "max_ltarv": None, "notes": ""}
        else:
            return {"max_ltv": 0.65, "max_ltc": None, "max_ltarv": None, "notes": ""}
    
    elif rehab_type == RehabType.LIGHT:
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.80, "max_ltc": 0.80, "max_ltarv": 0.70, 
                    "notes": "" if is_exp else "All Closing Costs Paid by Sponsor"}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.70, "max_ltc": None, "max_ltarv": 0.65,
                    "notes": "All Closing Costs Paid by Sponsor"}
        else:
            return {"max_ltv": 0.65, "max_ltc": None, "max_ltarv": 0.60, "notes": ""}
    
    elif rehab_type == RehabType.HEAVY:
        if loan_purpose == LoanPurpose.PURCHASE and transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.80, "max_ltc": 0.80, "max_ltarv": 0.65, 
                    "notes": "" if is_exp else "All Closing Costs Paid by Sponsor"}
        elif transaction_type == TransactionType.NO_CASH_OUT:
            return {"max_ltv": 0.65, "max_ltc": None, "max_ltarv": 0.60,
                    "notes": "All Closing Costs Paid by Sponsor"}
        else:
            return {"max_ltv": None, "max_ltc": None, "max_ltarv": None, "notes": "Cash out not allowed"}
    
    return {"max_ltv": 0.75, "max_ltc": 0.75, "max_ltarv": 0.70, "notes": ""}


def get_guc_maximums(guc_exp: int, loan_purpose: LoanPurpose) -> Dict:
    """Get maximums for Ground Up Construction (GUC) loans."""
    
    if guc_exp >= 5:
        if loan_purpose == LoanPurpose.PURCHASE:
            return {"max_ltv": 0.75, "max_ltc": 0.75, "max_ltarv": 0.70, "max_lttc": 0.85}
        else:  # Refinance
            return {"max_ltv": 0.60, "max_ltc": None, "max_ltarv": 0.70, "max_lttc": 0.85}
    elif guc_exp >= 2:
        if loan_purpose == LoanPurpose.PURCHASE:
            return {"max_ltv": 0.70, "max_ltc": 0.70, "max_ltarv": 0.65, "max_lttc": 0.80}
        else:  # Refinance
            return {"max_ltv": 0.60, "max_ltc": None, "max_ltarv": 0.65, "max_lttc": 0.80}
    else:
        # < 2 experience - not eligible
        return {"max_ltv": None, "max_ltc": None, "max_ltarv": None, "max_lttc": None, 
                "notes": "Minimum 2 GUC projects required"}


def calculate_leverage_tests(inputs: BridgeInputs, 
                              max_ltv: float, 
                              max_ltc: float, 
                              max_ltarv: Optional[float]) -> Tuple[LeverageTest, LeverageTest, LeverageTest, float]:
    """
    Calculate LTV, LTC, and LTARV tests.
    
    Returns: (ltv_test, ltc_test, ltarv_test, max_loan_amount)
    """
    valuation = inputs.valuation
    loan = inputs.loan
    
    # Calculate total cost basis
    total_cost = valuation.initial_cost_basis + loan.rehab_amount + loan.assignment_fees
    
    # Calculate requested loan ratios
    requested_ltv = loan.initial_loan_amount / valuation.as_is_value if valuation.as_is_value > 0 else 1.0
    requested_ltc = loan.initial_loan_amount / total_cost if total_cost > 0 else 1.0
    requested_ltarv = (loan.initial_loan_amount / valuation.as_repaired_value 
                       if valuation.as_repaired_value > 0 else None)
    
    # Max loan amounts
    max_loan_ltv = valuation.as_is_value * max_ltv
    max_loan_ltc = total_cost * max_ltc if max_ltc else 0
    max_loan_ltarv = (valuation.as_repaired_value * max_ltarv) if max_ltarv else float('inf')
    
    # Overall max loan
    max_loan = min(max_loan_ltv, max_loan_ltc, max_loan_ltarv)
    
    # Create test results
    ltv_test = LeverageTest(
        category="Loan to Value",
        loan_amount=loan.initial_loan_amount,
        max_starting=max_ltv,
        max_adjusted=max_ltv,  # Adjustments applied separately
        adjustment=0.0,
        passed=requested_ltv <= max_ltv
    )
    
    ltc_test = LeverageTest(
        category="Loan To Cost",
        loan_amount=loan.initial_loan_amount,
        max_starting=max_ltc if max_ltc else 0,
        max_adjusted=max_ltc if max_ltc else 0,
        adjustment=0.0,
        passed=requested_ltc <= max_ltc if max_ltc else True
    )
    
    ltarv_test = LeverageTest(
        category="Loan To As Repaired Value",
        loan_amount=loan.initial_loan_amount,
        max_starting=max_ltarv if max_ltarv else 0,
        max_adjusted=max_ltarv if max_ltarv else 0,
        adjustment=0.0,
        passed=(requested_ltarv <= max_ltarv) if max_ltarv and requested_ltarv else True
    )
    
    return ltv_test, ltc_test, ltarv_test, max_loan


def run_eligibility_tests(inputs: BridgeInputs) -> List[EligibilityTest]:
    """Run all bridge eligibility tests."""
    
    tests = []
    v = inputs.valuation
    p = inputs.property
    l = inputs.loan
    b = inputs.borrower
    
    # 1. Rehab Type test
    tests.append(EligibilityTest("Rehab Type", True, inputs.rehab_type.value))
    
    # 2. Min Loan Amount ($100K typically)
    min_loan = 100000
    tests.append(EligibilityTest(
        "Min Loan Amount", 
        l.initial_loan_amount >= min_loan,
        f"${l.initial_loan_amount:,.0f} vs ${min_loan:,.0f} min"
    ))
    
    # 3. Max Budget / Loan Amount
    max_budget_ratio = 0.50  # Rehab budget max 50% of loan
    budget_ratio = l.rehab_amount / l.initial_loan_amount if l.initial_loan_amount > 0 else 0
    tests.append(EligibilityTest(
        "Max Budget / Loan Amount",
        budget_ratio <= max_budget_ratio,
        f"{budget_ratio:.1%} vs {max_budget_ratio:.1%} max"
    ))
    
    # 4. Min Property Value ($80K per unit for 1-4)
    min_per_unit = 80000
    min_value = min_per_unit * p.units
    tests.append(EligibilityTest(
        "Min Property Value",
        v.as_is_value >= min_value,
        f"${v.as_is_value:,.0f} vs ${min_value:,.0f} min"
    ))
    
    # 5. Square footage
    min_sqft = 600  # Typical minimum
    tests.append(EligibilityTest(
        "Square footage",
        p.square_footage >= min_sqft,
        f"{p.square_footage:,.0f} vs {min_sqft} min"
    ))
    
    # 6. Citizenship
    tests.append(EligibilityTest(
        "Citizenship",
        True,
        b.citizenship.value
    ))
    
    # 7. Rural Property/Population Density
    # Would need zip code lookup - placeholder
    tests.append(EligibilityTest("Rural Property/Pop. Density", True, "Check required"))
    
    # 8. Profitability (ARV/Cost Basis)
    prof_ratio = calculate_profitability_ratio(v.as_repaired_value, v.initial_cost_basis)
    min_profitability = 1.15
    tests.append(EligibilityTest(
        "Profitability (ARV/Cost Basis)",
        prof_ratio >= min_profitability,
        f"{prof_ratio:.2f}x vs {min_profitability:.2f}x min"
    ))
    
    # 9. Assignment Fees
    max_assignment = 50000  # Typical max
    tests.append(EligibilityTest(
        "Assignment Fees",
        l.assignment_fees <= max_assignment,
        f"${l.assignment_fees:,.0f} vs ${max_assignment:,.0f} max"
    ))
    
    # 10. Stabilized DSCR (for stabilized properties)
    if inputs.rehab_type == RehabType.NONE and inputs.stabilized_property:
        _, dscr = calculate_cash_flow(inputs.cash_flow)
        tests.append(EligibilityTest(
            "Stabilized DSCR",
            dscr >= 1.20,
            f"{dscr:.2f}x vs 1.20x min"
        ))
    else:
        tests.append(EligibilityTest("Stabilized DSCR", True, "N/A - Not stabilized"))
    
    # 11. 1-4 Family Rent Yield (min 10%)
    # Annual rent / loan amount
    annual_rent = inputs.cash_flow.annual_resi_rent
    rent_yield = annual_rent / l.initial_loan_amount if l.initial_loan_amount > 0 else 0
    min_yield = 0.10
    tests.append(EligibilityTest(
        "1-4 Family Rent Yield",
        rent_yield >= min_yield or p.units > 4,  # Only for 1-4
        f"{rent_yield:.1%} vs {min_yield:.1%} min"
    ))
    
    return tests


def get_bridge_pricing(borrower: BridgeBorrower, rehab_type: RehabType,
                       loan_amount: float, is_multi: bool = False) -> Tuple[float, float, Dict]:
    """
    Get bridge loan pricing.
    
    Returns: (base_rate, points, adjustments)
    """
    # Base rates by rehab type
    if rehab_type == RehabType.NONE:
        base_rate = 0.0875  # 8.75%
        base_points = 0.0075  # 0.75 points
    elif rehab_type == RehabType.LIGHT:
        base_rate = 0.0875  # 8.75%
        base_points = 0.005  # 0.50 points
    else:  # Heavy
        base_rate = 0.09  # 9.0%
        base_points = 0.0075  # 0.75 points
    
    adjustments = {}
    
    # Loan Level Adjusters
    if borrower.fico < 700:
        adjustments['fico_lt_700'] = 0.0025
    
    if loan_amount > 2500000:
        adjustments['loan_gt_2.5m'] = 0.01
    elif loan_amount > 1500000:
        adjustments['loan_gt_1.5m'] = 0.005
    
    if is_multi:
        adjustments['multi_family'] = 0.01
    
    # Experience-based pricing
    if borrower.bridge_experience >= 10:
        adjustments['institutional_10_plus'] = -0.005  # -0.50% for experienced
    
    final_rate = base_rate + sum(adjustments.values())
    
    return base_rate, base_points, adjustments, final_rate


def run_bridge_sizer(inputs: BridgeInputs) -> BridgeResults:
    """Run the complete Bridge loan sizer."""
    
    failures = []
    warnings = []
    
    # 1. Get ICE Loan Type
    ice_loan_type = get_ice_loan_type(
        inputs.borrower, inputs.rehab_type,
        inputs.loan_purpose, inputs.transaction_type
    )
    
    # 2. Calculate Profitability
    prof_ratio = calculate_profitability_ratio(
        inputs.valuation.as_repaired_value,
        inputs.valuation.initial_cost_basis
    )
    prof_passed = prof_ratio >= 1.15
    if not prof_passed:
        failures.append(f"Profitability ratio {prof_ratio:.2f}x below 1.15x minimum")
    
    # 3. Calculate Cash Flow
    annual_ncf, dscr = calculate_cash_flow(inputs.cash_flow)
    dscr_passed = dscr >= 1.20 or not inputs.stabilized_property
    if not dscr_passed:
        failures.append(f"DSCR {dscr:.2f}x below 1.20x minimum")
    
    # 4. Get Program Maximums
    is_multi = inputs.property.units >= 5
    program_max = get_program_maximums(
        inputs.borrower, inputs.rehab_type,
        inputs.loan_purpose, inputs.transaction_type,
        inputs.property.property_type, is_multi
    )
    
    max_ltv = program_max['max_ltv']
    max_ltc = program_max['max_ltc']
    max_ltarv = program_max.get('max_ltarv')
    
    if program_max.get('notes'):
        warnings.append(program_max['notes'])
    
    # 5. Calculate Leverage Tests
    ltv_test, ltc_test, ltarv_test, max_loan = calculate_leverage_tests(
        inputs, max_ltv, max_ltc, max_ltarv
    )
    
    if not ltv_test.passed:
        failures.append(f"LTV test failed: {ltv_test.loan_amount/max_ltv:.1%} > {max_ltv:.1%}")
    if not ltc_test.passed:
        failures.append(f"LTC test failed")
    if not ltarv_test.passed:
        failures.append(f"LTARV test failed")
    
    # 6. Calculate Max Loan Amounts
    max_loan_ltv = inputs.valuation.as_is_value * max_ltv if max_ltv else 0
    total_cost = (inputs.valuation.initial_cost_basis + 
                  inputs.loan.rehab_amount + 
                  inputs.loan.assignment_fees)
    max_loan_ltc = total_cost * max_ltc if max_ltc else 0
    max_loan_ltarv = (inputs.valuation.as_repaired_value * max_ltarv) if max_ltarv else float('inf')
    
    # 7. Recommended Structure
    senior_loan = max_loan
    junior_loan = 0  # No mezz for now
    total_loan = senior_loan
    construction_budget = inputs.loan.rehab_amount
    
    # 8. Run Eligibility Tests
    eligibility_tests = run_eligibility_tests(inputs)
    
    for test in eligibility_tests:
        if not test.passed:
            failures.append(f"{test.test_name}: {test.details}")
    
    # 9. Get Pricing
    base_rate, points, adjustments, final_rate = get_bridge_pricing(
        inputs.borrower, inputs.rehab_type, inputs.loan.initial_loan_amount, is_multi
    )
    
    # 10. Overall Decision
    overall_pass = len(failures) == 0
    
    # Debt yield test (for multi-family)
    if is_multi:
        noi = annual_ncf + inputs.cash_flow.replacement_reserves  # Approximate
        debt_yield = noi / total_loan if total_loan > 0 else 0
        min_debt_yield = 0.08  # 8%
        debt_yield_test = LeverageTest(
            category="Debt Yield",
            loan_amount=total_loan,
            max_starting=min_debt_yield,
            max_adjusted=min_debt_yield,
            adjustment=0,
            passed=debt_yield >= min_debt_yield
        )
        if not debt_yield_test.passed:
            failures.append(f"Debt yield {debt_yield:.1%} below {min_debt_yield:.1%} minimum")
    else:
        debt_yield_test = None
    
    return BridgeResults(
        ice_loan_type=ice_loan_type,
        profitability_ratio=prof_ratio,
        min_profitability_required=1.15,
        profitability_passed=prof_passed,
        annual_ncf=annual_ncf,
        stabilized_dscr=dscr,
        min_dscr_required=1.20,
        dscr_passed=dscr_passed,
        ltv_test=ltv_test,
        ltc_test=ltc_test,
        ltarv_test=ltarv_test,
        debt_yield_test=debt_yield_test,
        max_loan_ltv=max_loan_ltv,
        max_loan_ltc=max_loan_ltc,
        max_loan_ltarv=max_loan_ltarv if max_ltarv else 0,
        max_loan_overall=max_loan,
        senior_loan=senior_loan,
        junior_loan=junior_loan,
        total_loan=total_loan,
        construction_budget=construction_budget,
        eligibility_tests=eligibility_tests,
        base_rate=base_rate,
        points=points,
        rate_adjustments=adjustments,
        final_rate=final_rate,
        overall_pass=overall_pass,
        failures=failures,
        warnings=warnings
    )


def get_bridge_programs() -> List[Dict]:
    """Get available Bridge loan programs."""
    return [
        {
            "name": "Internal 1-4 Bridge",
            "description": "Bridge financing for 1-4 family residential properties",
            "property_types": ["SFR", "Condo", "Townhome", "2-4 Unit"],
            "max_ltv": 0.90,
            "max_term": 24,
            "min_fico": 680,
        },
        {
            "name": "Multi Bridge",
            "description": "Bridge financing for 5+ unit multifamily properties",
            "property_types": ["5+ Unit", "Mixed-Use"],
            "max_ltv": 0.80,
            "max_term": 24,
            "min_fico": 680,
            "min_dscr": 1.20,
        },
        {
            "name": "1-4 GUC (Ground Up)",
            "description": "Ground up construction financing for 1-4 family properties",
            "property_types": ["SFR", "Condo", "Townhome", "2-4 Unit"],
            "max_ltv": 0.75,
            "max_ltc": 0.75,
            "max_term": 18,
            "min_experience": 2,
        }
    ]
