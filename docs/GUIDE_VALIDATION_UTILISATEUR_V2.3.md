# Guide de Validation Utilisateur – Budget Famille v2.3

## RÈGLE ABSOLUE - VALIDATION OBLIGATOIRE
**Conformément au fichier CLAUDE.md du projet, l'utilisateur principal DOIT valider cette fonctionnalité avant toute finalisation. Cette règle est non négociable.**

---

## 1. OBJECTIF ET PÉRIMÈTRE

### Fonctionnalité à valider : Import CSV Intelligent
- ✅ Détection automatique du mois dans les fichiers CSV
- ✅ Navigation automatique vers le mois détecté
- ✅ Gestion des doublons (internes au fichier + données existantes)
- ✅ Sélection multi-mois avec interface dédiée
- ✅ Toasts intelligents avec actions rapides
- ✅ Architecture backend modernisée avec types complets

### Couverture des tests
- **Scénarios nominaux** : Import réussi, navigation automatique
- **Gestion d'erreurs** : Fichiers corrompus, formats non supportés
- **Cas limites** : Doublons, multi-mois, encodages différents
- **Performance** : Import de volumes moyens
- **Expérience utilisateur** : Toasts, actions rapides, feedbacks

---

## 2. PRÉREQUIS ET PRÉPARATION

### Environnement requis
- **OS** : Windows 10/11
- **Python** : Python 3.8+ (vérifier avec `python3 --version`)
- **Droits** : Écriture dans le dossier du projet
- **Réseau** : Aucun (application locale)

### Données de test fournies
📁 **Dossier** : `/tests/csv-samples/`
- `01_happy_path_janvier_2024.csv` → Cas nominal (15 transactions)
- `02_multi_mois_2024_Q1.csv` → Multi-mois Q1 2024 (24 transactions)
- `03_doublons_janvier_2024.csv` → Avec doublons (12 transactions, 3 doublons)
- `04_problemes_format.csv` → Erreurs de format volontaires
- `05_excel_fr_cp1252.csv` → Encodage français Excel (9 transactions)

### Configuration de test
- **Base de données** : Utiliser un profil/environnement de test (jamais vos données personnelles)
- **Sauvegarde** : Créer une sauvegarde avant de commencer
- **Réinitialisation** : Possibilité de vider la base entre scénarios

---

## 3. INSTRUCTIONS DE LANCEMENT

### Option A : Script automatique (recommandé)
```bash
# Si un script existe
double-cliquer sur : start_test.bat ou run_app.bat
```

### Option B : Lancement manuel
```bash
# 1. Ouvrir PowerShell dans le dossier du projet
cd "C:\Users\tkado\OneDrive\Documents\fichiers perso\fichier thomas et iana\budget-app-starter-v2.3"

# 2. Créer environnement virtuel
python3 -m venv .venv

# 3. Activer l'environnement
.venv\Scripts\Activate.ps1

# 4. Installer dépendances
pip install -r requirements.txt

# 5. Lancer le backend
python3 backend/app_simple.py

# 6. Dans un autre terminal, lancer le frontend
cd frontend
npm run dev

# 7. Ouvrir l'URL affichée (ex: http://localhost:3000)
```

### Vérification du lancement
- ✅ Backend démarré sans erreur
- ✅ Frontend accessible dans le navigateur
- ✅ Page d'accueil s'affiche correctement
- ✅ Menu "Importer CSV" visible

---

## 4. PROTOCOLE DE TEST PAR SCÉNARIO

### RÈGLES DE CONDUITE
1. **Chronométrer** les imports (performance)
2. **Capturer** les screenshots des toasts et pages
3. **Noter** tous les messages affichés
4. **Réinitialiser** la base entre scénarios si demandé
5. **Respecter** l'ordre des scénarios

---

### SCÉNARIO 1 : Parcours heureux simple
**🎯 Objectif** : Valider détection automatique d'un mois unique + navigation auto

**📋 Préparation** : Base vide (réinitialiser si nécessaire)

**📝 Étapes** :
1. Aller sur "Importer CSV"
2. Sélectionner `01_happy_path_janvier_2024.csv`
3. Lancer l'import
4. Chronométrer le temps

**✅ Résultats attendus** :
- Toast affiché : "15 transactions importées, 0 doublon"
- Navigation automatique vers Janvier 2024
- Action rapide "Voir le mois" disponible dans le toast
- Toutes les 15 transactions visibles dans le mois
- Temps d'import < 2 secondes

**📊 À noter** :
- Temps exact : _____ secondes
- Toast exact : "_____"
- Navigation automatique : OUI / NON
- Actions disponibles : "_____"

---

### SCÉNARIO 2 : Doublons internes au fichier
**🎯 Objectif** : Vérifier que les doublons dans le même CSV ne sont pas importés deux fois

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `03_doublons_janvier_2024.csv`
2. Observer le toast affiché
3. Vérifier les compteurs

**✅ Résultats attendus** :
- Toast : "9 transactions importées, 3 doublons ignorés"
- Seules 9 transactions uniques importées (pas 12)
- Action "Détails des doublons" disponible (si implémentée)
- Navigation vers Janvier 2024

**📊 À noter** :
- Nombre importé : _____ / 9 attendu
- Nombre de doublons : _____ / 3 attendu
- Détails des doublons visibles : OUI / NON

---

### SCÉNARIO 3 : Idempotence (réimport)
**🎯 Objectif** : Réimporter le même fichier ne doit créer aucune nouvelle transaction

**📋 Préparation** : Avoir importé le fichier du Scénario 1

**📝 Étapes** :
1. Réimporter exactement `01_happy_path_janvier_2024.csv`
2. Observer le message

**✅ Résultats attendus** :
- Toast : "0 transaction importée, 15 doublons (déjà existants)"
- Aucune nouvelle transaction dans le mois
- Compteurs inchangés
- Pas de duplication visible

**📊 À noter** :
- Message exact : "_____"
- Nombre total de transactions dans le mois : _____ (doit rester 15)

---

### SCÉNARIO 4 : Multi-mois avec sélection simple
**🎯 Objectif** : Interface de sélection multi-mois + import partiel

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `02_multi_mois_2024_Q1.csv`
2. Observer l'interface de sélection
3. Cocher UNIQUEMENT "Février 2024"
4. Lancer l'import
5. Vérifier la navigation

**✅ Résultats attendus** :
- Interface de sélection affiche : Janvier, Février, Mars 2024
- Seul Février contient des transactions après import
- Navigation automatique vers Février 2024
- Toast indique le nombre importé pour le mois sélectionné

**📊 À noter** :
- Mois détectés : "_____"
- Mois sélectionné : Février
- Transactions importées : _____ 
- Navigation automatique vers : _____

---

### SCÉNARIO 5 : Multi-mois avec sélection multiple
**🎯 Objectif** : Import de plusieurs mois simultanément

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `02_multi_mois_2024_Q1.csv`
2. Cocher "Janvier 2024" ET "Mars 2024"
3. Lancer l'import
4. Vérifier les deux mois

**✅ Résultats attendus** :
- Janvier ET Mars contiennent des transactions
- Février reste vide
- Navigation automatique ou choix proposé
- Toast reflète l'import des 2 mois

**📊 À noter** :
- Transactions en Janvier : _____
- Transactions en Mars : _____
- Février vide : OUI / NON
- Navigation vers : _____

---

### SCÉNARIO 6 : Gestion des erreurs de format
**🎯 Objectif** : Messages d'erreur clairs, pas de crash

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `04_problemes_format.csv`
2. Observer les messages d'erreur
3. Vérifier si des lignes valides sont importées

**✅ Résultats attendus** :
- Messages d'erreur détaillés et compréhensibles
- Application ne plante pas
- Lignes valides importées malgré les erreurs
- Possibilité de corriger et réimporter

**📊 À noter** :
- Message d'erreur principal : "_____"
- Nombre de lignes valides importées : _____
- Erreurs spécifiques mentionnées : "_____"

---

### SCÉNARIO 7 : Encodage français (Excel)
**🎯 Objectif** : Support des caractères spéciaux français

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `05_excel_fr_cp1252.csv`
2. Vérifier l'affichage des accents
3. Contrôler les montants avec virgules

**✅ Résultats attendus** :
- Caractères É, è, –, ' correctement affichés
- Montants avec virgules française reconnus
- 9 transactions importées
- Navigation vers Janvier 2024

**📊 À noter** :
- Accents préservés : OUI / NON
- Montants corrects : OUI / NON
- Transactions importées : _____ / 9 attendu

---

### SCÉNARIO 8 : Actions rapides dans les toasts
**🎯 Objectif** : Vérifier les actions "Voir le mois", "Détails", etc.

**📋 Préparation** : Base vide

**📝 Étapes** :
1. Importer `01_happy_path_janvier_2024.csv`
2. Dans le toast, cliquer sur "Voir le mois"
3. Réimporter le même fichier
4. Dans le toast, cliquer sur "Détails" (si disponible)

**✅ Résultats attendus** :
- "Voir le mois" → Navigation directe vers Janvier 2024
- "Détails" → Écran de rapport d'import ou doublons
- Actions cliquables pendant la durée du toast
- Toast reste visible suffisamment longtemps

**📊 À noter** :
- Actions disponibles : "_____"
- "Voir le mois" fonctionne : OUI / NON
- "Détails" disponible : OUI / NON
- Durée d'affichage du toast : _____ secondes

---

## 5. CRITÈRES D'ACCEPTATION FINAUX

### ✅ CRITÈRES FONCTIONNELS OBLIGATOIRES
- [ ] **Détection automatique** : 100% des fichiers mono-mois ouvrent le bon mois
- [ ] **Multi-mois** : Interface de sélection s'affiche pour les CSV multi-périodes
- [ ] **Doublons internes** : Aucun doublon interne au CSV n'est importé
- [ ] **Idempotence** : Réimporter ne crée aucune nouvelle transaction
- [ ] **Navigation automatique** : L'app navigue vers le(s) mois importé(s)
- [ ] **Toasts et actions** : Messages clairs + actions rapides fonctionnelles
- [ ] **Gestion d'erreurs** : Messages explicites, pas de crash

### ✅ CRITÈRES DE PERFORMANCE
- [ ] **Petits fichiers** (15-25 lignes) : < 2 secondes
- [ ] **Fichiers moyens** (100+ lignes) : < 5 secondes  
- [ ] **Interface réactive** : Pas de gel, feedback visuel

### ✅ CRITÈRES DE QUALITÉ
- [ ] **Robustesse** : Formats CSV variés supportés (délimiteurs, encodages)
- [ ] **UX** : Messages compréhensibles, navigation intuitive
- [ ] **Intégrité** : Données importées cohérentes avec le fichier source

---

## 6. JOURNAL DE VALIDATION

### Template par scénario :
```
SCÉNARIO N° : ____
FICHIER UTILISÉ : ____
ÉTAT BASE : Vide / Avec données
RÉSULTAT : OK / KO / À CLARIFIER
TEMPS D'IMPORT : ____ secondes
TOAST AFFICHÉ : "____"
NAVIGATION AUTO : OUI / NON → ____
COMMENTAIRES : ____
CAPTURE D'ÉCRAN : [Joindre si nécessaire]
```

---

## 7. PROCESSUS DE VALIDATION FINALE

### 🔴 VALIDATION OBLIGATOIRE (RÈGLE CLAUDE.md)
L'utilisateur principal doit fournir un **GO/NOGO formel** incluant :

#### Déclaration de validation :
> "Je confirme avoir exécuté les 8 scénarios décrits dans ce guide de validation.
> Je confirme que les critères d'acceptation de la section 5 sont respectés.
> J'autorise la mise en production de la fonctionnalité d'import CSV v2.3."
>
> **Date** : ____________
> **Nom** : ____________  
> **Signature** : ____________

### En cas de problèmes détectés :
1. **Créer un ticket** par problème avec :
   - Titre précis (ex: "[Import CSV] Navigation vers mauvais mois")
   - Scénario concerné
   - Fichier de test utilisé
   - Résultat attendu vs observé
   - Capture d'écran
   - Sévérité : BLOQUANT / MAJEUR / MINEUR

2. **Priorisation** :
   - BLOQUANT → Release impossible
   - MAJEUR → À corriger avant release
   - MINEUR → Peut être reporté

---

## 8. CONTACTS ET SUPPORT

### En cas de problème technique
- **Impossible de lancer l'application** → Contacter l'équipe dev
- **Fichiers de test corrompus** → Utiliser `generate_samples.py --regen`
- **Doutes sur un comportement** → Noter et continuer, clarifier en debrief

### Debrief post-validation
- **Durée** : 15-30 minutes
- **Participants** : Product Owner + Utilisateur principal
- **Ordre du jour** : 
  - Revue des scénarios testés
  - Priorisation des tickets ouverts
  - Décision GO/NOGO finale

---

## 9. CHECKLIST RAPIDE

**Avant de commencer :**
- [ ] Application lance correctement
- [ ] Fichiers CSV disponibles dans `/tests/csv-samples/`
- [ ] Base de données en mode test

**Scénarios à valider :**
- [ ] Scénario 1 : Parcours heureux simple
- [ ] Scénario 2 : Doublons internes
- [ ] Scénario 3 : Idempotence (réimport)
- [ ] Scénario 4 : Multi-mois sélection simple
- [ ] Scénario 5 : Multi-mois sélection multiple
- [ ] Scénario 6 : Gestion erreurs de format
- [ ] Scénario 7 : Encodage français Excel
- [ ] Scénario 8 : Actions rapides toasts

**Validation finale :**
- [ ] Critères d'acceptation validés
- [ ] GO/NOGO signé par utilisateur principal
- [ ] Tickets créés pour les problèmes identifiés

---

**🚀 Une fois ce guide complété et signé, la fonctionnalité d'import CSV sera prête pour la production !**