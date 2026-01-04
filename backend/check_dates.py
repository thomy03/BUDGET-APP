"""Script pour analyser les problèmes de dates dans les transactions"""
import sqlite3

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Voir les transactions où date_op ne correspond pas à month
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE substr(date_op, 1, 7) != month
    ORDER BY date_op DESC
    LIMIT 30
""")
print('=== Transactions avec date_op et month desynchronises ===')
results = cursor.fetchall()
for row in results:
    print(f'ID:{row[0]} | date_op:{row[1]} | month:{row[2]} | {row[3][:55]}')

# Compter le total
cursor.execute("""
    SELECT COUNT(*)
    FROM transactions
    WHERE substr(date_op, 1, 7) != month
""")
total = cursor.fetchone()[0]
print(f'\nTotal transactions desynchronisees: {total}')

# Voir les transactions de decembre 2025 avec les vraies dates dans le libelle
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE month = '2025-12'
""")
print('\n=== Toutes les transactions de decembre 2025 ===')
for row in cursor.fetchall():
    print(f'ID:{row[0]} | date_op:{row[1]} | month:{row[2]} | {row[3][:55]}')

# Voir les transactions de novembre 2025
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE month = '2025-11'
    ORDER BY date_op DESC
    LIMIT 15
""")
print('\n=== Transactions novembre 2025 (15 premieres) ===')
for row in cursor.fetchall():
    print(f'ID:{row[0]} | date_op:{row[1]} | month:{row[2]} | {row[3][:55]}')

conn.close()
