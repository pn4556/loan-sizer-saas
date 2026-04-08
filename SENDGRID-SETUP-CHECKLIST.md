# SendGrid Setup Checklist for ComplAiCore

## ✅ Completed

### Backend Configuration
- [x] SendGrid API Key added to Render (`SG.JJ80dzj8S3ysCQnTTl18VQ...`)
- [x] FROM_EMAIL set to `loans@complaicore.com`
- [x] Backend deployed with enhanced email templates
- [x] Test user created: `testbroker@complaicore.com`
- [x] Test client: `ComplAiCore Test` (slug: `complaicore-test`)
- [x] Excel template uploaded

### Your Forwarding Address
```
loans+complaicore-test@complaicore.com
```

---

## ⏳ You Complete These Steps

### Step 1: Domain Authentication (5 mins)
**Required to send emails from loans@complaicore.com**

1. Go to https://app.sendgrid.com/settings/sender_auth
2. Click **Authenticate Your Domain**
3. Select **Other Host** (not in dropdown)
4. Enter domain: `complaicore.com`
5. Check ✅ **Automated Security**
6. Click **Next**

**You will see 3 DNS records like:**
```
Type: CNAME | Name: emXXXX.complaicore.com | Value: uXXXX.wlXXX.sendgrid.net
Type: CNAME | Name: s1._domainkey.complaicore.com | Value: s1.domainkey.uXXXX.wlXXX.sendgrid.net  
Type: CNAME | Name: s2._domainkey.complaicore.com | Value: s2.domainkey.uXXXX.wlXXX.sendgrid.net
```

### Step 2: Add DNS to Squarespace (5 mins)

1. Login to Squarespace
2. Go to **Settings** → **Domains** → **complaicore.com** → **DNS**
3. Add the 3 CNAME records from Step 1
4. Save

### Step 3: Verify Domain (2 mins)

1. Back in SendGrid, click **Verify**
2. Wait 2-5 minutes
3. ✅ Green checkmark = Ready!

### Step 4: Inbound Parse Webhook (3 mins)

1. Go to https://app.sendgrid.com/settings/parse
2. Click **Add Host & URL**
3. **Receiving Domain**: `complaicore.com`
4. **Destination URL**: 
   ```
   https://loan-sizer-saas.onrender.com/email/webhook/sendgrid
   ```
5. Check ✅ **Spam Check**
6. Click **Save**

---

## 🧪 Test Script

Once setup is complete, run this test:

```bash
# Test 1: Simulate SendGrid webhook
curl -X POST "https://loan-sizer-saas.onrender.com/email/webhook/sendgrid" \
  -F "to=loans+complaicore-test@complaicore.com" \
  -F "from=testbroker@complaicore.com" \
  -F "subject=Loan App - 123 Main St" \
  -F "text=Purchase Price: 500000
Loan Amount: 400000
Address: 123 Main St
City: Los Angeles
State: CA
Zip: 90210
Units: 1
Credit Score: 720"

# Test 2: Check processing history
curl "https://loan-sizer-saas.onrender.com/email/processing-history" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📧 What Prospects Will Experience

### 1. Forward Email To:
```
loans+complaicore-test@complaicore.com
```

### 2. Receive Response (within 30 seconds):
**Subject:** RE: Loan App - 123 Main St - APPROVE

**Email Body:**
- Large ✓ APPROVE or ✗ DECLINE decision box
- Property details table
- If FAIL: Bullet points explaining why
- Program results table
- Completed Excel file attached

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "from address does not match verified Sender Identity" | Complete Step 1-3 (Domain Auth) |
| Emails not being received | Check SendGrid Inbound Parse logs |
| Webhook returning errors | Check Render logs at dashboard.render.com |
| Data not extracting properly | Try different email formatting |

---

## 📊 Pricing

- **SendGrid Free**: 100 emails/day
- **Render Free**: 750 hours/month
- **Your cost**: $0/month for testing

---

## Next Steps

1. ✅ Complete Steps 1-4 above
2. ✅ Forward a test email to `loans+complaicore-test@complaicore.com`
3. ✅ Check your inbox for the automated response
4. ✅ Review the attached Excel file

**Total setup time: ~15 minutes**

---

## Support

Need help? Check:
- Render logs: https://dashboard.render.com/web/srv-d7at2ksvjg8s73en075g
- SendGrid activity: https://app.sendgrid.com/email_activity
- API docs: https://loan-sizer-saas.onrender.com/docs
