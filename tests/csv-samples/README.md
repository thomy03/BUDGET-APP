# Échantillons CSV – Budget Famille v2.3

Ce dossier contient 5 fichiers de test professionnels pour valider le système d'import CSV avec navigation automatique des mois.

## Fichiers de test

### 01_happy_path_janvier_2024.csv
- **Objectif** : Cas nominal, données parfaitement valides
- **Période** : Mono-mois (janvier 2024)
- **Contenu** : ~15 transactions familiales réalistes
- **Mois détecté** : 2024-01
- **Particularités** : Aucune - toutes les données respectent le format attendu

### 02_multi_mois_2024_Q1.csv
- **Objectif** : Test de navigation multi-mois
- **Période** : 3 mois (janvier, février, mars 2024)
- **Contenu** : ~24 transactions réparties sur Q1 2024
- **Mois détectés** : 2024-01, 2024-02, 2024-03
- **Particularités** : 
  - Inclut un transfert interne (Compte Courant → Livret A)
  - Teste la détection automatique des mois multiples
  - Valide la navigation entre mois dans l'interface

### 03_doublons_janvier_2024.csv
- **Objectif** : Test du système de détection/gestion des doublons
- **Période** : Mono-mois (janvier 2024) 
- **Contenu** : ~12 transactions avec 3 doublons exacts
- **Mois détecté** : 2024-01
- **Particularités** :
  - Doublons : EDF (×2), ALDI (×2), Salaire ACME (×2)
  - Teste la capacité du système à identifier et traiter les doublons
  - Permet de valider les alertes utilisateur

### 04_problemes_format.csv
- **Objectif** : Test de robustesse face aux erreurs de format
- **Période** : Multi-mois avec données corrompues
- **Contenu** : ~15 lignes avec erreurs volontaires diverses
- **Erreurs incluses** :
  - Décimales avec point au lieu de virgule (`-54.32`)
  - Caractères non numériques dans montant (`-12,3O`)
  - Champ compte vide
  - Colonnes manquantes (4 colonnes au lieu de 5)
  - Espaces comme séparateur de milliers (`2 500,00`)
  - Date invalide (`31/02/2024`)
  - Format de date ISO (`2024-03-05`)
  - Point-virgule dans description avec guillemets
  - Ligne avec colonnes supplémentaires
  - Espaces parasites autour des champs
  - Ligne quasi-vide
- **Usage** : Valider les messages d'erreur et la robustesse du parser

### 05_excel_fr_cp1252.csv
- **Objectif** : Test de compatibilité Excel français
- **Période** : Mono-mois (janvier 2024)
- **Contenu** : ~9 transactions avec caractères spéciaux français
- **Mois détecté** : 2024-01
- **Particularités** :
  - Ligne `sep=;` en première ligne (export Excel typique)
  - Encodage CP1252 souhaité (caractères É, è, –, ')
  - Terminaisons CRLF recommandées
  - Catégories françaises (Éducation, avec accents)

## Spécifications techniques

### Format CSV attendu
- **Séparateur** : `;` (point-virgule)
- **Décimales** : `,` (virgule française)
- **Colonnes** : `date;description;montant;compte;tag`
- **Format date** : `DD/MM/YYYY`
- **Encodage** : UTF-8 (sauf fichier 05 en CP1252)

### Conventions métier
- **Dépenses** : Montants négatifs (ex: `-950,00`)
- **Revenus** : Montants positifs (ex: `2500,00`)
- **Comptes** : Compte Courant, Carte Débit, Carte Crédit, Livret A
- **Catégories** : Logement, Courses, Revenus, Transport, Santé, Éducation, Loisirs, Épargne, Impôts

### Détection des mois
Le backend convertit les dates `DD/MM/YYYY` en format `YYYY-MM` pour :
- Grouper les transactions par mois
- Permettre la navigation mensuelle dans l'interface
- Détecter automatiquement les périodes couvertes

## Utilisation pour les tests

### Test d'import basique
1. Lancer le backend FastAPI
2. Importer `01_happy_path_janvier_2024.csv`
3. Vérifier que 15 transactions sont importées
4. Vérifier que le mois 2024-01 est détecté

### Test multi-mois
1. Importer `02_multi_mois_2024_Q1.csv`
2. Vérifier la détection des 3 mois : 2024-01, 2024-02, 2024-03
3. Tester la navigation entre les mois dans l'interface
4. Vérifier le traitement des transferts internes

### Test de doublons
1. Importer `03_doublons_janvier_2024.csv`
2. Vérifier la détection des 3 paires de doublons
3. Valider les alertes/confirmations utilisateur
4. Tester les options de traitement (ignorer/importer quand même)

### Test de robustesse
1. Importer `04_problemes_format.csv`
2. Vérifier que les erreurs sont correctement signalées
3. Valider que les lignes valides sont quand même importées
4. Tester les messages d'erreur détaillés

### Test Excel français
1. Importer `05_excel_fr_cp1252.csv`
2. Vérifier le traitement de la ligne `sep=;`
3. Valider l'encodage des caractères spéciaux
4. Tester avec un vrai export Excel si possible

## Script de génération

Le fichier `generate_samples.py` permet de :
- Régénérer tous les fichiers de test (`--regen`)
- Créer des échantillons aléatoires personnalisés (`--random`)
- Valider le format des fichiers existants (`--validate`)

```bash
# Régénérer tous les fichiers
python tests/csv-samples/generate_samples.py --regen

# Valider un fichier
python tests/csv-samples/generate_samples.py --validate tests/csv-samples/01_happy_path_janvier_2024.csv

# Créer un échantillon aléatoire
python tests/csv-samples/generate_samples.py --random custom.csv --random-months 2
```

## Résultats attendus

### Comptages par fichier
- **Fichier 01** : 15 transactions, 1 mois (2024-01)
- **Fichier 02** : 24 transactions, 3 mois (2024-01,02,03)  
- **Fichier 03** : 12 transactions, 3 doublons détectés
- **Fichier 04** : ~8 lignes valides, ~7 erreurs signalées
- **Fichier 05** : 9 transactions, caractères spéciaux préservés

### Validation de l'intégration
- [ ] Import sans erreur pour fichiers 01, 02, 03, 05
- [ ] Messages d'erreur clairs pour fichier 04
- [ ] Navigation mensuelle fonctionnelle
- [ ] Détection automatique des doublons
- [ ] Préservation des caractères français
- [ ] Performance acceptable (< 2s par fichier)