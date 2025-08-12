#!/bin/bash

# Budget Family v2.3 - Development Cleanup Script
# This script stops both backend and frontend services

echo "🛑 Stopping Budget Family v2.3 Development Environment"
echo "======================================================"

# Function to kill processes on specific ports
cleanup_port() {
    port=$1
    echo "🧹 Stopping processes on port $port..."
    
    # Find and kill processes using the port
    pids=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "   Found processes: $pids"
        kill $pids 2>/dev/null
        sleep 2
        
        # Force kill if still running
        remaining_pids=$(lsof -ti :$port 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo "   Force killing remaining processes: $remaining_pids"
            kill -9 $remaining_pids 2>/dev/null
        fi
        echo "✅ Stopped processes on port $port"
    else
        echo "   No processes found on port $port"
    fi
}

# Stop backend from PID file if it exists
if [ -f ".backend_pid" ]; then
    BACKEND_PID=$(cat .backend_pid)
    echo "🔧 Stopping backend (PID: $BACKEND_PID)..."
    
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill -9 $BACKEND_PID 2>/dev/null
        fi
        echo "✅ Backend stopped"
    else
        echo "   Backend process not found (may have already stopped)"
    fi
    
    rm -f .backend_pid
else
    echo "🔧 No backend PID file found, cleaning up port 8000..."
    cleanup_port 8000
fi

# Stop frontend Docker container
echo "🐳 Stopping frontend container..."
if [ -d "frontend" ]; then
    cd frontend
    
    if docker-compose ps frontend-dev | grep -q "Up"; then
        docker-compose stop frontend-dev
        echo "✅ Frontend container stopped"
    else
        echo "   Frontend container not running"
    fi
    
    # Optional: remove the container completely
    echo "❓ Do you want to remove the frontend container? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        docker-compose rm -f frontend-dev
        echo "✅ Frontend container removed"
    fi
    
    cd ..
else
    echo "❌ Frontend directory not found"
fi

# Clean up any remaining processes on our ports
cleanup_port 45678

# Clean up log files
echo "🧹 Cleaning up log files..."
if [ -f "backend.log" ]; then
    rm -f backend.log
    echo "✅ Removed backend.log"
fi

if [ -f "frontend/server.log" ]; then
    rm -f frontend/server.log
    echo "✅ Removed frontend server.log"
fi

echo ""
echo "🎯 Development environment cleanup complete!"
echo "==========================================="
echo ""
echo "📊 Final port status:"
port_8000=$(lsof -ti :8000 2>/dev/null)
port_45678=$(lsof -ti :45678 2>/dev/null)

if [ -z "$port_8000" ]; then
    echo "✅ Port 8000 (backend) is now free"
else
    echo "⚠️  Port 8000 still has processes: $port_8000"
fi

if [ -z "$port_45678" ]; then
    echo "✅ Port 45678 (frontend) is now free"
else
    echo "⚠️  Port 45678 still has processes: $port_45678"
fi

echo ""
echo "💡 You can now restart the development environment with:"
echo "   ./start-development.sh"