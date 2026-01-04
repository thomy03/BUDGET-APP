"""Analyse transactions decembre 2025."""
import sqlite3
import re

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE month = '2025-12'
    ORDER BY date_op DESC
""")

print('=== Transactions decembre 2025 ===')
for row in cursor.fetchall():
    tx_id, date_op, month, label = row
    match = re.search(r'(\d{2})/(\d{2})/(\d{2})', label)
    if match:
        day, mon, year = match.groups()
        label_date = f'20{year}-{mon}-{day}'
        status = "OK" if str(date_op)[:10] == label_date else "MISMATCH"
        print(f'ID:{tx_id} | DB:{date_op} | Label:{label_date} | {status} | {label[:45]}')
    else:
        print(f'ID:{tx_id} | DB:{date_op} | Pas de date | {label[:45]}')

conn.close()
