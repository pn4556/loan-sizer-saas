# Lender Requirements Alignment Document

## Overview
This document ensures all 3 loan sizers (Bridge, DSCR, Fix & Flip) correlate correctly with the Multi-Lender Dashboard.

## Lender Specifications

### 1. BRIDGE LOANS

#### Bridge Capital
- **Max LTV**: 75%
- **Interest Rate**: 9.5%
- **Points**: 1.5%
- **Min FICO**: 620
- **Approval**: Asset-based, primarily on LTV

#### Eastview Bridge
- **Max LTV**: 80%
- **Interest Rate**: 9.25%
- **Points**: 2.0%
- **Min FICO**: 660
- **Approval**: Based on borrower grade (A+, A, B, C)

#### ICE Bridge
- **Max LTV**: 75%
- **Interest Rate**: 9.75%
- **Points**: 1.0%
- **Min FICO**: 680
- **Approval**: Standard bridge terms

---

### 2. FIX & FLIP / RENOVATION LOANS

#### IFC Renovation Program
- **Max LTV**: 90%
- **Max LTC**: 90%
- **Max LTARV**: 75%
- **Rates by FICO**:
  - 740+: 7.75% - 8.00%
  - 700-739: 7.75% - 8.125%
  - 680-699: 8.00% - 8.25%
  - 660-679: 8.25% - 8.50%
- **Points**: 2.0%
- **Min FICO**: 660
- **Cash Out Adjustment**: +0.50%

#### ICE Light Rehab
- **Max LTV**: 90%
- **Max LTC**: 90%
- **Max LTARV**: 75%
- **Base Rate**: 8.75%
- **Points**: 0.5%
- **Min FICO**: 680
- **Adjustments**:
  - Cash Out: +0.50%
  - FICO < 700: +0.25%
  - Institutional (10+ deals, $2.5M+): -0.50%

#### Eastview Fix & Flip
- **Borrower Grade System**:
  - A+: Max 90% LTV/LTC, 75% LTARV, 9.25% rate
  - A: Max 85% LTV/LTC, 70% LTARV, 9.50% rate
  - B: Max 82.5% LTV/LTC, 65% LTARV, 9.75% rate
  - C: Max 75% LTV/LTC, 60% LTARV, 10.25% rate
- **Points**: 1.5%
- **Min FICO**: 660
- **Grade Calculation**:
  - Credit: 700+ = 3 pts, 680-699 = 1 pt, <680 = 0 pts
  - Experience: 10+ yrs = 7 pts, 3-9 yrs = 5 pts, <3 yrs = 1 pt
  - Total: 7+ = A+, 5-6 = A, 2-4 = B, <2 = C

---

### 3. DSCR LOANS (30-Year Conventional)

#### DSCR Conventional
- **Max LTV**: 80%
- **Rate Range**: 7.50% - 8.50%
- **Points**: 1.0% - 2.0%
- **Min FICO**: 680
- **Min DSCR**: 1.20
- **Max Loan**: $2,000,000
- **Adjustments**:
  - FICO < 700: +0.25%
  - Cash Out: +0.25%
  - DSCR < 1.25: +0.25%

---

## Multi-Lender Dashboard Calculation

The `calculateMultiLenderFallback()` function uses these exact specifications to ensure consistency across all loan types.

### Key Alignment Points:

1. **LTV/LTC Calculations**: Same across all sizers
2. **Rate Schedules**: Matched to lender requirements
3. **Approval Logic**: Consistent FICO and experience thresholds
4. **Points**: Fixed per lender program
5. **Grade System**: Eastview uses same calculation everywhere

### Data Flow:
```
Individual Sizer Form 
    ↓
API Call (or Client-Side Fallback)
    ↓
Lender Calculation Logic (consistent)
    ↓
Results Display (Dashboard/Sizer)
```

## Validation Checklist

- [x] Bridge Capital: 75% LTV, 9.5%, 1.5 pts
- [x] Eastview Bridge: 80% LTV, 9.25%, 2.0 pts
- [x] ICE Bridge: 75% LTV, 9.75%, 1.0 pt
- [x] IFC Renovation: 90% LTV/LTC, 7.75-8.50%, 2.0 pts
- [x] ICE Light Rehab: 90% LTV/LTC, 8.75%, 0.5 pts
- [x] Eastview Fix & Flip: Grade-based, 1.5 pts
- [x] DSCR: 80% LTV, 7.50-8.50%, 1-2 pts

## Monthly Payment Calculation

All sizers use: `Monthly Payment = Loan Amount × (Rate / 100) / 12`

This is consistent across Bridge, DSCR, and Fix & Flip calculations.
