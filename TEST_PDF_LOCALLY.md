# Test PDF Parsing Locally - Quick Start

## ⏰ Time Required: 2 minutes

---

## Step 1: Open Terminal

**On your Mac:**
- Press `Cmd + Space`
- Type "Terminal"
- Press Enter

---

## Step 2: Navigate to Project

```bash
cd ~/workspace/loan-sizer-saas/backend
```

---

## Step 3: Start Backend Server

```bash
uvicorn pdf_api:app --host 0.0.0.0 --port 8000
```

**You should see:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Leave this Terminal window open!** (This is your running server)

---

## Step 4: Test Health Endpoint (New Terminal Window)

**Open a NEW Terminal window** (Cmd + Space, type "Terminal")

```bash
curl http://localhost:8000/api/v1/health
```

**Expected response:**
```json
{"status":"healthy","redis":false,"timestamp":"2026-05-09T..."}
```

✅ **If you see this, the backend is working!**

---

## Step 5: Test PDF Upload (Same New Terminal)

**Create a test PDF or use an existing one:**

```bash
# If you have a PDF file:
curl -X POST http://localhost:8000/api/v1/demo/parse-pdf \
  -F "file=@/path/to/your/loan_application.pdf"

# Example:
curl -X POST http://localhost:8000/api/v1/demo/parse-pdf \
  -F "file=@~/Downloads/loan_app.pdf"
```

**Expected response:**
```json
{
  "success": true,
  "fields": {
    "purchase_price": 250000,
    "as_is_value": 240000,
    ...
  },
  "filename": "loan_app.pdf"
}
```

---

## Step 6: Test Frontend Integration

1. Open `frontend/index.html` in your browser:
   ```bash
   open ~/workspace/loan-sizer-saas/frontend/index.html
   ```

2. Go to "Multi-Lender Compare" tab

3. Upload a PDF file

4. **It should auto-populate the form!**

---

## ❌ Common Errors

### Error: "command not found: uvicorn"

**Fix:**
```bash
pip install uvicorn fastapi
```

### Error: "No module named 'pdf_api'"

**Fix:** Make sure you're in the backend directory:
```bash
cd ~/workspace/loan-sizer-saas/backend
```

### Error: "Address already in use"

**Fix:** Port 8000 is in use. Kill it:
```bash
lsof -ti:8000 | xargs kill -9
```
Then restart the server.

---

## 🚀 Once Local Testing Works

Deploy to Render so anyone can use it:

1. Go to https://dashboard.render.com/
2. Click "New +" → "Blueprint"
3. Connect `pn4556/loan-sizer-saas`
4. Deploy!

---

## ❓ Need Help?

**If you get stuck, tell me:**
1. What step you're on
2. What error you see
3. I'll help fix it

**Ready to test?** Open Terminal and follow Step 1!
