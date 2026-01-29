"""
Tags router for Budget Famille v2.3
Complete tag management with CRUD operations, statistics, and smart features
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from auth import get_current_user
from models.database import get_db, Transaction, LabelTagMapping, TagFixedLineMapping, FixedLine
from models.schemas import (
    TagOut, TagUpdate, TagStats, TagPatterns, TagDelete, TagsListResponse,
    TxOut, ExpenseTypeConversion
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    responses={404: {"description": "Not found"}}
)


def extract_tags_from_transactions(db: Session) -> Dict[str, Dict[str, Any]]:
    """Extract all unique tags from transactions and compute statistics"""
    tags_data = defaultdict(lambda: {
        'transactions': [],
        'total_amount': 0.0,
        'transaction_count': 0,
        'last_used': None,
        'expense_types': Counter(),
        'categories': Counter(),
        'merchants': Counter()
    })
    
    # Get all transactions with tags
    transactions = db.query(Transaction).filter(
        Transaction.tags != "",
        Transaction.tags.is_not(None),
        Transaction.exclude == False
    ).all()
    
    for tx in transactions:
        if not tx.tags:
            continue
            
        # Split tags by comma and clean them
        tx_tags = [tag.strip().lower() for tag in tx.tags.split(',') if tag.strip()]
        
        for tag in tx_tags:
            tag_data = tags_data[tag]
            tag_data['transactions'].append(tx)
            tag_data['total_amount'] += abs(tx.amount) if tx.amount else 0
            tag_data['transaction_count'] += 1
            
            # Update last used date
            if tx.date_op and (not tag_data['last_used'] or tx.date_op > tag_data['last_used']):
                tag_data['last_used'] = tx.date_op
            
            # Update counters
            tag_data['expense_types'][tx.expense_type or 'VARIABLE'] += 1
            tag_data['categories'][tx.category or 'autres'] += 1
            
            # Extract merchant from label
            if tx.label:
                merchant = tx.label.split()[0] if tx.label.split() else 'Inconnu'
                tag_data['merchants'][merchant] += 1
    
    return tags_data


def get_tag_expense_type(tag_stats: Dict[str, Any]) -> str:
    """Determine the primary expense type for a tag based on usage"""
    expense_types = tag_stats['expense_types']
    if not expense_types:
        return 'VARIABLE'
    
    # Return the most common expense type and normalize case
    most_common_type = expense_types.most_common(1)[0][0]
    # Normalize to uppercase to handle case inconsistencies
    return most_common_type.upper() if most_common_type else 'VARIABLE'


def get_tag_patterns(db: Session, tag_name: str) -> List[str]:
    """Get patterns associated with a tag from label mappings"""
    patterns = []
    
    # Get from label_tag_mappings
    mappings = db.query(LabelTagMapping).filter(
        LabelTagMapping.suggested_tags.contains(tag_name),
        LabelTagMapping.is_active == True
    ).all()
    
    for mapping in mappings:
        if mapping.label_pattern:
            patterns.append(mapping.label_pattern)
    
    return list(set(patterns))


@router.get("", response_model=TagsListResponse)
async def list_tags(
    expense_type: Optional[str] = Query(None, description="Filtrer par type de dépense"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    min_usage: Optional[int] = Query(None, description="Nombre minimum d'utilisations"),
    sort_by: str = Query("usage", description="Tri: usage, amount, name, last_used"),
    limit: Optional[int] = Query(None, description="Limite le nombre de résultats"),
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Liste tous les tags avec statistiques complètes
    
    Retourne tous les tags utilisés dans les transactions avec leurs statistiques
    détaillées, leur type de dépense principal et leurs patterns de reconnaissance.
    """
    try:
        # Extract tags data from transactions
        tags_data = extract_tags_from_transactions(db)
        
        # Build tag objects
        tags_list = []
        tag_id = 1
        
        for tag_name, stats in tags_data.items():
            # Apply filters
            primary_expense_type = get_tag_expense_type(stats)
            primary_category = stats['categories'].most_common(1)[0][0] if stats['categories'] else None
            
            if expense_type and primary_expense_type != expense_type:
                continue
            if category and primary_category != category:
                continue
            if min_usage and stats['transaction_count'] < min_usage:
                continue
            
            # Get patterns for this tag
            patterns = get_tag_patterns(db, tag_name)
            
            tag_out = TagOut(
                id=tag_id,
                name=tag_name,
                expense_type=primary_expense_type,
                transaction_count=stats['transaction_count'],
                total_amount=stats['total_amount'],
                patterns=patterns,
                category=primary_category,
                created_at=datetime.now(),  # We don't track creation date, use current
                last_used=stats['last_used']
            )
            
            tags_list.append(tag_out)
            tag_id += 1
        
        # Sort tags
        if sort_by == "usage":
            tags_list.sort(key=lambda x: x.transaction_count, reverse=True)
        elif sort_by == "amount":
            tags_list.sort(key=lambda x: x.total_amount, reverse=True)
        elif sort_by == "name":
            tags_list.sort(key=lambda x: x.name)
        elif sort_by == "last_used":
            tags_list.sort(key=lambda x: x.last_used or datetime.min, reverse=True)
        
        # Apply limit (ensure limit is an integer)
        if limit and isinstance(limit, int) and limit > 0:
            tags_list = tags_list[:limit]
        
        # Calculate global stats
        total_transactions_tagged = sum(tag.transaction_count for tag in tags_list)
        most_used_tags = [tag.name for tag in tags_list[:5]]
        expense_type_distribution = {}
        
        for tag in tags_list:
            expense_type_distribution[tag.expense_type] = expense_type_distribution.get(tag.expense_type, 0) + 1
        
        stats = {
            "most_used_tags": most_used_tags,
            "total_transactions_tagged": total_transactions_tagged,
            "expense_type_distribution": expense_type_distribution,
            "average_transactions_per_tag": total_transactions_tagged / len(tags_list) if tags_list else 0,
            "tags_with_patterns": len([tag for tag in tags_list if tag.patterns])
        }
        
        response = TagsListResponse(
            tags=tags_list,
            total_count=len(tags_list),
            stats=stats
        )
        
        logger.info(f"Retrieved {len(tags_list)} tags with filters: expense_type={expense_type}, category={category}, min_usage={min_usage}")
        return response
        
    except Exception as e:
        logger.error(f"Error listing tags: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des tags")


@router.put("/{tag_id}", response_model=Dict[str, Any])
async def update_tag(
    tag_id: int,
    payload: TagUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifier un tag
    
    Met à jour un tag existant et applique les changements à toutes les transactions
    associées. Recalcule automatiquement les statistiques.
    """
    try:
        # First, we need to find the tag by extracting it from transactions
        tags_data = extract_tags_from_transactions(db)
        tag_names = list(tags_data.keys())
        
        if tag_id < 1 or tag_id > len(tag_names):
            raise HTTPException(status_code=404, detail="Tag introuvable")
        
        # Get the actual tag name (tags are indexed by position)
        old_tag_name = sorted(tag_names)[tag_id - 1]
        
        # If name is being updated, we need to update all transactions
        new_tag_name = payload.name if payload.name is not None else old_tag_name
        
        updated_transactions = 0
        updated_mappings = 0
        
        if payload.name and payload.name != old_tag_name:
            # Update all transactions with the old tag name
            transactions = db.query(Transaction).filter(
                Transaction.tags.contains(old_tag_name)
            ).all()
            
            for tx in transactions:
                if tx.tags:
                    # Replace the old tag name with the new one
                    tags_list = [tag.strip() for tag in tx.tags.split(',')]
                    new_tags = []
                    for tag in tags_list:
                        if tag.lower() == old_tag_name.lower():
                            new_tags.append(new_tag_name)
                        else:
                            new_tags.append(tag)
                    tx.tags = ','.join(new_tags)
                    updated_transactions += 1
        
        # Update expense type for all transactions with this tag
        if payload.expense_type:
            transactions = db.query(Transaction).filter(
                Transaction.tags.contains(new_tag_name)
            ).all()
            
            for tx in transactions:
                if tx.tags and new_tag_name.lower() in [t.strip().lower() for t in tx.tags.split(',')]:
                    tx.expense_type = payload.expense_type
                    updated_transactions += 1
        
        # Update patterns in label_tag_mappings
        if payload.patterns is not None:
            # Remove old mappings for this tag
            db.query(LabelTagMapping).filter(
                LabelTagMapping.suggested_tags.contains(new_tag_name)
            ).delete()
            
            # Add new patterns
            for pattern in payload.patterns:
                mapping = LabelTagMapping(
                    label_pattern=pattern,
                    suggested_tags=new_tag_name,
                    confidence_score=1.0,
                    created_by=current_user.username,
                    match_type='contains',
                    case_sensitive=False
                )
                db.add(mapping)
                updated_mappings += 1
        
        # If expense type changed to FIXED, create or update fixed line mappings
        if payload.expense_type == "FIXED":
            # Check if there's already a fixed line for this tag
            existing_mapping = db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.tag_name == new_tag_name,
                TagFixedLineMapping.is_active == True
            ).first()
            
            if not existing_mapping:
                # Create a new fixed line based on tag statistics
                tag_stats = tags_data.get(old_tag_name) or tags_data.get(new_tag_name)
                if tag_stats and tag_stats['transactions']:
                    avg_amount = tag_stats['total_amount'] / tag_stats['transaction_count']
                    most_common_category = tag_stats['categories'].most_common(1)[0][0] if tag_stats['categories'] else 'autres'
                    
                    # Create fixed line
                    fixed_line = FixedLine(
                        label=f"Charges {new_tag_name}",
                        amount=avg_amount,
                        freq="mensuelle",
                        split_mode="clé",
                        split1=50.0,
                        split2=50.0,
                        category=most_common_category,
                        active=True
                    )
                    db.add(fixed_line)
                    db.flush()
                    
                    # Create mapping
                    mapping = TagFixedLineMapping(
                        tag_name=new_tag_name,
                        fixed_line_id=fixed_line.id,
                        auto_created=True,
                        created_by=current_user.username
                    )
                    db.add(mapping)
        
        db.commit()
        
        # Get updated tag information
        updated_tags_data = extract_tags_from_transactions(db)
        updated_tag_stats = updated_tags_data.get(new_tag_name, {})
        
        response = {
            "success": True,
            "message": f"Tag '{old_tag_name}' mis à jour avec succès",
            "updates": {
                "old_name": old_tag_name,
                "new_name": new_tag_name,
                "updated_transactions": updated_transactions,
                "updated_mappings": updated_mappings,
                "new_expense_type": payload.expense_type,
                "patterns_added": len(payload.patterns) if payload.patterns else 0
            },
            "updated_stats": {
                "transaction_count": updated_tag_stats.get('transaction_count', 0),
                "total_amount": updated_tag_stats.get('total_amount', 0.0)
            }
        }
        
        logger.info(f"Tag updated: {old_tag_name} → {new_tag_name}, {updated_transactions} transactions updated by {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tag {tag_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du tag")


@router.post("/{tag_id}/toggle-type", response_model=Dict[str, Any])
async def toggle_expense_type(
    tag_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Basculer le type de dépense d'un tag (Fixe/Variable)
    
    Change automatiquement le type de dépense pour toutes les transactions
    avec ce tag et gère les mappings vers les lignes fixes.
    """
    try:
        # Get the tag name from ID
        tags_data = extract_tags_from_transactions(db)
        tag_names = list(tags_data.keys())
        
        if tag_id < 1 or tag_id > len(tag_names):
            raise HTTPException(status_code=404, detail="Tag introuvable")
        
        tag_name = sorted(tag_names)[tag_id - 1]
        tag_stats = tags_data[tag_name]
        
        # Determine current primary expense type
        current_type = get_tag_expense_type(tag_stats)
        new_type = "VARIABLE" if current_type == "FIXED" else "FIXED"
        
        # Update all transactions with this tag
        transactions = db.query(Transaction).filter(
            Transaction.tags.contains(tag_name)
        ).all()
        
        updated_count = 0
        for tx in transactions:
            if tx.tags and tag_name.lower() in [t.strip().lower() for t in tx.tags.split(',')]:
                tx.expense_type = new_type
                updated_count += 1
        
        # Handle fixed line mappings
        mapping_action = ""
        if new_type == "FIXED":
            # Create or activate fixed line mapping
            existing_mapping = db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.tag_name == tag_name
            ).first()
            
            if existing_mapping:
                existing_mapping.is_active = True
                mapping_action = "activated_existing_mapping"
            else:
                # Create new fixed line
                avg_amount = tag_stats['total_amount'] / tag_stats['transaction_count']
                most_common_category = tag_stats['categories'].most_common(1)[0][0] if tag_stats['categories'] else 'autres'
                
                fixed_line = FixedLine(
                    label=f"Charges {tag_name}",
                    amount=avg_amount,
                    freq="mensuelle",
                    split_mode="clé",
                    split1=50.0,
                    split2=50.0,
                    category=most_common_category,
                    active=True
                )
                db.add(fixed_line)
                db.flush()
                
                # Create mapping
                mapping = TagFixedLineMapping(
                    tag_name=tag_name,
                    fixed_line_id=fixed_line.id,
                    auto_created=True,
                    created_by=current_user.username
                )
                db.add(mapping)
                mapping_action = "created_new_mapping"
                
        else:  # new_type == "VARIABLE"
            # Deactivate fixed line mappings
            mappings = db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.tag_name == tag_name,
                TagFixedLineMapping.is_active == True
            ).all()
            
            for mapping in mappings:
                mapping.is_active = False
                mapping_action = "deactivated_mappings"
        
        db.commit()
        
        response = {
            "success": True,
            "tag_name": tag_name,
            "previous_type": current_type,
            "new_type": new_type,
            "updated_transactions": updated_count,
            "mapping_action": mapping_action,
            "stats": {
                "transaction_count": tag_stats['transaction_count'],
                "total_amount": tag_stats['total_amount'],
                "average_amount": tag_stats['total_amount'] / tag_stats['transaction_count'] if tag_stats['transaction_count'] > 0 else 0
            }
        }
        
        logger.info(f"Tag '{tag_name}' expense type toggled: {current_type} → {new_type}, {updated_count} transactions updated")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling expense type for tag {tag_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors du basculement de type")


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    cascade: bool = Query(False, description="Si True, supprime le tag de toutes les transactions"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprimer un tag
    
    Supprime un tag du système. Si cascade=True, supprime le tag de toutes
    les transactions, sinon refuse la suppression si le tag est utilisé.
    """
    try:
        # Get the tag name from ID
        tags_data = extract_tags_from_transactions(db)
        tag_names = list(tags_data.keys())
        
        if tag_id < 1 or tag_id > len(tag_names):
            raise HTTPException(status_code=404, detail="Tag introuvable")
        
        tag_name = sorted(tag_names)[tag_id - 1]
        tag_stats = tags_data[tag_name]
        
        # Check if tag is in use
        if tag_stats['transaction_count'] > 0 and not cascade:
            raise HTTPException(
                status_code=409, 
                detail=f"Tag '{tag_name}' utilisé dans {tag_stats['transaction_count']} transactions. Utiliser cascade=true pour forcer la suppression."
            )
        
        removed_from_transactions = 0
        removed_mappings = 0
        deactivated_fixed_lines = 0
        
        if cascade:
            # Remove tag from all transactions
            transactions = db.query(Transaction).filter(
                Transaction.tags.contains(tag_name)
            ).all()
            
            for tx in transactions:
                if tx.tags:
                    # Remove the tag from the tags string
                    tags_list = [tag.strip() for tag in tx.tags.split(',') if tag.strip()]
                    new_tags = [tag for tag in tags_list if tag.lower() != tag_name.lower()]
                    tx.tags = ','.join(new_tags)
                    removed_from_transactions += 1
        
        # Remove from label_tag_mappings
        label_mappings = db.query(LabelTagMapping).filter(
            LabelTagMapping.suggested_tags.contains(tag_name)
        ).all()
        
        for mapping in label_mappings:
            # Remove this tag from the suggested_tags
            tags_list = [tag.strip() for tag in mapping.suggested_tags.split(',') if tag.strip()]
            new_tags = [tag for tag in tags_list if tag.lower() != tag_name.lower()]
            
            if new_tags:
                mapping.suggested_tags = ','.join(new_tags)
            else:
                db.delete(mapping)
            removed_mappings += 1
        
        # Deactivate related fixed line mappings
        fixed_mappings = db.query(TagFixedLineMapping).filter(
            TagFixedLineMapping.tag_name == tag_name,
            TagFixedLineMapping.is_active == True
        ).all()
        
        for mapping in fixed_mappings:
            mapping.is_active = False
            deactivated_fixed_lines += 1
        
        db.commit()
        
        response = {
            "success": True,
            "message": f"Tag '{tag_name}' supprimé avec succès",
            "tag_name": tag_name,
            "cascade": cascade,
            "stats": {
                "original_transaction_count": tag_stats['transaction_count'],
                "removed_from_transactions": removed_from_transactions,
                "removed_mappings": removed_mappings,
                "deactivated_fixed_lines": deactivated_fixed_lines
            }
        }
        
        logger.info(f"Tag '{tag_name}' deleted with cascade={cascade} by {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tag {tag_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du tag")


@router.post("/{tag_id}/patterns", response_model=Dict[str, Any])
async def add_tag_patterns(
    tag_id: int,
    payload: TagPatterns,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ajouter des patterns de reconnaissance à un tag
    
    Ajoute des patterns pour la reconnaissance automatique d'un tag
    lors de l'import de transactions.
    """
    try:
        # Get the tag name from ID
        tags_data = extract_tags_from_transactions(db)
        tag_names = list(tags_data.keys())
        
        if tag_id < 1 or tag_id > len(tag_names):
            raise HTTPException(status_code=404, detail="Tag introuvable")
        
        tag_name = sorted(tag_names)[tag_id - 1]
        
        # Add patterns to label_tag_mappings
        added_patterns = 0
        existing_patterns = []
        
        for pattern in payload.patterns:
            # Check if pattern already exists
            existing = db.query(LabelTagMapping).filter(
                LabelTagMapping.label_pattern == pattern,
                LabelTagMapping.suggested_tags.contains(tag_name)
            ).first()
            
            if existing:
                existing_patterns.append(pattern)
                continue
            
            # Create new mapping
            mapping = LabelTagMapping(
                label_pattern=pattern,
                suggested_tags=tag_name,
                confidence_score=1.0,
                created_by=current_user.username,
                match_type='contains',
                case_sensitive=False
            )
            db.add(mapping)
            added_patterns += 1
        
        db.commit()
        
        # Get updated patterns list
        all_patterns = get_tag_patterns(db, tag_name)
        
        response = {
            "success": True,
            "tag_name": tag_name,
            "added_patterns": added_patterns,
            "existing_patterns": existing_patterns,
            "total_patterns": len(all_patterns),
            "all_patterns": all_patterns,
            "message": f"{added_patterns} nouveaux patterns ajoutés au tag '{tag_name}'"
        }
        
        logger.info(f"Added {added_patterns} patterns to tag '{tag_name}' by {current_user.username}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding patterns to tag {tag_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout des patterns")


@router.get("/{tag_id}/transactions", response_model=Dict[str, Any])
async def get_tag_transactions(
    tag_id: int,
    limit: int = Query(50, description="Nombre maximum de transactions"),
    offset: int = Query(0, description="Décalage pour la pagination"),
    month: Optional[str] = Query(None, description="Filtrer par mois (YYYY-MM)"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer toutes les transactions d'un tag
    
    Retourne la liste paginée des transactions associées à un tag
    avec possibilité de filtrage par mois.
    """
    try:
        # Get the tag name from ID
        tags_data = extract_tags_from_transactions(db)
        tag_names = list(tags_data.keys())
        
        if tag_id < 1 or tag_id > len(tag_names):
            raise HTTPException(status_code=404, detail="Tag introuvable")
        
        tag_name = sorted(tag_names)[tag_id - 1]
        
        # Build query
        query = db.query(Transaction).filter(
            Transaction.tags.contains(tag_name),
            Transaction.exclude == False
        )
        
        if month:
            query = query.filter(Transaction.month == month)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        transactions = query.order_by(desc(Transaction.date_op)).offset(offset).limit(limit).all()
        
        # Convert to TxOut format
        transactions_out = []
        for tx in transactions:
            tx_out = TxOut(
                id=tx.id,
                month=tx.month,
                date_op=tx.date_op,
                date_valeur=tx.date_op,  # Use date_op as date_valeur if not available
                amount=tx.amount,
                label=tx.label,
                category=tx.category,
                subcategory=tx.category_parent,
                is_expense=tx.is_expense,
                exclude=tx.exclude,
                expense_type=tx.expense_type,
                tags=[tag.strip() for tag in tx.tags.split(',') if tag.strip()] if tx.tags else []
            )
            transactions_out.append(tx_out)
        
        # Calculate stats for this filtered set
        total_amount = sum(abs(tx.amount) if tx.amount else 0 for tx in transactions)
        avg_amount = total_amount / len(transactions) if transactions else 0
        
        # Group by month for trends
        monthly_stats = defaultdict(lambda: {'count': 0, 'amount': 0.0})
        for tx in transactions:
            if tx.month:
                monthly_stats[tx.month]['count'] += 1
                monthly_stats[tx.month]['amount'] += abs(tx.amount) if tx.amount else 0
        
        response = {
            "tag_name": tag_name,
            "transactions": transactions_out,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "stats": {
                "filtered_count": len(transactions),
                "total_amount": total_amount,
                "average_amount": avg_amount,
                "month_filter": month
            },
            "monthly_breakdown": dict(monthly_stats),
            "expense_type_distribution": {
                tx.expense_type: len([t for t in transactions if t.expense_type == tx.expense_type])
                for tx in transactions if tx.expense_type
            }
        }
        
        logger.info(f"Retrieved {len(transactions)} transactions for tag '{tag_name}' (total: {total_count})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transactions for tag {tag_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des transactions")


@router.get("/search")
async def search_tags(
    query: str = Query(..., description="Terme de recherche"),
    limit: int = Query(10, description="Nombre maximum de résultats"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rechercher des tags par nom
    
    Recherche des tags existants par nom avec correspondance partielle.
    """
    try:
        tags_data = extract_tags_from_transactions(db)
        
        # Filter tags by query
        matching_tags = []
        tag_id = 1
        
        query_lower = query.lower()
        for tag_name, stats in tags_data.items():
            if query_lower in tag_name.lower():
                primary_expense_type = get_tag_expense_type(stats)
                primary_category = stats['categories'].most_common(1)[0][0] if stats['categories'] else None
                patterns = get_tag_patterns(db, tag_name)
                
                tag_out = TagOut(
                    id=tag_id,
                    name=tag_name,
                    expense_type=primary_expense_type,
                    transaction_count=stats['transaction_count'],
                    total_amount=stats['total_amount'],
                    patterns=patterns,
                    category=primary_category,
                    created_at=datetime.now(),
                    last_used=stats['last_used']
                )
                matching_tags.append(tag_out)
                
                if len(matching_tags) >= limit:
                    break
                    
            tag_id += 1
        
        # Sort by usage
        matching_tags.sort(key=lambda x: x.transaction_count, reverse=True)
        
        response = {
            "query": query,
            "results": matching_tags,
            "total_found": len(matching_tags)
        }
        
        logger.info(f"Tag search for '{query}' returned {len(matching_tags)} results")
        return response
        
    except Exception as e:
        logger.error(f"Error searching tags with query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la recherche de tags")


@router.get("/stats", response_model=Dict[str, Any])
async def get_tags_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir les statistiques globales des tags
    
    Retourne des statistiques complètes sur l'usage des tags dans le système.
    """
    try:
        tags_data = extract_tags_from_transactions(db)
        
        if not tags_data:
            return {
                "total_tags": 0,
                "total_transactions_tagged": 0,
                "average_tags_per_transaction": 0.0,
                "most_used_tags": [],
                "expense_type_distribution": {"FIXED": 0, "VARIABLE": 0},
                "tag_usage_distribution": {},
                "untagged_transactions_count": 0
            }
        
        # Calculate statistics
        total_tags = len(tags_data)
        total_transactions_tagged = sum(stats['transaction_count'] for stats in tags_data.values())
        
        # Most used tags (top 10)
        most_used = sorted(tags_data.items(), key=lambda x: x[1]['transaction_count'], reverse=True)[:10]
        most_used_tags = [{"name": tag, "count": stats['transaction_count']} for tag, stats in most_used]
        
        # Expense type distribution
        expense_type_dist = {"FIXED": 0, "VARIABLE": 0, "PROVISION": 0}
        for stats in tags_data.values():
            primary_type = get_tag_expense_type(stats)
            # Ensure we handle any unexpected expense types gracefully
            if primary_type in expense_type_dist:
                expense_type_dist[primary_type] += 1
            else:
                # If we encounter an unknown type, default to VARIABLE
                expense_type_dist["VARIABLE"] += 1
        
        # Tag usage distribution (by usage frequency)
        usage_distribution = {
            "1-5_uses": 0,
            "6-20_uses": 0, 
            "21-50_uses": 0,
            "51+_uses": 0
        }
        
        for stats in tags_data.values():
            count = stats['transaction_count']
            if count <= 5:
                usage_distribution["1-5_uses"] += 1
            elif count <= 20:
                usage_distribution["6-20_uses"] += 1
            elif count <= 50:
                usage_distribution["21-50_uses"] += 1
            else:
                usage_distribution["51+_uses"] += 1
        
        # Count untagged transactions
        untagged_count = db.query(Transaction).filter(
            or_(Transaction.tags == "", Transaction.tags.is_(None)),
            Transaction.exclude == False
        ).count()
        
        # Total tagged transactions (including those with multiple tags)
        total_with_tags = db.query(Transaction).filter(
            Transaction.tags != "",
            Transaction.tags.is_not(None),
            Transaction.exclude == False
        ).count()
        
        average_tags_per_transaction = total_transactions_tagged / total_with_tags if total_with_tags > 0 else 0
        
        stats = {
            "total_tags": total_tags,
            "total_transactions_tagged": total_transactions_tagged,
            "total_transactions_with_tags": total_with_tags,
            "untagged_transactions_count": untagged_count,
            "average_tags_per_transaction": round(average_tags_per_transaction, 2),
            "most_used_tags": most_used_tags,
            "expense_type_distribution": expense_type_dist,
            "tag_usage_distribution": usage_distribution,
            "tags_with_patterns": len([tag for tag, _ in tags_data.items() if get_tag_patterns(db, tag)]),
            "average_amount_per_tag": {
                tag: round(stats['total_amount'] / stats['transaction_count'], 2) 
                if stats['transaction_count'] > 0 else 0
                for tag, stats in most_used[:5]  # Top 5 tags only
            }
        }
        
        logger.info(f"Tags stats retrieved: {total_tags} tags, {total_transactions_tagged} tagged transactions")
        return stats

    except Exception as e:
        logger.error(f"Error getting tags stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")


# =============================================================================
# MERGE TAGS ENDPOINT - Fusionner plusieurs tags en un seul
# =============================================================================

from pydantic import BaseModel, Field
from typing import List


class MergeTagsRequest(BaseModel):
    """Request schema for merging tags"""
    source_tags: List[str] = Field(
        ...,
        min_items=1,
        description="List of source tag names to merge (will be removed)"
    )
    target_tag: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target tag name (all transactions will receive this tag)"
    )
    delete_source_tags: bool = Field(
        default=True,
        description="If true, remove source tags from transactions after merge"
    )

    class Config:
        schema_extra = {
            "example": {
                "source_tags": ["resto", "restaurant", "restau"],
                "target_tag": "restaurant",
                "delete_source_tags": True
            }
        }


class MergeTagsResponse(BaseModel):
    """Response schema for merge operation"""
    success: bool
    message: str
    source_tags: List[str]
    target_tag: str
    transactions_updated: int
    patterns_merged: int
    fixed_line_mappings_updated: int
    stats: Dict[str, Any]


@router.post("/merge", response_model=MergeTagsResponse)
async def merge_tags(
    payload: MergeTagsRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fusionner plusieurs tags en un seul.

    Cette opération :
    1. Met à jour toutes les transactions avec les tags sources pour utiliser le tag cible
    2. Fusionne les patterns de reconnaissance automatique
    3. Met à jour les mappings vers les lignes fixes
    4. Optionnellement supprime les tags sources des transactions

    **Exemple d'usage :**
    - Fusionner "resto", "restaurant", "restau" → "restaurant"
    - Fusionner "courses", "supermarché", "alimentation" → "courses"

    **Important :**
    - Le tag cible peut être un tag existant ou un nouveau tag
    - Si delete_source_tags=true, les tags sources sont supprimés
    - Les patterns ML sont automatiquement associés au tag cible
    """
    try:
        source_tags = [tag.strip().lower() for tag in payload.source_tags if tag.strip()]
        target_tag = payload.target_tag.strip().lower()

        if not source_tags:
            raise HTTPException(status_code=400, detail="Au moins un tag source est requis")

        if target_tag in source_tags and len(source_tags) == 1:
            raise HTTPException(
                status_code=400,
                detail="Le tag cible ne peut pas être le seul tag source"
            )

        # Remove target from source list if present (no need to "merge" it with itself)
        source_tags = [tag for tag in source_tags if tag != target_tag]

        if not source_tags:
            return MergeTagsResponse(
                success=True,
                message="Aucune fusion nécessaire - tous les tags sources sont identiques au tag cible",
                source_tags=payload.source_tags,
                target_tag=target_tag,
                transactions_updated=0,
                patterns_merged=0,
                fixed_line_mappings_updated=0,
                stats={}
            )

        transactions_updated = 0
        patterns_merged = 0
        fixed_line_mappings_updated = 0
        source_stats = {}

        # Process each source tag
        for source_tag in source_tags:
            # Find all transactions with this source tag
            transactions = db.query(Transaction).filter(
                Transaction.tags.contains(source_tag)
            ).all()

            source_stats[source_tag] = {
                "transaction_count": len(transactions),
                "updated": 0
            }

            for tx in transactions:
                if not tx.tags:
                    continue

                # Parse existing tags
                tx_tags = [t.strip().lower() for t in tx.tags.split(',') if t.strip()]

                # Check if this transaction has the source tag
                if source_tag not in tx_tags:
                    continue

                # Update tags: remove source, add target if not present
                new_tags = []
                has_target = False

                for tag in tx_tags:
                    if tag == source_tag:
                        # Replace source with target
                        if not has_target:
                            new_tags.append(target_tag)
                            has_target = True
                    elif tag == target_tag:
                        # Target already exists
                        if not has_target:
                            new_tags.append(tag)
                            has_target = True
                    else:
                        # Keep other tags
                        new_tags.append(tag)

                # Remove duplicates while preserving order
                seen = set()
                unique_tags = []
                for tag in new_tags:
                    if tag not in seen:
                        seen.add(tag)
                        unique_tags.append(tag)

                tx.tags = ','.join(unique_tags)
                transactions_updated += 1
                source_stats[source_tag]["updated"] += 1

            # Merge label_tag_mappings (patterns)
            source_mappings = db.query(LabelTagMapping).filter(
                LabelTagMapping.suggested_tags.contains(source_tag)
            ).all()

            for mapping in source_mappings:
                if mapping.suggested_tags:
                    # Replace source tag with target in suggested_tags
                    tags_list = [t.strip() for t in mapping.suggested_tags.split(',') if t.strip()]
                    new_mapping_tags = []
                    has_target_mapping = False

                    for tag in tags_list:
                        if tag.lower() == source_tag:
                            if not has_target_mapping:
                                new_mapping_tags.append(target_tag)
                                has_target_mapping = True
                        elif tag.lower() == target_tag:
                            if not has_target_mapping:
                                new_mapping_tags.append(tag)
                                has_target_mapping = True
                        else:
                            new_mapping_tags.append(tag)

                    mapping.suggested_tags = ','.join(new_mapping_tags)
                    patterns_merged += 1

            # Update TagFixedLineMapping
            fixed_mappings = db.query(TagFixedLineMapping).filter(
                TagFixedLineMapping.tag_name == source_tag,
                TagFixedLineMapping.is_active == True
            ).all()

            for fixed_mapping in fixed_mappings:
                # Check if target already has a mapping
                existing_target_mapping = db.query(TagFixedLineMapping).filter(
                    TagFixedLineMapping.tag_name == target_tag,
                    TagFixedLineMapping.is_active == True
                ).first()

                if existing_target_mapping:
                    # Deactivate source mapping (target already covered)
                    fixed_mapping.is_active = False
                else:
                    # Transfer mapping to target tag
                    fixed_mapping.tag_name = target_tag
                fixed_line_mappings_updated += 1

        db.commit()

        # Calculate final stats
        tags_data = extract_tags_from_transactions(db)
        target_stats = tags_data.get(target_tag, {})

        response = MergeTagsResponse(
            success=True,
            message=f"Fusion réussie: {len(source_tags)} tags fusionnés vers '{target_tag}'",
            source_tags=source_tags,
            target_tag=target_tag,
            transactions_updated=transactions_updated,
            patterns_merged=patterns_merged,
            fixed_line_mappings_updated=fixed_line_mappings_updated,
            stats={
                "source_tags_stats": source_stats,
                "target_tag_final_stats": {
                    "transaction_count": target_stats.get('transaction_count', 0),
                    "total_amount": target_stats.get('total_amount', 0.0)
                }
            }
        )

        logger.info(
            f"Tags merged by {current_user.username}: "
            f"{source_tags} → {target_tag}, "
            f"{transactions_updated} transactions updated"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging tags: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la fusion des tags: {str(e)}"
        )