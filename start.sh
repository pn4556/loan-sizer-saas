#!/bin/bash

# Loan Sizer Automation - Quick Start Script

echo "🏦 Loan Sizer Automation System"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -q -r backend/requirements.txt

echo ""
echo "🚀 Starting the system..."
echo ""

# Start backend in background
cd backend
echo "🌐 Starting API server on http://localhost:5050"
python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

cd ..

# Open frontend
echo "🎨 Opening dashboard..."
if command -v open &> /dev/null; then
    # macOS
    open frontend/index.html
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open frontend/index.html
else
    echo "📁 Please open frontend/index.html in your browser"
fi

echo ""
echo "✅ System is running!"
echo ""
echo "📊 Dashboard: frontend/index.html"
echo "🔌 API: http://localhost:5050"
echo ""
echo "Press Ctrl+C to stop"

# Wait for interrupt
trap "kill $BACKEND_PID; exit" INT
wait
