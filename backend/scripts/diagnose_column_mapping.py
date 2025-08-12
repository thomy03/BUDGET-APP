#!/usr/bin/env python3
"""
Diagnostic du mapping des colonnes CSV
Analyse le problème d'erreur 400: "Colonnes manquantes: description, montant, compte"
"""
import pandas as pd
import re
import os
from typing import Dict, List, Tuple
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_column_name(col_name: str) -> str:
    """Normalise un nom de colonne pour le mapping"""
    if not col_name:
        return ""
    
    # Conversion en minuscules et suppression des espaces
    normalized = col_name.lower().strip()
    
    # Suppression des accents
    accent_map = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'ç': 'c', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ô': 'o', 'ö': 'o', 'î': 'i', 'ï': 'i'
    }
    
    for accented, plain in accent_map.items():
        normalized = normalized.replace(accented, plain)
    
    # Suppression des caractères spéciaux et espaces multiples
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized

def analyze_current_mapping() -> Dict[str, str]:
    """Analyse le mapping actuel dans normalize_cols()"""
    current_mapping = {
        'date opération': 'date_op',
        'date_operation': 'date_op',
        'date op': 'date_op',
        'date': 'date_op',
        'date valeur': 'date_valeur',
        'montant': 'amount',
        'crédit': 'amount',
        'débit': 'amount',
        'libellé': 'label',
        'libelle': 'label',
        'description': 'label',
        'catégorie': 'category',
        'categorie': 'category',
        'sous-catégorie': 'subcategory',
        'sous_categorie': 'subcategory',
        'subcategory': 'subcategory'
    }
    
    logger.info("Mapping actuel dans normalize_cols():")
    for old, new in current_mapping.items():
        logger.info(f"  '{old}' -> '{new}'")
    
    return current_mapping

def create_enhanced_mapping() -> Dict[str, str]:
    """Crée un mapping étendu pour plus de variations"""
    enhanced_mapping = {
        # Variations de Date
        'date operation': 'date_op',
        'date opération': 'date_op',
        'date_operation': 'date_op',
        'date op': 'date_op',
        'date': 'date_op',
        'date valeur': 'date_valeur',
        'date_valeur': 'date_valeur',
        'dateop': 'date_op',
        
        # Variations de Montant
        'montant': 'amount',
        'amount': 'amount',
        'credit': 'amount',
        'crédit': 'amount',
        'debit': 'amount',
        'débit': 'amount',
        'somme': 'amount',
        'valeur': 'amount',
        'prix': 'amount',
        
        # Variations de Description/Libellé
        'libelle': 'label',
        'libellé': 'label',
        'description': 'label',
        'label': 'label',
        'operation': 'label',
        'opération': 'label',
        'intitule': 'label',
        'intitulé': 'label',
        'reference': 'label',
        'référence': 'label',
        'memo': 'label',
        'mémo': 'label',
        
        # Variations de Compte
        'compte': 'account',
        'account': 'account',
        'numero compte': 'account',
        'numéro compte': 'account',
        'num compte': 'account',
        'compte bancaire': 'account',
        'nom compte': 'account',
        
        # Variations de Catégorie
        'categorie': 'category',
        'catégorie': 'category',
        'category': 'category',
        'type': 'category',
        'classe': 'category',
        
        # Variations de Sous-catégorie
        'sous categorie': 'subcategory',
        'sous-categorie': 'subcategory',
        'sous catégorie': 'subcategory',
        'sous-catégorie': 'subcategory',
        'subcategory': 'subcategory',
        'sub category': 'subcategory',
        'subtype': 'subcategory'
    }
    
    return enhanced_mapping

def test_column_recognition(test_columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """Teste la reconnaissance des colonnes avec le mapping étendu"""
    enhanced_mapping = create_enhanced_mapping()
    
    # Normalise les colonnes de test
    normalized_test_columns = [normalize_column_name(col) for col in test_columns]
    
    # Applique le mapping
    mapped_columns = {}
    unrecognized_columns = []
    
    for original, normalized in zip(test_columns, normalized_test_columns):
        if normalized in enhanced_mapping:
            mapped_columns[original] = enhanced_mapping[normalized]
        else:
            unrecognized_columns.append(original)
    
    return mapped_columns, unrecognized_columns

def simulate_csv_examples():
    """Simule différents formats de CSV bancaires"""
    csv_examples = {
        "BNP Paribas": ["Date opération", "Libellé", "Montant", "Compte"],
        "Crédit Agricole": ["Date", "Description", "Crédit", "Débit", "Numéro compte"],
        "LCL": ["Date valeur", "Intitulé", "Montant", "Compte bancaire"],
        "Société Générale": ["Date op", "Référence", "Somme", "Nom compte"],
        "Format générique": ["DATE", "DESCRIPTION", "MONTANT", "COMPTE"],
        "Export problématique": ["Date opération", "Libellé", "Montant", "Catégorie"]
    }
    
    logger.info("\n" + "="*60)
    logger.info("SIMULATION DE FORMATS CSV BANCAIRES")
    logger.info("="*60)
    
    for bank, columns in csv_examples.items():
        logger.info(f"\n📊 Format {bank}:")
        logger.info(f"Colonnes originales: {columns}")
        
        mapped, unrecognized = test_column_recognition(columns)
        
        logger.info("✅ Colonnes reconnues:")
        for original, target in mapped.items():
            logger.info(f"  '{original}' -> '{target}'")
        
        if unrecognized:
            logger.info("❌ Colonnes non reconnues:")
            for col in unrecognized:
                logger.info(f"  '{col}'")
        
        # Vérification des colonnes essentielles
        essential_targets = {'date_op', 'amount', 'label'}
        found_targets = set(mapped.values())
        missing_targets = essential_targets - found_targets
        
        if missing_targets:
            logger.warning(f"⚠️  Colonnes essentielles manquantes: {missing_targets}")
        else:
            logger.info("✅ Toutes les colonnes essentielles sont présentes")

def identify_error_source():
    """Identifie la source de l'erreur 'Colonnes manquantes: description, montant, compte'"""
    logger.info("\n" + "="*60)
    logger.info("ANALYSE DE L'ERREUR")
    logger.info("="*60)
    
    # L'erreur mentionne "description", "montant", "compte"
    # Mais le code cherche probablement 'date_op', 'amount', 'label'
    
    problematic_columns = ["description", "montant", "compte"]
    logger.info(f"Colonnes mentionnées dans l'erreur: {problematic_columns}")
    
    mapped, unrecognized = test_column_recognition(problematic_columns)
    logger.info(f"Mapping résultat: {mapped}")
    logger.info(f"Non reconnues: {unrecognized}")
    
    # Diagnostic du problème
    logger.info("\n🔍 DIAGNOSTIC:")
    
    if 'compte' in unrecognized:
        logger.error("❌ PROBLÈME: 'compte' n'est pas mappé vers une colonne attendue")
        logger.error("   Le mapping actuel ne contient pas de correspondance pour 'compte'")
    
    if mapped.get('description') == 'label':
        logger.info("✅ 'description' est correctement mappé vers 'label'")
    
    if mapped.get('montant') == 'amount':
        logger.info("✅ 'montant' est correctement mappé vers 'amount'")

def generate_fix_recommendations():
    """Génère des recommandations de correction"""
    logger.info("\n" + "="*60)
    logger.info("RECOMMANDATIONS DE CORRECTION")
    logger.info("="*60)
    
    recommendations = [
        "1. Ajouter le mapping 'compte' -> 'account' dans normalize_cols()",
        "2. Améliorer la normalisation des noms de colonnes (accents, espaces)",
        "3. Ajouter plus de variations pour les formats bancaires",
        "4. Implémenter une validation plus robuste des colonnes requises",
        "5. Améliorer les messages d'erreur avec les colonnes trouvées vs attendues"
    ]
    
    for rec in recommendations:
        logger.info(rec)
    
    # Mapping étendu proposé
    logger.info("\n📝 MAPPING ÉTENDU PROPOSÉ:")
    enhanced = create_enhanced_mapping()
    
    new_mappings = {
        'compte': 'account',
        'numero compte': 'account',
        'numéro compte': 'account',
        'nom compte': 'account',
        'compte bancaire': 'account'
    }
    
    for old, new in new_mappings.items():
        logger.info(f"  '{old}' -> '{new}'")

def main():
    """Fonction principale de diagnostic"""
    logger.info("DIAGNOSTIC DU MAPPING DES COLONNES CSV")
    logger.info("="*60)
    
    # 1. Analyse du mapping actuel
    analyze_current_mapping()
    
    # 2. Simulation des formats CSV
    simulate_csv_examples()
    
    # 3. Identification de la source de l'erreur
    identify_error_source()
    
    # 4. Recommandations de correction
    generate_fix_recommendations()
    
    logger.info("\n✅ Diagnostic terminé")

if __name__ == "__main__":
    main()