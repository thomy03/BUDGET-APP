"""
Script pour importer les tags existants des transactions dans le système ML.
Ceci permet au système d'apprendre des 734 transactions déjà tagguées.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
import re
from collections import defaultdict
from datetime import datetime

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'budget.db')
PATTERNS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'learned_patterns.json')

def normalize_merchant_name(label: str) -> str:
    """
    Normalise le nom du marchand pour créer des patterns cohérents.
    Supprime les dates, numéros de carte, préfixes de paiement, etc.
    """
    if not label:
        return ""

    normalized = label.upper().strip()

    # Patterns à supprimer (dans l'ordre)
    patterns_to_remove = [
        r'^CB\s+',  # Carte Bleue prefix
        r'^CARTE\s+',  # CARTE prefix
        r'^VIR\s+',  # Virement prefix
        r'^PRLV\s+',  # Prelevement prefix
        r'^CHQ\s+',  # Cheque prefix
        r'\d{2}/\d{2}/\d{2,4}',  # Full date DD/MM/YY or DD/MM/YYYY anywhere
        r'\d{2}/\d{2}',  # Short date DD/MM anywhere
        r'\d{1,2}H\d{2}',  # Time patterns like 14H30
        r'\d+\.\d{2}\s*$',  # Amount patterns at end like 25.99
        r'CB\*\d+',  # Card number patterns CB*1234
        r'\s+\d+$',  # Trailing numbers
        r'\s{2,}',  # Multiple spaces
    ]

    for pattern in patterns_to_remove:
        normalized = re.sub(pattern, ' ', normalized)

    # Nettoyer les espaces
    normalized = ' '.join(normalized.split()).strip()

    return normalized

def load_transactions():
    """Charge toutes les transactions avec des tags valides."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Récupérer les transactions avec tags (hors "Non classé" et vides)
    cursor.execute("""
        SELECT id, label, tags, amount
        FROM transactions
        WHERE tags IS NOT NULL
        AND tags != ''
        AND tags != 'Non classé'
        AND tags != 'Non classe'
    """)

    transactions = cursor.fetchall()
    conn.close()

    return transactions

def create_patterns(transactions):
    """
    Crée des patterns à partir des transactions existantes.
    Groupe par pattern normalisé + tag et compte les occurrences.
    """
    # Structure: {normalized_pattern: {tag: [transaction_ids]}}
    pattern_groups = defaultdict(lambda: defaultdict(list))

    for tx_id, label, tags, amount in transactions:
        normalized = normalize_merchant_name(label)

        if not normalized or len(normalized) < 3:
            continue

        # Prendre le premier tag si multiples (séparés par virgule)
        tag = tags.split(',')[0].strip() if tags else None

        if tag and tag not in ['Non classé', 'Non classe']:
            pattern_groups[normalized][tag].append({
                'id': tx_id,
                'label': label,
                'amount': amount
            })

    return pattern_groups

def generate_ml_patterns(pattern_groups, min_occurrences=1):
    """
    Génère les patterns ML avec scores de confiance.
    Nécessite au moins min_occurrences pour créer un pattern.
    """
    patterns = {}
    stats = {
        'total_patterns': 0,
        'single_tag_patterns': 0,
        'multi_tag_patterns': 0,
        'skipped_low_count': 0
    }

    for normalized_pattern, tag_data in pattern_groups.items():
        # Trouver le tag dominant (celui avec le plus d'occurrences)
        tag_counts = {tag: len(txs) for tag, txs in tag_data.items()}
        total_count = sum(tag_counts.values())

        if total_count < min_occurrences:
            stats['skipped_low_count'] += 1
            continue

        dominant_tag = max(tag_counts, key=tag_counts.get)
        dominant_count = tag_counts[dominant_tag]

        # Calculer le score de confiance
        # 100% si tous les mêmes tags, moins si mixte
        confidence = dominant_count / total_count

        # Bonus si beaucoup d'occurrences
        if dominant_count >= 5:
            confidence = min(1.0, confidence + 0.1)
        elif dominant_count >= 3:
            confidence = min(1.0, confidence + 0.05)

        patterns[normalized_pattern] = {
            'suggested_tag': dominant_tag,
            'correction_count': dominant_count,
            'confidence_score': round(confidence, 3),
            'last_updated': datetime.now().isoformat(),
            'source': 'import_existing',
            'all_tags': tag_counts
        }

        stats['total_patterns'] += 1
        if len(tag_counts) == 1:
            stats['single_tag_patterns'] += 1
        else:
            stats['multi_tag_patterns'] += 1

    return patterns, stats

def save_patterns(patterns):
    """Sauvegarde les patterns dans le fichier JSON."""
    # Créer le dossier data si nécessaire
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)

    # Charger les patterns existants
    existing_patterns = {}
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, 'r', encoding='utf-8') as f:
                existing_patterns = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing_patterns = {}

    # Fusionner avec les nouveaux patterns
    # Les nouveaux patterns écrasent les anciens si même clé
    merged_patterns = {**existing_patterns, **patterns}

    # Sauvegarder
    with open(PATTERNS_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged_patterns, f, ensure_ascii=False, indent=2)

    return len(existing_patterns), len(merged_patterns)

def main():
    print("=" * 60)
    print("IMPORT DES TAGS EXISTANTS VERS LE SYSTEME ML")
    print("=" * 60)
    print()

    # 1. Charger les transactions
    print("[1/4] Chargement des transactions tagguees...")
    transactions = load_transactions()
    print(f"   -> {len(transactions)} transactions avec tags trouvees")
    print()

    if not transactions:
        print("ERREUR: Aucune transaction avec tag trouvee!")
        return

    # 2. Creer les patterns
    print("[2/4] Creation des patterns normalises...")
    pattern_groups = create_patterns(transactions)
    print(f"   -> {len(pattern_groups)} patterns uniques identifies")
    print()

    # 3. Generer les patterns ML
    print("[3/4] Generation des patterns ML...")
    patterns, stats = generate_ml_patterns(pattern_groups, min_occurrences=1)
    print(f"   -> {stats['total_patterns']} patterns crees")
    print(f"   -> {stats['single_tag_patterns']} avec tag unique (100% confiance)")
    print(f"   -> {stats['multi_tag_patterns']} avec tags multiples (confiance variable)")
    print(f"   -> {stats['skipped_low_count']} ignores (occurrences insuffisantes)")
    print()

    # 4. Sauvegarder
    print("[4/4] Sauvegarde des patterns...")
    old_count, new_count = save_patterns(patterns)
    print(f"   -> Avant: {old_count} patterns")
    print(f"   -> Apres: {new_count} patterns")
    print()

    # 5. Afficher quelques exemples
    print("Exemples de patterns crees:")
    print("-" * 60)
    for i, (pattern, data) in enumerate(list(patterns.items())[:10]):
        print(f"   {pattern[:40]:<40} -> {data['suggested_tag']:<15} ({data['correction_count']}x, {data['confidence_score']*100:.0f}%)")

    if len(patterns) > 10:
        print(f"   ... et {len(patterns) - 10} autres patterns")
    print()

    print("=" * 60)
    print("IMPORT TERMINE AVEC SUCCES!")
    print("=" * 60)
    print()
    print("IMPORTANT: Redemarrez le backend pour charger les nouveaux patterns:")
    print("    cd backend && python app.py")
    print()

if __name__ == "__main__":
    main()
