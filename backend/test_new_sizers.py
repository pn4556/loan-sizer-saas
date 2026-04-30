"""
Test examples for RTL (Fix & Flip) and Bridge Loan Sizers
Real-world scenarios to validate the implementation
"""

import json
from datetime import datetime

# Import the sizers
from rtl_sizer_logic import (
    RTLInputs, RTLProperty, Guarantor, run_rtl_sizer,
    LoanPurpose as RTLLoanPurpose, RehabType as RTLRehabType,
    get_rtl_programs
)
from bridge_sizer_logic import (
    BridgeInputs, BridgeProperty, BridgeBorrower, BridgeValuation,
    BridgeLoanRequest, BridgeCashFlow, BridgeMarketData, run_bridge_sizer,
    LoanPurpose, RehabType, TransactionType, Citizenship, PropertyType,
    get_bridge_programs
)


def test_rtl_scenario_1():
    """
    Scenario 1: Experienced Investor - Light Rehab Purchase
    
    Borrower: Professional investor with 11 projects
    Property: SFR in Miami, light cosmetic rehab
    Loan: $382,500 on $450K as-is, $750K ARV
    """
    print("=" * 80)
    print("TEST 1: RTL - Experienced Investor Light Rehab")
    print("=" * 80)
    
    inputs = RTLInputs(
        loan_purpose=RTLLoanPurpose.PURCHASE,
        expected_closing_date="2025-12-01",
        first_payment_date="2026-02-01",
        maturity_date="2026-12-01",
        seasoning_days=0,
        entity_name="Topp Investments LLC",
        num_owners=1,
        guarantors=[
            Guarantor(
                name="John Topp",
                credit_score=720,
                is_guarantor=True,
                ownership_pct=100.0
            )
        ],
        rehabs_completed_and_sold=3,
        rehabs_completed_refinanced=2,
        rentals_acquired=6,
        gc_rehabs_completed=0,
        property=RTLProperty(
            address="3260 Bird Ave",
            city="Miami",
            state="FL",
            zip_code="33133",
            property_type="SFR",
            square_footage=2100
        ),
        purchase_price=425000,
        borrower_cost_basis=425000,
        as_is_value=450000,
        after_repair_value=750000,
        total_rehab_budget=75000,
        sqft_expansion=0,
        change_of_use=False,
        conversion_of_structure=False,
        rehab_severity=RTLRehabType.LIGHT,
        loan_amount=382500,  # 90% LTC
        loan_term_months=12,
        interest_accrual_type="Non-Dutch / Multiple Draws"
    )
    
    result = run_rtl_sizer(inputs)
    
    print(f"Borrower Classification: {result.borrower_classification.value}")
    print(f"Total Score: {result.total_score}")
    print(f"Max LTV: {result.max_ltv:.1%}")
    print(f"Max LTC: {result.max_ltc:.1%}")
    if result.max_ltarv:
        print(f"Max LTARV: {result.max_ltarv:.1%}")
    else:
        print("Max LTARV: N/A")
    print(f"ROI Ratio: {result.roi_ratio:.1%}")
    print(f"ROI Check: {'PASS' if result.roi_check_passed else 'FAIL'}")
    print(f"Liquidity Required: ${result.liquidity_requirement:,.2f}")
    print(f"Overall Decision: {'PASS' if result.overall_pass else 'FAIL'}")
    if result.failures:
        print(f"Failures: {result.failures}")
    print()
    return result


def test_rtl_scenario_2():
    """
    Scenario 2: New Investor - Heavy Rehab
    
    Borrower: First-time investor with limited experience
    Property: Duplex requiring major renovation
    """
    print("=" * 80)
    print("TEST 2: RTL - New Investor Heavy Rehab")
    print("=" * 80)
    
    inputs = RTLInputs(
        loan_purpose=RTLLoanPurpose.PURCHASE,
        expected_closing_date="2025-12-01",
        first_payment_date="2026-02-01",
        maturity_date="2027-06-01",
        seasoning_days=0,
        entity_name="First Flip LLC",
        num_owners=2,
        guarantors=[
            Guarantor(
                name="Sarah Johnson",
                credit_score=680,
                is_guarantor=True,
                ownership_pct=50.0
            ),
            Guarantor(
                name="Mike Johnson",
                credit_score=695,
                is_guarantor=True,
                ownership_pct=50.0
            )
        ],
        rehabs_completed_and_sold=0,
        rehabs_completed_refinanced=0,
        rentals_acquired=1,
        gc_rehabs_completed=0,
        property=RTLProperty(
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
            property_type="2 Unit",
            square_footage=2800
        ),
        purchase_price=350000,
        borrower_cost_basis=350000,
        as_is_value=375000,
        after_repair_value=550000,
        total_rehab_budget=125000,
        sqft_expansion=0,
        change_of_use=False,
        conversion_of_structure=False,
        rehab_severity=RTLRehabType.HEAVY,
        loan_amount=297500,  # 85% LTC
        loan_term_months=18,
        interest_accrual_type="Non-Dutch / Multiple Draws"
    )
    
    result = run_rtl_sizer(inputs)
    
    print(f"Borrower Classification: {result.borrower_classification.value}")
    print(f"Total Score: {result.total_score}")
    print(f"Max LTV: {result.max_ltv:.1%}")
    print(f"Max LTC: {result.max_ltc:.1%}")
    print(f"Max LTARV: {result.max_ltarv:.1% if result.max_ltarv else 'N/A'}")
    print(f"ROI Ratio: {result.roi_ratio:.1%}")
    print(f"ROI Check: {'PASS' if result.roi_check_passed else 'FAIL'}")
    print(f"Liquidity Required: ${result.liquidity_requirement:,.2f}")
    print(f"Overall Decision: {'PASS' if result.overall_pass else 'FAIL'}")
    if result.failures:
        print(f"Failures: {result.failures}")
    print()
    return result


def test_bridge_scenario_1():
    """
    Scenario 1: Professional Investor - Light Rehab Purchase
    
    Borrower: 30 bridge loans experience
    Property: SFR in Los Angeles
    Loan: $900K on $1M purchase, $1.5M ARV
    """
    print("=" * 80)
    print("TEST 3: BRIDGE - Professional Investor Light Rehab")
    print("=" * 80)
    
    inputs = BridgeInputs(
        property=BridgeProperty(
            address="123 Main St",
            city="Los Angeles",
            state="CA",
            zip_code="91604",
            property_type=PropertyType.SFR,
            units=1,
            square_footage=4000,
            occupancy_pct=1.0
        ),
        borrower=BridgeBorrower(
            name="Jane Smith",
            fico=770,
            citizenship=Citizenship.US_CITIZEN,
            bridge_experience=30,
            guc_experience=5,
            is_institutional=False
        ),
        valuation=BridgeValuation(
            as_is_value=1000000,
            purchase_price=1000000,
            as_repaired_value=1500000,
            verified_hard_soft_costs=0,
            initial_cost_basis=1000000,
            condo_conversion=False,
            change_of_use=False,
            property_expansion_20pct=False,
            midstream_financing=False,
            arv_3x_multiplier=False
        ),
        loan=BridgeLoanRequest(
            initial_loan_amount=900000,  # 90% LTC
            rehab_amount=150000,
            assignment_fees=0,
            current_debt=0,
            seasoning=">12 Months",
            exit_strategy="Rehab to Rent"
        ),
        cash_flow=BridgeCashFlow(
            annual_resi_rent=0,  # Rehab project
            annual_comm_rent=0,
            annual_other_income=0,
            annual_property_taxes=15000,
            annual_insurance=10000,
            replacement_reserves=300,
            operating_expenses_pct=0.12
        ),
        market=BridgeMarketData(
            msa="Los Angeles-Long Beach-Anaheim, CA",
            zhvi=1723953.18,
            hpa=0.0173,
            dom=54
        ),
        loan_purpose=LoanPurpose.PURCHASE,
        transaction_type=TransactionType.NO_CASH_OUT,
        rehab_type=RehabType.LIGHT,
        stabilized_property=False
    )
    
    result = run_bridge_sizer(inputs)
    
    print(f"ICE Loan Type: {result.ice_loan_type}")
    print(f"Profitability Ratio: {result.profitability_ratio:.2f}x (Min: 1.15x)")
    print(f"Profitability Check: {'PASS' if result.profitability_passed else 'FAIL'}")
    print(f"LTV Test: {result.ltv_test.loan_amount/inputs.valuation.as_is_value:.1%} <= {result.ltv_test.max_starting:.1%} ({'PASS' if result.ltv_test.passed else 'FAIL'})")
    print(f"LTC Test: {result.ltc_test.passed}")
    print(f"LTARV Test: {result.ltarv_test.passed}")
    print(f"Max Loan (LTV): ${result.max_loan_ltv:,.0f}")
    print(f"Max Loan (LTC): ${result.max_loan_ltc:,.0f}")
    print(f"Max Loan (LTARV): ${result.max_loan_ltarv:,.0f}")
    print(f"Max Loan Overall: ${result.max_loan_overall:,.0f}")
    print(f"Recommended Total Loan: ${result.total_loan:,.0f}")
    print(f"Base Rate: {result.base_rate:.2%}")
    print(f"Final Rate: {result.final_rate:.2%}")
    print(f"Points: {result.points:.2%}")
    print(f"Overall Decision: {'PASS' if result.overall_pass else 'FAIL'}")
    if result.failures:
        print(f"Failures: {result.failures}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")
    print()
    return result


def test_bridge_scenario_2():
    """
    Scenario 2: Multi-Family Bridge Loan
    
    Borrower: Experienced with 8 properties
    Property: 8-unit multifamily in Austin
    Purpose: Refinance with light rehab
    """
    print("=" * 80)
    print("TEST 4: BRIDGE - Multi-Family Refinance")
    print("=" * 80)
    
    inputs = BridgeInputs(
        property=BridgeProperty(
            address="456 Oak Ave",
            city="Austin",
            state="TX",
            zip_code="78704",
            property_type=PropertyType.MULTI_5_PLUS,
            units=8,
            square_footage=6000,
            occupancy_pct=0.95
        ),
        borrower=BridgeBorrower(
            name="Robert Chen",
            fico=740,
            citizenship=Citizenship.US_CITIZEN,
            bridge_experience=8,
            guc_experience=0,
            is_institutional=False
        ),
        valuation=BridgeValuation(
            as_is_value=2500000,
            purchase_price=0,  # Refinance
            as_repaired_value=2800000,
            verified_hard_soft_costs=0,
            initial_cost_basis=2200000,
            condo_conversion=False,
            change_of_use=False,
            property_expansion_20pct=False,
            midstream_financing=False,
            arv_3x_multiplier=False
        ),
        loan=BridgeLoanRequest(
            initial_loan_amount=1750000,  # 70% LTV
            rehab_amount=200000,
            assignment_fees=0,
            current_debt=1600000,
            seasoning=">12 Months",
            exit_strategy="Refinance"
        ),
        cash_flow=BridgeCashFlow(
            annual_resi_rent=240000,  # $2500/unit/month * 8 * 12
            annual_comm_rent=0,
            annual_other_income=5000,
            annual_property_taxes=45000,
            annual_insurance=20000,
            replacement_reserves=2400,
            operating_expenses_pct=0.25
        ),
        market=BridgeMarketData(
            msa="Austin-Round Rock, TX",
            zhvi=550000,
            hpa=0.025,
            dom=30
        ),
        loan_purpose=LoanPurpose.REFINANCE,
        transaction_type=TransactionType.NO_CASH_OUT,
        rehab_type=RehabType.LIGHT,
        stabilized_property=True
    )
    
    result = run_bridge_sizer(inputs)
    
    print(f"ICE Loan Type: {result.ice_loan_type}")
    print(f"Profitability Ratio: {result.profitability_ratio:.2f}x")
    print(f"Annual NCF: ${result.annual_ncf:,.0f}")
    print(f"DSCR: {result.stabilized_dscr:.2f}x")
    print(f"LTV Test: {result.ltv_test.loan_amount/inputs.valuation.as_is_value:.1%} ({'PASS' if result.ltv_test.passed else 'FAIL'})")
    print(f"Max Loan Overall: ${result.max_loan_overall:,.0f}")
    print(f"Recommended Total Loan: ${result.total_loan:,.0f}")
    print(f"Final Rate: {result.final_rate:.2%}")
    print(f"Overall Decision: {'PASS' if result.overall_pass else 'FAIL'}")
    if result.failures:
        print(f"Failures: {result.failures}")
    print()
    return result


def test_bridge_scenario_3():
    """
    Scenario 3: Ground Up Construction (GUC)
    
    Borrower: 6 GUC projects completed
    Property: SFR new construction
    """
    print("=" * 80)
    print("TEST 5: BRIDGE - Ground Up Construction (GUC)")
    print("=" * 80)
    
    # Note: GUC logic is embedded in bridge sizer
    inputs = BridgeInputs(
        property=BridgeProperty(
            address="789 Builder Ln",
            city="Phoenix",
            state="AZ",
            zip_code="85018",
            property_type=PropertyType.SFR,
            units=1,
            square_footage=3200,
            occupancy_pct=0
        ),
        borrower=BridgeBorrower(
            name="Construction Pro LLC",
            fico=760,
            citizenship=Citizenship.US_CITIZEN,
            bridge_experience=12,
            guc_experience=6,  # 6 GUC projects
            is_institutional=False
        ),
        valuation=BridgeValuation(
            as_is_value=250000,  # Land value
            purchase_price=250000,
            as_repaired_value=950000,  # Completed value
            verified_hard_soft_costs=600000,
            initial_cost_basis=250000,
            condo_conversion=False,
            change_of_use=False,
            property_expansion_20pct=False,
            midstream_financing=False,
            arv_3x_multiplier=True  # 950/250 = 3.8x
        ),
        loan=BridgeLoanRequest(
            initial_loan_amount=712500,  # 75% LTC on land + construction
            rehab_amount=600000,
            assignment_fees=0,
            current_debt=0,
            seasoning=">12 Months",
            exit_strategy="Sale"
        ),
        cash_flow=BridgeCashFlow(
            annual_resi_rent=0,
            annual_comm_rent=0,
            annual_other_income=0,
            annual_property_taxes=3000,
            annual_insurance=5000,
            replacement_reserves=0,
            operating_expenses_pct=0.12
        ),
        market=BridgeMarketData(
            msa="Phoenix-Mesa-Scottsdale, AZ",
            zhvi=485000,
            hpa=0.03,
            dom=35
        ),
        loan_purpose=LoanPurpose.PURCHASE,
        transaction_type=TransactionType.NO_CASH_OUT,
        rehab_type=RehabType.HEAVY,  # New construction
        stabilized_property=False
    )
    
    result = run_bridge_sizer(inputs)
    
    print(f"ICE Loan Type: {result.ice_loan_type}")
    print(f"Profitability Ratio: {result.profitability_ratio:.2f}x")
    print(f"LTV Test: {'PASS' if result.ltv_test.passed else 'FAIL'}")
    print(f"LTC Test: {'PASS' if result.ltc_test.passed else 'FAIL'}")
    print(f"LTARV Test: {'PASS' if result.ltarv_test.passed else 'FAIL'}")
    print(f"Max Loan Overall: ${result.max_loan_overall:,.0f}")
    print(f"Recommended Total Loan: ${result.total_loan:,.0f}")
    print(f"Final Rate: {result.final_rate:.2%}")
    print(f"Overall Decision: {'PASS' if result.overall_pass else 'FAIL'}")
    if result.failures:
        print(f"Failures: {result.failures}")
    print()
    return result


def run_all_tests():
    """Run all test scenarios and generate report."""
    print("\n" + "=" * 80)
    print("LOAN SIZER TEST SUITE")
    print("Testing RTL (Fix & Flip) and Bridge Loan Logic")
    print("=" * 80 + "\n")
    
    results = []
    
    # RTL Tests
    try:
        r1 = test_rtl_scenario_1()
        results.append(("RTL-1", r1.overall_pass))
    except Exception as e:
        print(f"RTL-1 FAILED: {e}\n")
        results.append(("RTL-1", False))
    
    try:
        r2 = test_rtl_scenario_2()
        results.append(("RTL-2", r2.overall_pass))
    except Exception as e:
        print(f"RTL-2 FAILED: {e}\n")
        results.append(("RTL-2", False))
    
    # Bridge Tests
    try:
        r3 = test_bridge_scenario_1()
        results.append(("Bridge-1", r3.overall_pass))
    except Exception as e:
        print(f"Bridge-1 FAILED: {e}\n")
        results.append(("Bridge-1", False))
    
    try:
        r4 = test_bridge_scenario_2()
        results.append(("Bridge-2", r4.overall_pass))
    except Exception as e:
        print(f"Bridge-2 FAILED: {e}\n")
        results.append(("Bridge-2", False))
    
    try:
        r5 = test_bridge_scenario_3()
        results.append(("Bridge-3", r5.overall_pass))
    except Exception as e:
        print(f"Bridge-3 FAILED: {e}\n")
        results.append(("Bridge-3", False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed_test in results:
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    run_all_tests()
