#!/usr/bin/env python3
"""
Test d'intégration des lignes fixes dans les calculs de summary
"""

import sys
sys.path.append('/mnt/c/Users/tkado/Documents/budget-app-starter-v2.3/backend')

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app import FixedLine, Config, get_split, split_amount

def test_integration_with_summary():
    """Test l'intégration des fixed lines dans les calculs"""
    print("🧪 Test intégration FixedLine avec Summary")
    print("=" * 45)
    
    # Utiliser la vraie base de données
    engine = create_engine("sqlite:///budget.db")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Ajouter quelques lignes de test avec catégories
        print("\n1. 📝 Création de lignes fixes de test...")
        
        test_lines = [
            FixedLine(
                label="Électricité EDF",
                amount=125.0,
                freq="mensuelle",
                split_mode="50/50",
                category="logement",
                active=True
            ),
            FixedLine(
                label="Assurance auto",
                amount=720.0,  # 60€/mois
                freq="annuelle",
                split_mode="clé",
                category="transport",
                active=True
            ),
            FixedLine(
                label="Internet Fibre",
                amount=45.0,
                freq="mensuelle",
                split_mode="50/50",
                category="services",
                active=True
            ),
            FixedLine(
                label="Netflix",
                amount=15.99,
                freq="mensuelle",
                split_mode="m1",  # 100% membre 1
                category="loisirs",
                active=True
            )
        ]
        
        # Nettoyer d'abord les anciennes lignes de test
        db.query(FixedLine).filter(FixedLine.label.like("%test%")).delete()
        db.query(FixedLine).filter(FixedLine.label.in_([
            "Électricité EDF", "Assurance auto", "Internet Fibre", "Netflix"
        ])).delete()
        
        for line in test_lines:
            db.add(line)
        db.commit()
        
        for line in test_lines:
            db.refresh(line)
            print(f"   ✅ {line.label} - {line.amount}€ ({line.freq}) - {line.category}")
        
        # 2. Récupérer la config
        print("\n2. ⚙️  Configuration de répartition...")
        config = db.query(Config).first()
        if not config:
            print("❌ Aucune configuration trouvée")
            return False
        
        r1, r2 = get_split(config)
        print(f"   • {config.member1}: {r1:.2%}")
        print(f"   • {config.member2}: {r2:.2%}")
        
        # 3. Calculer les répartitions comme dans summary()
        print("\n3. 🧮 Calcul des répartitions...")
        
        lines = db.query(FixedLine).filter(FixedLine.active == True).all()
        lines_total = 0.0
        lines_detail = []
        
        for ln in lines:
            # Conversion en montant mensuel
            if ln.freq == "mensuelle":
                mval = ln.amount
            elif ln.freq == "trimestrielle":
                mval = (ln.amount or 0.0) / 3.0
            else:  # annuelle
                mval = (ln.amount or 0.0) / 12.0
            
            # Calcul de la répartition
            p1, p2 = split_amount(mval, ln.split_mode, r1, r2, ln.split1, ln.split2)
            
            lines_total += mval
            lines_detail.append((ln.label, ln.category, mval, p1, p2))
            
            print(f"   • {ln.label}")
            print(f"     {ln.amount}€ ({ln.freq}) → {mval:.2f}€/mois")
            print(f"     Répartition ({ln.split_mode}): {config.member1}={p1:.2f}€, {config.member2}={p2:.2f}€")
            print()
        
        # 4. Statistiques par catégorie
        print("4. 📊 Statistiques par catégorie...")
        
        from collections import defaultdict
        stats_by_category = defaultdict(lambda: {"count": 0, "monthly_total": 0.0, "lines": []})
        
        for label, category, monthly, p1, p2 in lines_detail:
            stats_by_category[category]["count"] += 1
            stats_by_category[category]["monthly_total"] += monthly
            stats_by_category[category]["lines"].append((label, monthly, p1, p2))
        
        for category, stats in stats_by_category.items():
            print(f"\n   📁 {category.upper()}")
            print(f"      Lignes: {stats['count']}")
            print(f"      Total mensuel: {stats['monthly_total']:.2f}€")
            
            for line_label, monthly, p1, p2 in stats["lines"]:
                print(f"        • {line_label}: {monthly:.2f}€ ({p1:.2f}€ / {p2:.2f}€)")
        
        # 5. Totaux généraux
        print(f"\n5. 💰 Totaux généraux")
        print(f"   • Total mensuel: {lines_total:.2f}€")
        
        total_p1 = sum(p1 for _, _, _, p1, _ in lines_detail)
        total_p2 = sum(p2 for _, _, _, _, p2 in lines_detail)
        
        print(f"   • {config.member1}: {total_p1:.2f}€")
        print(f"   • {config.member2}: {total_p2:.2f}€")
        print(f"   • Vérification: {total_p1 + total_p2:.2f}€ = {lines_total:.2f}€")
        
        # 6. Test de l'endpoint stats
        print(f"\n6. 📈 Test simulation endpoint stats...")
        
        # Simuler la logique de l'endpoint /fixed-lines/stats/by-category
        monthly_stats = []
        for category, stats in stats_by_category.items():
            monthly_stats.append({
                "category": category,
                "count": stats["count"],
                "monthly_total": round(stats["monthly_total"], 2)
            })
        
        global_monthly_total = sum(s["monthly_total"] for s in monthly_stats)
        
        print(f"   API Response simulation:")
        print(f"   {{")
        print(f"     \"by_category\": {monthly_stats},")
        print(f"     \"global_monthly_total\": {global_monthly_total:.2f},")
        print(f"     \"total_lines\": {sum(s['count'] for s in monthly_stats)}")
        print(f"   }}")
        
        print(f"\n✅ Test d'intégration réussi!")
        print(f"   • {len(lines)} lignes fixes actives")
        print(f"   • {len(stats_by_category)} catégories utilisées")
        print(f"   • Total mensuel: {lines_total:.2f}€")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

def cleanup_test_data():
    """Nettoie les données de test"""
    print("\n🧹 Nettoyage des données de test...")
    
    engine = create_engine("sqlite:///budget.db")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Supprimer les lignes de test
        deleted = db.query(FixedLine).filter(FixedLine.label.in_([
            "Électricité EDF", "Assurance auto", "Internet Fibre", "Netflix"
        ])).delete()
        
        db.commit()
        print(f"✅ {deleted} ligne(s) de test supprimée(s)")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Test intégration FixedLine → Summary")
    
    try:
        success = test_integration_with_summary()
        
        # Proposer le nettoyage
        if success:
            response = input("\n❓ Supprimer les données de test ? (y/n): ").strip().lower()
            if response in ['y', 'yes', 'oui']:
                cleanup_test_data()
        
        exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrompu")
        exit(1)