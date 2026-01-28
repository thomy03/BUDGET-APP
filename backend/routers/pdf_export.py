"""
PDF Export Router for Budget Famille
Endpoints for generating and downloading PDF reports
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from auth import get_current_user
from models.database import get_db, Transaction, Config, FixedLine, CustomProvision
from services.pdf_export import generate_budget_pdf
from services.calculations import get_split, split_amount, calculate_provision_amount

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/export/pdf",
    tags=["pdf-export"],
    responses={404: {"description": "Not found"}}
)


def get_summary_data(month: str, current_user, db: Session) -> dict:
    """Get summary data for PDF generation"""
    from models.database import ensure_default_config

    cfg = ensure_default_config(db)
    r1, r2 = get_split(cfg)

    # Fixed lines
    lines = db.query(FixedLine).filter(FixedLine.active == True).all()
    lines_total = 0.0
    fixed_p1 = 0.0
    fixed_p2 = 0.0

    for ln in lines:
        if ln.freq == "mensuelle":
            mval = ln.amount
        elif ln.freq == "trimestrielle":
            mval = (ln.amount or 0.0) / 3.0
        else:
            mval = (ln.amount or 0.0) / 12.0
        p1, p2 = split_amount(mval, ln.split_mode, r1, r2, ln.split1, ln.split2)
        lines_total += mval
        fixed_p1 += p1
        fixed_p2 += p2

    # Provisions
    custom_provisions = db.query(CustomProvision).filter(
        CustomProvision.created_by == current_user.username,
        CustomProvision.is_active == True
    ).all()

    provisions_total = 0.0
    provisions_p1 = 0.0
    provisions_p2 = 0.0

    for provision in custom_provisions:
        monthly_amount, member1_amount, member2_amount = calculate_provision_amount(provision, cfg)
        provisions_total += monthly_amount
        provisions_p1 += member1_amount
        provisions_p2 += member2_amount

    # Transactions
    txs = db.query(Transaction).filter(Transaction.month == month).all()
    var_total = -sum(t.amount for t in txs if (t.is_expense and not t.exclude and t.amount is not None))
    var_p1 = var_total * r1
    var_p2 = var_total * r2

    # Totals
    total_p1 = var_p1 + fixed_p1 + provisions_p1
    total_p2 = var_p2 + fixed_p2 + provisions_p2

    return {
        "month": month,
        "member1": cfg.member1,
        "member2": cfg.member2,
        "var_total": round(var_total, 2),
        "var_p1": round(var_p1, 2),
        "var_p2": round(var_p2, 2),
        "fixed_lines_total": round(lines_total, 2),
        "fixed_p1": round(fixed_p1, 2),
        "fixed_p2": round(fixed_p2, 2),
        "provisions_total": round(provisions_total, 2),
        "provisions_p1": round(provisions_p1, 2),
        "provisions_p2": round(provisions_p2, 2),
        "total_p1": round(total_p1, 2),
        "total_p2": round(total_p2, 2),
        "grand_total": round(total_p1 + total_p2, 2),
        "r1": r1,
        "r2": r2,
    }


def get_tags_summary(month: str, db: Session) -> dict:
    """Get tags breakdown for the month"""
    from collections import defaultdict

    txs = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.is_expense == True,
        Transaction.exclude == False
    ).all()

    tags_data = defaultdict(lambda: {"count": 0, "total": 0.0})

    for tx in txs:
        if tx.tags:
            tag_list = [t.strip().lower() for t in tx.tags.split(',') if t.strip()]
            if tag_list:
                amount_per_tag = abs(tx.amount) / len(tag_list)
                for tag in tag_list:
                    tags_data[tag]["count"] += 1
                    tags_data[tag]["total"] += amount_per_tag
            else:
                tags_data["non-tague"]["count"] += 1
                tags_data["non-tague"]["total"] += abs(tx.amount)
        else:
            tags_data["non-tague"]["count"] += 1
            tags_data["non-tague"]["total"] += abs(tx.amount)

    return {"tags": dict(tags_data)}


@router.get("/monthly/{month}")
async def export_monthly_pdf(
    month: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and download a monthly budget report as PDF

    Args:
        month: Month in YYYY-MM format (e.g., 2025-12)

    Returns:
        PDF file as downloadable attachment
    """
    try:
        logger.info(f"Generating PDF report for {month} by user {current_user.username}")

        # Get data
        summary = get_summary_data(month, current_user, db)

        # Get transactions (sorted by amount)
        transactions = db.query(Transaction).filter(
            Transaction.month == month,
            Transaction.is_expense == True,
            Transaction.exclude == False
        ).order_by(Transaction.amount.asc()).all()

        transactions_list = [
            {
                "id": tx.id,
                "date_op": tx.date_op,
                "label": tx.label,
                "amount": tx.amount,
                "tags": tx.tags,
            }
            for tx in transactions
        ]

        # Get config
        config = db.query(Config).first()
        config_dict = {
            "member1": config.member1 if config else "Membre 1",
            "member2": config.member2 if config else "Membre 2",
        }

        # Get tags summary
        tags_summary = get_tags_summary(month, db)

        # Generate PDF
        pdf_bytes = generate_budget_pdf(
            month=month,
            summary=summary,
            transactions=transactions_list,
            config=config_dict,
            tags_summary=tags_summary
        )

        # Format filename
        filename = f"budget_famille_{month}.pdf"

        logger.info(f"PDF generated successfully: {filename} ({len(pdf_bytes)} bytes)")

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la generation du PDF: {str(e)}"
        )


@router.get("/preview/{month}")
async def preview_pdf_data(
    month: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview the data that would be included in the PDF report

    Useful for debugging or showing a preview before generating
    """
    summary = get_summary_data(month, current_user, db)
    tags_summary = get_tags_summary(month, db)

    transactions = db.query(Transaction).filter(
        Transaction.month == month,
        Transaction.is_expense == True,
        Transaction.exclude == False
    ).order_by(Transaction.amount.asc()).limit(15).all()

    return {
        "month": month,
        "summary": summary,
        "tags_summary": tags_summary,
        "top_transactions": [
            {
                "date": str(tx.date_op) if tx.date_op else None,
                "label": tx.label,
                "amount": tx.amount,
            }
            for tx in transactions
        ],
        "pdf_ready": True
    }
