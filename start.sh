#!/bin/bash
# BankCCTV - Start all services

echo "🏦 BankCCTV AI Investigation System"
echo "======================================"

# Start backend
echo "🚀 Starting FastAPI backend on port 8000..."
cd /Users/samaysamrat/bankcctv/backend
./venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

# Start frontend
echo "🎨 Starting React frontend on port 5173..."
cd /Users/samaysamrat/bankcctv/frontend
npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Services started!"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
