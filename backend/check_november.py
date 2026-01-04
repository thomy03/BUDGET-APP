"""Analyser les transactions de novembre."""
import sqlite3
conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Voir les transactions de novembre triees par date
cursor.execute("""
    SELECT id, date_op, label
    FROM transactions
    WHERE month = '2025-11'
    ORDER BY date_op ASC
""")

print('=== Transactions novembre 2025 (triees par date) ===')
results = cursor.fetchall()
for row in results:
    print(f'ID:{row[0]} | {row[1]} | {row[2][:50]}')

print(f'\nTotal: {len(results)} transactions')

# Verifier la plage de dates
cursor.execute("""
    SELECT MIN(date_op), MAX(date_op)
    FROM transactions
    WHERE month = '2025-11'
""")
min_date, max_date = cursor.fetchone()
print(f'\nPlage: {min_date} a {max_date}')

conn.close()
