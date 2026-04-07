# 🚀 Edward's Quick Testing Reference
## Loan Sizer SaaS - Ready for Testing Tonight

---

## ⚡ SUPER QUICK TEST (Copy & Send)

**Use this email to test the system right now:**

```
Subject: Loan Submission - 8 Unit Multifamily - Rate & Term Refi

LOAN TYPE: DSCR Term Loan - Multifamily (4-9 Unit)

PROPERTY DETAILS:
Property Address: 123 Main Boulevard
City/State/ZIP: Chicago, IL 60644
Property Type: Multifamily
Number of Units: 8
Unit Mix: 5 one-bedroom/1-bath, 3 two-bedroom/1-bath
Asset Class: C

FINANCIALS:
Estimated Value: $770,000
Current Debt: $500,000
Loan Type: Rate & Term Refinance
Annual Gross Income: $130,800
Property Taxes: $11,974
Insurance: $756/month

BORROWER INFO:
Credit Score 1: 740
Credit Score 2: 755
Credit Score 3: 748
Experience Level: Experienced
U.S. Citizen: Yes
Foreclosure/Bankruptcy: No

TIMING:
Seasoning: > 6 months

CLIENT INFO:
Client Type: Direct
```

**Send to:** `your-company@process.loansizer.com`

**Wait:** 30-60 seconds

**Expected:** ✅ **PASS** with Deep Haven (just like in our meeting!)

---

## 🎯 THE 6 LOAN TYPES AT A GLANCE

| # | Loan Type | When to Use | Key Fields |
|---|-----------|-------------|------------|
| 1 | **DSCR 4-9 Unit** | Multifamily rentals (5-9 units) | Units, income, DSCR |
| 2 | **DSCR 1-4 Unit** | Small rentals (1-4 units) | Same as above |
| 3 | **Mixed Use** | Commercial + Residential | Commercial income + residential |
| 4 | **Bridge** | Quick acquisition (A to B) | Short term, exit strategy |
| 5 | **Fix & Flip** | Buy + Renovate + Sell | Rehab budget, ARV |
| 6 | **Construction** | Ground up building | Construction costs, timeline |

---

## ✅ CHECKLIST: What System Should Extract

### Property Info:
- [ ] Full address
- [ ] Property type
- [ ] Number of units
- [ ] Unit mix (1BR, 2BR, etc.)
- [ ] Asset class (A/B/C/D)

### Financials:
- [ ] Estimated value
- [ ] Purchase price OR current debt
- [ ] Loan type (Purchase/Rate & Term/Cash Out)
- [ ] Annual gross income
- [ ] Property taxes
- [ ] Insurance (monthly)

### Borrower:
- [ ] All 3 credit scores
- [ ] **Middle score calculated**
- [ ] Experience level
- [ ] U.S. citizen
- [ ] Foreclosure/bankruptcy history

### Other:
- [ ] Seasoning (< 6mo or > 6mo)
- [ ] Client type (Direct/Broker)

---

## 📊 WHAT YOU GET BACK

### Email Response Includes:
1. **✅ PASS / ❌ FAIL / ⚠️ CONDITIONAL** (Highlighted in color)
2. **Which note buyers** will purchase the loan:
   - Deep Haven
   - Verus
   - Blackstone
   - Churchill
   - (And others)
3. **Interest rate** based on credit box
4. **Failure reasons** (if any)
5. **📎 Excel sizer** fully populated

### Example Response:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ✅  DECISION: PASS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Loan qualifies with:
✅ Deep Haven - PASS
❌ Blackstone - FAIL (guidelines)
❌ Churchill - FAIL (guidelines)

Credit Box: 700-719
Rate: 8.50%

Recommendation: Submit to Deep Haven

📎 Excel sizer attached
```

---

## 🔍 IF SOMETHING GOES WRONG

### No response after 2 minutes?
- Check email sent to correct address
- Verify you're sending from registered email
- Check spam folder

### Wrong data extracted?
- Make sure using standard format above
- Include "LOAN TYPE:" at top
- Clearly label all numbers

### No Excel attachment?
- Check file size (max 10MB)
- Make sure template uploaded in dashboard

---

## 💰 PRICING TIERS TO TEST

### Test Both:
1. **Direct Client** = Better rates
2. **Broker Client** = Standard rates

### Credit Score Impact:
- 740+ = Best rates
- 700-719 = Good rates
- 680-699 = Standard
- < 680 = May not qualify

### Seasoning Impact:
- > 6 months = Better rate
- < 6 months = Higher rate

---

## ⏱️ TIMING EXPECTATIONS

| Loan Type | Processing Time |
|-----------|----------------|
| DSCR 1-4 Unit | 20-30 seconds |
| DSCR 4-9 Unit | 20-30 seconds |
| Mixed Use | 30-45 seconds |
| Bridge | 15-25 seconds |
| Fix & Flip | 30-45 seconds |
| Construction | 45-60 seconds |

---

## 📈 TIME SAVINGS

### Before (Manual):
- Read email: 2 min
- Extract data: 5 min
- Enter sizer: 10 min
- Run analysis: 5 min
- Review: 3 min
- **Total: 25 minutes**

### After (Automated):
- Forward email: 10 sec
- Wait: 50 sec
- Review: 1 min
- **Total: 2 minutes**

**SAVINGS: 23 minutes per loan (92% faster)**

---

## 🎯 PRIORITY TESTS FOR TONIGHT

### Must Test (In Order):
1. ✅ **Test #1** - The exact loan from our meeting (DSCR 4-9 Unit)
2. ✅ **Test #4** - 1-4 Unit rental (most common)
3. ✅ **Test #7** - Bridge loan (urgent closes)
4. ✅ **Test #10** - Decline scenario (test error handling)

### Nice to Test:
5. Test #2 - High LTV (conditional)
6. Test #6 - Mixed use
7. Test #8 - Fix & flip
8. Test #9 - Construction

---

## 📞 TROUBLESHOOTING

**Problem:** System not recognizing loan type
**Fix:** Add "LOAN TYPE:" at very top of email

**Problem:** Credit score not calculated
**Fix:** Label clearly: "Credit Score 1: 740"

**Problem:** Wrong middle score
**Fix:** System should auto-calculate middle of 3 scores

**Problem:** Seasoning not detected
**Fix:** Include "Seasoning: > 6 months" explicitly

---

## ✅ SUCCESS CHECKLIST

After testing, verify:
- [ ] All 6 loan types work
- [ ] Middle credit score calculated correctly
- [ ] LTV computed accurately
- [ ] Pass/fail logic matches your manual analysis
- [ ] Excel file opens with data populated
- [ ] Response time under 60 seconds
- [ ] Direct vs broker pricing different
- [ ] Seasoning affects rate appropriately

---

## 🎉 READY TO TEST!

1. Copy test email above
2. Send to your forwarding address
3. Wait 30-60 seconds
4. Check your inbox
5. Download Excel
6. Review results

**Questions?** Check EDWARD-TEST-EMAILS.md for all 10 detailed examples.

**Let's do this!** 🚀
