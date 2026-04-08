# ComplAiCore Email Integration Setup

## Overview
Enable prospects to forward loan application emails to `loans@complaicore.com` and receive automated analysis with PASS/FAIL decision + completed Excel template.

## How It Works

```
1. Prospect forwards loan app email → loans+{client-slug}@complaicore.com
2. SendGrid webhook sends email to API
3. AI extracts loan data from email body + attachments
4. Runs sizer with client's Excel template
5. Sends back professional HTML email with:
   - ✓ PASS or ✗ FAIL decision (prominently displayed)
   - If FAIL: Bullet points explaining why
   - Property details table
   - Program-by-program breakdown
   - Completed Excel file attached
```

## Setup Steps

### 1. Configure SendGrid for complaicore.com

#### A. Domain Authentication (complaicore.com)
1. Login to SendGrid: https://app.sendgrid.com
2. Go to **Settings** → **Sender Authentication** → **Domain Authentication**
3. Click **Authenticate Your Domain**
4. Select **Other Host** (not listed)
5. Enter domain: `complaicore.com`
6. Enable **Automated Security**
7. SendGrid provides DNS records to add

#### B. Add DNS Records to Squarespace/Registrar
Add these records to your complaicore.com DNS:

```
Type: CNAME
Name: s1._domainkey.complaicore.com
Value: s1.domainkey.uXXXXX.wlXXX.sendgrid.net

Type: CNAME
Name: s2._domainkey.complaicore.com
Value: s2.domainkey.uXXXXX.wlXXX.sendgrid.net

Type: CNAME
Name: emXXXX.complaicore.com
Value: uXXXXX.wlXXX.sendgrid.net
```

*(Actual values provided by SendGrid during setup)*

#### C. Verify Domain
- Back in SendGrid, click **Verify**
- May take a few minutes for DNS to propagate

### 2. Set Up Inbound Parse Webhook

#### A. Create Inbound Parse Rule
1. In SendGrid: **Settings** → **Inbound Parse**
2. Click **Add Host & URL**
3. **Hostname**: `complaicore.com`
4. **Receiving Domain**: `complaicore.com`
5. **Destination URL**: 
   ```
   https://loan-sizer-saas.onrender.com/email/webhook/sendgrid
   ```
6. Check **Spam Check** (optional)
7. Check **Send Raw** (optional)
8. Click **Save**

#### B. Create Catch-All Email Route
In your domain registrar (Squarespace):

1. Go to **Domains** → **complaicore.com** → **DNS**
2. Add MX record:
   ```
   Type: MX
   Name: @ (or loans)
   Priority: 10
   Value: mx.sendgrid.net
   ```

Or use SendGrid's email routing to catch all emails at `loans+*@complaicore.com`.

### 3. Configure API Environment Variables

Add to Render Dashboard (loan-sizer-saas service):

```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=loans@complaicore.com
FROM_NAME=ComplAiCore Loan Sizer
```

### 4. Test the Flow

#### Register a Test Client
```bash
curl -X POST "https://loan-sizer-saas.onrender.com/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@mortgage.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User",
    "company_name": "Test Mortgage Co"
  }'
```

#### Upload Excel Template
```bash
# Login first to get token, then:
curl -X POST "https://loan-sizer-saas.onrender.com/templates/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@your-template.xlsx" \
  -F "name=DSCR Template" \
  -F "loan_type=DSCR"
```

#### Get Forwarding Address
```bash
curl "https://loan-sizer-saas.onrender.com/email/forwarding-address/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "client_id": 1,
  "client_name": "Test Mortgage Co",
  "forwarding_address": "loans+test-mortgage-co@complaicore.com",
  "instructions": "Forward loan application emails to: loans+test-mortgage-co@complaicore.com"
}
```

#### Test Email Forwarding
Forward an email containing:
```
Subject: Loan Application - 123 Main St

Purchase Price: $500,000
Loan Amount: $400,000
Property Type: Single Family
Address: 123 Main St
City: Los Angeles
State: CA
Zip Code: 90210
Units: 1
Credit Score: 720
LTV: 80%
DSCR: 1.25
```

To: `loans+test-mortgage-co@complaicore.com`

### 5. Expected Response Email

You'll receive back:

**Subject:** RE: Loan Application - 123 Main St - APPROVE

**Body:**
- Large ✓ APPROVE box with decision prominently displayed
- Property details table
- Program-by-program results
- If FAIL: Red box with bullet points explaining why
- "📎 Complete Analysis Attached" notice

**Attachment:** `LoanSizer_Analysis_20250408.xlsx`

## Email Format Support

The system handles various forwarded email formats:
- **Gmail**: "---------- Forwarded message ----------"
- **Outlook**: "From: ... Sent: ..."
- **Apple Mail**: "Begin forwarded message:"
- **Plain text**: Direct email body

## Data Extraction

AI automatically extracts:
- Purchase Price / Estimated Value
- Loan Amount
- Property Address (street, city, state, zip)
- Units
- Credit Scores
- LTV / DSCR
- Property Type
- Points/Fees

From both:
- Email body text
- PDF attachments

## Troubleshooting

### Emails Not Being Processed
1. Check SendGrid **Inbound Parse** logs
2. Verify webhook URL is accessible: `curl https://loan-sizer-saas.onrender.com/health`
3. Check Render logs for errors

### No Response Email Received
1. Check spam/junk folders
2. Verify SendGrid API key is valid
3. Check sender reputation in SendGrid

### Data Not Extracting Correctly
1. Try different email formatting
2. Include key fields explicitly: "Purchase Price: $XXX,XXX"
3. Attach PDF loan application as backup

## Security Features

- Only registered client users can forward emails
- Each client has unique `loans+{slug}@complaicore.com` address
- Email processing logged for audit trail
- Attachments scanned (via SendGrid)

## Pricing

- **SendGrid**: Free tier = 100 emails/day
- **Render**: Free tier = 750 hours/month
- **Storage**: Free tier = 512MB

Upgrade as needed for higher volume.

## Support

For issues:
1. Check Render logs: https://dashboard.render.com/
2. Check SendGrid activity: https://app.sendgrid.com/email_activity
3. Contact: support@complaicore.com
