<#
.SYNOPSIS
    Budget Famille - Système de Backup SQLite automatisé

.DESCRIPTION
    Gère les sauvegardes de la base de données SQLite avec:
    - Backups quotidiens, hebdomadaires et manuels
    - Vérification d'intégrité avec PRAGMA
    - Rotation automatique des anciens backups
    - Rapport de santé des backups

.PARAMETER Action
    Action à effectuer: daily, weekly, manual, cleanup, report, health

.PARAMETER DailyRetention
    Nombre de jours de rétention pour les backups quotidiens (défaut: 7)

.PARAMETER WeeklyRetention
    Nombre de jours de rétention pour les backups hebdomadaires (défaut: 28)

.PARAMETER ManualRetention
    Nombre de jours de rétention pour les backups manuels (défaut: 90)

.EXAMPLE
    .\Backup-Database.ps1
    Crée un backup quotidien

.EXAMPLE
    .\Backup-Database.ps1 -Action manual
    Crée un backup manuel

.EXAMPLE
    .\Backup-Database.ps1 -Action cleanup
    Nettoie les anciens backups

.EXAMPLE
    .\Backup-Database.ps1 -Action report
    Affiche un rapport des backups existants
#>

param(
    [ValidateSet('daily', 'weekly', 'manual', 'cleanup', 'report', 'health')]
    [string]$Action = 'daily',

    [int]$DailyRetention = 7,
    [int]$WeeklyRetention = 28,
    [int]$ManualRetention = 90
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
    Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "  ║   💾 BUDGET FAMILLE - Système de Backup               ║" -ForegroundColor Blue
    Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

# Initialisation du dossier de backups
function Initialize-BackupDirectory {
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        Write-Success "Dossier de backups créé: $BackupDir"
    }

    # Sous-dossiers par type
    @('daily', 'weekly', 'manual') | ForEach-Object {
        $subDir = Join-Path $BackupDir $_
        if (-not (Test-Path $subDir)) {
            New-Item -ItemType Directory -Path $subDir -Force | Out-Null
        }
    }
}

# Vérification de l'intégrité de la base
function Test-DatabaseIntegrity {
    param([string]$DbPath)

    Write-Info "Vérification de l'intégrité..."

    if (-not (Test-Path $DbPath)) {
        Write-Error "Base de données non trouvée: $DbPath"
        return $false
    }

    # Utiliser Python pour exécuter PRAGMA integrity_check
    $checkScript = @"
import sqlite3
import sys
try:
    conn = sqlite3.connect('$($DbPath -replace '\\', '/')')
    cursor = conn.execute('PRAGMA integrity_check')
    result = cursor.fetchone()[0]
    conn.close()
    if result == 'ok':
        print('OK')
        sys.exit(0)
    else:
        print(f'ERREUR: {result}')
        sys.exit(1)
except Exception as e:
    print(f'ERREUR: {e}')
    sys.exit(1)
"@

    $result = python -c $checkScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Intégrité OK"
        return $true
    } else {
        Write-Error "Échec vérification intégrité: $result"
        return $false
    }
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

    # Compter les transactions
    cursor.execute('SELECT COUNT(*) FROM transactions')
    tx_count = cursor.fetchone()[0]

    # Compter les provisions
    cursor.execute('SELECT COUNT(*) FROM custom_provisions')
    prov_count = cursor.fetchone()[0]

    # Taille de la base
    cursor.execute('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()')
    db_size = cursor.fetchone()[0]

    conn.close()

    print(json.dumps({
        'transactions': tx_count,
        'provisions': prov_count,
        'size_bytes': db_size
    }))
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

# Créer un backup
function New-Backup {
    param(
        [ValidateSet('daily', 'weekly', 'manual')]
        [string]$Type = 'daily'
    )

    Write-Step "Création d'un backup $Type..."

    # Vérifier la base source
    if (-not (Test-Path $DatabasePath)) {
        Write-Error "Base de données source non trouvée: $DatabasePath"
        return $false
    }

    # Vérifier l'intégrité avant backup
    if (-not (Test-DatabaseIntegrity -DbPath $DatabasePath)) {
        Write-Error "La base de données source est corrompue!"
        return $false
    }

    # Créer le nom du fichier
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupName = "budget_${Type}_${timestamp}.db"
    $backupPath = Join-Path $BackupDir $Type $backupName

    # Copier la base
    try {
        Copy-Item -Path $DatabasePath -Destination $backupPath -Force
        Write-Success "Backup créé: $backupName"
    } catch {
        Write-Error "Échec de la copie: $_"
        return $false
    }

    # Vérifier l'intégrité du backup
    if (-not (Test-DatabaseIntegrity -DbPath $backupPath)) {
        Write-Error "Le backup créé est corrompu!"
        Remove-Item $backupPath -Force
        return $false
    }

    # Statistiques
    $stats = Get-DatabaseStats -DbPath $backupPath
    if (-not $stats.error) {
        $sizeMB = [math]::Round($stats.size_bytes / 1MB, 2)
        Write-Info "Transactions: $($stats.transactions)"
        Write-Info "Provisions: $($stats.provisions)"
        Write-Info "Taille: $sizeMB MB"
    }

    # Créer un fichier de métadonnées
    $metaPath = $backupPath -replace '\.db$', '.json'
    $metadata = @{
        created = (Get-Date).ToString('o')
        type = $Type
        source = $DatabasePath
        transactions = $stats.transactions
        provisions = $stats.provisions
        size_bytes = $stats.size_bytes
        integrity = 'verified'
    } | ConvertTo-Json

    $metadata | Out-File -FilePath $metaPath -Encoding utf8

    Write-Success "Backup $Type terminé avec succès!"
    return $true
}

# Nettoyer les anciens backups
function Remove-OldBackups {
    Write-Step "Nettoyage des anciens backups..."

    $removed = 0

    # Daily
    $dailyDir = Join-Path $BackupDir "daily"
    $dailyCutoff = (Get-Date).AddDays(-$DailyRetention)
    Get-ChildItem -Path $dailyDir -Filter "*.db" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $dailyCutoff } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Remove-Item ($_.FullName -replace '\.db$', '.json') -Force -ErrorAction SilentlyContinue
            $removed++
        }
    Write-Info "Daily: supprimé $removed fichier(s) > $DailyRetention jours"

    # Weekly
    $weeklyDir = Join-Path $BackupDir "weekly"
    $weeklyCutoff = (Get-Date).AddDays(-$WeeklyRetention)
    $weeklyRemoved = 0
    Get-ChildItem -Path $weeklyDir -Filter "*.db" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $weeklyCutoff } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Remove-Item ($_.FullName -replace '\.db$', '.json') -Force -ErrorAction SilentlyContinue
            $weeklyRemoved++
        }
    Write-Info "Weekly: supprimé $weeklyRemoved fichier(s) > $WeeklyRetention jours"

    # Manual
    $manualDir = Join-Path $BackupDir "manual"
    $manualCutoff = (Get-Date).AddDays(-$ManualRetention)
    $manualRemoved = 0
    Get-ChildItem -Path $manualDir -Filter "*.db" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $manualCutoff } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Remove-Item ($_.FullName -replace '\.db$', '.json') -Force -ErrorAction SilentlyContinue
            $manualRemoved++
        }
    Write-Info "Manual: supprimé $manualRemoved fichier(s) > $ManualRetention jours"

    $total = $removed + $weeklyRemoved + $manualRemoved
    Write-Success "Nettoyage terminé: $total fichier(s) supprimé(s)"
}

# Rapport des backups
function Show-BackupReport {
    Write-Step "Rapport des backups..."

    $report = @()

    @('daily', 'weekly', 'manual') | ForEach-Object {
        $dir = Join-Path $BackupDir $_
        $files = Get-ChildItem -Path $dir -Filter "*.db" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending

        $count = ($files | Measure-Object).Count
        $totalSize = ($files | Measure-Object -Property Length -Sum).Sum
        $latest = $files | Select-Object -First 1
        $oldest = $files | Select-Object -Last 1

        $report += [PSCustomObject]@{
            Type = $_.ToUpper()
            Count = $count
            'Taille (MB)' = [math]::Round($totalSize / 1MB, 2)
            'Dernier' = if ($latest) { $latest.LastWriteTime.ToString('yyyy-MM-dd HH:mm') } else { '-' }
            'Plus ancien' = if ($oldest) { $oldest.LastWriteTime.ToString('yyyy-MM-dd HH:mm') } else { '-' }
        }
    }

    Write-Host ""
    $report | Format-Table -AutoSize

    # Détails des derniers backups
    Write-Host "`n  📋 5 derniers backups:" -ForegroundColor Cyan
    Get-ChildItem -Path $BackupDir -Filter "*.db" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object {
            $type = $_.Directory.Name
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            Write-Host "  → [$type] $($_.Name) ($sizeMB MB) - $($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))" -ForegroundColor White
        }
}

# Vérification de santé
function Test-BackupHealth {
    Write-Step "Vérification de santé des backups..."

    $issues = @()

    # Vérifier le dernier backup quotidien
    $dailyDir = Join-Path $BackupDir "daily"
    $latestDaily = Get-ChildItem -Path $dailyDir -Filter "*.db" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latestDaily) {
        $issues += "Aucun backup quotidien trouvé!"
    } elseif ($latestDaily.LastWriteTime -lt (Get-Date).AddDays(-1)) {
        $issues += "Dernier backup quotidien trop ancien: $($latestDaily.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))"
    } else {
        Write-Success "Backup quotidien récent: $($latestDaily.Name)"
    }

    # Vérifier l'intégrité du dernier backup
    if ($latestDaily) {
        if (Test-DatabaseIntegrity -DbPath $latestDaily.FullName) {
            Write-Success "Intégrité du dernier backup vérifiée"
        } else {
            $issues += "Le dernier backup est corrompu!"
        }
    }

    # Vérifier l'espace disque
    $drive = (Get-Item $BackupDir).PSDrive
    $freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
    if ($freeSpaceGB -lt 1) {
        $issues += "Espace disque faible: $freeSpaceGB GB restant"
    } else {
        Write-Success "Espace disque OK: $freeSpaceGB GB disponible"
    }

    # Résumé
    if ($issues.Count -eq 0) {
        Write-Host ""
        Write-Host "  ✅ Tous les contrôles de santé sont OK!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "  ⚠️ Problèmes détectés:" -ForegroundColor Yellow
        $issues | ForEach-Object {
            Write-Host "     • $_" -ForegroundColor Yellow
        }
    }
}

# Fonction principale
function Main {
    Show-Banner

    # Vérifier Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python requis pour les vérifications d'intégrité"
        exit 1
    }

    # Initialiser
    Initialize-BackupDirectory

    # Exécuter l'action
    switch ($Action) {
        'daily' {
            New-Backup -Type 'daily'
            Remove-OldBackups
        }
        'weekly' {
            New-Backup -Type 'weekly'
            Remove-OldBackups
        }
        'manual' {
            New-Backup -Type 'manual'
        }
        'cleanup' {
            Remove-OldBackups
        }
        'report' {
            Show-BackupReport
        }
        'health' {
            Test-BackupHealth
        }
    }

    Write-Host ""
}

# Exécution
Main
