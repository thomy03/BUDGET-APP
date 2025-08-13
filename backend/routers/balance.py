"""
Account Balance Management Router
Handles account balance storage and retrieval for monthly calculations
"""
import logging
from typing import Optional, List
from datetime import datetime as dt
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from models.database import get_db, GlobalMonth
from models.schemas import (
    AccountBalanceUpdate, AccountBalanceResponse, GlobalMonthCreate, 
    GlobalMonthUpdate, BalanceTransferCalculation
)
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/balance", tags=["account-balance"])


def get_or_create_global_month(db: Session, month: str, created_by: str = None) -> GlobalMonth:
    """Get existing GlobalMonth or create a new one"""
    global_month = db.query(GlobalMonth).filter(GlobalMonth.month == month).first()
    
    if not global_month:
        global_month = GlobalMonth(
            month=month,
            account_balance=0.0,
            created_by=created_by
        )
        db.add(global_month)
        db.commit()
        db.refresh(global_month)
        logger.info(f"Created new GlobalMonth for {month}")
    
    return global_month


@router.put("/{month}", response_model=AccountBalanceResponse)
def update_account_balance(
    month: str,
    balance_data: AccountBalanceUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update account balance for a specific month
    
    Creates a new GlobalMonth entry if it doesn't exist, or updates the existing one.
    """
    try:
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Get or create global month
        global_month = get_or_create_global_month(db, month, current_user.username)
        
        # Update balance and metadata
        global_month.account_balance = balance_data.account_balance
        global_month.updated_at = dt.now()
        global_month.created_by = current_user.username  # Update the last modifier
        
        if balance_data.notes is not None:
            global_month.notes = balance_data.notes
        
        db.commit()
        db.refresh(global_month)
        
        logger.info(f"Updated account balance for {month}: {balance_data.account_balance} by {current_user.username}")
        return global_month
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account balance for {month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account balance: {str(e)}"
        )


@router.get("/{month}", response_model=AccountBalanceResponse)
def get_account_balance(
    month: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get account balance for a specific month
    
    Returns the balance and associated month data. Creates a new entry with 0.0 balance if none exists.
    """
    try:
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Get or create global month
        global_month = get_or_create_global_month(db, month, current_user.username)
        
        return global_month
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account balance for {month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account balance: {str(e)}"
        )


@router.post("/", response_model=AccountBalanceResponse)
def create_global_month(
    month_data: GlobalMonthCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new global month entry with initial settings
    
    Use this endpoint to set up a new month with specific targets and initial balance.
    """
    try:
        # Check if month already exists
        existing = db.query(GlobalMonth).filter(GlobalMonth.month == month_data.month).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Global month entry for {month_data.month} already exists"
            )
        
        # Create new global month
        global_month = GlobalMonth(
            month=month_data.month,
            account_balance=month_data.account_balance,
            budget_target=month_data.budget_target,
            savings_goal=month_data.savings_goal,
            notes=month_data.notes,
            created_by=current_user.username
        )
        
        db.add(global_month)
        db.commit()
        db.refresh(global_month)
        
        logger.info(f"Created global month {month_data.month} with balance {month_data.account_balance} by {current_user.username}")
        return global_month
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating global month {month_data.month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create global month: {str(e)}"
        )


@router.patch("/{month}", response_model=AccountBalanceResponse)
def update_global_month(
    month: str,
    update_data: GlobalMonthUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update global month settings (balance, targets, notes)
    
    Allows partial updates of month settings without affecting other fields.
    """
    try:
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Get or create global month
        global_month = get_or_create_global_month(db, month, current_user.username)
        
        # Update only provided fields
        if update_data.account_balance is not None:
            global_month.account_balance = update_data.account_balance
            
        if update_data.budget_target is not None:
            global_month.budget_target = update_data.budget_target
            
        if update_data.savings_goal is not None:
            global_month.savings_goal = update_data.savings_goal
            
        if update_data.notes is not None:
            global_month.notes = update_data.notes
            
        if update_data.is_closed is not None:
            global_month.is_closed = update_data.is_closed
        
        global_month.updated_at = dt.now()
        global_month.created_by = current_user.username
        
        db.commit()
        db.refresh(global_month)
        
        logger.info(f"Updated global month settings for {month} by {current_user.username}")
        return global_month
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating global month {month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update global month: {str(e)}"
        )


@router.get("/", response_model=List[AccountBalanceResponse])
def list_global_months(
    limit: int = 12,
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all global months with their balances and settings
    
    Returns a paginated list of months ordered by month descending (most recent first).
    """
    try:
        global_months = db.query(GlobalMonth).order_by(
            GlobalMonth.month.desc()
        ).offset(offset).limit(limit).all()
        
        return global_months
        
    except Exception as e:
        logger.error(f"Error listing global months: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list global months: {str(e)}"
        )


@router.get("/{month}/transfer-calculation", response_model=BalanceTransferCalculation)
def calculate_transfer_with_balance(
    month: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate transfer amounts needed considering current account balance
    
    This endpoint combines the enhanced summary calculations with the account balance
    to determine how much each member should transfer to cover monthly expenses.
    """
    try:
        # Import required modules for calculations
        from models.database import Config, Transaction, FixedLine, CustomProvision, ensure_default_config
        from services.calculations import get_split, split_amount, calculate_provision_amount
        from collections import defaultdict
        
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Get account balance for the month
        global_month = get_or_create_global_month(db, month, current_user.username)
        current_balance = global_month.account_balance or 0.0
        
        # Get configuration for split calculations
        cfg = ensure_default_config(db)
        r1, r2 = get_split(cfg)
        
        # === CALCULATE TOTAL EXPENSES ===
        
        # 1. Fixed expenses (manual + AI classified)
        fixed_total = 0.0
        fixed_p1_total = 0.0
        fixed_p2_total = 0.0
        
        # Manual fixed lines
        lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        for ln in lines:
            if ln.freq == "mensuelle":
                mval = ln.amount
            elif ln.freq == "trimestrielle":
                mval = (ln.amount or 0.0) / 3.0
            else:
                mval = (ln.amount or 0.0) / 12.0
            
            p1, p2 = split_amount(mval, ln.split_mode, r1, r2, ln.split1, ln.split2)
            fixed_total += mval
            fixed_p1_total += p1
            fixed_p2_total += p2
        
        # AI classified fixed expenses  
        fixed_txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.expense_type == 'FIXED'
        ).all()
        
        fixed_tx_amount = sum(abs(tx.amount or 0) for tx in fixed_txs)
        fixed_total += fixed_tx_amount
        fixed_p1_total += fixed_tx_amount * r1
        fixed_p2_total += fixed_tx_amount * r2
        
        # 2. Variable expenses
        variable_txs = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.expense_type == 'VARIABLE'
        ).all()
        
        variables_total = sum(abs(tx.amount or 0) for tx in variable_txs)
        variables_p1_total = variables_total * r1
        variables_p2_total = variables_total * r2
        
        # 3. Provisions (savings)
        custom_provisions = db.query(CustomProvision).filter(
            CustomProvision.created_by == current_user.username,
            CustomProvision.is_active == True
        ).all()
        
        provisions_total = 0.0
        provisions_p1_total = 0.0
        provisions_p2_total = 0.0
        
        for provision in custom_provisions:
            monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, cfg)
            provisions_total += monthly_amount
            provisions_p1_total += member1_amount
            provisions_p2_total += member2_amount
        
        # === CALCULATE TOTALS ===
        total_expenses = fixed_total + variables_total + provisions_total
        total_member1 = fixed_p1_total + variables_p1_total + provisions_p1_total
        total_member2 = fixed_p2_total + variables_p2_total + provisions_p2_total
        
        # === TRANSFER CALCULATION ===
        # Each member should transfer their share to cover expenses
        suggested_transfer_member1 = max(0, total_member1)
        suggested_transfer_member2 = max(0, total_member2)
        
        # Calculate projected balance after transfers
        final_balance_after_transfers = current_balance + suggested_transfer_member1 + suggested_transfer_member2 - total_expenses
        
        # Determine balance status
        if final_balance_after_transfers >= total_expenses * 0.1:  # 10% buffer
            balance_status = "sufficient"
        elif final_balance_after_transfers >= 0:
            balance_status = "tight"
        else:
            balance_status = "deficit"
            
        # Check for surplus (more than 150% of expenses)
        if current_balance > total_expenses * 1.5:
            balance_status = "surplus"
        
        result = BalanceTransferCalculation(
            month=month,
            total_expenses=round(total_expenses, 2),
            total_member1=round(total_member1, 2),
            total_member2=round(total_member2, 2),
            current_balance=round(current_balance, 2),
            suggested_transfer_member1=round(suggested_transfer_member1, 2),
            suggested_transfer_member2=round(suggested_transfer_member2, 2),
            final_balance_after_transfers=round(final_balance_after_transfers, 2),
            balance_status=balance_status
        )
        
        logger.info(f"Transfer calculation for {month}: {balance_status} - balance: {current_balance}, expenses: {total_expenses}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating transfers with balance for {month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate transfers: {str(e)}"
        )


@router.delete("/{month}")
def delete_global_month(
    month: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a global month entry
    
    Use with caution - this will remove all balance and settings data for the month.
    """
    try:
        # Validate month format
        if not month or len(month) != 7 or month[4] != '-':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be in YYYY-MM format"
            )
        
        # Find the global month
        global_month = db.query(GlobalMonth).filter(GlobalMonth.month == month).first()
        if not global_month:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No global month entry found for {month}"
            )
        
        # Delete the entry
        db.delete(global_month)
        db.commit()
        
        logger.info(f"Deleted global month {month} by {current_user.username}")
        return {"message": f"Global month {month} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting global month {month}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete global month: {str(e)}"
        )