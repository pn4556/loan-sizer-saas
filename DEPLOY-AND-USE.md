# 🚀 Loan Sizer SaaS - Deploy to Render & Usage Guide

## Part 1: Deploy to Render (15 minutes)

### Step 1: Push Code to GitHub

```bash
cd ~/workspace/loan-sizer-automation

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial SaaS deployment"

# Create GitHub repo and push
gh repo create loan-sizer-saas --public --source=. --push
```

### Step 2: Deploy Backend to Render

1. **Go to Render Dashboard**: https://dashboard.render.com

2. **Create PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - Name: `loan-sizer-db`
   - Plan: Starter ($7/month)
   - Click "Create Database"
   - **Copy the Internal Database URL** (you'll need it)

3. **Create Web Service for Backend**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repo: `loan-sizer-saas`
   - Configure:
     - **Name**: `loan-sizer-api`
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r backend/requirements-saas.txt`
     - **Start Command**: `cd backend && uvicorn api_saas:app --host 0.0.0.0 --port $PORT`
   
4. **Add Environment Variables**:
   - Click "Advanced" → "Add Environment Variable"
   - Add these:
     ```
     DATABASE_URL = postgresql://loansizer:password@host:5432/loansizer (from step 2)
     SECRET_KEY = (generate a random string - use: openssl rand -hex 32)
     ANTHROPIC_API_KEY = your_claude_api_key_here (optional - demo works without)
     DEFAULT_RATE = 8.50
     CORS_ORIGINS = *
     ```
   
5. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Wait for "Deploy succeeded" message
   - **Copy your API URL**: `https://loan-sizer-api-xxx.onrender.com`

### Step 3: Deploy Frontend to Render

1. **Create Static Site**:
   - Click "New +" → "Static Site"
   - Connect the same GitHub repo
   - Configure:
     - **Name**: `loan-sizer-dashboard`
     - **Build Command**: `echo "No build needed"`
     - **Publish Directory**: `./frontend`
   
2. **Add Environment Variable**:
   ```
   API_URL = https://loan-sizer-api-xxx.onrender.com (from Step 2)
   ```

3. **Create Custom Domain (Optional)**:
   - In your static site settings, click "Custom Domains"
   - Add your subdomain: `loansizer.yourdomain.com`
   - Follow Render's DNS instructions
   - Or use Render's free subdomain: `loan-sizer-dashboard.onrender.com`

4. **Deploy**:
   - Click "Create Static Site"
   - Your dashboard is now live!

---

## Part 2: Initial Setup (10 minutes)

### Step 1: Create First Admin Account

Use curl or Postman to create the first client:

```bash
curl -X POST https://loan-sizer-api-xxx.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Your Lending Company",
    "email": "admin@yourcompany.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Smith"
  }'
```

**Response will include**:
- Client ID
- Admin user details
- Login credentials

### Step 2: Log Into Dashboard

1. Open your dashboard URL: `https://loan-sizer-dashboard-xxx.onrender.com`
2. Log in with:
   - Email: `admin@yourcompany.com`
   - Password: `SecurePass123!`

### Step 3: Upload Excel Sizer Template

1. Click "Templates" in the sidebar
2. Click "Upload New Template"
3. Select your Excel sizer file (.xlsx or .xlsm)
4. Configure cell mappings (match your sizer layout):
   ```
   Units → C8
   Address → E5
   City → E6
   State → E7
   Zip → E8
   Estimated Value → G5
   Purchase Price → G6
   Loan Amount → I5
   Credit Score → M7
   ```
5. Click "Save Template"

---

## Part 3: Process Your First Loan Application

### Method 1: Email Processing

1. **Navigate to Dashboard** → "Process Application"

2. **Paste Applicant Email**:
   ```
   Subject: Loan Application - 8 Unit Multifamily

   Hello,

   I'm interested in financing for an 8-unit multifamily property at 
   307 S Main Street, Hopkinsville, KY 44240.

   Property Details:
   - 8 units, approximately 750 sq ft each
   - Estimated value: $1,200,000
   - Purchase price: $980,000
   - Requested loan amount: $784,000
   - Note type: 30 YR Fixed

   My credit scores are 688, 712, and 703.
   Points to lender: 1%

   Please let me know what programs I qualify for.

   Thanks,
   James Whitfield
   james.whitfield@email.com
   ```

3. **Enter Daily Rate**: 8.50 (or your current rate)

4. **Click "Process Application"**

5. **Review Results** (takes ~30 seconds):
   - Extracted data fields
   - Credit score (middle of 3: 703)
   - LTV ratio (65.3%)
   - Program eligibility
   - Overall decision (APPROVE/DECLINE)

6. **Download Populated Sizer** or **Send Email** to applicant

### Method 2: PDF Upload

1. Click "PDF Upload" tab
2. Drag & drop applicant's PDF
3. System extracts data automatically
4. Review and process same as email

### Method 3: Manual Entry

1. Click "Manual Entry" tab
2. Fill in property and applicant details
3. Click "Process"

---

## Part 4: Understanding Results

### Program Evaluation

The system checks against your configured programs:

| Program | Criteria | Status |
|---------|----------|--------|
| Insurance Program | LTV ≤ 75%, Credit ≥ 680 | ✅ PASS |
| Short Term Sale | LTV ≤ 70%, Credit ≥ 650 | ✅ PASS |
| Bridge Loan | LTV ≤ 65%, DSCR ≥ 1.2 | ❌ FAIL |

### Decision Logic

- **APPROVE**: Qualified for ≥2 programs
- **CONDITIONAL**: Qualified for 1 program
- **DECLINE**: Qualified for 0 programs

### Generated Email

The system drafts an email:

```
Subject: Loan Application Update - 307 S Main Street

Dear James,

Thank you for your loan application. We're pleased to inform you 
that you've been pre-qualified for the following programs:

✅ Insurance Program (Max: $900,000)
✅ Short Term Note Sale (Max: $840,000)

Next steps:
1. Schedule property appraisal
2. Submit full documentation
3. Final underwriting review

Best regards,
Your Lending Team
```

---

## Part 5: Managing Users

### Add Loan Officers

1. Go to "Users" section
2. Click "Add User"
3. Enter:
   - Email
   - Name
   - Role: Loan Officer
4. System sends invite email

### User Roles

| Role | Permissions |
|------|-------------|
| Admin | Full access, billing, user management |
| Loan Officer | Process applications, view reports |
| Viewer | Read-only access to applications |

---

## Part 6: Daily Workflow

### Morning Routine (5 minutes)

1. Check overnight applications
2. Review any flagged items
3. Update daily interest rate

### Processing Applications (2 minutes each)

1. Copy email from inbox
2. Paste into dashboard
3. Click "Process"
4. Review AI extraction
5. Download sizer / Send email

### End of Day

1. Review day's decisions
2. Export reports
3. Check application pipeline

---

## Part 7: Customization

### Update Interest Rates

1. Go to Settings
2. Update "Default Rate"
3. All new applications use this rate

### Modify Email Templates

1. Go to Templates → Email Templates
2. Edit approval/rejection templates
3. Use variables: `{applicant_name}`, `{property_address}`, `{programs}`

### Add New Programs

Contact support to add custom program logic based on your lending criteria.

---

## Troubleshooting

### Issue: "Login Failed"
- Check email/password
- Verify API is running: Visit `https://your-api-url/health`

### Issue: "Processing Failed"
- Check ANTHROPIC_API_KEY is set (for AI features)
- Without API key, system uses regex fallback

### Issue: "Template Upload Error"
- Ensure Excel file is .xlsx or .xlsm
- Check file size (< 10MB)
- Verify cell mappings are correct

---

## API Reference (For Developers)

### Authentication
```bash
POST /auth/login
Body: {"email": "...", "password": "..."}
```

### Process Application
```bash
POST /api/process
Headers: Authorization: Bearer <token>
Body: email_content=...&daily_rate=8.50
```

### Upload Template
```bash
POST /templates/upload
Headers: Authorization: Bearer <token>
Body: file=@template.xlsx
```

---

## Next Steps

1. ✅ Deploy to Render
2. ✅ Create admin account
3. ✅ Upload Excel template
4. ✅ Process test application
5. 🔄 Train your team
6. 🔄 Connect email inbox (Gmail/Outlook API)
7. 🔄 Go live with real applications

---

## Support

- **Email**: PN@complaicore.com
- **Documentation**: See README.md
- **API Docs**: Visit `/docs` on your API URL

---

**Time to First Application**: ~25 minutes  
**Time per Application**: ~2 minutes (vs 25 minutes manually)  
**Monthly Savings**: ~$9,500 (20 applications/day)

🎉 Ready to transform your loan processing!
