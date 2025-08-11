# PRD — Budget Famille (v3 vision)

**Version**: 0.1 (brouillon)

**Date**: 09/08/2025

**Owner**: à définir (vous)

**Equipe**: Produit, Dev (Frontend Next.js / Backend FastAPI), Design

---

## 1) Contexte & Problème

La gestion budgétaire familiale repose aujourd’hui sur un Excel (onglet *Calcul provision*). Cela rend difficile:

* la mise à jour rapide (imports bancaires, exclusions ponctuelles),
* la transparence de la répartition entre membres du foyer,
* le suivi des charges fixes/variables et des provisions (vacances, bébé, plaisir),
* l’analyse par nature de dépenses dans le temps.

*Budget Famille* vise à offrir une webapp simple, fiable et “opinionated”, avec des automatisations utiles et une vision **mensuelle** claire: combien prévoir chacun, pourquoi, et d’où viennent les montants.

---

## 2) Objectifs (SMART)

1. **Provision mensuelle fiable**: calculer pour chaque mois la part de chacun (membre A / membre B) avec transparence poste par poste.
2. **Import rapide**: charger un export bancaire CSV/XLSX (multi-mois), visualiser/exclure, tagger, agréger — en < 2 minutes.
3. **Clé de répartition flexible**: par revenus (proportionnel) ou manuel (%), possibilité de **dérogation par poste fixe**.
4. **Provisions intelligentes**: mensualiser automatiquement taxe foncière, copro, et provisions % de revenu fiscal N.
5. **Analyses utiles**: dépenses par tags, tendances mensuelles, alertes (dépenses inhabituelles / dépassements).
6. **Expérience cohérente**: sélection de **mois global** conservée d’une page à l’autre.

**Non-objectifs (pour l’instant)**: gestion patrimoniale avancée, fiscalité détaillée, trading, multi-devises complexes, rapprochements bancaires au centime près.

---

## 3) Personae & Cas d’usage

* **Couple bi-revenus** (2 membres par défaut) — peut évoluer vers 3+ membres.
* **Cas fréquents**:

  * Fin de mois: “Combien chacun doit verser ?”
  * Milieu de mois: “Suis-je en avance/en retard sur mes variables ?”
  * Dépense exceptionnelle: “Je l’exclus du calcul de provision.”
  * Planif: “J’ajoute un poste fixe (assurance, internet) avec répartition 100%/50-50/manuelle.”

---

## 4) Principes Produit

* **Clarté avant tout**: toujours montrer le **détail** du calcul (crédit, autres fixes, provisions %, variables).
* **Peu de champs, bien nommés**: réglages rapides sur le Dashboard.
* **Éditable in-line**: moins d’allers-retours Paramètres ⇄ Dashboard.
* **Sélecteur de mois global** persistant.
* **Sans magie opaque**: les automatisations/ML proposent, l’utilisateur décide.

---

## 5) Portée Fonctionnelle (vue d’ensemble)

### 5.1 Membres & Clé de répartition

* 2 membres (A/B) avec noms personnalisés.
* Modes de clé: **par revenus** (proportion), **manuel** (%), **égale 50/50** pour certains postes.
* Extension future: **N membres** (MVP 2 membres).

### 5.2 Charges fixes

* **Crédit immo + voiture**: montant mensuel total + option **50/50** ou **clé**.
* **Autres fixes (v2 héritée)**:

  * Mode *simple* (montant mensuel direct),
  * Mode *détaillé* (Taxe foncière N-1 annuelle + Copro mensuelle/trimestrielle → mensualisation),
  * Répartition: clé générale ou 50/50.
* **Lignes fixes personnalisées (illimitées)**:

  * Libellé, montant, **fréquence** (mensuelle/trimestrielle/annuelle),
  * Répartition par ligne: **clé**, **50/50**, **100% Membre A**, **100% Membre B**, **manuelle (%)**.

### 5.3 Dépenses variables

* **Import** CSV/XLSX multi-mois; détection du **mois par dateOp**.
* Visualisation ligne à ligne; **Exclude** toggle.
* **Tags** éditables (champ libre, virgules) pour analyses.
* Détection heuristique **revenus/transferts** → exclus par défaut.

### 5.4 Provisions % de revenu fiscal

* % configurable, base: **2 revenus**, **membre A**, **membre B**.
* Mensualisation automatique.

### 5.5 Calcul de provision mensuelle (sortie attendue)

* Totaux par membre:

  * Crédit (réparti), Autres fixes (et/ou lignes fixes), Provision %, Variables (réparties selon clé),
  * **Somme finale par membre** (montant à prévoir/virer).
* Transparence: tableau “Détail par poste”.

### 5.6 Analyses & Rapports

* **Par tags** (mois courant): total & %.
* **Tendances**: variables par mois, top tags, évolution charges fixes (roadmap).
* Export **CSV/XLSX/PDF** de la synthèse mensuelle (roadmap).

### 5.7 Règles & Intelligence (roadmap)

* **Règles de tags**: “si libellé contient *CARREFOUR*, alors tag *courses*”.
* **Normalisation commerçants** (regex/lexique).
* **Suggestions ML**: auto-tagging, détection d’anomalies (montant inhabituel), prévision fin de mois.
* **Recommandations**: “Tu dépasseras le budget *resto* de 40€ vs moyenne, veux-tu augmenter la provision ?”.

### 5.8 Notifications & Automations

* Alerte après import si >X% de lignes **non taguées**.
* Alerte “hausse inhabituelle” pour un tag (>2 écarts-types vs 3 derniers mois).
* Rappel mensuel: “Clôture et virement de provisions”.

### 5.9 Intégrations bancaires (optionnel)

* Via agrégateurs **PSD2** (ex: Powens/Tink/Budget Insight/Linxo Connect). OAuth, SCA.
* Synchronisation périodique (lecture seule), mapping vers schéma interne.

### 5.10 Sauvegarde / Import-Export

* Export config + transactions + tags en **ZIP**.
* Import d’une sauvegarde (fusion/sur-écriture).

### 5.11 Sécurité & Confidentialité

* Données **locales** (SQLite) par défaut; aucune remontée tierce sans consentement.
* HTTPS recommandé si déploiement.
* Journalisation minimale (pas de logs de données sensibles en clair).

---

## 6) Exigences détaillées (User stories & critères d’acceptation)

### 6.1 Import multi-mois

* **En tant qu’utilisateur**, je peux déposer un fichier CSV/XLSX contenant plusieurs mois.
* **DoD**: chaque ligne reçoit `month=YYYY-MM` d’après `dateOp`. Après import, un message indique la **liste des mois détectés**.

### 6.2 Exclusions & Tags

* Toggle **Exclude** sur chaque dépense → recalcul immédiat du total variables.
* Champ **Tags** (liste via virgules). **Blur/Enter** enregistre; dédoublonnage.
* **DoD**: l’agrégat par tags reflète la table en temps réel.

### 6.3 Lignes fixes personnalisées

* CRUD complet (ajout, édition, suppression).
* Fréquence → mensualisation: mensuel (= montant), trimestriel (= /3), annuel (= /12).
* Répartition par ligne: clé/50-50/100%A/100%B/manuel(%).
* **DoD**: Dashboard affiche une ligne par poste fixe ajouté ("Fixe — Libellé").

### 6.4 Provisions % revenu fiscal

* % configurable + base (2/A/B). Mensualisation.
* **DoD**: visible dans le détail du Dashboard.

### 6.5 Clé de répartition & cohérence UI

* Sélecteur de **mois global** (localStorage). Persiste entre pages.
* Éditions côté Dashboard → bouton **Enregistrer**.

### 6.6 Analyses par tags

* Tableau: Tag | Total | %.
* **DoD**: somme des tags = total variables (non exclues) du mois (les lignes sans tag → bucket “(non tagué)”).

### 6.7 Export synthèse (roadmap)

* PDF/CSV avec récap mensuel (totaux, détail par poste, top tags).

### 6.8 Intégration bancaire (option)

* Connecteur via agrégateur; import incrémental; retries; gestion SCA expirée.

---

## 7) UX / IA (Information Architecture)

* **Navbar**: Dashboard | Transactions | Paramètres | Analyses | (Règles – roadmap) + sélecteur de **mois global**.
* **Dashboard**: métriques clés, détail par poste, réglages rapides.
* **Transactions**: upload, table (date, libellé, catégorie, montant, exclude, tags).
* **Paramètres**: membres & clé, charges fixes héritées, **lignes fixes personnalisées**.
* **Analyses**: agrégats par tag (table + futurs graphiques).
* **Règles (roadmap)**: table des règles de tags + test de correspondance.

**Accessibilité**: focus states visibles, contrastes suffisants, navigation clavier.

---

## 8) Mesures de succès (KPIs)

* Taux d’import réussi (>95%).
* Temps de mise à jour mensuelle < 2 min.
* % de lignes taggées > 80% au 2e mois.
* Nombre moyen de postes fixes personnalisés actifs (≥5) — signe d’adoption.
* Satisfaction (NPS-likert interne) ≥ 8/10.

---

## 9) Données & Modèle (high-level)

* **Config**: membres, revenus, split\_mode, split1/2, loan\_equal, loan\_amount, other\_fixed\_\*, vac\_percent, vac\_base.
* **Transaction**: id, date\_op, month, label, category, category\_parent, amount, account\_label, is\_expense, exclude, tags.
* **FixedLine**: id, label, amount, freq (mensuelle/trimestrielle/annuelle), split\_mode (clé/50/50/m1/m2/manuel), split1/2, active.
* **Rule (roadmap)**: id, pattern (regex/contient), action (add tags), scope (libellé/catégorie), ordre.

---

## 10) API (existant & prévu)

* `GET /config` | `POST /config`
* `POST /import` (auto-mois)
* `GET /transactions?month=YYYY-MM`
* `PATCH /transactions/{id}` { exclude }
* `PATCH /transactions/{id}/tags` { tags\[] }
* `GET /tags` | `GET /tags-summary?month=YYYY-MM`
* `GET /fixed-lines` | `POST /fixed-lines` | `PATCH /fixed-lines/{id}` | `DELETE /fixed-lines/{id}`
* **Roadmap**: `/rules` CRUD, `/export?month=…&format=pdf|csv`, `/forecast?month=…`.

---

## 11) Architecture & Tech

* **Frontend**: Next.js (App Router), Tailwind; état local + appels REST.
* **Backend**: FastAPI, SQLAlchemy, SQLite (dev). Option Postgres (prod).
* **Parsing**: robust CSV/XLSX, normalisation colonnes FR.
* **Sécurité**: CORS restreint (env), pas de secrets côté client.

---

## 12) Roadmap & Phasage

**V2.3 (livrée)**

* Import auto-mois, tags sur transactions, lignes fixes personnalisées, mois global partagé, analyses par tags.

**V3 (1–2 semaines) — Priorités validées**

* **Design system** (shadcn/ui + Tailwind) avec thèmes clair/sombre, toasts, micro-interactions, composants table modernes (recherche/tri/sticky header), "chips" de tags.
* **Règles de tags (moteur + UI)** : conditions *contient / regex* sur libellé & catégorie, actions *ajouter/supprimer tags*, ordre d’évaluation, aperçu avant application, exécution automatique à l’import + bouton "Appliquer maintenant".
* **Charts** :

  * Évolution des **dépenses variables** sur 12 mois,
  * **Top tags** du mois,
  * Donut **Fixes vs Variables**.
* **Export PDF – Synthèse mensuelle** : 1 à 2 pages A4 avec résumé par poste, "qui doit combien", top 5 tags, total variables, liste d’exclusions. Nom de fichier: `Synthese-{YYYY-MM}.pdf`.

**V3.1 (1 semaine)**

* **Prévision fin de mois** (extrapolation historique lissé).
* **Alertes** : dépassement vs moyenne 3 mois, % lignes non taguées élevé, dépense inhabituelle.
* **Simulateur** : jouer la clé de répartition et le % de provision et voir l’impact en direct.

**V3.2 (2 semaines)**

* **Budgets par enveloppe** (courses, resto, etc.) avec jauges & objectifs mensuels.
* **Multi-membres (3+)**.
* **Moteur d’import avancé** (mapping de colonnes + presets banques).

---

## 13) Risques & Atténuations

* **Qualité des exports bancaires** (colonnes variables) → normalisation robuste, mapping via UI si besoin (roadmap).
* **Confidentialité** → local-first, export/import local, pas de cloud sans consentement.
* **Complexité des règles** → commencer simple (contient/regex), garder audit des modifications de tags.

---

## 14) Plan de tests (extraits)

* Import CSV avec séparateurs différents (`,` `;` `\t`) → 100% ok.
* Import multi-mois → transactions correctement ventilées par `month`.
* Exclude/Tags → recalcul var\_total immédiat; analyses alignées.
* Lignes fixes (mensuelle/trimestrielle/annuelle) → mensualisation correcte.
* Changement clé → répartition poste par poste ajustée.
* Sélecteur mois global → persistance cross-pages.

---

## 15) Questions ouvertes

1. **N membres**: à quelle échéance le support >2 est-il prioritaire ?
2. **Banque**: agrégateur préféré ? (coût & friction SCA)
3. **Export officiel**: format souhaité (PDF signé, CSV, XLSX) ?
4. **Seuils d’alertes**: valeurs par défaut ? (ex: +25% vs moyenne 3 mois)
5. **Catégorisation**: dictionnaire commerçants à initialiser ?

---

## 16) Annexes (idées d’évolutions “intelligentes”)

* **Prévision fin de mois**: extrapolation des variables à J+30 basée historique.
* **Rebalancing**: suggestion de virement équilibrage mid-month.
* **Conseils**: “Si tu augmentes la provision vacances à 6%, tu atteins X€ d’ici août 2026.”
* **Détection doublons** (opérations identiques rapprochées) & auto-exclusion.
* **Rapprochement virements internes** (débit/crédit liés) pour ne pas gonfler les variables.

## 17) Backlog V3 détaillé & critères d’acceptation

### A. Design system

* **Livrables** : thème clair/sombre, boutons, inputs, tables, tags chips, toasts, skeletons, transitions.
* **CA** : contraste AA, focus visibles, pas de *layout shift* perceptible, navigation clavier OK.

### B. Règles de tags

* **Livrables** : CRUD règles ; conditions (*contient* / *regex*) sur `label` / `category` ; actions add/remove tags ; ordre ; aperçu ; exécution auto à l’import + bulk "Appliquer maintenant".
* **CA** : création/édition/suppression en <3 clics ; import 5k lignes s’exécute en <10s sur machine standard ; dédoublonnage de tags ; journal minimal (qui/quoi/quand) en base.

### C. Charts

* **Livrables** : ligne 12 mois (variables), barres *Top tags (mois)*, donut *Fixes vs Variables*.
* **CA** : données cohérentes avec Dashboard (écart < 0,01€) ; export PNG rapide ; sélection du mois global respectée.

### D. Export PDF Synthèse

* **Livrables** : PDF A4 1–2 pages ; sections *Détail par poste*, *Qui doit combien*, *Top tags* ; option pour inclure/exclure la liste des opérations exclues.
* **CA** : nom `Synthese-YYYY-MM.pdf` ; total = Dashboard ; génération < 2s pour 1 mois standard.

### E. Qualité & Perf

* **Livrables** : tests unitaires calculs, tests API principaux, index DB, pagination transactions.
* **CA** : Taux d’import réussi ≥ 95% ; temps mise à jour mensuelle < 2 min ; Lighthouse perf ≥ 90 (local).
