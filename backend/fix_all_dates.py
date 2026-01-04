"""
Corriger TOUTES les dates en utilisant la date du libelle au lieu de dateOp.
La date dans le libelle (ex: 'CARTE 30/10/25') est la vraie date de transaction.
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
            # Valider la date
            parsed = datetime(int(full_year), int(month), int(day))
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None

# Analyser TOUTES les transactions avec dates dans le libelle
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
        # Si la date est differente, on corrige
        if db_date != label_date:
            corrections.append({
                'id': tx_id,
                'old_date_op': db_date,
                'new_date_op': label_date,
                'old_month': month,
                'new_month': label_date[:7],
                'label': label[:55]
            })

print(f'Trouve {len(corrections)} transactions avec dates a corriger')

if corrections:
    print()
    print('=== Exemples de corrections ===')
    for corr in corrections[:15]:
        print(f"ID:{corr['id']} | {corr['old_date_op']} -> {corr['new_date_op']} | {corr['old_month']} -> {corr['new_month']}")
        print(f"   {corr['label']}")

    if len(corrections) > 15:
        print(f'... et {len(corrections) - 15} autres corrections')

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

# Supprimer les doublons (meme label, meme montant, meme date)
print()
print('=== Suppression des doublons ===')
cursor.execute("""
    SELECT label, amount, date_op, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
    FROM transactions
    GROUP BY label, amount, date_op
    HAVING cnt > 1
""")

duplicates = cursor.fetchall()
print(f'Trouve {len(duplicates)} groupes de doublons')

deleted_count = 0
for label, amount, date_op, count, ids_str in duplicates:
    ids = [int(i) for i in ids_str.split(',')]
    # Garder le premier, supprimer les autres
    to_delete = ids[1:]
    for del_id in to_delete:
        cursor.execute("DELETE FROM transactions WHERE id = ?", (del_id,))
        deleted_count += 1

if deleted_count > 0:
    conn.commit()
    print(f'OK! {deleted_count} doublons supprimes!')

# Verification finale
print()
print('=== Verification finale ===')
cursor.execute("""
    SELECT month, COUNT(*) as cnt
    FROM transactions
    WHERE month >= '2025-09'
    GROUP BY month
    ORDER BY month
""")
for row in cursor.fetchall():
    print(f'Mois {row[0]}: {row[1]} transactions')

# Plage de dates par mois
print()
print('=== Plages de dates ===')
cursor.execute("""
    SELECT month, MIN(date_op), MAX(date_op)
    FROM transactions
    WHERE month >= '2025-09'
    GROUP BY month
    ORDER BY month
""")
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} a {row[2]}')

conn.close()
print()
print('Termine.')
