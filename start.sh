#!/bin/bash
cd /c/Projects/QuantHub

echo "Starting database..."
cd docker && docker compose up -d && cd ..

echo "Starting backend..."
cd backend
export DATABASE_URL="postgresql+asyncpg://quant_hub:$(grep POSTGRES_PASSWORD docker/.env 2>/dev/null | cut -d= -f2)@localhost:5432/quant_hub"
PYTHONPATH=src python -m uvicorn quant_hub.main:app --reload &
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
