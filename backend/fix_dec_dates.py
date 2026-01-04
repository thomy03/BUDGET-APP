"""
Corriger les transactions de decembre 2025 en utilisant la date du libelle.
"""
import sqlite3
import re

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Transactions de decembre 2025 a corriger
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE month = '2025-12'
""")

corrections = []
for row in cursor.fetchall():
    tx_id, date_op, month, label = row
    match = re.search(r'(\d{2})/(\d{2})/(\d{2})', label)
    if match:
        day, mon, year = match.groups()
        new_date = f'20{year}-{mon}-{day}'
        new_month = f'20{year}-{mon}'
        corrections.append({
            'id': tx_id,
            'old_date': str(date_op)[:10],
            'new_date': new_date,
            'old_month': month,
            'new_month': new_month,
            'label': label[:50]
        })

print(f'Transactions a corriger: {len(corrections)}')
print()

for corr in corrections:
    print(f"ID:{corr['id']} | {corr['old_date']} -> {corr['new_date']} | {corr['old_month']} -> {corr['new_month']}")
    print(f"   {corr['label']}")

print()
print('Application des corrections...')

for corr in corrections:
    cursor.execute("""
        UPDATE transactions
        SET date_op = ?, month = ?
        WHERE id = ?
    """, (corr['new_date'], corr['new_month'], corr['id']))

conn.commit()
print(f'OK! {len(corrections)} transactions corrigees!')

# Verification finale
print()
print('=== Verification ===')
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
