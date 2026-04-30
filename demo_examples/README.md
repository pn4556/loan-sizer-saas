# Loan Sizer Demo Examples

This folder contains 10 demo files for testing the Loan Sizer website during your demo.

## 📁 File Overview

| File | Scenario | Format | Upload To |
|------|----------|--------|-----------|
| 01_rtl_purchase_simple.txt | RTL - Purchase, Light Rehab | CSV | Fix & Flip (RTL) Sizer |
| 02_rtl_refi_simple.txt | RTL - Refinance, Heavy Rehab | CSV | Fix & Flip (RTL) Sizer |
| 03_bridge_purchase_light.txt | Bridge - Purchase, Light Rehab | CSV | Bridge Loan Sizer |
| 04_bridge_refi_cashout.txt | Bridge - Cash Out Refinance | CSV | Bridge Loan Sizer |
| 05_dscr_1unit_email.txt | DSCR 1-4 Unit - Single Family | Email Text | Main Email Upload |
| 06_dscr_duplex_email.txt | DSCR 1-4 Unit - Duplex | Email Text | Main Email Upload |
| 07_dscr_fourplex_email.txt | DSCR 1-4 Unit - Fourplex | Email Text | Main Email Upload |
| 08_dscr_6unit_email.txt | DSCR 4-9 Unit - 6 Units | Email Text | Main Email Upload |
| 09_dscr_8unit_email.txt | DSCR 4-9 Unit - 8 Units | Email Text | Main Email Upload |
| 10_mixed_use_email.txt | Mixed Use - Retail + Residential | Email Text | Main Email Upload |

## 🎯 Demo Flow Suggestions

### Flow 1: DSCR Loans (Most Common)
1. Start with `05_dscr_1unit_email.txt` - Simple SFR purchase
2. Show `06_dscr_duplex_email.txt` - Cash-out refinance
3. Demonstrate `08_dscr_6unit_email.txt` - Larger multifamily

### Flow 2: Bridge/Flip Loans
1. Use `01_rtl_purchase_simple.txt` in RTL Sizer
2. Show `03_bridge_purchase_light.txt` in Bridge Sizer
3. Compare results side-by-side with Multi-Lender Comparison

### Flow 3: Complete Walkthrough
1. Email upload: `07_dscr_fourplex_email.txt`
2. Manual entry: Fix & Flip with `02_rtl_refi_simple.txt`
3. Bridge loan: `04_bridge_refi_cashout.txt`
4. Multi-lender comparison with same property details

## 📋 File Format Details

### CSV Format (RTL & Bridge)
Simple key-value pairs:
```
loanPurpose,Purchase
rehabType,Light Rehab
```

### Email Format (DSCR)
Full email text with:
- Property details
- Financial information
- Credit scores
- Borrower information

## ⚠️ Important Notes

1. **RTL/Bridge File Upload**: The file upload only populates the visible dropdown fields (Loan Purpose, Transaction Type, Rehab Type). You'll need to manually fill in the borrower and property details.

2. **DSCR Email Upload**: Paste the entire email text into the "Paste email content here..." box on the main dashboard.

3. **Multi-Lender Comparison**: Use the values from any scenario to compare IFC, ICE, and Eastview pricing side-by-side.

## 🔧 Expected Results

### File 05 (DSCR 1-Unit)
- **Expected**: APPROVE or REVIEW
- **LTV**: ~70%
- **Middle FICO**: 745
- **Program**: DSCR Conventional likely

### File 01 (RTL Purchase)
- Populates: Loan Purpose = Purchase, Rehab Type = Light Rehab
- After manual entry: Should show A+ or A borrower grade with strong rates

### File 03 (Bridge Light Rehab)
- Populates: Loan Purpose = Purchase, Transaction Type = No Cash Out, Rehab Type = Light Rehab
- After manual entry: Should show ~8.75% base rate

## 🧪 Testing Checklist

Before your demo, verify:

- [ ] All 10 files are in this folder
- [ ] Files open correctly (not corrupted)
- [ ] Website is loading at the Render URL
- [ ] Email upload works with DSCR files
- [ ] CSV upload works with RTL/Bridge files
- [ ] Multi-lender comparison section is visible

## 🆘 Troubleshooting

**File upload not working?**
- Check that file extension is `.txt`
- Verify no extra blank lines at start of file
- Ensure comma separators (not tabs)

**Email parsing failed?**
- Paste entire file content (don't modify)
- Ensure credit scores are 3-digit numbers
- Check dollar amounts don't have $ signs in extraction

**Bridge/RTL form incomplete?**
- File upload only fills dropdowns
- Manually enter borrower name, FICO, property details
- Click "Analyze Loan" after filling all fields

---

**Last Updated**: April 30, 2026
**Version**: Demo Ready v1.0
