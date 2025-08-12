#!/bin/bash

# Budget App Development Environment Startup Script
# DevOps-optimized startup with health checks and monitoring

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "🚀 Starting Budget App Development Environment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend"
FRONTEND_DIR="/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=45678
MAX_RETRIES=30
RETRY_INTERVAL=2

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Health check function
health_check() {
    local url=$1
    local service_name=$2
    local retries=0
    
    log "Checking health of $service_name at $url..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            success "$service_name is healthy!"
            return 0
        fi
        
        retries=$((retries + 1))
        if [ $retries -lt $MAX_RETRIES ]; then
            log "Attempt $retries/$MAX_RETRIES failed, retrying in ${RETRY_INTERVAL}s..."
            sleep $RETRY_INTERVAL
        fi
    done
    
    error "$service_name failed health check after $MAX_RETRIES attempts"
    return 1
}

# Check if ports are available
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i:$port > /dev/null 2>&1; then
        warning "Port $port is already in use by $service"
        read -p "Kill existing process on port $port? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "Killing process on port $port..."
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            sleep 2
        else
            error "Cannot start $service - port $port is occupied"
            exit 1
        fi
    fi
}

# Start backend service
start_backend() {
    log "Starting Backend Service..."
    
    # Verify backend directory and dependencies
    if [ ! -d "$BACKEND_DIR" ]; then
        error "Backend directory not found: $BACKEND_DIR"
        exit 1
    fi
    
    cd "$BACKEND_DIR"
    
    # Check Python and dependencies
    if ! command -v python3 &> /dev/null; then
        error "Python3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check virtual environment or create one
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        warning "No virtual environment found. Creating one..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        # Activate existing virtual environment
        if [ -d "venv" ]; then
            source venv/bin/activate
        elif [ -d ".venv" ]; then
            source .venv/bin/activate
        fi
    fi
    
    # Check if requirements are installed
    if ! pip list | grep -q fastapi; then
        warning "Installing backend dependencies..."
        pip install -r requirements.txt
    fi
    
    check_port $BACKEND_PORT "Backend"
    
    # Start backend server in background
    log "Launching uvicorn server on port $BACKEND_PORT..."
    nohup python3 -m uvicorn app:app --reload --host 127.0.0.1 --port $BACKEND_PORT > backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > backend.pid
    
    # Health check
    if health_check "http://127.0.0.1:$BACKEND_PORT/docs" "Backend API"; then
        success "Backend started successfully (PID: $BACKEND_PID)"
    else
        error "Backend startup failed"
        exit 1
    fi
}

# Start frontend service
start_frontend() {
    log "Starting Frontend Service..."
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        error "Frontend directory not found: $FRONTEND_DIR"
        exit 1
    fi
    
    cd "$FRONTEND_DIR"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker"
        exit 1
    fi
    
    # Check if container already exists
    if docker ps -a --format "table {{.Names}}" | grep -q "budget-frontend"; then
        warning "Existing budget-frontend container found"
        docker rm -f budget-frontend
    fi
    
    check_port $FRONTEND_PORT "Frontend"
    
    # Build and start frontend container
    log "Building frontend Docker image..."
    docker build -f Dockerfile.dev -t budget-frontend-dev .
    
    log "Starting frontend container on port $FRONTEND_PORT..."
    docker run -d \
        --name budget-frontend \
        -p $FRONTEND_PORT:$FRONTEND_PORT \
        -v "$(pwd)":/app \
        -v /app/node_modules \
        -v /app/.next \
        -e NODE_ENV=development \
        -e NEXT_PUBLIC_API_BASE=http://127.0.0.1:$BACKEND_PORT \
        budget-frontend-dev
    
    # Health check
    if health_check "http://127.0.0.1:$FRONTEND_PORT" "Frontend"; then
        success "Frontend started successfully"
    else
        error "Frontend startup failed"
        exit 1
    fi
}

# Monitor services
monitor_services() {
    log "Setting up service monitoring..."
    
    # Create monitoring script
    cat > monitor.sh << 'EOF'
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
EOF
    
    chmod +x monitor.sh
    success "Monitoring script created: monitor.sh"
}

# Main execution
main() {
    log "🏗️  Budget App DevOps Startup v2.3"
    log "Backend: http://127.0.0.1:$BACKEND_PORT"
    log "Frontend: http://127.0.0.1:$FRONTEND_PORT"
    echo
    
    # Start services
    start_backend
    start_frontend
    monitor_services
    
    echo
    success "🎉 Development environment ready!"
    echo
    echo "📊 Service URLs:"
    echo "   Backend API: http://127.0.0.1:$BACKEND_PORT"
    echo "   API Docs: http://127.0.0.1:$BACKEND_PORT/docs"
    echo "   Frontend: http://127.0.0.1:$FRONTEND_PORT"
    echo
    echo "📋 Management Commands:"
    echo "   Stop all: ./stop-development.sh"
    echo "   Monitor: ./monitor.sh"
    echo "   Backend logs: tail -f $BACKEND_DIR/backend.log"
    echo "   Frontend logs: docker logs -f budget-frontend"
    echo
    echo "🔧 Development Features:"
    echo "   • Auto-reload enabled for both services"
    echo "   • Hot module replacement active"
    echo "   • Health monitoring configured"
    echo "   • CORS properly configured"
    echo
}

# Trap signals for graceful shutdown
trap 'echo; log "Received interrupt signal. Use ./stop-development.sh to stop services."; exit 0' INT TERM

main "$@"