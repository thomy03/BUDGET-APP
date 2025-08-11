"""
Configuration Gunicorn pour Budget Famille Backend
Production-ready avec monitoring et sécurité
"""

import multiprocessing
import os

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = int(os.getenv('MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('MAX_REQUESTS_JITTER', '50'))

# Timeout configuration
timeout = int(os.getenv('TIMEOUT', '30'))
keepalive = int(os.getenv('KEEP_ALIVE', '5'))
graceful_timeout = 30

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# Process naming
proc_name = 'budget-famille-api'

# User and group
user = os.getenv('APP_USER', 'appuser')
group = os.getenv('APP_GROUP', 'appuser')

# Security limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Capture output
capture_output = True

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Preload application
preload_app = True

# Threading
threads = int(os.getenv('THREADS', '2'))

# Memory management
max_worker_memory = int(os.getenv('MAX_WORKER_MEMORY', '200000'))  # KB

# ============================================================================
# MONITORING & HEALTH
# ============================================================================

def when_ready(server):
    """Called when the server is started."""
    server.log.info("Budget Famille API server is ready. Listening at: %s", server.address)

def worker_int(worker):
    """Called when worker received INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called before worker processes are forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called after worker processes are forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    """Called before the server is execed."""
    server.log.info("Forked child, re-executing.")

def worker_abort(worker):
    """Called when worker received SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")