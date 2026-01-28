#!/usr/bin/env python3
"""
Script pour réimporter le fichier CSV d'octobre avec toutes les transactions
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DB_PATH = Path(__file__).parent / "budget.db"
CSV_PATH = Path("/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/export-operations-05-11-2025_21-43-35.csv")

print(f"📂 Base de données : {DB_PATH}")
print(f"📂 Fichier CSV : {CSV_PATH}")

if not CSV_PATH.exists():
    print(f"❌ Fichier CSV introuvable : {CSV_PATH}")
    sys.exit(1)

# Connexion à la base de données
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

print("\n🔍 État actuel de la base de données :")
result = session.execute(text("""
    SELECT
        COUNT(*) as total,
        MIN(date_op) as min_date,
        MAX(date_op) as max_date
    FROM transactions
    WHERE date_op LIKE '2025-10%'
""")).fetchone()
print(f"   Octobre 2025 : {result[0]} transactions (du {result[1]} au {result[2]})")

# Lecture du CSV
print(f"\n📖 Lecture du fichier CSV...")
transactions_csv = []
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        date_op = row['dateOp']
        if date_op.startswith('2025-10'):
            transactions_csv.append({
                'date_op': date_op,
                'label': row['label'],
                'amount': float(row['amount'].replace(',', '.').replace(' ', '')),
                'category': row.get('category', ''),
                'category_parent': row.get('categoryParent', ''),
            })

print(f"   Trouvé {len(transactions_csv)} transactions d'octobre dans le CSV")

# Compter les transactions par date
from collections import Counter
dates_count = Counter(t['date_op'] for t in transactions_csv)
print(f"\n📊 Répartition par date dans le CSV :")
for date in sorted(dates_count.keys()):
    print(f"   {date}: {dates_count[date]} transactions")

# Vérifier les transactions manquantes (1-9 octobre)
missing_dates = [d for d in dates_count.keys() if d.split('-')[2] in [f'{i:02d}' for i in range(1, 10)]]
if missing_dates:
    total_missing = sum(dates_count[d] for d in missing_dates)
    print(f"\n⚠️  {total_missing} transactions du 1-9 octobre dans le CSV mais pas en BDD")
    print(f"   Dates concernées : {', '.join(sorted(missing_dates))}")

# Mode ANNULE ET REMPLACE pour octobre
print(f"\n🗑️  Suppression des transactions d'octobre existantes...")
session.execute(text("DELETE FROM transactions WHERE date_op LIKE '2025-10%'"))
session.commit()
print(f"   ✅ Transactions supprimées")

# Insertion des nouvelles transactions
print(f"\n💾 Insertion de {len(transactions_csv)} transactions...")
insert_count = 0
for tx in transactions_csv:
    try:
        session.execute(text("""
            INSERT INTO transactions (date_op, label, amount, category, category_parent, month, tags, exclude)
            VALUES (:date_op, :label, :amount, :category, :category_parent, :month, '', 0)
        """), {
            'date_op': tx['date_op'],
            'label': tx['label'],
            'amount': tx['amount'],
            'category': tx['category'],
            'category_parent': tx['category_parent'],
            'month': tx['date_op'][:7]  # YYYY-MM
        })
        insert_count += 1
    except Exception as e:
        print(f"   ⚠️  Erreur insertion : {e}")

session.commit()
print(f"   ✅ {insert_count} transactions insérées")

# Vérification finale
print(f"\n✅ Vérification finale :")
result = session.execute(text("""
    SELECT
        COUNT(*) as total,
        MIN(date_op) as min_date,
        MAX(date_op) as max_date
    FROM transactions
    WHERE date_op LIKE '2025-10%'
""")).fetchone()
print(f"   Octobre 2025 : {result[0]} transactions (du {result[1]} au {result[2]})")

if result[0] == len(transactions_csv):
    print(f"\n🎉 Succès ! Toutes les {result[0]} transactions ont été importées")
else:
    print(f"\n⚠️  Attention : {len(transactions_csv)} dans CSV vs {result[0]} en BDD")

session.close()
