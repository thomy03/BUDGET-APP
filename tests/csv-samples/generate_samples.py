#!/usr/bin/env python3
"""
Générateur et validateur d'échantillons CSV pour Budget Famille v2.3

Usage:
    python generate_samples.py --regen                    # Régénère les 5 fichiers fixes
    python generate_samples.py --validate *.csv          # Valide les fichiers CSV
    python generate_samples.py --random custom.csv       # Crée un échantillon aléatoire
"""
import os
import csv
import argparse
from datetime import datetime, date, timedelta
import random
import re

SAMPLES_DIR = os.path.join("tests", "csv-samples")

def ensure_dir():
    """Crée le dossier de samples s'il n'existe pas"""
    os.makedirs(SAMPLES_DIR, exist_ok=True)

def write_csv(path, rows, encoding="utf-8", add_sep_line=False, windows_newlines=True):
    """Écrit un fichier CSV avec les paramètres spécifiés"""
    ensure_dir()
    newline = "" if windows_newlines else None
    
    with open(path, "w", encoding=encoding, newline=newline) as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\r\n" if windows_newlines else "\n", quoting=csv.QUOTE_MINIMAL)
        
        # Ligne sep=; optionnelle (Excel)
        if add_sep_line:
            f.write("sep=;\r\n" if windows_newlines else "sep=;\n")
        
        # Écriture des données
        for row in rows:
            writer.writerow(row)

def fixed_samples():
    """Retourne les 5 jeux de données fixes"""
    
    # Fichier 1: Happy path janvier 2024
    s1 = [
        ["date","description","montant","compte","tag"],
        ["02/01/2024","Loyer Janvier","-950,00","Compte Courant","Logement"],
        ["03/01/2024","Eau de Paris 0124","-28,50","Compte Courant","Logement"],
        ["04/01/2024","Internet Orange Fibre","-39,99","Compte Courant","Logement"],
        ["05/01/2024","EDF Facture 0124","-72,18","Compte Courant","Logement"],
        ["06/01/2024","ALDI","-54,32","Carte Débit","Courses"],
        ["06/01/2024","Carburant Total","-68,45","Carte Débit","Transport"],
        ["10/01/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],
        ["12/01/2024","Boulangerie Dupont","-8,20","Carte Débit","Courses"],
        ["15/01/2024","Remboursement Sécu","23,50","Compte Courant","Santé"],
        ["18/01/2024","Pharmacie Centrale","-12,30","Carte Débit","Santé"],
        ["20/01/2024","Marché local","-24,60","Carte Débit","Courses"],
        ["25/01/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
        ["28/01/2024","Abonnement Navigo","-75,20","Compte Courant","Transport"],
        ["29/01/2024","Monoprix","-76,80","Carte Débit","Courses"],
        ["30/01/2024","Médecin généraliste","-25,00","Compte Courant","Santé"],
    ]
    
    # Fichier 2: Multi-mois Q1 2024
    s2 = [
        ["date","description","montant","compte","tag"],
        ["02/01/2024","Loyer Janvier","-950,00","Compte Courant","Logement"],
        ["04/01/2024","Internet Orange Fibre","-39,99","Compte Courant","Logement"],
        ["06/01/2024","Carrefour","-82,45","Carte Débit","Courses"],
        ["08/01/2024","Carburant Total","-64,30","Carte Débit","Transport"],
        ["12/01/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],
        ["15/01/2024","Remboursement Sécu","18,70","Compte Courant","Santé"],
        ["20/01/2024","Pharmacie Centrale","-9,80","Carte Débit","Santé"],
        ["25/01/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
        ["02/02/2024","Loyer Février","-950,00","Compte Courant","Logement"],
        ["05/02/2024","EDF Facture 0224","-68,10","Compte Courant","Logement"],
        ["07/02/2024","ALDI","-57,25","Carte Débit","Courses"],
        ["10/02/2024","Carburant Total","-70,00","Carte Débit","Transport"],
        ["12/02/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],
        ["15/02/2024","Transfert vers Livret A","-200,00","Compte Courant","Épargne"],
        ["15/02/2024","Transfert depuis CC","200,00","Livret A","Épargne"],
        ["25/02/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
        ["02/03/2024","Loyer Mars","-950,00","Compte Courant","Logement"],
        ["04/03/2024","Internet Orange Fibre","-39,99","Compte Courant","Logement"],
        ["06/03/2024","Monoprix","-86,10","Carte Débit","Courses"],
        ["09/03/2024","Carburant Total","-66,40","Carte Débit","Transport"],
        ["12/03/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],
        ["15/03/2024","Remboursement Sécu","22,10","Compte Courant","Santé"],
        ["18/03/2024","Impôts - acompte","-200,00","Compte Courant","Impôts"],
        ["25/03/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
    ]
    
    # Fichier 3: Doublons janvier 2024
    s3 = [
        ["date","description","montant","compte","tag"],
        ["02/01/2024","Loyer Janvier","-950,00","Compte Courant","Logement"],
        ["05/01/2024","EDF Facture 0124","-72,18","Compte Courant","Logement"],
        ["05/01/2024","EDF Facture 0124","-72,18","Compte Courant","Logement"],  # Doublon
        ["06/01/2024","ALDI","-54,32","Carte Débit","Courses"],
        ["06/01/2024","ALDI","-54,32","Carte Débit","Courses"],  # Doublon
        ["10/01/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],
        ["12/01/2024","Boulangerie Dupont","-8,20","Carte Débit","Courses"],
        ["15/01/2024","Remboursement Sécu","23,50","Compte Courant","Santé"],
        ["25/01/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
        ["25/01/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],  # Doublon
        ["28/01/2024","Abonnement Navigo","-75,20","Compte Courant","Transport"],
        ["29/01/2024","Monoprix","-76,80","Carte Débit","Courses"],
    ]
    
    # Fichier 4: Problèmes de format (erreurs volontaires)
    s4 = [
        ["date","description","montant","compte","tag"],
        ["01/01/2024","Loyer Janvier","-950,00","Compte Courant","Logement"],             # OK
        ["05/01/2024","ALDI","-54.32","Carte Débit","Courses"],                            # Point au lieu de virgule
        ["10/01/2024","Pharmacie du Centre","-12,3O","Carte Débit","Santé"],               # 'O' au lieu de '0'
        ["15/01/2024","Remboursement Sécu","23,50","","Santé"],                             # Compte vide
        ["20/01/2024","Restaurant Chez Léa","-42,00","Carte Crédit"],                      # Colonne manquante
        ["25/01/2024","Salaire ACME SA","2 500,00","Compte Courant","Revenus"],            # Espace millier
        ["31/01/2024","Internet Orange Fibre","-39,99","Compte Courant","Logement"],       # OK
        ["31/02/2024","Test Date Invalide","-10,00","Compte Courant","Divers"],            # Date invalide
        ["2024-03-05","Eau de Paris","-28,50","Compte Courant","Logement"],                # Format ISO au lieu de FR
        ['07/03/2024','"Pharmacie; du Centre"','-9,80',"Carte Débit","Santé"],            # Point-virgule dans guillemets
        ["10/03/2024","Abonnement Navigo","-75,20","Compte Courant","Transport"],          # OK
        ["15/03/2024","","","",""],                                                        # Champs vides
        ["18/03/2024","Mutuelle Santé","-45,90","Compte Courant","Santé"],                 # OK
        ["20/03/2024","Epargne Livret A","-100,00","Compte Courant","Épargne","EXTRA"],    # Colonne supplémentaire
        ["22/03/2024",' "Monoprix" '," -76,80 "," Carte Débit "," Courses "],              # Espaces parasites
    ]
    
    # Fichier 5: Excel français avec caractères spéciaux
    s5 = [
        ["date","description","montant","compte","tag"],
        ["02/01/2024","Loyer – Janvier","-950,00","Compte Courant","Logement"],
        ["05/01/2024","Électricité EDF","-72,18","Compte Courant","Logement"],
        ["06/01/2024","Crèche municipale","-180,00","Compte Courant","Éducation"],
        ["07/01/2024","Café Paul","-3,20","Carte Débit","Courses"],
        ["12/01/2024","Cinéma – Gaumont","-24,00","Carte Crédit","Loisirs"],
        ["15/01/2024","Remboursement Sécurité sociale","23,50","Compte Courant","Santé"],
        ["25/01/2024","Salaire ACME SA","2500,00","Compte Courant","Revenus"],
        ["27/01/2024","Pharmacie de l'Hôtel de Ville","-9,80","Carte Débit","Santé"],
        ["28/01/2024","Chèque cantine","-35,00","Compte Courant","Éducation"],
    ]
    
    return s1, s2, s3, s4, s5

def save_fixed_samples():
    """Génère et sauvegarde les 5 fichiers de test fixes"""
    s1, s2, s3, s4, s5 = fixed_samples()
    
    # Fichiers UTF-8 avec BOM pour compatibilité Windows
    write_csv(os.path.join(SAMPLES_DIR, "01_happy_path_janvier_2024.csv"), s1, encoding="utf-8-sig")
    write_csv(os.path.join(SAMPLES_DIR, "02_multi_mois_2024_Q1.csv"), s2, encoding="utf-8-sig")
    write_csv(os.path.join(SAMPLES_DIR, "03_doublons_janvier_2024.csv"), s3, encoding="utf-8-sig")
    write_csv(os.path.join(SAMPLES_DIR, "04_problemes_format.csv"), s4, encoding="utf-8-sig")
    
    # Fichier Excel français: CP1252 + sep=; + CRLF
    write_csv(os.path.join(SAMPLES_DIR, "05_excel_fr_cp1252.csv"), s5, 
              encoding="cp1252", add_sep_line=True, windows_newlines=True)
    
    print("✓ 5 fichiers de test générés dans", SAMPLES_DIR)

def try_open_text(path):
    """Tente d'ouvrir un fichier avec différents encodages"""
    for enc in ("utf-8-sig", "cp1252", "utf-8", "latin1"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unable", "", 0, 1, "Aucun encodage compatible trouvé")

def validate_file(path):
    """Valide un fichier CSV et affiche les statistiques"""
    if not os.path.exists(path):
        print(f"[{path}] Fichier introuvable")
        return
    
    try:
        text, enc = try_open_text(path)
    except UnicodeDecodeError as e:
        print(f"[{path}] Erreur d'encodage: {e}")
        return
    
    lines = text.splitlines()
    if not lines:
        print(f"[{path}] Fichier vide")
        return
    
    # Détection du séparateur (ligne sep=; optionnelle)
    delim = ";"
    start = 0
    if lines[0].lower().startswith("sep="):
        if len(lines[0]) >= 5:
            delim = lines[0][4]
        start = 1
        print(f"[{path}] Ligne sep= détectée, délimiteur: '{delim}'")
    
    # Parse CSV
    try:
        reader = csv.reader(lines[start:], delimiter=delim)
        rows = list(reader)
    except Exception as e:
        print(f"[{path}] Erreur de parsing CSV: {e}")
        return
    
    if not rows:
        print(f"[{path}] Aucune donnée après l'entête (enc: {enc})")
        return
    
    # Validation de l'entête
    header = rows[0]
    header_norm = [h.strip().lower() for h in header]
    expected = ["date", "description", "montant", "compte", "tag"]
    
    if header_norm != expected:
        print(f"[{path}] ⚠️  Entêtes inattendues: {header}")
        print(f"         Attendu: {expected}")
    
    # Analyse des données
    errors = []
    months = set()
    amount_re = re.compile(r'^[+-]?\d{1,3}(\s?\d{3})*(,\d{1,2})?$')  # Tolère séparateur millier
    
    for idx, row in enumerate(rows[1:], start=2+start):
        # Ignorer lignes complètement vides
        if len(row) == 0 or all((c.strip() == "" for c in row)):
            continue
        
        # Vérification nombre de colonnes
        if len(row) != 5:
            errors.append((idx, "colonnes", f"{len(row)} colonnes au lieu de 5"))
            continue
        
        d, desc, amt, acct, tag = [c.strip() for c in row]
        
        # Validation date
        if d:  # Ne pas valider les dates vides (pour fichier de test)
            try:
                dt = datetime.strptime(d, "%d/%m/%Y")
                months.add(dt.strftime("%Y-%m"))
            except ValueError:
                errors.append((idx, "date", d))
        
        # Validation montant
        if amt and not amount_re.match(amt):
            errors.append((idx, "montant", amt))
        
        # Validation compte (peut être vide dans certains cas de test)
        if not acct and "problemes" not in path.lower():
            errors.append((idx, "compte", "vide"))
    
    # Affichage des résultats
    print(f"[{path}]")
    print(f"  Encodage: {enc}")
    print(f"  Délimiteur: '{delim}'") 
    print(f"  Lignes de données: {len(rows)-1}")
    print(f"  Mois détectés: {sorted(months) if months else 'aucun'}")
    print(f"  Erreurs: {len(errors)}")
    
    # Détail des erreurs (max 10)
    for error in errors[:10]:
        print(f"    - Ligne {error[0]}: {error[1]} = {error[2]}")
    
    if len(errors) > 10:
        print(f"    ... et {len(errors)-10} erreurs supplémentaires")
    
    print()

def random_sample(path, start_month="2024-04", months=2, seed=42, cp1252=False):
    """Génère un échantillon CSV aléatoire"""
    random.seed(seed)
    
    # Parse mois de départ
    y, m = map(int, start_month.split("-"))
    
    # Données de référence
    categories = ["Courses", "Revenus", "Logement", "Transport", "Santé", "Loisirs", "Épargne"]
    shops = {
        "Courses": ["ALDI", "Carrefour", "Monoprix", "Marché local", "Boulangerie Dupont", "Casino"],
        "Logement": ["Loyer", "EDF", "Eau de Paris", "Internet Orange", "Assurance Habitation"],
        "Transport": ["Carburant Total", "Abonnement Navigo", "Uber", "SNCF Connect", "Autolib"],
        "Santé": ["Pharmacie Centrale", "Mutuelle Santé", "Médecin généraliste", "Dentiste", "Opticien"],
        "Loisirs": ["Netflix", "Cinéma", "Decathlon", "Fnac", "Restaurant"],
        "Revenus": ["Salaire ACME SA", "Prime trimestrielle", "Remboursement Sécu", "CAF"],
        "Épargne": ["Virement Livret A", "PEL", "Assurance Vie"]
    }
    
    comptes = ["Compte Courant", "Carte Débit", "Carte Crédit", "Livret A"]
    
    rows = [["date", "description", "montant", "compte", "tag"]]
    
    cur_y, cur_m = y, m
    
    for _ in range(months):
        # Transaction fixe: salaire le 25
        rows.append([
            f"25/{cur_m:02d}/{cur_y}",
            "Salaire ACME SA",
            "2500,00",
            "Compte Courant",
            "Revenus"
        ])
        
        # Transaction fixe: loyer le 02
        rows.append([
            f"02/{cur_m:02d}/{cur_y}",
            f"Loyer {cur_y}-{cur_m:02d}",
            "-950,00",
            "Compte Courant",
            "Logement"
        ])
        
        # 8 transactions aléatoires
        for _ in range(8):
            cat = random.choice([c for c in categories if c != "Revenus"])
            desc = random.choice(shops[cat])
            day = random.randint(1, 28)
            
            # Montant négatif pour les dépenses
            euros = random.randint(5, 200)
            cents = random.randint(0, 99)
            amount = f"-{euros},{cents:02d}"
            
            # Revenues (remboursements) occasionnels
            if cat == "Santé" and random.random() < 0.3:
                amount = f"{euros//2},{cents:02d}"  # Montant positif plus petit
                desc = f"Remboursement {desc}"
            
            compte = random.choice(comptes)
            
            rows.append([
                f"{day:02d}/{cur_m:02d}/{cur_y}",
                desc,
                amount,
                compte,
                cat
            ])
        
        # Mois suivant
        if cur_m == 12:
            cur_y += 1
            cur_m = 1
        else:
            cur_m += 1
    
    # Écriture du fichier
    encoding = "cp1252" if cp1252 else "utf-8-sig"
    write_csv(path, rows, encoding=encoding, add_sep_line=cp1252, windows_newlines=True)
    
    print(f"✓ Échantillon aléatoire créé: {path}")
    print(f"  Période: {start_month} + {months} mois")
    print(f"  Encodage: {encoding}")
    print(f"  Transactions: {len(rows)-1}")

def main():
    parser = argparse.ArgumentParser(description="Générateur et validateur d'échantillons CSV pour Budget Famille v2.3")
    
    parser.add_argument("--regen", action="store_true", 
                       help="Régénère les 5 fichiers de test fixes")
    
    parser.add_argument("--validate", nargs="*", metavar="FICHIER", 
                       help="Valide un ou plusieurs fichiers CSV")
    
    parser.add_argument("--random", metavar="FICHIER", 
                       help="Génère un échantillon aléatoire")
    
    parser.add_argument("--random-start", default="2024-04", 
                       help="Mois de départ pour l'aléatoire (format: YYYY-MM)")
    
    parser.add_argument("--random-months", type=int, default=2, 
                       help="Nombre de mois à générer pour l'aléatoire")
    
    parser.add_argument("--random-cp1252", action="store_true", 
                       help="Utiliser encodage CP1252 avec sep=; (format Excel)")
    
    args = parser.parse_args()
    
    # Exécution des commandes
    if args.regen:
        save_fixed_samples()
    
    if args.random:
        ensure_dir()
        full_path = os.path.join(SAMPLES_DIR, args.random)
        random_sample(
            full_path,
            start_month=args.random_start,
            months=args.random_months,
            cp1252=args.random_cp1252
        )
    
    if args.validate is not None:
        if len(args.validate) == 0:
            # Valider tous les fichiers CSV du dossier
            if os.path.exists(SAMPLES_DIR):
                files = [f for f in os.listdir(SAMPLES_DIR) if f.endswith('.csv')]
                files = [os.path.join(SAMPLES_DIR, f) for f in sorted(files)]
            else:
                files = []
        else:
            files = args.validate
        
        if not files:
            print("Aucun fichier CSV à valider")
        else:
            print(f"Validation de {len(files)} fichier(s):\n")
            for filepath in files:
                validate_file(filepath)
    
    # Affichage d'aide si aucune option
    if not any([args.regen, args.validate is not None, args.random]):
        print("Usage:")
        print("  python generate_samples.py --regen")
        print("  python generate_samples.py --validate *.csv")
        print("  python generate_samples.py --random custom.csv --random-months 3")
        print("\nUtilisez --help pour plus d'options")

if __name__ == "__main__":
    main()