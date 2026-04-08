# 🏦 Loan Sizer Automation System

AI-powered loan application processing that reduces 20-30 minute manual reviews to under 2 minutes.

## 🎯 What This System Does

**Problem:** Real estate loan officers spend 20-30 minutes manually extracting data from applicant emails, entering it into Excel sizers, checking daily rates, and drafting approval/rejection emails.

**Solution:** AI automation that processes applications in under 2 minutes with human oversight.

### Workflow Overview

```
Applicant Email → AI Extraction → Sizer Population → Programs Evaluation → Email Draft
     (30 sec)         (20 sec)          (10 sec)           (15 sec)        (20 sec)
```

**Total Time: ~95 seconds vs. 25 minutes manually (93% time savings)**

---

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.8+
pip install fastapi uvicorn anthropic openpyxl python-dotenv

# Or install from requirements.txt
pip install -r backend/requirements.txt
```

### Running the Backend
```bash
cd backend

# Set your Anthropic API key (optional - demo mode works without it)
export ANTHROPIC_API_KEY="your-key-here"

# Start the server
python app.py

# API will be available at http://localhost:5050
```

### Running the Frontend
```bash
# Simply open the HTML file in a browser
cd frontend
open index.html

# Or serve with a simple HTTP server
python -m http.server 8080
# Then visit http://localhost:8080
```

---

## 📁 Project Structure

```
loan-sizer-automation/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables (create this)
├── frontend/
│   └── index.html            # Dashboard UI
├── demo-data/
│   └── template.xlsx         # Excel sizer template (add yours)
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
DEFAULT_RATE=8.50
EMAIL_FROM=loans@yourcompany.com
```

### Excel Sizer Template

1. Add your Excel `.xlsm` file to `demo-data/template.xlsx`
2. Update the cell mappings in `app.py` to match your sizer layout:

```python
cell_mappings = {
    'C8': application.units,
    'C9': application.unit_size,
    'E5': application.address,
    'E6': application.city,
    'E7': application.state,
    'E8': application.zip_code,
    'G5': application.estimated_value,
    'G6': application.purchase_price,
    'I5': application.loan_amount,
    'I8': application.note_type,
    'I10': application.points_to_lender,
    'M7': application.credit_scores.middle_score,
    'G10': daily_rate,
}
```

---

## 📡 API Endpoints

### 1. Extract Application Data
```http
POST /api/extract
Content-Type: application/x-www-form-urlencoded

email_content=Subject: Loan Application...
```

**Response:**
```json
{
  "application": {
    "units": 8,
    "address": "1428 Elmwood Ave",
    "city": "Philadelphia",
    "state": "PA",
    "zip_code": "19103",
    "estimated_value": 1200000,
    "purchase_price": 980000,
    "loan_amount": 784000,
    "note_type": "30 YR Fixed",
    "points_to_lender": 1.0,
    "credit_scores": {
      "score1": 688,
      "score2": 712,
      "score3": 703,
      "middle_score": 703
    }
  },
  "confidence": 0.95,
  "missing_fields": []
}
```

### 2. Full Processing Pipeline
```http
POST /api/process
Content-Type: application/x-www-form-urlencoded

email_content=...&daily_rate=8.50&applicant_email=james@email.com
```

**Response:**
```json
{
  "status": "complete",
  "extraction": {...},
  "sizer_result": {
    "programs": [
      {
        "program_name": "Short Term Note Sale",
        "status": "PASS",
        "max_loan_amount": 900000,
        "dscr": 1.25
      }
    ],
    "overall_decision": "APPROVE",
    "decision_reason": "Qualified for 2 of 3 programs"
  },
  "generated_email": {...},
  "time_saved": "20-25 minutes"
}
```

### 3. Get Demo Scenarios
```http
GET /api/demo/scenarios
```

---

## 🎨 Features

### For Loan Officers
- 📧 **Email Intake** - Paste any applicant email (no structured form needed)
- 🤖 **AI Extraction** - Claude API extracts all relevant fields automatically
- 📊 **Credit Score Logic** - Automatically takes middle of 3 scores
- 💾 **Sizer Population** - Auto-populates Excel with extracted data
- ✅ **Programs Evaluation** - Checks pass/fail for all loan programs
- 📧 **Email Generation** - Drafts approval/rejection emails instantly
- 👁️ **Human Review** - Officer reviews before sending

### Technical Features
- **FastAPI Backend** - Modern, fast Python API
- **Claude AI Integration** - Intelligent email parsing (falls back to regex if no API key)
- **Excel Automation** - openpyxl for reading/writing sizers
- **Real-time Processing** - Under 2 minutes end-to-end
- **Responsive Dashboard** - Clean UI for processing applications
- **Demo Scenarios** - Built-in test cases for demonstration

---

## 💰 Business Value

### Time Savings
- **Before:** 25 minutes per application
- **After:** 2 minutes per application
- **Savings:** 23 minutes per application

### Cost Savings (20 applications/day)
- Manual processing: 8.3 hours/day
- With automation: 0.7 hours/day
- **Daily savings:** 7.6 hours
- **Monthly savings:** ~$9,500 (at $50/hr)

### Error Reduction
- No manual transcription errors
- Consistent credit score calculations
- Standardized email templates
- Full audit trail

---

## 🔒 Security & Compliance

### Data Protection
- No applicant data stored permanently (configurable)
- API keys in environment variables
- Optional audit logging

### Human Oversight
- All decisions require officer review
- One-click approval to send emails
- Override capability for edge cases

---

## 🚀 Deployment Options

### Option 1: Local Server
```bash
python backend/app.py
# Access at http://localhost:5050
```

### Option 2: Cloud Deployment (Render/Railway)
```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push origin main

# Connect to Render or Railway
# Set environment variables in dashboard
```

### Option 3: Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "app.py"]
```

---

## 🛠️ Customization

### Adding New Programs
Edit the `_evaluate_programs` method in `backend/app.py`:

```python
def _evaluate_programs(self, application, rate):
    programs = []
    
    # Your custom program logic
    if application.ltv_ratio <= 75 and application.credit_scores.middle_score >= 680:
        programs.append(ProgramResult(
            program_name="Your Custom Program",
            status="PASS",
            max_loan_amount=application.estimated_value * 0.75
        ))
    
    return programs
```

### Custom Email Templates
Edit `generate_approval_email` and `generate_rejection_email` functions in `app.py`.

### Integration with Email Systems
Connect to Gmail/Outlook APIs to automatically monitor inbox:

```python
# Gmail API integration example
def monitor_inbox():
    # Check for new loan application emails
    # Process each one automatically
    pass
```

---

## 📞 Support & Next Steps

### For the Client
1. **Week 1:** Deploy MVP with demo scenarios
2. **Week 2:** Integrate real Excel sizer template
3. **Week 3:** Connect to live email inbox
4. **Week 4:** Train loan officers & go live

### Customization Needs
- Custom program guidelines
- Branded email templates
- Additional data fields
- Integration with LOS (Loan Origination System)

---

## 📧 Contact

Built by: **Phong Nguyen**  
📧 PN@complaicore.com  
🌐 complaicore.com

---

*This system represents the future of loan processing - AI-augmented, human-supervised, dramatically faster.*
# Loan Sizer Web Processor


<!-- Deployed: 2026-04-08 21:15 EST -->
