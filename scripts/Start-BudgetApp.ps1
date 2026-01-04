<#
.SYNOPSIS
    Budget Famille v3.0 - Script de demarrage unifie PowerShell

.DESCRIPTION
    Lance le backend (FastAPI) et le frontend (Next.js) avec gestion complete:
    - Verification des prerequis (Python, Node.js, ports)
    - Creation/activation automatique de l'environnement virtuel
    - Installation des dependances si necessaire
    - Health check avant ouverture du navigateur
    - Arret propre avec Ctrl+C

.PARAMETER Backend
    Lance uniquement le backend

.PARAMETER Frontend
    Lance uniquement le frontend

.PARAMETER NoBrowser
    Ne pas ouvrir le navigateur automatiquement

.PARAMETER Install
    Force la reinstallation des dependances

.EXAMPLE
    .\Start-BudgetApp.ps1
    Lance l'application complete (backend + frontend)

.EXAMPLE
    .\Start-BudgetApp.ps1 -Backend
    Lance uniquement le backend

.EXAMPLE
    .\Start-BudgetApp.ps1 -NoBrowser
    Lance sans ouvrir le navigateur
#>

param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$NoBrowser,
    [switch]$Install,
    [switch]$VerboseOutput
)

# Configuration
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:BackendPath = Join-Path $ProjectRoot "backend"
$script:FrontendPath = Join-Path $ProjectRoot "frontend"
$script:VenvPath = Join-Path $BackendPath ".winvenv"
$script:BackendPort = 8000
$script:FrontendPort = 3000
$script:BackendProcess = $null
$script:FrontendProcess = $null

# Couleurs
function Write-Step { param($msg) Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "  [X] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  -> $msg" -ForegroundColor White }

# Banniere
function Show-Banner {
    Write-Host ""
    Write-Host "  =========================================================" -ForegroundColor Magenta
    Write-Host "  |                                                       |" -ForegroundColor Magenta
    Write-Host "  |   BUDGET FAMILLE v3.0                                 |" -ForegroundColor Magenta
    Write-Host "  |   Application de Gestion Budgetaire                   |" -ForegroundColor Magenta
    Write-Host "  |                                                       |" -ForegroundColor Magenta
    Write-Host "  =========================================================" -ForegroundColor Magenta
    Write-Host ""
}

# Verification des prerequis
function Test-Prerequisites {
    Write-Step "Verification des prerequis..."

    # Python
    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCmd = "py"
    }

    if ($pythonCmd) {
        $pyVersion = & $pythonCmd --version 2>&1
        Write-Success "Python trouve: $pyVersion"
        $script:PythonCmd = $pythonCmd
    } else {
        Write-Err "Python non trouve! Installez Python 3.8+ depuis https://python.org"
        return $false
    }

    # Node.js
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $nodeVersion = node --version 2>&1
        Write-Success "Node.js trouve: $nodeVersion"
    } else {
        Write-Err "Node.js non trouve! Installez Node.js 18+ depuis https://nodejs.org"
        return $false
    }

    # npm
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $npmVersion = npm --version 2>&1
        Write-Success "npm trouve: v$npmVersion"
    } else {
        Write-Err "npm non trouve!"
        return $false
    }

    return $true
}

# Verification des ports
function Test-Ports {
    Write-Step "Verification des ports..."

    $backendInUse = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue
    $frontendInUse = Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue

    if ($backendInUse -and -not $Frontend) {
        Write-Warn "Port $BackendPort deja utilise (Backend peut-etre deja lance)"
        $continue = Read-Host "  Continuer quand meme? (O/n)"
        if ($continue -eq 'n') { return $false }
    } else {
        Write-Success "Port $BackendPort disponible (Backend)"
    }

    if ($frontendInUse -and -not $Backend) {
        Write-Warn "Port $FrontendPort deja utilise (Frontend peut-etre deja lance)"
        $continue = Read-Host "  Continuer quand meme? (O/n)"
        if ($continue -eq 'n') { return $false }
    } else {
        Write-Success "Port $FrontendPort disponible (Frontend)"
    }

    return $true
}

# Gestion environnement virtuel
function Initialize-VirtualEnv {
    Write-Step "Configuration environnement virtuel Python..."

    # Chercher un venv existant
    $possibleVenvs = @(
        (Join-Path $BackendPath ".winvenv"),
        (Join-Path $BackendPath ".venv"),
        (Join-Path $ProjectRoot ".venv"),
        (Join-Path $ProjectRoot ".venv311")
    )

    $foundVenv = $null
    foreach ($venv in $possibleVenvs) {
        $activateScript = Join-Path $venv "Scripts\Activate.ps1"
        if (Test-Path $activateScript) {
            $foundVenv = $venv
            break
        }
    }

    if ($foundVenv) {
        $script:VenvPath = $foundVenv
        Write-Success "Environnement virtuel trouve: $foundVenv"
    } else {
        Write-Info "Creation de l'environnement virtuel..."
        $newVenv = Join-Path $BackendPath ".winvenv"
        & $script:PythonCmd -m venv $newVenv
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Echec de la creation de l'environnement virtuel"
            return $false
        }
        $script:VenvPath = $newVenv
        Write-Success "Environnement virtuel cree"
        $script:NeedInstall = $true
    }

    # Activation
    $activateScript = Join-Path $script:VenvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        try {
            . $activateScript
            Write-Success "Environnement virtuel active"
        } catch {
            Write-Err "Impossible d'activer l'environnement virtuel: $_"
            return $false
        }
    } else {
        Write-Err "Script d'activation non trouve: $activateScript"
        return $false
    }

    return $true
}

# Installation des dependances
function Install-Dependencies {
    param([switch]$Force)

    Write-Step "Verification des dependances..."

    # Backend (Python)
    if ($Force -or $script:NeedInstall) {
        Write-Info "Installation des dependances Python..."
        $reqFile = Join-Path $BackendPath "requirements.txt"
        if (Test-Path $reqFile) {
            & pip install -r $reqFile --quiet
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Dependances Python installees"
            } else {
                Write-Warn "Certaines dependances Python n'ont pas pu etre installees"
            }
        }
    } else {
        # Verification rapide
        $testImport = & python -c "import fastapi, uvicorn" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Dependances Python OK"
        } else {
            Write-Info "Installation des dependances Python manquantes..."
            $reqFile = Join-Path $BackendPath "requirements.txt"
            & pip install -r $reqFile --quiet
        }
    }

    # Frontend (npm)
    $nodeModules = Join-Path $FrontendPath "node_modules"
    if ($Force -or -not (Test-Path $nodeModules)) {
        Write-Info "Installation des dependances Node.js..."
        Push-Location $FrontendPath
        npm ci --silent 2>$null
        if ($LASTEXITCODE -ne 0) {
            npm install --silent 2>$null
        }
        Pop-Location
        Write-Success "Dependances Node.js installees"
    } else {
        Write-Success "Dependances Node.js OK"
    }
}

# Demarrage Backend
function Start-Backend {
    Write-Step "Demarrage du Backend (FastAPI)..."

    $pythonExe = Join-Path $script:VenvPath "Scripts\python.exe"

    $script:BackendJob = Start-Job -ScriptBlock {
        param($backendPath, $pythonExe)
        Set-Location $backendPath
        & $pythonExe -m uvicorn app:app --reload --host 127.0.0.1 --port 8000 2>&1
    } -ArgumentList $BackendPath, $pythonExe

    Write-Info "Backend demarre (Job ID: $($script:BackendJob.Id))"
    Write-Info "URL: http://localhost:$BackendPort"
    Write-Info "API Docs: http://localhost:$BackendPort/docs"

    return $true
}

# Demarrage Frontend
function Start-Frontend {
    Write-Step "Demarrage du Frontend (Next.js)..."

    $script:FrontendJob = Start-Job -ScriptBlock {
        param($frontendPath, $backendPort)
        Set-Location $frontendPath
        $env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:$backendPort"
        npm run dev 2>&1
    } -ArgumentList $FrontendPath, $BackendPort

    Write-Info "Frontend demarre (Job ID: $($script:FrontendJob.Id))"
    Write-Info "URL: http://localhost:$FrontendPort"

    return $true
}

# Health Check
function Wait-ForServices {
    Write-Step "Attente des services..."

    $maxAttempts = 30
    $attempt = 0
    $backendReady = $Backend -eq $false -and $Frontend -eq $true
    $frontendReady = $Frontend -eq $false -and $Backend -eq $true

    while ($attempt -lt $maxAttempts) {
        $attempt++

        # Check Backend
        if (-not $backendReady -and -not $Frontend) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/docs" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Success "Backend pret!"
                    $backendReady = $true
                }
            } catch { }
        }

        # Check Frontend
        if (-not $frontendReady -and -not $Backend) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Success "Frontend pret!"
                    $frontendReady = $true
                }
            } catch { }
        }

        if ($backendReady -and $frontendReady) {
            return $true
        }

        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }

    Write-Host ""
    if (-not $backendReady -and -not $Frontend) {
        Write-Warn "Backend n'a pas repondu dans le temps imparti"
    }
    if (-not $frontendReady -and -not $Backend) {
        Write-Warn "Frontend n'a pas repondu dans le temps imparti"
    }

    return $true
}

# Afficher les informations finales
function Show-Summary {
    Write-Host ""
    Write-Host "  =========================================================" -ForegroundColor Green
    Write-Host "  |           APPLICATION DEMARREE !                      |" -ForegroundColor Green
    Write-Host "  =========================================================" -ForegroundColor Green
    Write-Host ""

    if (-not $Frontend) {
        Write-Host "  Backend API:     " -NoNewline -ForegroundColor White
        Write-Host "http://localhost:$BackendPort" -ForegroundColor Cyan
        Write-Host "  Documentation:   " -NoNewline -ForegroundColor White
        Write-Host "http://localhost:$BackendPort/docs" -ForegroundColor Cyan
    }

    if (-not $Backend) {
        Write-Host "  Frontend:        " -NoNewline -ForegroundColor White
        Write-Host "http://localhost:$FrontendPort" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "  Identifiants:    " -NoNewline -ForegroundColor White
    Write-Host "admin / secret" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Ctrl+C pour arreter les services" -ForegroundColor Gray
    Write-Host ""
}

# Nettoyage a la fermeture
function Stop-Services {
    Write-Host ""
    Write-Step "Arret des services..."

    if ($script:BackendJob) {
        Stop-Job -Job $script:BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:BackendJob -Force -ErrorAction SilentlyContinue
        Write-Success "Backend arrete"
    }

    if ($script:FrontendJob) {
        Stop-Job -Job $script:FrontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:FrontendJob -Force -ErrorAction SilentlyContinue
        Write-Success "Frontend arrete"
    }

    Write-Host ""
    Write-Host "  A bientot!" -ForegroundColor Magenta
    Write-Host ""
}

# Gestionnaire Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-Services }

# Fonction principale
function Start-BudgetApp {
    try {
        Show-Banner

        # Prerequis
        if (-not (Test-Prerequisites)) {
            exit 1
        }

        # Ports
        if (-not (Test-Ports)) {
            exit 1
        }

        # Environnement virtuel (sauf si frontend seul)
        if (-not $Frontend) {
            if (-not (Initialize-VirtualEnv)) {
                exit 1
            }
        }

        # Dependances
        Install-Dependencies -Force:$Install

        # Demarrage services
        if (-not $Frontend) {
            Start-Backend
        }

        if (-not $Backend) {
            Start-Frontend
        }

        # Attendre que les services soient prets
        Wait-ForServices

        # Ouvrir le navigateur
        if (-not $NoBrowser -and -not $Backend) {
            Start-Process "http://localhost:$FrontendPort"
        }

        # Afficher le resume
        Show-Summary

        # Boucle principale - afficher les logs
        Write-Host "  Logs des services (Ctrl+C pour arreter):" -ForegroundColor Gray
        Write-Host "  -----------------------------------------" -ForegroundColor Gray

        while ($true) {
            # Afficher les logs du backend
            if ($script:BackendJob) {
                $output = Receive-Job -Job $script:BackendJob -ErrorAction SilentlyContinue
                if ($output) {
                    $output | ForEach-Object {
                        Write-Host "  [API] $_" -ForegroundColor DarkCyan
                    }
                }
            }

            # Afficher les logs du frontend
            if ($script:FrontendJob) {
                $output = Receive-Job -Job $script:FrontendJob -ErrorAction SilentlyContinue
                if ($output) {
                    $output | ForEach-Object {
                        Write-Host "  [WEB] $_" -ForegroundColor DarkMagenta
                    }
                }
            }

            Start-Sleep -Milliseconds 500

            # Verifier si les jobs sont toujours actifs
            $jobsRunning = $false
            if ($script:BackendJob -and $script:BackendJob.State -eq 'Running') { $jobsRunning = $true }
            if ($script:FrontendJob -and $script:FrontendJob.State -eq 'Running') { $jobsRunning = $true }

            if (-not $jobsRunning -and ($script:BackendJob -or $script:FrontendJob)) {
                Write-Warn "Un ou plusieurs services se sont arretes"
                break
            }
        }

    } catch {
        Write-Err "Erreur: $_"
    } finally {
        Stop-Services
    }
}

# Execution
Start-BudgetApp
