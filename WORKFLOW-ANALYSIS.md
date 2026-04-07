# 🏦 Loan Sizer SaaS - Real Workflow Analysis
## Based on Meeting with Edward Kaye (Icecap Lending) - April 3, 2026

---

## 📋 EXECUTIVE SUMMARY

**Edward's Current Pain Point:** Manual data entry from emails into Excel sizers takes 20-30 minutes per loan application.

**Solution:** Automated email-to-sizer workflow that populates Excel and returns results in under 60 seconds.

**Key Discovery:** There are **6 DIFFERENT LOAN WORKFLOWS**, not just one. Each requires different sizers and data fields.

---

## 🎯 THE 6 LOAN TYPES IDENTIFIED

### 1. **Bridge Loan** (A to B)
- **Purpose:** Quick acquisition financing
- **Duration:** Short-term (6-24 months)
- **Use Case:** Help borrower acquire property quickly

### 2. **Fix & Flip Loan**
- **Purpose:** Acquisition + Renovation financing
- **Components:** 
  - Purchase money
  - Construction/rehab funds
- **Use Case:** Investors buying distressed properties to renovate and sell

### 3. **DSCR Term Loan - 1-4 Unit** (Rental Loan)
- **Purpose:** Long-term rental property financing
- **Property Type:** Single family to 4-unit multifamily
- **Term:** 30-year fixed
- **Analysis:** Debt Service Coverage Ratio based

### 4. **DSCR Term Loan - 4-9 Unit** (Multifamily)
- **Purpose:** Long-term multifamily financing
- **Property Type:** 5-9 unit apartment buildings
- **Term:** 30-year fixed
- **Analysis:** Based on property income, not borrower income

### 5. **DSCR Term Loan - Mixed Use**
- **Purpose:** Commercial + Residential financing
- **Property Type:** Mixed commercial and residential units
- **Example:** Ground floor retail + upstairs apartments

### 6. **Ground Up Construction Loan**
- **Purpose:** New construction financing
- **Type:** Development/Construction
- **Different sizer required**

---

## 🔍 DETAILED WORKFLOW: DSCR Term Loan (What We Analyzed)

### Step 1: Receive Application Email
**Current State:** Broker sends unstructured email with property details

**Required Input Fields (Standardized Format):**
```
Property Address: [Full Address]
Property Type: [Multifamily/Mixed Use/etc]
Units: [#]
Unit Mix: [#] 1BR, [#] 2BR, etc.
Asset Class: [A/B/C/D]
Estimated Value: $[Amount]
Purchase Price: $[Amount] (if applicable)
Current Debt: $[Amount] (for refinances)
Loan Type: [Purchase/Rate & Term Refi/Cash Out Refi]
Annual Gross Income: $[Amount]
Property Taxes: $[Amount]
Insurance: $[Amount/month]
Credit Score 1: [###]
Credit Score 2: [###]
Credit Score 3: [###]
Seasoning: [< 6 months / > 6 months]
Client Type: [Direct/Broker]
Experience Level: [First-time/Experienced]
U.S. Citizen: [Yes/No]
Foreclosure/Bankruptcy: [Yes/No]
Felonies: [Yes/No]
```

### Step 2: Extract Data to Sizer
**Edward's Current Process:**
1. Open Excel sizer (Multi and Mixed-Use Term Sizer)
2. Manually enter each field
3. Adjust based on daily rate sheet

**Automated Process:**
- Bot extracts from standardized email
- Auto-populates Excel cells
- Pulls daily rates from rate sheet (updated daily)

### Step 3: Asset Class Determination
**Edward's Input:** Loan officer determines A/B/C/D class based on:
- Location (West Palm Beach island = Class A)
- Neighborhood quality
- Property condition
- **Currently manual** - Edward enters this

**Bot Handling:** For now, loan officer specifies in email. Future enhancement: Bot could determine via address analysis.

### Step 4: Credit Score Processing
**Rule:** ALWAYS use middle score of 3 bureaus

**Example from Meeting:**
- Scores: 740, 755, 748
- **Middle Score: 748**
- **Pricing Box: 700-719** (determines interest rate tier)

### Step 5: Purchase Price Discovery
**If not provided by broker:**
- Edward searches Zillow/Public Records
- Finds last recorded sale price
- Some states are non-disclosure (no sale price available)
- **Bot enhancement:** Could auto-search Zillow/Redfin

### Step 6: Calculate Net Operating Income
```
Gross Annual Income: $130,800
Property Taxes: $11,974
Insurance: $756/month = $9,072/year
Other Expenses: [User inputs]
= Net Operating Income
```

### Step 7: Run Sizer Analysis
**Sizer Output Includes:**
- Program eligibility (PASS/FAIL for each note buyer)
- Interest rate based on credit box
- DSCR calculation
- Loan amount checks
- Guidelines compliance

**Note Buyers for Long-Term Debt:**
- Verus
- Deep Haven
- Blackstone
- Churchill
- (And others)

### Step 8: Review Pass/Fail Results
**From Meeting Example:**
- ✅ **PASS:** Deep Haven guidelines
- ❌ **FAIL:** Churchill guidelines
- ❌ **FAIL:** Blackstone guidelines

**Edward's Decision:** Send to Deep Haven (where it passes)

### Step 9: Determine Why It Failed (If Applicable)
Sizer shows specific failure reasons:
- Guidelines failure
- Fee issues
- Proceeds issues
- DSCR too low
- Loan amount check failed

### Step 10: Adjust and Re-run
If failing, Edward adjusts:
- Add lender points
- Change loan amount
- Modify terms
- Re-run sizer

### Step 11: Generate Output
**What Edward Needs Back:**
1. ✅ **PASS/FAIL status** for each program
2. **Which note buyers** will buy the loan
3. **Interest rate** based on credit box
4. **Populated Excel sizer** (full file)
5. **Summary of why** any failures occurred

---

## 💰 PRICING TIERS (From Discussion)

### Internal vs Broker Pricing
- **Direct Client:** Better pricing (lower rates)
- **Broker Client:** Standard pricing (higher rates)
- **Must specify** in input whether direct or broker

### Credit Score Tiers
Middle score determines rate:
- 740+ = Best rates
- 700-719 = Good rates
- 680-699 = Standard rates
- Below 680 = May not qualify

### Seasoning Impact
- **> 6 months owned:** Better rate
- **< 6 months owned:** Rate reduction (higher rate)

---

## 📊 KEY DATA POINTS FOR SIZER INPUT

### Property Details
- [ ] Property Type (Multifamily, Mixed-Use, etc.)
- [ ] Asset Class (A, B, C, D)
- [ ] Address
- [ ] City, State, ZIP
- [ ] City Population (determines program eligibility)
- [ ] Units
- [ ] Unit Mix
- [ ] Estimated Value
- [ ] Purchase Price (or last sale price)

### Loan Details
- [ ] Loan Type (Purchase/Rate & Term/Cash Out)
- [ ] Current Debt (for refinances)
- [ ] Desired Loan Amount
- [ ] Note Type (30 YR Fixed, etc.)
- [ ] Seasoning (< 6mo or > 6mo)
- [ ] Client Type (Direct/Broker)

### Financials
- [ ] Annual Gross Income
- [ ] Property Taxes
- [ ] Insurance (monthly)
- [ ] Other Expenses

### Borrower Details
- [ ] Credit Score 1
- [ ] Credit Score 2
- [ ] Credit Score 3
- [ ] Middle Score (calculated)
- [ ] Experience Level (First-time/Experienced)
- [ ] U.S. Citizen (Yes/No)
- [ ] Foreclosure/Bankruptcy History
- [ ] Felony History
- [ ] Recourse Status (all loans recourse)

---

## 🔧 SYSTEM REQUIREMENTS (From Meeting)

### Must Handle
1. **6 Different Sizers** (one per loan type)
2. **Daily Rate Updates** (rates change daily)
3. **Multiple Note Buyers** (each with different guidelines)
4. **Pass/Fail Logic** per note buyer
5. **Internal vs Broker Pricing**
6. **Asset Class Determination** (A/B/C/D)
7. **Seasoning Calculations** (< 6mo vs > 6mo)
8. **Credit Score Tiering**

### Email Input Format
**Edward's Request:** Standardized email template so brokers send data in consistent format

**Alternative:** Bot requests missing variables if email is unstructured

### Output Requirements
1. **Excel sizer** populated with data
2. **Pass/Fail results** for each program
3. **Which note buyers** will purchase
4. **Interest rate** based on credit box
5. **Failure reasons** (if applicable)

---

## 📈 TIME SAVINGS ANALYSIS

### Current Manual Process
- Read email: 2 min
- Extract data: 5 min
- Enter into sizer: 10 min
- Adjust/fine-tune: 5 min
- Determine pass/fail: 3 min
- **Total: 25 minutes**

### Automated Process
- Forward email: 10 sec
- Wait for processing: 50 sec
- Review results: 1 min
- **Total: 2 minutes**

**Time Saved: 23 minutes per application (92% reduction)**

---

## 🎯 NEXT STEPS (From Meeting)

### Phase 1: DSCR Term Loan (4-9 Unit)
**What We Built:** Email-to-sizer workflow for multifamily term loans

### Phase 2: Remaining 5 Loan Types
**Need to Build:**
1. Bridge Loan sizer workflow
2. Fix & Flip sizer workflow
3. DSCR 1-4 Unit workflow
4. DSCR Mixed Use workflow
5. Ground Up Construction workflow

### Phase 3: Integration with Jotform
**Edward's Current System:** Uses Jotform for:
- Loan submission forms
- Scope of work
- Borrower docs
- DSCR questionnaire
- Fix & Flip funding forms

**Integration:** Bot could pull from Jotform submissions

---

## 📋 REVISED SYSTEM ARCHITECTURE

```
EMAIL INPUT → BOT PARSER → SIZER SELECTOR → EXCEL POPULATOR → ANALYZER → OUTPUT GENERATOR
                  ↓              ↓                ↓              ↓             ↓
            Extract Data   Determine Loan   Populate Cells   Run Logic    Email Results
            from Email     Type (6 types)   with Data        Pass/Fail    + Excel
```

### Loan Type Detection
System must detect which of 6 loan types:
- **Keywords:** Bridge, Fix & Flip, Term, Construction
- **Property Type:** 1-4 unit, 4-9 unit, Mixed Use
- **User Selection:** Explicit loan type in email

### Sizer Selection Matrix
| Loan Type | Sizer File | Key Fields |
|-----------|------------|------------|
| Bridge | Bridge Sizer | A to B, short term |
| Fix & Flip | Fix & Flip Sizer | Acquisition + Rehab |
| DSCR 1-4 Unit | Term Sizer 1-4 | Residential rental |
| DSCR 4-9 Unit | Term Sizer Multi | Multifamily |
| DSCR Mixed Use | Mixed Use Sizer | Commercial + Res |
| Construction | Construction Sizer | Ground up build |

---

## ✅ TESTING CHECKLIST (For Tonight)

### Test Email Should Include:
- [ ] Property address
- [ ] Property type (Multifamily/Mixed Use)
- [ ] Number of units
- [ ] Unit mix
- [ ] Asset class
- [ ] Estimated value
- [ ] Purchase price or current debt
- [ ] Loan type
- [ ] Annual gross income
- [ ] Property taxes
- [ ] Insurance amount
- [ ] All 3 credit scores
- [ ] Seasoning
- [ ] Client type (Direct/Broker)
- [ ] Experience level

### Expected Output:
- [ ] Populated Excel sizer
- [ ] Pass/Fail for each note buyer
- [ ] Interest rate based on credit box
- [ ] Specific failure reasons (if any)
- [ ] Recommendation on where to send loan

---

## 📝 NOTES FOR DEVELOPMENT

### From Edward:
- Rates change daily - need daily rate update mechanism
- Asset class determination currently manual (future: auto via address)
- Purchase price discovery sometimes requires Zillow search
- Non-disclosure states don't show sale prices
- All loans are recourse (no non-recourse option)
- Experienced vs first-time investor matters for pricing
- U.S. citizenship required
- Foreclosure/bankruptcy history matters

### Key Phrases Edward Uses:
- "Rate and term" = refinance, no cash out
- "Delayed purchase" = specific loan type
- "Seasoning" = how long owned (>6mo = better rate)
- "Note buyers" = companies that buy loans (Deep Haven, Verus, etc.)
- "DSCR" = Debt Service Coverage Ratio
- "Asset class" = A/B/C/D rating of neighborhood/property
- "Recourse" = personally guaranteed loans

---

## 🎯 SUCCESS METRICS

**Primary:** Reduce processing time from 25 minutes to 2 minutes

**Secondary:**
- 95%+ data extraction accuracy
- Zero manual data entry required
- Pass/fail results match manual analysis
- Edward can process 3x more applications per day

---

**Analysis Complete - Ready to Build Test Examples!** 🚀
