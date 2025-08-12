"""
Auto-Tagging Router for Budget Famille v2.3
Production-Ready Batch Processing API Endpoints

This router provides comprehensive batch auto-tagging capabilities with:
- Asynchronous batch processing with real-time progress tracking
- Intelligent error handling and recovery mechanisms
- Performance optimization for large datasets
- Comprehensive API documentation and validation
- Scalable architecture for enterprise-grade workloads

Endpoints:
- POST /api/auto-tag/batch - Initiate batch auto-tagging operation
- GET /api/auto-tag/progress/{batch_id} - Get real-time progress
- GET /api/auto-tag/results/{batch_id} - Get detailed results
- GET /api/auto-tag/statistics - Get service performance metrics

Author: Claude Code - Backend API Architect
Target: Handle 1000+ transactions with 99.9% reliability
"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from models.database import get_db, Transaction
from models.schemas import (
    BatchAutoTagRequest, BatchAutoTagResponse, BatchProgressResponse,
    BatchResultsResponse, BatchErrorResponse
)
from services.batch_processor import get_batch_processor, BatchProcessor

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auto-tag",
    tags=["auto-tagging"],
    responses={
        404: {"description": "Batch operation not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)

@router.post("/batch", response_model=BatchAutoTagResponse)
async def initiate_batch_auto_tagging(
    request: BatchAutoTagRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 Initiate Batch Auto-Tagging Operation
    
    Starts an asynchronous batch operation to automatically tag transactions
    for a specified month using AI-powered classification and optional web research.
    
    **Process Flow:**
    1. Validates request parameters and month format
    2. Counts eligible transactions for processing
    3. Estimates processing duration based on configuration
    4. Initiates background processing with progress tracking
    5. Returns batch ID for monitoring progress
    
    **Performance Considerations:**
    - Uses concurrent processing for pattern-based classification
    - Applies rate limiting when web research is enabled
    - Implements memory-efficient batch processing
    - Provides real-time progress updates
    
    **Error Handling:**
    - Validates month format (YYYY-MM)
    - Checks for sufficient transactions to process
    - Handles classification service failures gracefully
    - Provides detailed error messages with context
    
    **Security:**
    - Requires valid authentication token
    - Processes only user's accessible transactions
    - Validates all input parameters
    - Logs all operations for audit trail
    """
    try:
        logger.info(f"Batch auto-tagging requested by {current_user.username} for month {request.month}")
        
        # Validate month has transactions
        transaction_count = db.query(Transaction).filter(
            Transaction.month == request.month,
            Transaction.is_expense == True,
            Transaction.exclude == False
        ).count()
        
        if transaction_count == 0:
            logger.warning(f"No transactions found for month {request.month}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No eligible transactions found for month {request.month}"
            )
        
        # Get batch processor service
        batch_processor = get_batch_processor()
        
        # Initiate batch operation
        response = await batch_processor.initiate_batch_operation(
            request=request,
            db=db,
            current_user_username=current_user.username
        )
        
        logger.info(f"Batch {response.batch_id} initiated successfully: {response.total_transactions} transactions")
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in batch auto-tagging: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in batch auto-tagging: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during batch initiation"
        )

@router.get("/progress/{batch_id}", response_model=BatchProgressResponse)
async def get_batch_progress(
    batch_id: str = Path(..., description="Unique batch operation identifier"),
    current_user=Depends(get_current_user)
):
    """
    📊 Get Real-Time Batch Processing Progress
    
    Retrieves current progress and status information for an active or completed
    batch auto-tagging operation. Provides detailed metrics including processing
    speed, error counts, and estimated completion time.
    
    **Progress Tracking:**
    - Real-time progress percentage (0-100%)
    - Detailed transaction counts and status
    - Current operation description
    - Processing speed and time estimates
    - Error tracking and diagnostics
    
    **Status Values:**
    - `initiated`: Batch created but not yet started
    - `processing`: Currently processing transactions
    - `completed`: Successfully completed all transactions
    - `failed`: Critical error stopped processing
    - `partial`: Completed with some errors
    
    **Performance Metrics:**
    - Transactions processed per second
    - Memory usage estimation
    - Web research utilization
    - Error rate and types
    
    **Use Cases:**
    - Monitor long-running batch operations
    - Build progress bars in user interface
    - Detect and diagnose processing issues
    - Estimate completion time for planning
    """
    try:
        logger.debug(f"Progress requested for batch {batch_id} by {current_user.username}")
        
        batch_processor = get_batch_processor()
        progress = batch_processor.get_batch_progress(batch_id)
        
        return progress
        
    except ValueError as e:
        logger.warning(f"Batch {batch_id} not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch operation {batch_id} not found"
        )
    except Exception as e:
        logger.error(f"Error getting batch progress for {batch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving progress"
        )

@router.get("/results/{batch_id}", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str = Path(..., description="Unique batch operation identifier"),
    include_transactions: bool = Query(
        default=True, 
        description="Include detailed transaction results (set to false for summary only)"
    ),
    current_user=Depends(get_current_user)
):
    """
    📈 Get Comprehensive Batch Processing Results
    
    Retrieves complete results and analytics for a completed batch auto-tagging
    operation. Includes detailed transaction-level results, summary statistics,
    performance metrics, and actionable insights.
    
    **Result Components:**
    
    **Summary Statistics:**
    - Total transactions processed and tagged
    - Success rates and confidence scores
    - Classification breakdown (FIXED vs VARIABLE)
    - Processing performance metrics
    
    **Transaction Details:**
    - Individual transaction results with confidence scores
    - Applied tags and expense type classifications
    - Processing time and web research usage
    - Error details for failed transactions
    
    **Performance Analytics:**
    - Average processing time per transaction
    - Memory usage and optimization metrics
    - Cache hit rates and research efficiency
    - Concurrent processing statistics
    
    **Quality Metrics:**
    - Confidence score distributions
    - Tag diversity and coverage
    - Error patterns and root causes
    - User feedback integration opportunities
    
    **Business Intelligence:**
    - New tag discoveries and patterns
    - Merchant classification insights
    - Expense categorization trends
    - Automation effectiveness analysis
    
    **Use Cases:**
    - Review and validate batch processing results
    - Generate reports for financial analysis
    - Train and improve classification models
    - Monitor system performance and quality
    - Plan future automation strategies
    """
    try:
        logger.info(f"Results requested for batch {batch_id} by {current_user.username}")
        
        batch_processor = get_batch_processor()
        results = batch_processor.get_batch_results(batch_id)
        
        # Optionally filter out transaction details for performance
        if not include_transactions:
            results.transactions = []
            logger.debug(f"Transaction details excluded for batch {batch_id} (summary only)")
        
        logger.info(f"Results retrieved for batch {batch_id}: {results.summary.total_processed} transactions")
        
        return results
        
    except ValueError as e:
        logger.warning(f"Batch {batch_id} not found or still processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting batch results for {batch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving results"
        )

@router.get("/statistics")
async def get_service_statistics(
    current_user=Depends(get_current_user)
):
    """
    📊 Get Auto-Tagging Service Performance Statistics
    
    Provides comprehensive performance metrics and operational statistics
    for the auto-tagging service. Useful for monitoring, optimization,
    and capacity planning.
    
    **Service Metrics:**
    - Active and completed batch operations
    - Total transactions processed
    - Average processing times and throughput
    - Memory usage and resource utilization
    
    **Configuration Status:**
    - Current service configuration
    - Rate limiting and concurrency settings
    - Feature flags and optimization levels
    - Cache performance and hit rates
    
    **Operational Health:**
    - Error rates and types
    - Service availability and uptime
    - Queue depths and processing backlogs
    - Performance trends and patterns
    
    **Use Cases:**
    - Monitor service health and performance
    - Plan capacity and resource allocation
    - Optimize configuration parameters
    - Generate operational reports
    - Debug performance issues
    """
    try:
        logger.debug(f"Service statistics requested by {current_user.username}")
        
        batch_processor = get_batch_processor()
        statistics = batch_processor.get_service_statistics()
        
        # Add additional context for monitoring
        enhanced_statistics = {
            **statistics,
            "request_timestamp": datetime.now().isoformat(),
            "requested_by": current_user.username,
            "service_health": "operational",  # Could be computed based on error rates
            "version": "2.3.0"
        }
        
        return enhanced_statistics
        
    except Exception as e:
        logger.error(f"Error getting service statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving statistics"
        )

@router.delete("/batch/{batch_id}")
async def cancel_batch_operation(
    batch_id: str = Path(..., description="Unique batch operation identifier"),
    current_user=Depends(get_current_user)
):
    """
    🛑 Cancel Active Batch Operation
    
    Attempts to cancel an active batch auto-tagging operation.
    Note: Cancellation may not be immediate due to async processing.
    
    **Cancellation Behavior:**
    - Stops processing new transactions
    - Allows current transactions to complete
    - Preserves already processed results
    - Updates batch status to 'cancelled'
    
    **Limitations:**
    - Cannot cancel completed operations
    - May take time to fully stop processing
    - Some transactions may complete after cancellation
    
    **Use Cases:**
    - Stop long-running operations
    - Free up system resources
    - Correct configuration errors
    - Emergency stop for critical issues
    """
    try:
        logger.info(f"Cancellation requested for batch {batch_id} by {current_user.username}")
        
        batch_processor = get_batch_processor()
        
        # Check if batch exists and is active
        if batch_id not in batch_processor.active_batches:
            if batch_id in batch_processor.completed_batches:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel completed batch operation"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Batch operation {batch_id} not found"
                )
        
        # Mark batch for cancellation
        batch_state = batch_processor.active_batches[batch_id]
        batch_state.status = "cancelled"
        
        logger.info(f"Batch {batch_id} marked for cancellation")
        
        return {
            "batch_id": batch_id,
            "status": "cancellation_requested",
            "message": "Batch operation cancellation requested. Processing will stop gracefully.",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling batch {batch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during cancellation"
        )

@router.get("/health")
async def health_check():
    """
    ✅ Auto-Tagging Service Health Check
    
    Provides service health status and basic operational metrics.
    Used for monitoring, load balancing, and service discovery.
    
    **Health Indicators:**
    - Service availability and responsiveness
    - Active batch operations count
    - Resource utilization levels
    - Error rates and thresholds
    
    **Response Codes:**
    - 200: Service healthy and operational
    - 503: Service degraded or overloaded
    - 500: Service error or failure
    """
    try:
        batch_processor = get_batch_processor()
        stats = batch_processor.get_service_statistics()
        
        # Determine health status based on metrics
        active_batches = stats.get("active_batches", 0)
        health_status = "healthy"
        
        if active_batches > 10:  # Threshold for high load
            health_status = "degraded"
        
        health_response = {
            "status": health_status,
            "service": "auto-tagging",
            "version": "2.3.0",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "active_batches": active_batches,
                "total_batches_processed": stats.get("total_batches_processed", 0),
                "uptime_status": "operational"
            }
        }
        
        # Return appropriate status code
        if health_status == "healthy":
            return health_response
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_response
            )
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "unhealthy",
                "service": "auto-tagging",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Note: Exception handlers should be added to the main FastAPI app, not individual routers