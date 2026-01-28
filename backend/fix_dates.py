"""
Script pour corriger les dates inversées dans les transactions.

Le problème : les dates au format DD/MM/YY ont parfois été mal parsées
comme MM/DD/YY, inversant jour et mois.

Exemple: 11/12/25 devrait être 11 décembre 2025, pas 12 novembre 2025
Mais dans la base on a date_op=2025-12-11 alors que le libellé indique 10/11/25

Ce script:
1. Identifie les transactions où la date dans le libellé ne correspond pas à date_op
2. Corrige les dates inversées
3. Synchronise le champ month avec date_op
"""
import sqlite3
import re
from datetime import datetime

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Pattern pour extraire les dates du libellé: DD/MM/YY
DATE_PATTERN = re.compile(r'(\d{2})/(\d{2})/(\d{2})\b')

def extract_date_from_label(label):
    """Extrait la date DD/MM/YY du libellé."""
    match = DATE_PATTERN.search(label)
    if match:
        day, month, year = match.groups()
        # Convertir en format YYYY-MM-DD
        full_year = f"20{year}"
        try:
            # Valider la date
            parsed = datetime(int(full_year), int(month), int(day))
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            # Date invalide
            return None
    return None

def is_date_swapped(date_op_str, label_date_str):
    """Vérifie si les dates sont inversées (jour/mois)."""
    if not date_op_str or not label_date_str:
        return False

    # Comparer YYYY-MM-DD
    if date_op_str == label_date_str:
        return False  # Dates identiques, pas d'inversion

    # Extraire les composants
    try:
        db_year, db_month, db_day = date_op_str.split('-')
        label_year, label_month, label_day = label_date_str.split('-')

        # Si le jour de la DB correspond au mois du libellé et vice versa
        # Exemple: DB=2025-12-11 vs Label=2025-11-10
        # Correction: 11 (jour DB) devrait être le mois, 12 (mois DB) devrait être le jour
        if db_year == label_year and db_month == label_day and db_day == label_month:
            return True
    except:
        return False

    return False

# Analyser toutes les transactions
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE label LIKE '%/%/%'
""")

transactions = cursor.fetchall()
print(f"Analyse de {len(transactions)} transactions avec dates dans le libelle...")

corrections = []
for tx_id, date_op, month, label in transactions:
    label_date = extract_date_from_label(label)
    if label_date:
        # Comparer avec la date en DB
        if str(date_op)[:10] != label_date:
            # Le format de date_op peut être différent, normaliser
            db_date = str(date_op)[:10]

            # Vérifier si c'est une inversion jour/mois
            if is_date_swapped(db_date, label_date):
                corrections.append({
                    'id': tx_id,
                    'old_date_op': db_date,
                    'new_date_op': label_date,
                    'old_month': month,
                    'new_month': label_date[:7],
                    'label': label[:60]
                })

print(f"\nTrouve {len(corrections)} transactions avec dates inversees")

if corrections:
    print("\n=== Exemples de corrections a appliquer ===")
    for corr in corrections[:20]:
        print(f"ID:{corr['id']} | {corr['old_date_op']} -> {corr['new_date_op']} | {corr['old_month']} -> {corr['new_month']}")
        print(f"   Label: {corr['label']}")

    if len(corrections) > 20:
        print(f"... et {len(corrections) - 20} autres corrections")

    print("\n" + "="*60)
    confirm = input("Appliquer ces corrections? (oui/non): ")

    if confirm.lower() == 'oui':
        for corr in corrections:
            cursor.execute("""
                UPDATE transactions
                SET date_op = ?, month = ?
                WHERE id = ?
            """, (corr['new_date_op'], corr['new_month'], corr['id']))

        conn.commit()
        print(f"\n✅ {len(corrections)} transactions corrigees!")
    else:
        print("\n❌ Corrections annulees")
else:
    print("\nAucune correction necessaire.")

# Synchroniser tous les champs month qui ne correspondent pas a date_op
print("\n=== Synchronisation du champ month ===")
cursor.execute("""
    SELECT COUNT(*)
    FROM transactions
    WHERE substr(date_op, 1, 7) != month
""")
desync_count = cursor.fetchone()[0]
print(f"Transactions desynchronisees: {desync_count}")

if desync_count > 0:
    confirm = input("Synchroniser month avec date_op? (oui/non): ")
    if confirm.lower() == 'oui':
        cursor.execute("""
            UPDATE transactions
            SET month = substr(date_op, 1, 7)
            WHERE substr(date_op, 1, 7) != month
        """)
        conn.commit()
        print(f"✅ {desync_count} transactions synchronisees!")

conn.close()
print("\nTermine.")
