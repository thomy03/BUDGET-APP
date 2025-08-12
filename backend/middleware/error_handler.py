"""
Error handling and logging middleware for Budget API
"""
import logging
import time
import traceback
from typing import Callable
import uuid

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from config.settings import settings

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Centralized error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Add request ID to logs context
        logger.info(f"[{request_id}] {request.method} {request.url.path} - Started")
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful requests
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Time: {process_time:.3f}s"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions (4xx, 5xx)
            process_time = time.time() - start_time
            
            logger.warning(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"HTTP Exception: {e.status_code} - {e.detail} - Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "type": "http_error",
                        "message": e.detail,
                        "status_code": e.status_code,
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            process_time = time.time() - start_time
            
            logger.warning(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Validation Error: {str(e)} - Time: {process_time:.3f}s"
            )
            
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "type": "validation_error",
                        "message": "Invalid input data",
                        "details": e.errors(),
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )
            
        except SQLAlchemyError as e:
            # Handle database errors
            process_time = time.time() - start_time
            
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Database Error: {str(e)} - Time: {process_time:.3f}s"
            )
            
            # Don't expose internal database errors in production
            error_message = (
                str(e) if settings.debug
                else "A database error occurred. Please try again later."
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "type": "database_error",
                        "message": error_message,
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )
            
        except Exception as e:
            # Handle unexpected errors
            process_time = time.time() - start_time
            
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Unexpected Error: {str(e)} - Time: {process_time:.3f}s"
            )
            
            # Log full traceback for debugging
            if settings.debug:
                logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
            
            # Don't expose internal errors in production
            error_message = (
                f"Internal error: {str(e)}" if settings.debug
                else "An unexpected error occurred. Please try again later."
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "type": "internal_error",
                        "message": error_message,
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Log request details
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.info(
            f"[{request_id}] Request: {request.method} {request.url.path} - "
            f"IP: {client_ip} - User-Agent: {user_agent}"
        )
        
        # Log query parameters if any
        if request.query_params:
            logger.debug(f"[{request_id}] Query params: {dict(request.query_params)}")
        
        try:
            response = await call_next(request)
            
            # Calculate metrics
            process_time = time.time() - start_time
            response_size = response.headers.get("content-length", "unknown")
            
            # Log response details
            logger.info(
                f"[{request_id}] Response: {response.status_code} - "
                f"Size: {response_size} bytes - Time: {process_time:.3f}s"
            )
            
            # Add request ID to response
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] Error processing request: {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise


def create_http_error_handler():
    """Create custom HTTP error handler"""
    
    async def http_error_handler(request: Request, exc: HTTPException):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                    "path": request.url.path
                }
            }
        )
    
    return http_error_handler


def create_validation_error_handler():
    """Create custom validation error handler"""
    
    async def validation_error_handler(request: Request, exc: ValidationError):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "request_id": request_id,
                    "path": request.url.path
                }
            }
        )
    
    return validation_error_handler


def create_general_error_handler():
    """Create general error handler for unexpected errors"""
    
    async def general_error_handler(request: Request, exc: Exception):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        
        # Log the error
        logger.error(
            f"[{request_id}] Unhandled exception: {str(exc)} - "
            f"Path: {request.url.path} - Method: {request.method}"
        )
        
        if settings.debug:
            logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_error",
                    "message": (
                        f"Internal server error: {str(exc)}" if settings.debug
                        else "An unexpected error occurred"
                    ),
                    "request_id": request_id,
                    "path": request.url.path
                }
            }
        )
    
    return general_error_handler


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        if settings.environment == "production":
            security_headers.update({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
            })
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


# Performance monitoring utilities
class PerformanceMonitor:
    """Simple performance monitoring"""
    
    def __init__(self):
        self.request_times = []
        self.error_count = 0
        self.request_count = 0
    
    def record_request(self, duration: float, status_code: int):
        self.request_count += 1
        self.request_times.append(duration)
        
        if status_code >= 400:
            self.error_count += 1
        
        # Keep only last 1000 requests
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
    
    def get_stats(self):
        if not self.request_times:
            return {
                "avg_response_time": 0,
                "p95_response_time": 0,
                "error_rate": 0,
                "total_requests": 0
            }
        
        import numpy as np
        
        return {
            "avg_response_time": np.mean(self.request_times),
            "p95_response_time": np.percentile(self.request_times, 95),
            "error_rate": (self.error_count / self.request_count) * 100,
            "total_requests": self.request_count
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()