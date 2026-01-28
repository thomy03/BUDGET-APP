<#
.SYNOPSIS
    Budget Famille - Restauration de la base de données

.DESCRIPTION
    Restaure la base de données SQLite depuis un backup avec:
    - Sélection interactive des backups disponibles
    - Backup automatique avant restauration
    - Vérification d'intégrité avant et après
    - Rollback en cas d'échec

.PARAMETER BackupFile
    Chemin vers le fichier de backup à restaurer (optionnel)
    Si non spécifié, une liste interactive sera affichée

.PARAMETER NoBackup
    Ne pas créer de backup avant la restauration

.PARAMETER Force
    Ne pas demander de confirmation

.EXAMPLE
    .\Restore-Database.ps1
    Affiche la liste des backups et permet de choisir

.EXAMPLE
    .\Restore-Database.ps1 -BackupFile ".\backups\daily\budget_daily_2025-12-01.db"
    Restaure un backup spécifique

.EXAMPLE
    .\Restore-Database.ps1 -Force
    Restaure le dernier backup sans confirmation
#>

param(
    [string]$BackupFile,
    [switch]$NoBackup,
    [switch]$Force
)

# Configuration
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:BackendPath = Join-Path $ProjectRoot "backend"
$script:DatabasePath = Join-Path $BackendPath "budget.db"
$script:BackupDir = Join-Path $BackendPath "backups"

# Couleurs
function Write-Step { param($msg) Write-Host "`n[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  → $msg" -ForegroundColor White }

# Bannière
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "  ║   🔄 BUDGET FAMILLE - Restauration BDD                ║" -ForegroundColor Yellow
    Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
}

# Vérification de l'intégrité de la base
function Test-DatabaseIntegrity {
    param([string]$DbPath)

    if (-not (Test-Path $DbPath)) {
        return $false
    }

    $checkScript = @"
import sqlite3
import sys
try:
    conn = sqlite3.connect('$($DbPath -replace '\\', '/')')
    cursor = conn.execute('PRAGMA integrity_check')
    result = cursor.fetchone()[0]
    conn.close()
    sys.exit(0 if result == 'ok' else 1)
except:
    sys.exit(1)
"@

    python -c $checkScript 2>$null
    return $LASTEXITCODE -eq 0
}

# Obtenir les statistiques de la base
function Get-DatabaseStats {
    param([string]$DbPath)

    $statsScript = @"
import sqlite3
import json
try:
    conn = sqlite3.connect('$($DbPath -replace '\\', '/')')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM transactions')
    tx = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM custom_provisions')
    prov = cursor.fetchone()[0]
    conn.close()
    print(json.dumps({'transactions': tx, 'provisions': prov}))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"@

    $result = python -c $statsScript 2>&1
    try {
        return $result | ConvertFrom-Json
    } catch {
        return @{ error = "Impossible de lire les stats" }
    }
}

# Lister les backups disponibles
function Get-AvailableBackups {
    $backups = @()

    Get-ChildItem -Path $BackupDir -Filter "*.db" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        ForEach-Object {
            $type = $_.Directory.Name
            $stats = Get-DatabaseStats -DbPath $_.FullName
            $sizeMB = [math]::Round($_.Length / 1MB, 2)

            $backups += [PSCustomObject]@{
                Index = $backups.Count + 1
                Type = $type.ToUpper()
                Name = $_.Name
                Date = $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm')
                Transactions = if ($stats.transactions) { $stats.transactions } else { '?' }
                'Taille (MB)' = $sizeMB
                Path = $_.FullName
            }
        }

    return $backups
}

# Sélection interactive du backup
function Select-Backup {
    Write-Step "Backups disponibles..."

    $backups = Get-AvailableBackups

    if ($backups.Count -eq 0) {
        Write-Error "Aucun backup trouvé dans $BackupDir"
        return $null
    }

    Write-Host ""
    $backups | Select-Object Index, Type, Name, Date, Transactions, 'Taille (MB)' |
        Format-Table -AutoSize

    Write-Host ""
    $selection = Read-Host "  Entrez le numéro du backup à restaurer (ou 'q' pour quitter)"

    if ($selection -eq 'q') {
        return $null
    }

    $index = [int]$selection - 1
    if ($index -lt 0 -or $index -ge $backups.Count) {
        Write-Error "Sélection invalide"
        return $null
    }

    return $backups[$index]
}

# Créer un backup de sécurité avant restauration
function New-PreRestoreBackup {
    Write-Step "Création d'un backup de sécurité..."

    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupName = "budget_pre-restore_${timestamp}.db"
    $backupPath = Join-Path $BackupDir "manual" $backupName

    # Créer le dossier si nécessaire
    $manualDir = Join-Path $BackupDir "manual"
    if (-not (Test-Path $manualDir)) {
        New-Item -ItemType Directory -Path $manualDir -Force | Out-Null
    }

    try {
        Copy-Item -Path $DatabasePath -Destination $backupPath -Force
        Write-Success "Backup de sécurité créé: $backupName"
        return $backupPath
    } catch {
        Write-Error "Échec du backup de sécurité: $_"
        return $null
    }
}

# Restaurer la base de données
function Restore-Database {
    param([string]$SourcePath)

    Write-Step "Restauration de la base de données..."

    # Vérifier l'intégrité du backup source
    Write-Info "Vérification du backup source..."
    if (-not (Test-DatabaseIntegrity -DbPath $SourcePath)) {
        Write-Error "Le backup source est corrompu!"
        return $false
    }
    Write-Success "Backup source intègre"

    # Statistiques du backup
    $sourceStats = Get-DatabaseStats -DbPath $SourcePath
    Write-Info "Backup source: $($sourceStats.transactions) transactions, $($sourceStats.provisions) provisions"

    # Backup actuel si existe
    $preRestoreBackup = $null
    if ((Test-Path $DatabasePath) -and -not $NoBackup) {
        $currentStats = Get-DatabaseStats -DbPath $DatabasePath
        Write-Info "Base actuelle: $($currentStats.transactions) transactions, $($currentStats.provisions) provisions"

        $preRestoreBackup = New-PreRestoreBackup
        if (-not $preRestoreBackup) {
            if (-not $Force) {
                $continue = Read-Host "  Continuer sans backup de sécurité? (o/N)"
                if ($continue -ne 'o') {
                    return $false
                }
            }
        }
    }

    # Copier le backup vers la base de données
    Write-Info "Copie du backup..."
    try {
        Copy-Item -Path $SourcePath -Destination $DatabasePath -Force
    } catch {
        Write-Error "Échec de la copie: $_"

        # Rollback
        if ($preRestoreBackup) {
            Write-Warning "Tentative de rollback..."
            Copy-Item -Path $preRestoreBackup -Destination $DatabasePath -Force
        }
        return $false
    }

    # Vérifier l'intégrité après restauration
    Write-Info "Vérification post-restauration..."
    if (-not (Test-DatabaseIntegrity -DbPath $DatabasePath)) {
        Write-Error "La base restaurée est corrompue!"

        # Rollback
        if ($preRestoreBackup) {
            Write-Warning "Rollback automatique..."
            Copy-Item -Path $preRestoreBackup -Destination $DatabasePath -Force
            Write-Success "Rollback effectué"
        }
        return $false
    }

    # Vérifier les statistiques finales
    $finalStats = Get-DatabaseStats -DbPath $DatabasePath
    Write-Success "Restauration réussie!"
    Write-Info "Base restaurée: $($finalStats.transactions) transactions, $($finalStats.provisions) provisions"

    return $true
}

# Fonction principale
function Main {
    Show-Banner

    # Vérifier Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python requis pour les vérifications"
        exit 1
    }

    # Sélectionner le backup
    $selectedBackup = $null

    if ($BackupFile) {
        # Backup spécifié en paramètre
        if (-not (Test-Path $BackupFile)) {
            Write-Error "Fichier non trouvé: $BackupFile"
            exit 1
        }
        $selectedBackup = [PSCustomObject]@{
            Name = Split-Path $BackupFile -Leaf
            Path = $BackupFile
        }
    } else {
        # Sélection interactive
        $selectedBackup = Select-Backup
    }

    if (-not $selectedBackup) {
        Write-Host "`n  Restauration annulée." -ForegroundColor Gray
        exit 0
    }

    # Confirmation
    if (-not $Force) {
        Write-Host ""
        Write-Host "  ⚠️  ATTENTION: Cette opération va remplacer la base actuelle!" -ForegroundColor Yellow
        Write-Host "     Backup sélectionné: $($selectedBackup.Name)" -ForegroundColor White
        Write-Host ""
        $confirm = Read-Host "  Confirmer la restauration? (oui/non)"

        if ($confirm -ne 'oui') {
            Write-Host "`n  Restauration annulée." -ForegroundColor Gray
            exit 0
        }
    }

    # Effectuer la restauration
    $success = Restore-Database -SourcePath $selectedBackup.Path

    if ($success) {
        Write-Host ""
        Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "  ║   ✅ RESTAURATION TERMINÉE AVEC SUCCÈS!               ║" -ForegroundColor Green
        Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Redémarrez l'application pour utiliser la base restaurée." -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Red
        Write-Host "  ║   ❌ ÉCHEC DE LA RESTAURATION                         ║" -ForegroundColor Red
        Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}

# Exécution
Main
