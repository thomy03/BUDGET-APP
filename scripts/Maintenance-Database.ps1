<#
.SYNOPSIS
    Script de maintenance de la base de donnees Budget Famille
.DESCRIPTION
    - Synchronise le champ 'month' avec 'date_op'
    - Detecte et supprime les transactions en doublon
    - Verifie l'integrite de la base de donnees
    - Affiche des statistiques
.EXAMPLE
    .\Maintenance-Database.ps1
    .\Maintenance-Database.ps1 -Action sync
    .\Maintenance-Database.ps1 -Action duplicates
    .\Maintenance-Database.ps1 -Action integrity
    .\Maintenance-Database.ps1 -Action stats
    .\Maintenance-Database.ps1 -Action all
#>

param(
    [ValidateSet('sync', 'duplicates', 'integrity', 'stats', 'all')]
    [string]$Action = 'all',
    [switch]$DryRun,
    [switch]$Verbose
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DatabasePath = Join-Path $ProjectRoot "backend\budget.db"

# Verifier que sqlite3 est disponible
$sqlite3 = Get-Command sqlite3 -ErrorAction SilentlyContinue
if (-not $sqlite3) {
    Write-Host "`n[ERREUR] sqlite3 n'est pas installe ou pas dans le PATH" -ForegroundColor Red
    Write-Host "Installez SQLite depuis: https://www.sqlite.org/download.html" -ForegroundColor Yellow
    exit 1
}

# Verifier que la base existe
if (-not (Test-Path $DatabasePath)) {
    Write-Host "`n[ERREUR] Base de donnees introuvable: $DatabasePath" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " MAINTENANCE BASE DE DONNEES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Base: $DatabasePath"
Write-Host "Action: $Action"
if ($DryRun) {
    Write-Host "Mode: DRY RUN (aucune modification)" -ForegroundColor Yellow
}
Write-Host ""

function Show-Stats {
    Write-Host "`n--- STATISTIQUES ---" -ForegroundColor Green

    # Nombre total de transactions
    $total = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions;"
    Write-Host "Transactions totales: $total"

    # Par mois
    Write-Host "`nTransactions par mois:"
    $byMonth = sqlite3 $DatabasePath "SELECT month, COUNT(*) FROM transactions GROUP BY month ORDER BY month DESC LIMIT 12;"
    $byMonth | ForEach-Object {
        $parts = $_ -split '\|'
        Write-Host "  $($parts[0]): $($parts[1]) transactions"
    }

    # Transactions exclues
    $excluded = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions WHERE exclude = 1;"
    Write-Host "`nTransactions exclues: $excluded"

    # Transactions sans tag
    $noTag = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions WHERE tags IS NULL OR tags = '' OR tags = 'Non classe';"
    Write-Host "Transactions sans tag: $noTag"
}

function Sync-MonthField {
    Write-Host "`n--- SYNCHRONISATION MONTH/DATE_OP ---" -ForegroundColor Green

    # Trouver les transactions desynchronisees
    $desync = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions WHERE month != strftime('%Y-%m', date_op);"

    if ($desync -eq 0) {
        Write-Host "[OK] Toutes les transactions sont synchronisees" -ForegroundColor Green
        return
    }

    Write-Host "[!] $desync transactions desynchronisees" -ForegroundColor Yellow

    if ($Verbose) {
        Write-Host "`nExemples de transactions desynchronisees:"
        $examples = sqlite3 $DatabasePath "SELECT id, date_op, month, label FROM transactions WHERE month != strftime('%Y-%m', date_op) LIMIT 5;"
        $examples | ForEach-Object { Write-Host "  $_" }
    }

    if (-not $DryRun) {
        Write-Host "Correction en cours..."
        sqlite3 $DatabasePath "UPDATE transactions SET month = strftime('%Y-%m', date_op) WHERE month != strftime('%Y-%m', date_op);"
        Write-Host "[OK] $desync transactions corrigees" -ForegroundColor Green
    } else {
        Write-Host "[DRY RUN] $desync transactions seraient corrigees" -ForegroundColor Yellow
    }
}

function Remove-Duplicates {
    Write-Host "`n--- DETECTION DOUBLONS ---" -ForegroundColor Green

    # Trouver les doublons (meme date_op, label, amount)
    $duplicates = sqlite3 $DatabasePath @"
SELECT COUNT(*) FROM transactions
WHERE id NOT IN (
    SELECT MIN(id) FROM transactions
    GROUP BY date_op, label, amount
);
"@

    if ($duplicates -eq 0) {
        Write-Host "[OK] Aucun doublon detecte" -ForegroundColor Green
        return
    }

    Write-Host "[!] $duplicates doublons detectes" -ForegroundColor Yellow

    if ($Verbose) {
        Write-Host "`nExemples de doublons:"
        $examples = sqlite3 $DatabasePath @"
SELECT date_op, label, amount, COUNT(*) as cnt
FROM transactions
GROUP BY date_op, label, amount
HAVING cnt > 1
LIMIT 5;
"@
        $examples | ForEach-Object { Write-Host "  $_" }
    }

    if (-not $DryRun) {
        Write-Host "Suppression des doublons (garde le premier)..."
        sqlite3 $DatabasePath @"
DELETE FROM transactions
WHERE id NOT IN (
    SELECT MIN(id) FROM transactions
    GROUP BY date_op, label, amount
);
"@
        Write-Host "[OK] $duplicates doublons supprimes" -ForegroundColor Green
    } else {
        Write-Host "[DRY RUN] $duplicates doublons seraient supprimes" -ForegroundColor Yellow
    }
}

function Check-Integrity {
    Write-Host "`n--- VERIFICATION INTEGRITE ---" -ForegroundColor Green

    # Verification PRAGMA integrity_check
    $check = sqlite3 $DatabasePath "PRAGMA integrity_check;"

    if ($check -eq "ok") {
        Write-Host "[OK] Base de donnees integre" -ForegroundColor Green
    } else {
        Write-Host "[ERREUR] Probleme d'integrite detecte!" -ForegroundColor Red
        Write-Host $check
    }

    # Verifier les dates invalides
    $invalidDates = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions WHERE date_op IS NULL OR date_op = '';"
    if ($invalidDates -gt 0) {
        Write-Host "[!] $invalidDates transactions avec date invalide" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Toutes les dates sont valides" -ForegroundColor Green
    }

    # Verifier les montants nuls
    $nullAmounts = sqlite3 $DatabasePath "SELECT COUNT(*) FROM transactions WHERE amount IS NULL;"
    if ($nullAmounts -gt 0) {
        Write-Host "[!] $nullAmounts transactions avec montant NULL" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Tous les montants sont definis" -ForegroundColor Green
    }
}

# Executer les actions
switch ($Action) {
    'sync' { Sync-MonthField }
    'duplicates' { Remove-Duplicates }
    'integrity' { Check-Integrity }
    'stats' { Show-Stats }
    'all' {
        Show-Stats
        Check-Integrity
        Sync-MonthField
        Remove-Duplicates
        Write-Host "`n--- STATISTIQUES APRES MAINTENANCE ---" -ForegroundColor Green
        Show-Stats
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " MAINTENANCE TERMINEE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
