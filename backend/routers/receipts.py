"""
Receipts Router for Budget Famille v4.1
OCR-powered receipt scanning and transaction creation
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies.auth import get_current_user
from dependencies.database import get_db
from models.database import Transaction
from services.ocr_service import parse_receipt, is_ocr_available, ReceiptData

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/receipts",
    tags=["receipts"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "OCR service error"}
    }
)


# Pydantic Schemas

class ReceiptScanResponse(BaseModel):
    """Response from receipt scan"""
    success: bool
    merchant: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    suggested_tag: Optional[str] = None
    confidence: float = 0.0
    all_amounts: List[float] = []
    raw_text: str = ""
    message: str = ""


class ReceiptCreateRequest(BaseModel):
    """Request to create transaction from receipt"""
    merchant: str
    amount: float
    date: str  # YYYY-MM-DD
    tag: Optional[str] = None
    notes: Optional[str] = None


class ReceiptCreateResponse(BaseModel):
    """Response after creating transaction from receipt"""
    success: bool
    transaction_id: Optional[int] = None
    message: str = ""


class OCRStatusResponse(BaseModel):
    """OCR service status"""
    available: bool
    message: str


# Endpoints

@router.get("/status", response_model=OCRStatusResponse)
def get_ocr_status():
    """Check if OCR service is available"""
    available = is_ocr_available()
    return OCRStatusResponse(
        available=available,
        message="OCR service ready" if available else "OCR service not available - install easyocr"
    )


@router.post("/scan", response_model=ReceiptScanResponse)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    Scan a receipt image and extract merchant, amount, and date.

    Accepts JPEG, PNG, WEBP images.
    Works on CPU (no GPU required).
    Supports French receipts.
    """
    logger.info(f"Receipt scan requested by {current_user.username}")

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
    content_type = file.content_type or ''

    if content_type not in allowed_types and not content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Accepted: JPEG, PNG, WEBP"
        )

    # Check OCR availability
    if not is_ocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Install: pip install easyocr pillow"
        )

    try:
        # Read file content
        image_bytes = await file.read()

        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=400,
                detail="Image too large. Maximum size: 10MB"
            )

        logger.info(f"Processing image: {file.filename}, size: {len(image_bytes)} bytes")

        # Parse receipt
        receipt_data: ReceiptData = parse_receipt(image_bytes)

        # Build response
        if receipt_data.amount or receipt_data.merchant:
            return ReceiptScanResponse(
                success=True,
                merchant=receipt_data.merchant,
                amount=receipt_data.amount,
                date=receipt_data.date,
                suggested_tag=receipt_data.suggested_tag,
                confidence=round(receipt_data.confidence, 2),
                all_amounts=receipt_data.all_amounts[:10],  # Limit to 10
                raw_text=receipt_data.raw_text[:2000],  # Limit text length
                message="Receipt scanned successfully"
            )
        else:
            return ReceiptScanResponse(
                success=False,
                raw_text=receipt_data.raw_text[:2000],
                confidence=round(receipt_data.confidence, 2),
                message="Could not extract merchant or amount from receipt"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Receipt scan error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.post("/create", response_model=ReceiptCreateResponse)
async def create_transaction_from_receipt(
    request: ReceiptCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a transaction from scanned receipt data.

    After scanning with /scan, use this endpoint to create the transaction.
    """
    logger.info(f"Creating transaction from receipt by {current_user.username}")

    try:
        # Parse and validate date
        try:
            transaction_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {request.date}. Expected: YYYY-MM-DD"
            )

        # Determine month
        month = transaction_date.strftime("%Y-%m")

        # Create label
        label = f"[SCAN] {request.merchant}"
        if request.notes:
            label += f" - {request.notes}"

        # Create transaction (expense = negative amount)
        amount = -abs(request.amount)

        transaction = Transaction(
            label=label,
            amount=amount,
            date_op=transaction_date,
            month=month,
            tags=request.tag or "",
            category="",
            exclude=False
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        logger.info(f"Transaction created: id={transaction.id}, amount={amount}, merchant={request.merchant}")

        return ReceiptCreateResponse(
            success=True,
            transaction_id=transaction.id,
            message=f"Transaction created: {request.merchant} - {abs(amount):.2f} EUR"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transaction creation error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transaction: {str(e)}"
        )


@router.post("/scan-and-create", response_model=ReceiptCreateResponse)
async def scan_and_create_transaction(
    file: UploadFile = File(...),
    tag: Optional[str] = Form(None),
    auto_create: bool = Form(False),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan a receipt and optionally create a transaction in one step.

    If auto_create is True and confidence is high enough, creates the transaction.
    Otherwise, returns the scan result for user confirmation.
    """
    # First, scan the receipt
    scan_response = await scan_receipt(file, current_user)

    if not scan_response.success:
        return ReceiptCreateResponse(
            success=False,
            message=scan_response.message
        )

    # Check if we should auto-create
    if not auto_create:
        # Return scan result without creating
        return ReceiptCreateResponse(
            success=True,
            message=f"Scan complete. Merchant: {scan_response.merchant}, Amount: {scan_response.amount}"
        )

    # Validate we have enough data
    if not scan_response.amount:
        return ReceiptCreateResponse(
            success=False,
            message="Cannot auto-create: no amount detected"
        )

    if not scan_response.merchant:
        return ReceiptCreateResponse(
            success=False,
            message="Cannot auto-create: no merchant detected"
        )

    # Use scanned date or today
    transaction_date = scan_response.date or datetime.now().strftime("%Y-%m-%d")

    # Create the transaction
    create_request = ReceiptCreateRequest(
        merchant=scan_response.merchant,
        amount=scan_response.amount,
        date=transaction_date,
        tag=tag or scan_response.suggested_tag
    )

    return await create_transaction_from_receipt(create_request, current_user, db)
