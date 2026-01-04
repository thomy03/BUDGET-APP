"""Analyse des transactions de décembre pour comprendre le problème de dates."""
import sqlite3

conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Toutes les transactions avec month = 2025-12
cursor.execute("""
    SELECT id, date_op, month, label, amount
    FROM transactions
    WHERE month = '2025-12'
    ORDER BY date_op DESC
""")

print("=== Transactions stockées en décembre 2025 ===")
print(f"{'ID':<6} {'date_op':<12} {'month':<8} {'Label':<60} {'Montant':<10}")
print("-" * 100)

december_tx = cursor.fetchall()
for row in december_tx:
    tx_id, date_op, month, label, amount = row
    print(f"{tx_id:<6} {str(date_op):<12} {month:<8} {label[:58]:<60} {amount:<10.2f}")

print(f"\nTotal: {len(december_tx)} transactions")

# Vérifier s'il y a des transactions en novembre avec des dates de libellé de décembre
cursor.execute("""
    SELECT id, date_op, month, label, amount
    FROM transactions
    WHERE month = '2025-11'
    AND (label LIKE '%/12/25%' OR label LIKE '%01/12/%' OR label LIKE '%02/12/%' OR label LIKE '%03/12/%' OR label LIKE '%04/12/%' OR label LIKE '%05/12/%' OR label LIKE '%06/12/%')
""")

print("\n=== Transactions novembre avec dates décembre dans le libellé ===")
november_with_dec = cursor.fetchall()
for row in november_with_dec:
    tx_id, date_op, month, label, amount = row
    print(f"{tx_id:<6} {str(date_op):<12} {month:<8} {label[:58]:<60} {amount:<10.2f}")

if not november_with_dec:
    print("Aucune trouvée")

# Vérifier la cohérence des dates dans les libellés vs date_op
print("\n=== Analyse de cohérence date libellé vs date_op ===")
cursor.execute("""
    SELECT id, date_op, month, label
    FROM transactions
    WHERE month IN ('2025-11', '2025-12')
    ORDER BY date_op DESC
    LIMIT 30
""")

import re
for row in cursor.fetchall():
    tx_id, date_op, month, label = row
    # Extraire la date du libellé
    match = re.search(r'(\d{2})/(\d{2})/(\d{2})', label)
    if match:
        day, mon, year = match.groups()
        label_date = f"20{year}-{mon}-{day}"
        db_date = str(date_op)[:10]

        status = "✓" if label_date == db_date else "❌ MISMATCH"
        if label_date != db_date:
            print(f"ID:{tx_id} | DB:{db_date} | Label:{label_date} | month:{month} | {status}")
            print(f"   -> {label[:70]}")

conn.close()
