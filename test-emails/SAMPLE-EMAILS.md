# 📧 Sample Loan Application Emails for Testing

Use these emails to test the Loan Sizer SaaS email forward workflow.

---

## Email #1: Strong Approval - 8 Unit Multifamily

**Scenario:** Good credit, reasonable LTV, should qualify for multiple programs

```
Subject: Loan Application - 8 Unit Multifamily Property

Hello,

I'm interested in financing for an 8-unit multifamily property located at 307 S Main Street, Hopkinsville, KY 44240.

Property Details:
- 8 units, approximately 750 sq ft each
- Estimated value: $1,200,000
- Purchase price: $980,000
- Requested loan amount: $784,000 (80% LTV)
- Note type: 30 YR Fixed
- Points to lender: 1%

My credit scores are 688, 712, and 703.

Please let me know what programs I qualify for.

Thanks,
James Whitfield
james.whitfield@email.com
(555) 123-4567
```

**Expected Result:** ✅ APPROVE - Should qualify for Insurance Program and Short Term Sale

---

## Email #2: Conditional - 12 Unit with Higher LTV

**Scenario:** Borderline LTV, decent credit, may conditionally qualify

```
Subject: Financing Request - 12 Unit Apartment Building

Hi there,

Looking for financing on a 12-unit apartment building at 4521 Oak Avenue, Unit B, Philadelphia, PA 19103.

Property Information:
- 12 units, avg 850 sq ft
- Estimated Value: $1,850,000
- Purchase Price: $1,500,000
- Loan Amount Requested: $1,200,000
- Note Type: 30 Year Fixed
- Points: 1.5%

Credit Scores: 650, 672, 665

This is a stabilized property with 95% occupancy.

Please advise on available programs.

Best regards,
Sarah Chen
sarah.chen@investor.com
(215) 555-0199
```

**Expected Result:** ⚠️ CONDITIONAL - May only qualify for 1-2 programs due to higher LTV (80%)

---

## Email #3: Likely Decline - Low Credit Score

**Scenario:** Below minimum credit requirements

```
Subject: RE: Loan Application

Hi,

Saw your ad for real estate financing. I'm looking to purchase a 4-unit building at 789 Pine Street, Detroit, MI 48201.

Property:
- 4 units
- Value: $450,000
- Purchase: $380,000  
- Loan needed: $300,000
- 30 yr fixed

My credit scores are 580, 595, and 612.

Let me know if this works.

Mike Johnson
mike.j@fastmail.net
(313) 555-0147
```

**Expected Result:** ❌ DECLINE - Credit scores below 650 minimum for most programs

---

## Email #4: Strong Approval - Large Multifamily

**Scenario:** Strong borrower, conservative LTV, excellent credit

```
Subject: Commercial Loan Application - 20 Unit Multifamily

Dear Sir/Madam,

I am submitting a loan application for a 20-unit multifamily property.

PROPERTY DETAILS:
Address: 1500 Riverside Drive, Building C, Austin, TX 78701
Units: 20 (mix of 1BR and 2BR)
Estimated Value: $4,200,000
Purchase Price: $3,800,000
Loan Amount: $2,660,000 (70% LTV)
Note Type: 30 YR Fixed
Points to Lender: 1%

BORROWER INFO:
Credit Scores: 745, 762, 758
Middle Score: 758

The property is fully occupied with long-term tenants.

Please provide your best terms.

Regards,
Robert Martinez
rmartinez@capitalinvestments.com
(512) 555-0234
```

**Expected Result:** ✅ APPROVE - Should qualify for all programs

---

## Email #5: Mixed-Use Property

**Scenario:** Mixed commercial/residential

```
Subject: Loan Request - Mixed Use Building

Hello,

Interested in financing for a mixed-use property at 223 Commerce Street, Suite 100, Nashville, TN 37201.

Property Specs:
- 6 residential units (2BR/1BA each)
- 2 commercial storefronts on ground floor
- Total building size: 12,000 sq ft
- Estimated Value: $1,450,000
- Purchase Price: $1,200,000
- Requested Loan: $960,000
- Note Type: 30 YR Fixed
- Points: 1%

Credit: 702, 715, 698 (Middle: 702)

Property has been renovated in 2023.

Thanks,
Jennifer Park
j.park@realestategroup.com
(615) 555-0287
```

**Expected Result:** ✅ APPROVE - Good credit and reasonable LTV

---

## Email #6: Minimal Information (Test Extraction)

**Scenario:** Sparse details - tests AI extraction capabilities

```
Subject: Loan App

Need loan for 10 unit building at 55 Maple Ave, Chicago, IL 60614.

Value: $1.1M
Purchase: $900K  
Loan: $720K
Credit: 680, 695, 702
30 yr fixed

Contact: david.smith@email.com
```

**Expected Result:** ✅ APPROVE or ⚠️ CONDITIONAL - System should extract all key fields

---

## Email #7: High DSCR Property (Strong Cash Flow)

**Scenario:** Property with excellent debt service coverage

```
Subject: Financing Request - High Cash Flow Multifamily

Good afternoon,

Seeking financing for the following acquisition:

Property Address: 7890 Boardwalk Avenue, Atlantic City, NJ 08401
Property Type: 16-unit multifamily
Unit Mix: Twelve 2BR/1BA, Four 1BR/1BA
Estimated Value: $2,400,000
Purchase Price: $2,000,000
Requested Loan: $1,400,000 (70% LTV)
Note Terms: 30 Year Fixed
Points to Lender: 1.0%

Annual Gross Rent: $288,000
NOI: $230,000

Borrower Credit Scores: 728, 741, 735 (Middle: 735)

This property has consistent rental history and 100% occupancy.

Please review and advise.

Sincerely,
Michael Thompson
thompson.investments@outlook.com
(609) 555-0312
```

**Expected Result:** ✅ APPROVE - Strong DSCR should pass all programs

---

## Email #8: Rehab/Value-Add Property

**Scenario:** Property needing work, higher risk profile

```
Subject: Value-Add Opportunity - 6 Unit Building

Hi,

Looking at a value-add opportunity:

Address: 321 Industrial Blvd, Pittsburgh, PA 15201
Units: 6 (currently 4 occupied)
Est. Value (as-is): $650,000
Purchase Price: $520,000
Loan Needed: $416,000
Note: 30 YR Fixed

Current rents below market. Plan to renovate and lease up.

Credit scores: 665, 678, 672

Is this something you can finance?

Chris Anderson
andersongroup@pm.me
(412) 555-0456
```

**Expected Result:** ⚠️ CONDITIONAL - Lower occupancy may affect DSCR calculations

---

## Email #9: Short Term/Rental Arbitrage

**Scenario:** Short-term rental property

```
Subject: STR Investment Property Financing

Hello,

I'm looking to purchase a 4-unit property for short-term rental use:

Property: 456 Beachfront Drive, Miami Beach, FL 33139
Units: 4 (all 2BR/2BA, fully furnished)
Estimated Value: $1,800,000
Purchase Price: $1,550,000
Loan Amount: $1,240,000 (80% LTV)
Note Type: 30 YR Fixed
Points: 1%

Projected STR income: $220,000/year
Current long-term rents: $96,000/year

Credit Scores: 710, 722, 718

Property is in a high-demand tourist area.

Please let me know your thoughts.

Best,
Amanda Rodriguez
amanda.r@strinvestor.com
(305) 555-0567
```

**Expected Result:** ✅ APPROVE - Good credit, reasonable LTV

---

## Email #10: Large Portfolio Acquisition

**Scenario:** Multiple properties, portfolio loan

```
Subject: Portfolio Loan Request - 3 Properties

Dear Lending Team,

I'm seeking a portfolio loan for the acquisition of three multifamily properties:

PROPERTY A:
- Address: 100 First Street, Columbus, OH 43215
- Units: 8
- Value: $950,000
- Purchase: $800,000
- Loan: $640,000

PROPERTY B:
- Address: 200 Second Ave, Columbus, OH 43210  
- Units: 6
- Value: $720,000
- Purchase: $600,000
- Loan: $480,000

PROPERTY C:
- Address: 300 Third Blvd, Columbus, OH 43201
- Units: 4
- Value: $480,000
- Purchase: $400,000
- Loan: $320,000

TOTALS:
- Combined Units: 18
- Combined Value: $2,150,000
- Combined Purchase: $1,800,000
- Total Loan Requested: $1,440,000 (80% blended LTV)
- Note Type: 30 YR Fixed
- Points: 1%

Credit Scores: 692, 705, 698 (Middle: 698)

All properties are in the same submarket and professionally managed.

Please advise on portfolio terms.

Regards,
Kevin Williams
kwilliams@propertyportfolio.com
(614) 555-0789
```

**Expected Result:** ✅ APPROVE or ⚠️ CONDITIONAL - Test how system handles multiple properties

---

## 🧪 Testing Checklist

When testing each email, verify:

- [ ] Email forwards correctly to your `xxx@process.loansizer.com` address
- [ ] System extracts: address, units, loan amount, credit scores
- [ ] Credit score calculation: middle of 3 scores is correct
- [ ] LTV ratio calculated correctly
- [ ] Sizer runs without errors
- [ ] Decision (APPROVE/DECLINE/CONDITIONAL) is logical
- [ ] Programs evaluated with correct PASS/FAIL
- [ ] Response email received within 60 seconds
- [ ] Excel attachment is populated with data
- [ ] Email decision is highlighted (green/red)

---

## 📝 Notes for Testing

1. **Forward each email** from a registered user email to your forwarding address
2. **Wait 30-60 seconds** for processing
3. **Check inbox** for response email with attachment
4. **Download Excel** and verify data populated correctly
5. **Check dashboard** to see logged application

---

## 🎯 Expected Processing Times

| Email Complexity | Expected Time |
|-----------------|---------------|
| Simple (Email #6) | 15-20 seconds |
| Standard (Email #1, #4) | 20-30 seconds |
| Complex (Email #10) | 30-45 seconds |

---

Ready to test! Forward these emails and watch the magic happen! 🚀
