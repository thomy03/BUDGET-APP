# Système d'Import CSV - Mode ANNULE ET REMPLACE

## Vue d'ensemble

Le système d'import a été refactorisé le 07/09/2025 pour implémenter un mode "ANNULE ET REMPLACE" qui garantit l'absence de doublons lors d'imports multiples.

## Comportement

### Avant (Problématique)
- Chaque import vérifiait les doublons transaction par transaction
- Les imports multiples créaient des doublons malgré la vérification
- Exemple : 127 lignes CSV → 458 transactions après plusieurs imports
- Solde incorrect : -2806.14€ au lieu de -816.10€

### Après (Solution)
- **Mode ANNULE ET REMPLACE** : Suppression automatique de TOUTES les transactions du mois avant import
- Import propre des nouvelles transactions sans vérification de doublons
- Résultat garanti : 127 lignes CSV = 127 transactions en base
- Solde correct : -816.10€

## Implémentation Technique

### Fichier : `backend/routers/import_export.py`

```python
# ANNULE ET REMPLACE: Supprimer les transactions existantes pour les mois détectés
logger.info(f"🔄 Mode ANNULE ET REMPLACE pour les mois: {months_list}")
for month in months_list:
    existing_count = db.query(Transaction).filter(
        Transaction.month == month
    ).count()
    
    if existing_count > 0:
        logger.info(f"  ❌ Suppression de {existing_count} transactions existantes pour {month}")
        db.query(Transaction).filter(
            Transaction.month == month
        ).delete()

db.flush()  # Appliquer les suppressions avant d'ajouter les nouvelles
```

## Format de Date Français

### Problème Résolu
- Les dates au format DD/MM/YY (ex: 01/08/25) étaient mal interprétées
- 01/08/25 était lu comme 1er janvier au lieu du 1er août

### Solution
```python
# Parsing avec format français
date_op = pd.to_datetime(date_str, format='%d/%m/%y', errors='coerce')
```

## Flux d'Import

1. **Upload du fichier CSV**
2. **Détection des mois** dans le fichier
3. **Suppression** de toutes les transactions existantes pour ces mois
4. **Import** des nouvelles transactions
5. **Commit** en base de données

## Avantages

- ✅ **Idempotent** : Importer plusieurs fois = même résultat
- ✅ **Prédictible** : Nombre de transactions = nombre de lignes CSV
- ✅ **Simple** : Pas de logique complexe de détection de doublons
- ✅ **Performant** : Une seule suppression en masse au lieu de vérifications ligne par ligne

## Messages Utilisateur

### Avant
```
Import réussi : 458 nouvelles transactions (127 doublons ignorés)
```

### Après
```
Import réussi : 127 transactions importées (mode annule et remplace)
```

## Tests

### Script de Test : `backend/test_annule_remplace.py`

Vérifie que :
1. Premier import : 127 transactions créées
2. Deuxième import : toujours 127 transactions (pas de doublons)
3. Somme totale : -816.10€ (inchangée)

## Configuration Frontend

Le frontend n'a pas besoin de modification. Le message d'import affiche automatiquement le mode "annule et remplace" pour informer l'utilisateur.

## Cas d'Usage

### Import mensuel régulier
- L'utilisateur exporte son relevé bancaire mensuel
- Import dans l'application
- Les anciennes données du mois sont remplacées par les nouvelles
- Parfait pour corriger des erreurs ou mettre à jour avec le relevé définitif

### Import multi-mois
- Le système détecte tous les mois présents dans le CSV
- Chaque mois détecté est traité en mode annule et remplace
- Exemple : CSV avec juillet et août → suppression et remplacement des deux mois

## Limitations Connues

- Le système supprime TOUTES les transactions du mois, même celles ajoutées manuellement
- Recommandation : Toujours importer depuis les relevés bancaires officiels

## Historique des Modifications

- **07/09/2025** : Implémentation initiale du mode ANNULE ET REMPLACE
- **07/09/2025** : Correction du parsing des dates françaises DD/MM/YY
- **07/09/2025** : Suppression de la logique de détection de doublons (obsolète)