#!/bin/bash

echo "Stopping Flask..."
pkill -f "python -m src.api.app" || true

echo "Checking port..."
lsof -i :8000 || true

echo "Starting Flask..."
nohup python -m src.api.app > /tmp/dmv_flask.log 2>&1 &

sleep 3

echo "Testing localhost..."
curl -I http://localhost:8000/review/1

echo ""
echo "Flask log:"
tail -20 /tmp/dmv_flask.log
