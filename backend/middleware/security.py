"""
Security middleware for Budget Famille API
Implements rate limiting, request validation, and security headers
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with sliding window algorithm
    Implements progressive backoff for authentication endpoints
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        auth_requests_per_minute: int = 10,
        burst_size: int = 10,
        window_minutes: int = 5
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self.burst_size = burst_size
        self.window_minutes = window_minutes
        
        # Storage for rate limiting (in production, use Redis)
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.auth_failures: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Authentication endpoints that need stricter limits
        self.auth_endpoints = {
            "/token", "/api/v1/auth/token", "/api/v1/auth/login"
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_blocked(self, client_ip: str) -> bool:
        """Check if IP is temporarily blocked"""
        if client_ip in self.blocked_ips:
            block_time = self.blocked_ips[client_ip]
            if datetime.now() - block_time < timedelta(minutes=15):
                return True
            else:
                # Remove expired block
                del self.blocked_ips[client_ip]
        return False
    
    def _cleanup_old_requests(self, client_ip: str):
        """Remove requests older than the window"""
        cutoff = time.time() - (self.window_minutes * 60)
        
        # Clean general requests
        requests = self.request_counts[client_ip]
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        # Clean auth failures
        failures = self.auth_failures[client_ip]
        while failures and failures[0] < cutoff:
            failures.popleft()
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if endpoint is authentication-related"""
        return any(auth_path in path for auth_path in self.auth_endpoints)
    
    def _check_rate_limit(self, client_ip: str, path: str) -> Optional[Response]:
        """Check if request should be rate limited"""
        current_time = time.time()
        
        # Clean old requests
        self._cleanup_old_requests(client_ip)
        
        # Check if IP is blocked
        if self._is_blocked(client_ip):
            logger.warning(f"Blocked IP attempted request: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "IP temporarily blocked due to excessive requests",
                    "retry_after": 900  # 15 minutes
                }
            )
        
        # Check auth endpoint limits
        if self._is_auth_endpoint(path):
            auth_failures = len(self.auth_failures[client_ip])
            if auth_failures >= 5:  # 5 failed auth attempts
                self.blocked_ips[client_ip] = datetime.now()
                logger.warning(f"IP blocked due to auth failures: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many authentication failures",
                        "retry_after": 900
                    }
                )
            
            # Check auth rate limit
            requests = len(self.request_counts[client_ip])
            if requests >= self.auth_requests_per_minute:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Authentication rate limit exceeded",
                        "retry_after": 60
                    }
                )
        else:
            # Check general rate limit
            requests = len(self.request_counts[client_ip])
            if requests >= self.requests_per_minute:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": 60
                    }
                )
        
        # Record this request
        self.request_counts[client_ip].append(current_time)
        return None
    
    def record_auth_failure(self, client_ip: str):
        """Record authentication failure for progressive blocking"""
        self.auth_failures[client_ip].append(time.time())
        logger.info(f"Auth failure recorded for IP: {client_ip}")
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        # Check rate limits
        rate_limit_response = self._check_rate_limit(client_ip, path)
        if rate_limit_response:
            return rate_limit_response
        
        # Process request
        response = await call_next(request)
        
        # Record auth failures for rate limiting
        if self._is_auth_endpoint(path) and response.status_code == 401:
            self.record_auth_failure(client_ip)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware
    Adds security headers to all responses
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Remove server information
        response.headers["Server"] = "Budget-Famille-API"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware
    Validates request size, content type, and other security aspects
    """
    
    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_content_types: list = None
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/csv",
            "application/octet-stream"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(f"Request too large: {size} bytes from {request.client.host}")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Request entity too large"}
                    )
            except ValueError:
                pass
        
        # Validate content type for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0].strip()
            if content_type and not any(allowed in content_type for allowed in self.allowed_content_types):
                logger.warning(f"Invalid content type: {content_type} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": "Unsupported media type"}
                )
        
        return await call_next(request)


# Global instance for auth failure recording
rate_limiter = None

def get_rate_limiter() -> Optional[RateLimitMiddleware]:
    """Get the global rate limiter instance"""
    return rate_limiter

def set_rate_limiter(limiter: RateLimitMiddleware):
    """Set the global rate limiter instance"""
    global rate_limiter
    rate_limiter = limiter