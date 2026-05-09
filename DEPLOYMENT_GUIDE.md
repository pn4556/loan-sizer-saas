# Loan Sizer Backend - Complete Deployment Guide

## 🎯 Goal
Get the PDF upload working in the Multi-Lender Compare tab.

## 🚨 Problem
The backend API is not deployed. The frontend can't parse PDFs.

---

## ✅ Option 1: Local Testing (FASTEST - 2 minutes)

Test the PDF parsing on your local machine before deploying.

### Step 1: Start Local Backend

**On your Mac, open Terminal and run:**

```bash
cd ~/workspace/loan-sizer-saas/backend

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn pdf_api:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Test Local Backend

**Open a new Terminal window and run:**

```bash
curl http://localhost:8000/api/v1/health
```

**Expected response:**
```json
{"status": "healthy", "redis": false, "timestamp": "..."}
```

### Step 3: Update Frontend for Local Testing

**Edit `frontend/index.html`:**

Find line 6424-6426:
```javascript
const PARSER_API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api/v1'
    : 'https://loan-sizer-api.onrender.com/api/v1';
```

Change to (temporary):
```javascript
const PARSER_API_URL = 'http://localhost:8000/api/v1';
```

### Step 4: Test PDF Upload

1. Open `frontend/index.html` in your browser (file:// or local server)
2. Go to "Multi-Lender Compare" tab
3. Upload a PDF
4. It should work!

### Step 5: Deploy to Render (After Testing)

Once local testing works, deploy to Render so others can use it.

---

## 🌐 Option 2: Deploy to Render (RECOMMENDED - 10 minutes)

Deploy the backend to Render.com so it's accessible from anywhere.

### Step 1: Create Render Account (If Not Done)

1. Go to https://render.com/
2. Click "Get Started for Free"
3. Sign up with GitHub

### Step 2: Create Blueprint Deployment

1. Go to https://dashboard.render.com/blueprints
2. Click "New Blueprint Instance"
3. Connect your GitHub account
4. Find and select: `pn4556/loan-sizer-saas`
5. Click "Apply"

**Render will automatically:**
- Read `render.yaml`
- Create `loan-sizer-api` service
- Create PostgreSQL database
- Deploy the backend

### Step 3: Wait for Deployment

This takes 5-10 minutes. You'll see:
- Build logs
- "Your service is live" message
- URL: `https://loan-sizer-api.onrender.com`

### Step 4: Test Deployed Backend

```bash
curl https://loan-sizer-api.onrender.com/api/v1/health
```

**Expected:**
```json
{"status": "healthy", "redis": false, "timestamp": "..."}
```

### Step 5: Update Frontend (If Needed)

**In `frontend/index.html`, line 6424-6426:**

```javascript
const PARSER_API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api/v1'
    : 'https://loan-sizer-api.onrender.com/api/v1';
```

**This should already be correct.** If not, update the second URL.

### Step 6: Deploy Frontend

If frontend is on Render:
1. Go to https://dashboard.render.com/
2. Find `loan-sizer-dashboard` service
3. Click "Manual Deploy" → "Deploy latest commit"

If frontend is on GitHub Pages:
1. Push changes to GitHub
2. GitHub Pages auto-deploys

---

## 🐨 Option 3: Docker Deployment (ADVANCED)

Deploy using Docker for more control.

### Create Dockerfile

**File: `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "pdf_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run

```bash
cd ~/workspace/loan-sizer-saas/backend

# Build
docker build -t loan-sizer-api .

# Run
docker run -p 8000:8000 loan-sizer-api
```

### Deploy to Render (Docker)

1. In Render dashboard, create "Web Service"
2. Choose "Docker" runtime
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `docker build -t loan-sizer-api ./backend`
   - **Start Command:** `docker run -p $PORT:8000 loan-sizer-api`

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Fix:**
```bash
cd ~/workspace/loan-sizer-saas/backend
pip install fastapi uvicorn python-multipart pydantic
```

### Issue: "Port 8000 already in use"

**Fix:**
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn pdf_api:app --host 0.0.0.0 --port 8001
```

### Issue: "CORS error" in browser

**Fix:** Backend already has CORS enabled. If still failing, check:
- Frontend URL matches allowed origins
- Backend is running and accessible

### Issue: "Failed to fetch" when uploading PDF

**Check:**
1. Is backend running? `curl http://localhost:8000/api/v1/health`
2. Is frontend using correct URL? Check browser console
3. Is file size < 10MB? Large files may timeout

---

## 🎨 What I Can Do For You

Since I can't access your Render dashboard, here are your options:

### Option A: You Deploy (I Guide)
You follow the steps above, I answer questions in real-time.

### Option B: Manual PDF Processing (Immediate)
Upload PDFs to this chat, I extract data manually.

### Option C: Create Deployment Script
I create a one-click deployment script you run.

---

## 📞 Recommended Next Step

**Choose your path:**

1. **"TEST LOCAL"** - Start local backend now (2 min)
2. **"DEPLOY RENDER"** - I'll guide you step-by-step (10 min)
3. **"MANUAL PROCESS"** - Upload PDFs here, I extract data

**Current status:** Code is ready, deployment needed.

---

## 📋 Files Ready for Deployment

- ✅ `backend/pdf_api.py` - Main API with /demo/parse-pdf endpoint
- ✅ `backend/pdf_parser_service.py` - PDF parsing logic
- ✅ `backend/requirements.txt` - Dependencies
- ✅ `render.yaml` - Render deployment config
- ✅ `frontend/index.html` - Updated with correct API URL

**Everything is ready. Just need to deploy.**

Which option do you want?
