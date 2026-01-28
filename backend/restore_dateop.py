"""
Restaurer les dates depuis le fichier CSV original.
Les transactions en base ont été modifiées avec les dates du libellé,
mais nous voulons utiliser la colonne dateOp du CSV.
"""
import sqlite3
import pandas as pd

# Lire le CSV original
csv_file = '../export-operations-05-11-2025_21-43-35.csv'
df = pd.read_csv(csv_file, sep=';', encoding='utf-8-sig')

print(f"CSV lu: {len(df)} lignes")
print(f"Colonnes: {df.columns.tolist()}")

# Se connecter a la base
conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Supprimer les doublons d'abord
print("\n=== Suppression des doublons ===")
cursor.execute("""
    DELETE FROM transactions
    WHERE id NOT IN (
        SELECT MIN(id) FROM transactions
        GROUP BY label, amount, month
    )
""")
deleted = cursor.rowcount
conn.commit()
print(f"Doublons supprimes: {deleted}")

# Pour chaque ligne du CSV, mettre a jour la transaction correspondante
updated = 0
not_found = 0

for idx, row in df.iterrows():
    date_op = row.get('dateOp')
    label = row.get('label')
    amount = row.get('amount')

    if pd.isna(date_op) or pd.isna(label):
        continue

    # Convertir le montant
    if isinstance(amount, str):
        amount = float(amount.replace(',', '.').replace(' ', ''))

    # Parser la date
    date_parsed = pd.to_datetime(date_op, errors='coerce')
    if pd.isna(date_parsed):
        continue

    date_str = date_parsed.strftime('%Y-%m-%d')
    month_str = date_parsed.strftime('%Y-%m')

    # Chercher la transaction par label et montant
    cursor.execute("""
        SELECT id, date_op, month FROM transactions
        WHERE label = ? AND ABS(amount - ?) < 0.01
        LIMIT 1
    """, (label, amount))

    result = cursor.fetchone()
    if result:
        tx_id, old_date, old_month = result
        if str(old_date)[:10] != date_str or old_month != month_str:
            cursor.execute("""
                UPDATE transactions
                SET date_op = ?, month = ?
                WHERE id = ?
            """, (date_str, month_str, tx_id))
            updated += 1
    else:
        not_found += 1

conn.commit()

print(f"\nTransactions mises a jour: {updated}")
print(f"Non trouvees: {not_found}")

# Verification finale
print("\n=== Verification finale ===")
cursor.execute("""
    SELECT month, COUNT(*) as cnt, MIN(date_op), MAX(date_op)
    FROM transactions
    WHERE month >= '2025-09'
    GROUP BY month
    ORDER BY month
""")
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} transactions ({row[2]} a {row[3]})')

conn.close()
print("\nTermine.")
