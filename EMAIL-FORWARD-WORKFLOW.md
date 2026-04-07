# 📧 Email Forward Workflow - Zero-Touch Loan Processing

## Overview

**The simplest workflow possible:**

1. **Forward** applicant email to your unique address
2. **System reads** the email + any PDF attachments
3. **AI extracts** all loan application data
4. **Sizer runs** pass/fail analysis automatically
5. **Results emailed back** with filled Excel template attached

**Total Time: 5 seconds to forward → Results in 60 seconds**

---

## 🎯 How It Works

```
Loan Officer Workflow:
┌─────────────────┐
│  Get applicant  │
│     email       │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│ Forward to:              │
│ abclending@process.      │
│ loansizer.com            │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐     ┌─────────────────┐
│  System processes:       │────▶│ Parse forwarded │
│  • Extract email body    │     │ email format    │
│  • Read PDF attachments  │     └────────┬────────┘
│  • Extract variables     │              │
│  • Run sizer             │              ▼
│  • Generate results      │     ┌─────────────────┐
└────────┬─────────────────┘     │ Extract data:   │
         │                       │ • Address       │
         │                       │ • Loan amount   │
         │                       │ • Credit scores │
         │                       │ • Property info │
         │                       └────────┬────────┘
         │                                │
         ▼                                ▼
┌──────────────────────────┐     ┌─────────────────┐
│ Results email sent back: │     │ Run sizer with  │
│                          │◄────│ extracted data  │
│ ✅ DECISION: APPROVED    │     └─────────────────┘
│                          │
│ Programs:                │
│ • Insurance: PASS        │
│ • Short Term: PASS       │
│ • Bridge: FAIL           │
│                          │
│ 📎 Attachment:           │
│ Filled_Sizer.xlsx        │
└──────────────────────────┘
```

---

## 📋 Setup Instructions

### Step 1: Deploy to Render (Same as before)

Follow the `DEPLOY-AND-USE.md` guide to deploy the backend and frontend.

### Step 2: Configure Email Provider

Choose one of these providers for receiving/sending emails:

#### Option A: SendGrid (Recommended)

1. Sign up at https://sendgrid.com
2. Go to Settings → Inbound Parse
3. Add host/hostname: `process.loansizer.com`
4. Set webhook URL: `https://your-api.onrender.com/email/webhook/sendgrid`
5. Get API Key from Settings → API Keys

#### Option B: Mailgun

1. Sign up at https://mailgun.com
2. Add domain: `process.loansizer.com`
3. Create route: `.*@process.loansizer.com`
4. Set forward webhook: `https://your-api.onrender.com/email/webhook/mailgun`
5. Get API Key from Domain Settings

#### Option C: AWS SES + Lambda

For enterprise setups (not covered here, contact support).

### Step 3: Set Environment Variables in Render

Add these to your Render dashboard:

```bash
# Required for sending emails back
SENDGRID_API_KEY = SG.xxxxxx (or MAILGUN_API_KEY)
MAILGUN_DOMAIN = process.loansizer.com (if using Mailgun)

# Required for receiving emails
EMAIL_WEBHOOK_SECRET = random-secret-for-validation

# Your app's domain
APP_DOMAIN = https://your-api.onrender.com
```

### Step 4: Create Client & Get Forwarding Address

1. Register your lending company via the API:

```bash
curl -X POST https://your-api.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "ABC Lending",
    "email": "admin@abclending.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Smith"
  }'
```

2. Get your unique forwarding address:

```bash
curl -X GET https://your-api.onrender.com/email/forwarding-address/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "client_id": 1,
  "client_name": "ABC Lending",
  "forwarding_address": "abc-lending@process.loansizer.com",
  "instructions": "Forward loan application emails to: abc-lending@process.loansizer.com"
}
```

3. **Save this address** - this is where you'll forward all applicant emails!

---

## 🚀 Using the Workflow

### Forward an Email

1. **Receive applicant email** in your normal inbox
2. **Click Forward**
3. **Send to:** `abc-lending@process.loansizer.com`
4. **Done!** (No need to change subject or body)

### What the System Does

**Within 60 seconds:**

✅ **Parses forwarded email** (works with Gmail, Outlook, Apple Mail)
✅ **Extracts from email body:**
   - Property address
   - Loan amount
   - Credit scores
   - Units, purchase price, etc.

✅ **Reads PDF attachments** (if any)
   - Application forms
   - Property documents
   - Financial statements

✅ **Runs sizer** with extracted data
✅ **Generates email response** with:
   - **Bold, highlighted decision** (GREEN = APPROVE, RED = DECLINE)
   - Program pass/fail breakdown
   - Property summary
   - **Attached:** Filled Excel sizer

### Example Response Email

```
Subject: RE: Loan Application - 8 Unit Multifamily - APPROVED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         ✅  OVERALL DECISION: APPROVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You qualified for 2 of 3 programs

Property Details
─────────────────
Address: 307 S Main Street, Hopkinsville, KY 44240
Units: 8
Loan Amount: $784,000
LTV: 65.3%
Credit Score: 703

Program Results
─────────────────
Insurance Program        ✅ PASS    $900,000 max
Short Term Note Sale     ✅ PASS    $840,000 max  
Bridge Loan              ❌ FAIL    DSCR too low

📎 Attachment: LoanSizer_Analysis_20250407.xlsx

This analysis was generated automatically by Loan Sizer AI.
Processing time: 2.3 seconds
```

---

## 📎 Supported Email Formats

The system automatically detects and parses forwarded emails from:

### Gmail
```
---------- Forwarded message ----------
From: Applicant Name <applicant@email.com>
Date: Mon, Apr 7, 2025 at 10:30 AM
Subject: Loan Application
To: you@yourcompany.com

[Original message body]
```

### Outlook
```
From: Applicant Name <applicant@email.com>
Sent: Monday, April 7, 2025 10:30 AM
To: you@yourcompany.com
Subject: Loan Application

[Original message body]
```

### Apple Mail
```
Begin forwarded message:

From: Applicant Name <applicant@email.com>
Subject: Loan Application
Date: April 7, 2025 at 10:30:00 AM CDT

[Original message body]
```

---

## 📄 Supported Attachments

| File Type | Extracts Data From |
|-----------|-------------------|
| PDF | Application forms, credit reports, property docs |
| Excel (.xlsx, .xlsm) | Pre-filled sizers (for re-processing) |
| Images (.jpg, .png) | Not currently supported |

---

## 🔐 Security & Access Control

### Who Can Forward?

Only registered users for your client account can forward emails:

1. **Admin creates users** via dashboard
2. **Users forward from their registered email**
3. **System validates** forwarder is authorized
4. **Rejects emails** from unknown addresses

### Example Security Flow

```
Applicant ──▶ Loan Officer (john@abclending.com)
                    │
                    │ Forward
                    ▼
            abc-lending@process.loansizer.com
                    │
                    │ System checks:
                    │ ✅ john@abclending.com registered?
                    │ ✅ Belongs to ABC Lending client?
                    │
                    ▼
            Process & Send Results
                    │
                    ▼
            Back to john@abclending.com
```

---

## 📊 Viewing Processing History

### API Endpoint

```bash
curl -X GET https://your-api.onrender.com/email/processing-history \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "history": [
    {
      "id": 123,
      "forwarder_email": "john@abclending.com",
      "subject": "Fwd: Loan Application - 8 Unit",
      "original_sender": "applicant@email.com",
      "decision": "APPROVE",
      "status": "completed",
      "email_sent": true,
      "processing_time_ms": 2340,
      "created_at": "2025-04-07T14:30:00"
    }
  ]
}
```

### Dashboard View

Login to your dashboard → "Email History" tab

See:
- All processed emails
- Decisions made
- Processing times
- Download original attachments

---

## ⚙️ Customization

### Custom Email Domain

Instead of `@process.loansizer.com`, use your own:

**Setup:**
```
applications@abclending.com  →  forwards to  →  abc-lending@process.loansizer.com
```

**Steps:**
1. Create email alias in your domain (Google Workspace, Office 365, etc.)
2. Set to forward to your `abc-lending@process.loansizer.com` address
3. Update client record with custom domain

### Custom Email Templates

Modify the response email format:

1. Go to Dashboard → Settings → Email Templates
2. Edit HTML templates
3. Available variables:
   - `{{decision}}` - APPROVE/DECLINE
   - `{{decision_color}}` - Green/Red hex
   - `{{programs}}` - Program results table
   - `{{property_address}}`
   - `{{loan_amount}}`
   - `{{credit_score}}`

### Auto-Forward from Gmail

Set up Gmail filter to auto-forward:

1. Gmail → Settings → Filters
2. Create filter:
   - From: `*@gmail.com` (or specific domains)
   - Subject: `loan application`
3. Action: Forward to `abc-lending@process.loansizer.com`

⚠️ **Requires verification** - Gmail sends confirmation to forwarding address first

---

## 🛠️ Troubleshooting

### "Email not processed"

**Check:**
- Forwarder email is registered user
- Sending to correct address: `your-slug@process.loansizer.com`
- Email provider webhooks are configured

### "No data extracted"

**Check:**
- Email contains loan details (address, amount, credit scores)
- PDF is not scanned image (needs OCR - not supported yet)
- Try forwarding with full email body (not just snippet)

### "No response email received"

**Check:**
- `SENDGRID_API_KEY` or `MAILGUN_API_KEY` is set
- API key has mail send permissions
- Forwarder email not in bounce list

### "Wrong applicant email"

The system tries to extract applicant email from:
1. Forwarded email headers (From: field)
2. Email body signatures
3. Original sender info

**If wrong:** Update manually in dashboard after processing

---

## 💰 Pricing for Email Processing

Email processing uses the same pricing tiers:

| Plan | Monthly | Emails/Month | Users |
|------|---------|--------------|-------|
| Starter | $299 | 100 | 3 |
| Professional | $799 | 500 | 7 |
| Enterprise | $2,499 | Unlimited | Unlimited |

**Overages:** $0.50 per email after limit

---

## 🔄 Comparison: Dashboard vs Email Forward

| Feature | Dashboard | Email Forward |
|---------|-----------|---------------|
| **Time to process** | 2 min | 5 seconds |
| **Setup required** | Login, paste, click | Just forward |
| **Best for** | Complex apps, review needed | Quick screening |
| **PDF attachments** | Manual upload | Auto-processed |
| **Batch processing** | One at a time | Multiple forwards |
| **Human oversight** | Before sending | After receiving |

**Recommendation:** Use email forward for 80% of applications, dashboard for complex cases.

---

## 📈 Metrics & Analytics

Track via Dashboard:

- **Emails processed today/this week/month**
- **Average processing time**
- **Approval rate**
- **Most common rejection reasons**
- **Time saved vs manual processing**

---

## 🚀 Next Steps

1. ✅ Deploy to Render
2. ✅ Configure SendGrid/Mailgun
3. ✅ Create client account
4. ✅ Get forwarding address
5. ✅ Add team members
6. ✅ Forward first test email
7. ✅ Review results
8. 🔄 Train team on workflow
9. 🔄 Set up auto-forward filters
10. 🔄 Monitor metrics weekly

---

## 📞 Support

**Issues?**
- Check `/email/processing-history` endpoint
- Review logs in Render dashboard
- Contact: PN@complaicore.com

**Feature Requests:**
- Custom extraction rules
- Additional file formats
- Integration with specific LOS systems

---

**Ready to process loans in 5 seconds?** 🎉

Set up your forwarding address and test with a sample email!
