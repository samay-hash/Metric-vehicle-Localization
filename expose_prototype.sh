#!/bin/bash
echo "================================================="
echo "🚀 Sentinel Copilot Prototype Setup (A to Z)"
echo "================================================="

# 1. Clean up old crashed instances
echo "🧹 [1/4] Cleaning up background ports (8000, 5173)..."
lsof -i :8000 -t | xargs kill -9 > /dev/null 2>&1
lsof -i :5173 -t | xargs kill -9 > /dev/null 2>&1
lsof -i :5174 -t | xargs kill -9 > /dev/null 2>&1

# 2. Start Backend using safe dedicated environment
echo "⚙️  [2/4] Booting Python AI Backend..."
cd backend
# Absolute path to the working python environment
VENV="/Users/samaysamrat/bankcctv/backend/venv/bin"
# Unset any broken global python variables
unset VIRTUAL_ENV
# Make sure Gemini is installed
$VENV/pip install google-genai python-dotenv > /dev/null 2>&1
# Start backend in a single stable process
$VENV/python3 -m uvicorn main:app --port 8000 &
BACKEND_PID=$!

# 3. Start Frontend UI
echo "🎨 [3/4] Booting React Dashboard..."
cd ../frontend
# Run frontend on default port 5173
npm run dev -- --port 5173 &
FRONTEND_PID=$!

cd ..

echo "⏳ Waiting for systems to stabilize (5 seconds)..."
sleep 5

# 4. Generate Public Link
echo "🌐 [4/4] Creating Public Live Link..."
echo "================================================="
echo "✅ SUCCESS! The system is fully online."
echo ""
echo "💻 For Local Screen Recording open: http://localhost:5173"
echo "🌍 For Public Sharing, use the LocalTunnel link generated below:"
echo "================================================="
npx localtunnel --port 5173

# Cleanup if they hit Ctrl+C
trap "echo '\n🛑 Shutting down servers...'; kill -9 $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
