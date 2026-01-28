<#
.SYNOPSIS
    Budget Famille - Outils de développement

.DESCRIPTION
    Collection d'outils utiles pour le développement:
    - Nettoyage des caches
    - Vérification des ports
    - Health check des services
    - Test des endpoints API
    - Logs en temps réel

.PARAMETER Action
    Action à effectuer: clear-cache, check-ports, health, test-api, logs, kill-all

.EXAMPLE
    .\Dev-Tools.ps1 -Action clear-cache
    Nettoie tous les caches (node_modules/.cache, .next, __pycache__)

.EXAMPLE
    .\Dev-Tools.ps1 -Action check-ports
    Vérifie si les ports 3000 et 8000 sont disponibles

.EXAMPLE
    .\Dev-Tools.ps1 -Action health
    Vérifie l'état des services backend et frontend

.EXAMPLE
    .\Dev-Tools.ps1 -Action test-api
    Teste les endpoints API principaux

.EXAMPLE
    .\Dev-Tools.ps1 -Action kill-all
    Arrête tous les processus Node.js et Python liés à l'application
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('clear-cache', 'check-ports', 'health', 'test-api', 'logs', 'kill-all', 'info')]
    [string]$Action
)

# Configuration
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:BackendPath = Join-Path $ProjectRoot "backend"
$script:FrontendPath = Join-Path $ProjectRoot "frontend"
$script:BackendPort = 8000
$script:FrontendPort = 3000

# Couleurs
function Write-Step { param($msg) Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  → $msg" -ForegroundColor White }

# Bannière
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════════════╗" -ForegroundColor DarkCyan
    Write-Host "  ║   🔧 BUDGET FAMILLE - Outils de Développement         ║" -ForegroundColor DarkCyan
    Write-Host "  ╚═══════════════════════════════════════════════════════╝" -ForegroundColor DarkCyan
    Write-Host ""
}

# Nettoyer les caches
function Clear-AllCaches {
    Write-Step "Nettoyage des caches..."

    $totalSize = 0

    # Next.js cache
    $nextCache = Join-Path $FrontendPath ".next"
    if (Test-Path $nextCache) {
        $size = (Get-ChildItem $nextCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $totalSize += $size
        Remove-Item $nextCache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success ".next supprimé ($([math]::Round($size/1MB, 2)) MB)"
    } else {
        Write-Info ".next non trouvé"
    }

    # Node modules cache
    $nodeCache = Join-Path $FrontendPath "node_modules\.cache"
    if (Test-Path $nodeCache) {
        $size = (Get-ChildItem $nodeCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $totalSize += $size
        Remove-Item $nodeCache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Success "node_modules/.cache supprimé ($([math]::Round($size/1MB, 2)) MB)"
    } else {
        Write-Info "node_modules/.cache non trouvé"
    }

    # Python cache
    Get-ChildItem -Path $BackendPath -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue |
        ForEach-Object {
            $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $totalSize += $size
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    Write-Success "__pycache__ supprimés"

    # .pyc files
    Get-ChildItem -Path $BackendPath -Filter "*.pyc" -Recurse -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $totalSize += $_.Length
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        }

    Write-Host ""
    Write-Success "Total libéré: $([math]::Round($totalSize/1MB, 2)) MB"
}

# Vérifier les ports
function Test-Ports {
    Write-Step "Vérification des ports..."

    # Port Backend
    $backendConn = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue
    if ($backendConn) {
        $process = Get-Process -Id $backendConn.OwningProcess -ErrorAction SilentlyContinue
        Write-Warning "Port $BackendPort (Backend) UTILISÉ par $($process.ProcessName) (PID: $($process.Id))"
    } else {
        Write-Success "Port $BackendPort (Backend) disponible"
    }

    # Port Frontend
    $frontendConn = Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue
    if ($frontendConn) {
        $process = Get-Process -Id $frontendConn.OwningProcess -ErrorAction SilentlyContinue
        Write-Warning "Port $FrontendPort (Frontend) UTILISÉ par $($process.ProcessName) (PID: $($process.Id))"
    } else {
        Write-Success "Port $FrontendPort (Frontend) disponible"
    }

    # Autres ports courants
    @(5432, 6379, 5000) | ForEach-Object {
        $conn = Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue
        if ($conn) {
            $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            Write-Info "Port $_ utilisé par $($process.ProcessName)"
        }
    }
}

# Health check
function Test-Health {
    Write-Step "Vérification de santé des services..."

    # Backend
    Write-Info "Test du Backend (http://localhost:$BackendPort)..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Backend OK (Status: $($response.StatusCode))"

        # Tester l'API docs
        $docsResponse = Invoke-WebRequest -Uri "http://localhost:$BackendPort/docs" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "API Documentation accessible"
    } catch {
        try {
            # Essayer juste /docs si /health n'existe pas
            $docsResponse = Invoke-WebRequest -Uri "http://localhost:$BackendPort/docs" -TimeoutSec 5 -ErrorAction Stop
            Write-Success "Backend OK (via /docs)"
        } catch {
            Write-Error "Backend non accessible: $($_.Exception.Message)"
        }
    }

    # Frontend
    Write-Info "Test du Frontend (http://localhost:$FrontendPort)..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -TimeoutSec 10 -ErrorAction Stop
        Write-Success "Frontend OK (Status: $($response.StatusCode))"
    } catch {
        Write-Error "Frontend non accessible: $($_.Exception.Message)"
    }
}

# Tester les endpoints API
function Test-ApiEndpoints {
    Write-Step "Test des endpoints API..."

    $baseUrl = "http://localhost:$BackendPort"
    $endpoints = @(
        @{ Method = 'GET'; Path = '/health'; Description = 'Health Check' },
        @{ Method = 'GET'; Path = '/docs'; Description = 'API Documentation' },
        @{ Method = 'GET'; Path = '/api/transactions'; Description = 'Transactions' },
        @{ Method = 'GET'; Path = '/api/custom-provisions'; Description = 'Provisions' },
        @{ Method = 'GET'; Path = '/api/config'; Description = 'Configuration' },
        @{ Method = 'GET'; Path = '/api/tags'; Description = 'Tags' }
    )

    $results = @()

    foreach ($ep in $endpoints) {
        $url = "$baseUrl$($ep.Path)"
        try {
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-WebRequest -Uri $url -Method $ep.Method -TimeoutSec 10 -ErrorAction Stop
            $stopwatch.Stop()

            $results += [PSCustomObject]@{
                Endpoint = $ep.Path
                Status = $response.StatusCode
                Time = "$($stopwatch.ElapsedMilliseconds)ms"
                Result = 'OK'
            }
            Write-Success "$($ep.Description): $($response.StatusCode) ($($stopwatch.ElapsedMilliseconds)ms)"
        } catch {
            $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
            $results += [PSCustomObject]@{
                Endpoint = $ep.Path
                Status = $statusCode
                Time = '-'
                Result = 'FAIL'
            }
            Write-Error "$($ep.Description): $statusCode"
        }
    }

    Write-Host ""
    Write-Host "  📊 Résumé des tests:" -ForegroundColor Cyan
    $results | Format-Table -AutoSize
}

# Arrêter tous les processus
function Stop-AllProcesses {
    Write-Step "Arrêt des processus de développement..."

    # Node.js (Next.js)
    $nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*next*" -or $_.CommandLine -like "*$FrontendPath*" }

    if ($nodeProcesses) {
        $nodeProcesses | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Success "Processus Node.js arrêtés ($($nodeProcesses.Count))"
    } else {
        Write-Info "Aucun processus Node.js trouvé"
    }

    # Python (Uvicorn)
    $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*$BackendPath*" }

    if ($pythonProcesses) {
        $pythonProcesses | ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        Write-Success "Processus Python arrêtés ($($pythonProcesses.Count))"
    } else {
        Write-Info "Aucun processus Python trouvé"
    }

    # Libérer les ports
    Start-Sleep -Seconds 1
    Test-Ports
}

# Afficher les informations du projet
function Show-ProjectInfo {
    Write-Step "Informations du projet..."

    # Versions
    Write-Host ""
    Write-Host "  📦 Versions:" -ForegroundColor Cyan

    # Python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pyVersion = python --version 2>&1
        Write-Info "Python: $pyVersion"
    }

    # Node.js
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $nodeVersion = node --version 2>&1
        Write-Info "Node.js: $nodeVersion"
    }

    # npm
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $npmVersion = npm --version 2>&1
        Write-Info "npm: v$npmVersion"
    }

    # Structure du projet
    Write-Host ""
    Write-Host "  📁 Structure:" -ForegroundColor Cyan
    Write-Info "Racine: $ProjectRoot"
    Write-Info "Backend: $BackendPath"
    Write-Info "Frontend: $FrontendPath"

    # Base de données
    $dbPath = Join-Path $BackendPath "budget.db"
    if (Test-Path $dbPath) {
        $dbSize = (Get-Item $dbPath).Length
        Write-Info "Base de données: $([math]::Round($dbSize/1MB, 2)) MB"
    }

    # Environnement virtuel
    $venvPath = Join-Path $ProjectRoot ".venv"
    if (Test-Path $venvPath) {
        Write-Success "Environnement virtuel .venv présent"
    } else {
        Write-Warning "Environnement virtuel .venv absent"
    }

    # node_modules
    $nodeModules = Join-Path $FrontendPath "node_modules"
    if (Test-Path $nodeModules) {
        Write-Success "node_modules présent"
    } else {
        Write-Warning "node_modules absent"
    }

    # URLs
    Write-Host ""
    Write-Host "  🌐 URLs:" -ForegroundColor Cyan
    Write-Info "Frontend: http://localhost:$FrontendPort"
    Write-Info "Backend API: http://localhost:$BackendPort"
    Write-Info "API Docs: http://localhost:$BackendPort/docs"
}

# Fonction principale
function Main {
    Show-Banner

    switch ($Action) {
        'clear-cache' { Clear-AllCaches }
        'check-ports' { Test-Ports }
        'health' { Test-Health }
        'test-api' { Test-ApiEndpoints }
        'kill-all' { Stop-AllProcesses }
        'info' { Show-ProjectInfo }
        'logs' {
            Write-Step "Affichage des logs..."
            Write-Warning "Fonctionnalité à venir - utilisez les fenêtres de terminal"
        }
    }

    Write-Host ""
}

# Exécution
Main
