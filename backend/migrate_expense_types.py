#!/usr/bin/env python3
"""
Migration script for Budget Famille v2.3 - Expense Type Classification
Classifie automatiquement les transactions existantes selon leur type de dépense
pour éviter le double comptage entre Fixed et Variable.
"""

import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.database import Transaction, FixedLine, Base
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_database_connection():
    """Créer la connexion à la base de données"""
    DATABASE_URL = "sqlite:///./budget.db"
    
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        },
        pool_pre_ping=True,
        echo=False
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def analyze_current_transactions(session):
    """Analyser la répartition actuelle des transactions"""
    logger.info("🔍 Analyse des transactions existantes...")
    
    # Compter les transactions par type actuel
    total_transactions = session.query(Transaction).count()
    expense_transactions = session.query(Transaction).filter(Transaction.is_expense == True).count()
    excluded_transactions = session.query(Transaction).filter(Transaction.exclude == True).count()
    
    # Vérifier si la colonne expense_type existe
    try:
        variable_transactions = session.query(Transaction).filter(Transaction.expense_type == 'VARIABLE').count()
        fixed_transactions = session.query(Transaction).filter(Transaction.expense_type == 'FIXED').count()
        provision_transactions = session.query(Transaction).filter(Transaction.expense_type == 'PROVISION').count()
        has_expense_type = True
    except Exception:
        # La colonne n'existe pas encore
        variable_transactions = fixed_transactions = provision_transactions = 0
        has_expense_type = False
    
    # Analyser les charges fixes existantes
    fixed_lines = session.query(FixedLine).filter(FixedLine.active == True).all()
    
    logger.info(f"📊 État actuel de la base de données:")
    logger.info(f"  • Total transactions: {total_transactions}")
    logger.info(f"  • Transactions dépenses: {expense_transactions}")
    logger.info(f"  • Transactions exclues: {excluded_transactions}")
    logger.info(f"  • Lignes fixes actives: {len(fixed_lines)}")
    
    if has_expense_type:
        logger.info(f"  • Type VARIABLE: {variable_transactions}")
        logger.info(f"  • Type FIXED: {fixed_transactions}")
        logger.info(f"  • Type PROVISION: {provision_transactions}")
    else:
        logger.info("  • Colonne expense_type: NON PRÉSENTE")
    
    return {
        'total': total_transactions,
        'expenses': expense_transactions,
        'excluded': excluded_transactions,
        'fixed_lines': len(fixed_lines),
        'has_expense_type': has_expense_type,
        'current_variable': variable_transactions,
        'current_fixed': fixed_transactions,
        'current_provision': provision_transactions
    }

def identify_potential_duplicates(session):
    """Identifier les potentielles duplications entre fixed_lines et transactions"""
    logger.info("🔍 Recherche de potentiels doublons Fixed/Variable...")
    
    fixed_lines = session.query(FixedLine).filter(FixedLine.active == True).all()
    duplicates_found = []
    
    for fixed_line in fixed_lines:
        # Chercher des transactions avec des libellés similaires
        similar_transactions = session.query(Transaction).filter(
            Transaction.is_expense == True,
            Transaction.exclude == False,
            Transaction.label.ilike(f'%{fixed_line.label}%')
        ).all()
        
        if similar_transactions:
            duplicates_found.append({
                'fixed_line': fixed_line,
                'transactions': similar_transactions,
                'potential_amount_conflict': any(
                    abs(abs(tx.amount or 0) - fixed_line.amount) < 50 
                    for tx in similar_transactions
                )
            })
    
    logger.info(f"⚠️  Potentiels doublons détectés: {len(duplicates_found)}")
    
    for duplicate in duplicates_found:
        fixed = duplicate['fixed_line']
        txs = duplicate['transactions']
        logger.warning(f"  • Fixe '{fixed.label}' ({fixed.amount}€) <-> {len(txs)} transaction(s) similaire(s)")
        for tx in txs[:3]:  # Montrer les 3 premières
            logger.warning(f"    - TX {tx.id}: '{tx.label}' ({tx.amount}€) [{tx.month}]")
    
    return duplicates_found

def classify_transactions_intelligently(session, dry_run=True):
    """Classification intelligente des transactions par type"""
    logger.info("🤖 Classification intelligente des transactions...")
    
    classifications = {
        'VARIABLE': 0,
        'FIXED': 0,
        'PROVISION': 0,
        'SKIPPED': 0
    }
    
    # Obtenir toutes les transactions dépenses non exclues
    transactions = session.query(Transaction).filter(
        Transaction.is_expense == True,
        Transaction.exclude == False
    ).all()
    
    logger.info(f"📝 Traitement de {len(transactions)} transactions dépenses...")
    
    # Règles de classification
    provision_keywords = [
        'épargne', 'savings', 'investment', 'investissement', 'provision',
        'assurance vie', 'pel', 'livret', 'plan épargne', 'retraite'
    ]
    
    fixed_keywords = [
        'loyer', 'rent', 'électricité', 'electricity', 'gaz', 'gas',
        'internet', 'téléphone', 'phone', 'abonnement', 'subscription',
        'assurance', 'insurance', 'mutuelle', 'crédit', 'loan', 'emprunt',
        'impôt', 'tax', 'taxe', 'frais bancaire', 'bank fee'
    ]
    
    # Obtenir les tags des fixed_lines pour éviter les doublons
    fixed_lines = session.query(FixedLine).filter(FixedLine.active == True).all()
    fixed_line_labels = {line.label.lower() for line in fixed_lines}
    
    for tx in transactions:
        tx_label_lower = (tx.label or '').lower()
        tx_category_lower = (tx.category or '').lower()
        tx_amount = abs(tx.amount or 0)
        
        # Si déjà classifié, passer
        current_type = getattr(tx, 'expense_type', 'VARIABLE')
        if current_type != 'VARIABLE':
            classifications['SKIPPED'] += 1
            continue
        
        # Classification par mots-clés
        new_type = 'VARIABLE'  # par défaut
        
        # 1. Vérifier si c'est une provision
        if any(keyword in tx_label_lower for keyword in provision_keywords):
            new_type = 'PROVISION'
        # 2. Vérifier si c'est une charge fixe
        elif any(keyword in tx_label_lower or keyword in tx_category_lower for keyword in fixed_keywords):
            new_type = 'FIXED'
        # 3. Vérifier si le libellé correspond à une fixed_line existante
        elif any(fixed_label in tx_label_lower for fixed_label in fixed_line_labels):
            new_type = 'FIXED'
        # 4. Montants élevés récurrents (> 500€) probablement fixes
        elif tx_amount > 500:
            # Vérifier s'il y a d'autres transactions similaires ce mois
            similar_count = session.query(Transaction).filter(
                Transaction.month == tx.month,
                Transaction.is_expense == True,
                Transaction.exclude == False,
                Transaction.label.ilike(f'%{tx.label[:20]}%'),
                Transaction.id != tx.id
            ).count()
            if similar_count > 0:
                new_type = 'FIXED'
        
        # Appliquer la classification
        if not dry_run:
            tx.expense_type = new_type
            session.add(tx)
        
        classifications[new_type] += 1
        
        if new_type != 'VARIABLE':
            logger.info(f"  • TX {tx.id}: '{tx.label}' → {new_type} ({tx_amount:.2f}€)")
    
    if not dry_run:
        session.commit()
        logger.info("✅ Classifications appliquées en base de données")
    else:
        logger.info("🔍 Mode DRY RUN - Aucune modification appliquée")
    
    return classifications

def main():
    """Fonction principale de migration"""
    logger.info("🚀 Démarrage de la migration des types de dépenses")
    
    try:
        # Créer la connexion
        engine, SessionLocal = create_database_connection()
        session = SessionLocal()
        
        # 1. Analyser l'état actuel
        current_state = analyze_current_transactions(session)
        
        # 2. Identifier les potentiels doublons
        duplicates = identify_potential_duplicates(session)
        
        # 3. Classification intelligente (DRY RUN d'abord)
        logger.info("\n" + "="*60)
        logger.info("🔍 SIMULATION de la classification (DRY RUN)")
        logger.info("="*60)
        
        dry_classifications = classify_transactions_intelligently(session, dry_run=True)
        
        logger.info(f"\n📊 Résultats de la simulation:")
        logger.info(f"  • VARIABLE: {dry_classifications['VARIABLE']}")
        logger.info(f"  • FIXED: {dry_classifications['FIXED']}")
        logger.info(f"  • PROVISION: {dry_classifications['PROVISION']}")
        logger.info(f"  • IGNORÉES: {dry_classifications['SKIPPED']}")
        
        # 4. Demander confirmation pour appliquer
        print("\n" + "="*60)
        print("⚠️  ATTENTION: Cette migration va modifier les types de dépenses")
        print("="*60)
        
        if duplicates:
            print(f"🚨 {len(duplicates)} potentiels doublons détectés!")
            print("   Vérifiez les logs ci-dessus avant de continuer.")
        
        confirm = input("\nVoulez-vous appliquer ces modifications? (oui/non): ").lower().strip()
        
        if confirm in ['oui', 'yes', 'y', 'o']:
            logger.info("\n🔧 Application de la classification...")
            real_classifications = classify_transactions_intelligently(session, dry_run=False)
            
            # Vérification finale
            final_state = analyze_current_transactions(session)
            
            logger.info("\n✅ Migration terminée avec succès!")
            logger.info("📊 État final:")
            logger.info(f"  • VARIABLE: {final_state['current_variable']}")
            logger.info(f"  • FIXED: {final_state['current_fixed']}")
            logger.info(f"  • PROVISION: {final_state['current_provision']}")
            
        else:
            logger.info("❌ Migration annulée par l'utilisateur")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        raise

if __name__ == "__main__":
    main()