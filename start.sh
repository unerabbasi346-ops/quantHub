#!/bin/bash
cd /c/Projects/QuantHub

echo "Starting database..."
cd docker && docker compose up -d && cd ..

echo "Starting backend..."
cd backend
uv run python -m uvicorn quant_hub.main:app --reload &
cd ..

echo "Starting frontend..."
cd frontend
npm run dev &
cd ..

echo ""
echo "Everything is starting. Give it about 10 seconds, then open:"
echo "http://localhost:3000"
echo ""
echo "To stop everything, close this terminal window or press Ctrl+C."
wait
