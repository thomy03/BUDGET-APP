"""
Script pour corriger les dates inversees dans les transactions.
Le probleme: les dates DD/MM/YY ont ete mal parsees comme MM/DD/YY.
"""
import sqlite3
import re
from datetime import datetime

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

DATE_PATTERN = re.compile(r'(\d{2})/(\d{2})/(\d{2})\b')

def extract_date_from_label(label):
    """Extrait la date DD/MM/YY du libelle."""
    match = DATE_PATTERN.search(label)
    if match:
        day, month, year = match.groups()
        full_year = f'20{year}'
        try:
            parsed = datetime(int(full_year), int(month), int(day))
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None

def is_date_swapped(date_op_str, label_date_str):
    """Verifie si les dates sont inversees (jour/mois)."""
    if not date_op_str or not label_date_str:
        return False
    if date_op_str == label_date_str:
        return False
    try:
        db_year, db_month, db_day = date_op_str.split('-')
        label_year, label_month, label_day = label_date_str.split('-')
        # Si jour DB = mois label et mois DB = jour label
        if db_year == label_year and db_month == label_day and db_day == label_month:
            return True
    except:
        return False
    return False

# Analyser toutes les transactions avec dates dans le libelle
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE label LIKE '%/%/%'
""")

transactions = cursor.fetchall()
print(f'Analyse de {len(transactions)} transactions avec dates dans le libelle...')

corrections = []
for tx_id, date_op, month, label in transactions:
    label_date = extract_date_from_label(label)
    if label_date:
        db_date = str(date_op)[:10]
        if db_date != label_date:
            if is_date_swapped(db_date, label_date):
                corrections.append({
                    'id': tx_id,
                    'old_date_op': db_date,
                    'new_date_op': label_date,
                    'old_month': month,
                    'new_month': label_date[:7],
                    'label': label[:60]
                })

print(f'Trouve {len(corrections)} transactions avec dates inversees')

if corrections:
    print()
    print('=== Corrections a appliquer ===')
    for corr in corrections[:10]:
        print(f"ID:{corr['id']} | {corr['old_date_op']} -> {corr['new_date_op']} | {corr['old_month']} -> {corr['new_month']}")
        print(f"   Label: {corr['label']}")

    if len(corrections) > 10:
        print(f'... et {len(corrections) - 10} autres corrections')

    print()
    print('Application des corrections...')
    for corr in corrections:
        cursor.execute("""
            UPDATE transactions
            SET date_op = ?, month = ?
            WHERE id = ?
        """, (corr['new_date_op'], corr['new_month'], corr['id']))

    conn.commit()
    print(f'OK! {len(corrections)} transactions corrigees!')
else:
    print('Aucune correction necessaire.')

# Synchroniser tous les champs month qui ne correspondent pas a date_op
print()
print('=== Synchronisation du champ month ===')
cursor.execute("""
    SELECT COUNT(*)
    FROM transactions
    WHERE substr(date_op, 1, 7) != month
""")
desync_count = cursor.fetchone()[0]
print(f'Transactions desynchronisees: {desync_count}')

if desync_count > 0:
    cursor.execute("""
        UPDATE transactions
        SET month = substr(date_op, 1, 7)
        WHERE substr(date_op, 1, 7) != month
    """)
    conn.commit()
    print(f'OK! {desync_count} transactions synchronisees!')

# Verification finale
print()
print('=== Verification finale ===')
cursor.execute("""
    SELECT month, COUNT(*) as cnt
    FROM transactions
    WHERE month IN ('2025-10', '2025-11', '2025-12')
    GROUP BY month
    ORDER BY month
""")
for row in cursor.fetchall():
    print(f'Mois {row[0]}: {row[1]} transactions')

conn.close()
print()
print('Termine.')
