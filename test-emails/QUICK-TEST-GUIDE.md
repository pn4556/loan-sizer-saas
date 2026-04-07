# 🚀 Quick Test Guide - Loan Sizer SaaS

## ⚡ Quick Start (Copy & Paste)

### Step 1: Forward This Test Email

Copy this email and forward it to your `xxx@process.loansizer.com` address:

```
Subject: Loan Application - 8 Unit Multifamily

Hello,

I'm interested in financing for an 8-unit multifamily property at 307 S Main Street, Hopkinsville, KY 44240.

Property Details:
- 8 units, approximately 750 sq ft each
- Estimated value: $1,200,000
- Purchase price: $980,000
- Requested loan amount: $784,000
- Note type: 30 YR Fixed

My credit scores are 688, 712, and 703.
Points to lender: 1%

Thanks,
James Whitfield
james.whitfield@email.com
```

### Step 2: Wait for Response

⏱️ **30-60 seconds**

### Step 3: Check Results

You should receive an email with:
- ✅ **APPROVE** in green highlight
- Property summary
- Program results (Insurance Program: PASS, Short Term Sale: PASS)
- 📎 **Attached:** Filled Excel sizer

---

## 🧪 Test Scenarios (Copy Ready)

### Test #1: Strong Approval ✅
```
Subject: Loan App - Strong Credit

Property: 10 unit, 500 Market St, Philadelphia, PA 19103
Value: $1,500,000 | Purchase: $1,200,000 | Loan: $960,000
Credit: 740, 755, 748
30 yr fixed
Contact: strong@borrower.com
```

### Test #2: Conditional ⚠️
```
Subject: Loan App - Higher LTV

Property: 6 unit, 222 Oak Lane, Detroit, MI 48201
Value: $600,000 | Purchase: $550,000 | Loan: $495,000 (90% LTV)
Credit: 670, 685, 678
30 yr fixed
Contact: borderline@test.com
```

### Test #3: Decline ❌
```
Subject: Loan App - Low Credit

Property: 4 unit, 111 Pine St, Cleveland, OH 44101
Value: $400,000 | Purchase: $350,000 | Loan: $280,000
Credit: 580, 595, 588
30 yr fixed
Contact: lowcredit@email.com
```

---

## 📊 Expected Results Reference

| Test | LTV | Credit | Expected Decision | Programs Passed |
|------|-----|--------|------------------|-----------------|
| #1 | 64% | 748 | ✅ APPROVE | 2-3 |
| #2 | 82% | 678 | ⚠️ CONDITIONAL | 1-2 |
| #3 | 70% | 588 | ❌ DECLINE | 0 |

---

## ✅ Success Checklist

After forwarding email, verify:

- [ ] Response received within 60 seconds
- [ ] Email shows decision (APPROVE/DECLINE/CONDITIONAL)
- [ ] Decision is highlighted green/red
- [ ] Property details extracted correctly
- [ ] Credit score shows middle value (of 3 scores)
- [ ] LTV calculated correctly
- [ ] Programs show PASS/FAIL
- [ ] Excel file attached
- [ ] Excel opens with populated data

---

## 🐛 Troubleshooting

### No response after 2 minutes?
- Check email was sent to correct forwarding address
- Verify sender email is registered user
- Check spam folder
- Check Render logs for errors

### Wrong data extracted?
- Check email format matches samples
- Ensure numbers are clearly formatted
- Try forwarding full email (not just snippet)

### No attachment?
- Check email size (max 10MB)
- Verify Excel template uploaded in dashboard

---

## 🎯 Performance Benchmarks

| Metric | Target |
|--------|--------|
| Email processing | < 60 seconds |
| Data extraction | < 10 seconds |
| Sizer analysis | < 20 seconds |
| Email delivery | < 30 seconds |
| **Total** | **< 60 seconds** |

---

## 📈 Time Savings Calculation

**Manual Process:** 25 minutes
- Read email: 2 min
- Extract data: 5 min
- Enter sizer: 10 min
- Review programs: 5 min
- Draft email: 3 min

**Automated Process:** 60 seconds
- Forward email: 10 sec
- Wait for results: 50 sec

**Time Saved:** 24 minutes (96% reduction)

---

## 🎉 You're Ready!

1. Copy test email above
2. Forward to your address
3. Wait 60 seconds
4. Check your inbox
5. Download Excel
6. Review results

**Questions?** Check EMAIL-FORWARD-WORKFLOW.md for detailed guide.

Happy testing! 🚀
