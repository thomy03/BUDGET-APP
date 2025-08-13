#!/bin/bash
while true; do
    # Check backend
    if ! curl -s -f http://127.0.0.1:8000/docs > /dev/null; then
        echo "[$(date)] ❌ Backend health check failed"
    fi
    
    # Check frontend  
    if ! curl -s -f http://127.0.0.1:45678 > /dev/null; then
        echo "[$(date)] ❌ Frontend health check failed"
    fi
    
    # Check Docker container
    if ! docker ps --format "table {{.Names}}" | grep -q "budget-frontend"; then
        echo "[$(date)] ❌ Frontend container not running"
    fi
    
    sleep 30
done
