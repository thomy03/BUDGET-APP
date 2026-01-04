<#
.SYNOPSIS
    Reset complet: tue les ports, reinstalle les dependances, relance l'app
#>

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$VenvPath = Join-Path $BackendPath ".winvenv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Magenta
Write-Host "  |  BUDGET FAMILLE - RESET COMPLET     |" -ForegroundColor Magenta
Write-Host "  ========================================" -ForegroundColor Magenta
Write-Host ""

# Etape 1: Tuer les processus
Write-Host "[1/5] Arret des processus existants..." -ForegroundColor Cyan

# Tuer node
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  -> Arret node.exe (PID: $($_.Id))" -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Tuer python (uvicorn)
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  -> Arret python.exe (PID: $($_.Id))" -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Liberer port 3000
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($port3000) {
    $pids = $port3000.OwningProcess | Select-Object -Unique
    foreach ($pid in $pids) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}

# Liberer port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $pids = $port8000.OwningProcess | Select-Object -Unique
    foreach ($pid in $pids) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "  [OK] Processus arretes" -ForegroundColor Green
Start-Sleep -Seconds 2

# Etape 2: Installer pydantic-settings
Write-Host "`n[2/5] Installation de pydantic-settings..." -ForegroundColor Cyan
if (Test-Path $PythonExe) {
    & $PythonExe -m pip install pydantic-settings --quiet
    Write-Host "  [OK] pydantic-settings installe" -ForegroundColor Green
} else {
    Write-Host "  [!] Python venv non trouve" -ForegroundColor Yellow
}

# Etape 3: Verifier node_modules
Write-Host "`n[3/5] Verification des dependances frontend..." -ForegroundColor Cyan
$nodeModules = Join-Path $FrontendPath "node_modules"
$nextBin = Join-Path $nodeModules ".bin\next.cmd"

if (-not (Test-Path $nextBin)) {
    Write-Host "  -> Installation des dependances npm..." -ForegroundColor White
    Push-Location $FrontendPath
    npm install --silent 2>$null
    Pop-Location
}
Write-Host "  [OK] Dependances frontend OK" -ForegroundColor Green

# Etape 4: Demarrer le backend
Write-Host "`n[4/5] Demarrage du Backend..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($backendPath, $pythonExe)
    Set-Location $backendPath
    & $pythonExe -m uvicorn app:app --reload --host 127.0.0.1 --port 8000 2>&1
} -ArgumentList $BackendPath, $PythonExe

Write-Host "  -> Backend demarre (Job: $($backendJob.Id))" -ForegroundColor White
Write-Host "  -> URL: http://localhost:8000" -ForegroundColor Gray

# Attendre que le backend soit pret
Write-Host "  -> Attente du backend..." -ForegroundColor Gray
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "." -NoNewline
}
Write-Host ""
if ($ready) {
    Write-Host "  [OK] Backend pret!" -ForegroundColor Green
} else {
    Write-Host "  [!] Backend peut ne pas etre pret" -ForegroundColor Yellow
}

# Etape 5: Demarrer le frontend
Write-Host "`n[5/5] Demarrage du Frontend..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    param($frontendPath)
    Set-Location $frontendPath
    $env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000"
    npm run dev 2>&1
} -ArgumentList $FrontendPath

Write-Host "  -> Frontend demarre (Job: $($frontendJob.Id))" -ForegroundColor White
Write-Host "  -> URL: http://localhost:3000" -ForegroundColor Gray

# Attendre que le frontend soit pret
Write-Host "  -> Attente du frontend..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Ouvrir le navigateur
Start-Process "http://localhost:3000"

# Afficher le resume
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  |       APPLICATION DEMARREE !        |" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Identifiants: admin / secret" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Ctrl+C pour arreter" -ForegroundColor Gray
Write-Host ""

# Boucle de logs
while ($true) {
    # Backend logs
    $output = Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
    if ($output) {
        $output | ForEach-Object {
            Write-Host "  [API] $_" -ForegroundColor DarkCyan
        }
    }

    # Frontend logs
    $output = Receive-Job -Job $frontendJob -ErrorAction SilentlyContinue
    if ($output) {
        $output | ForEach-Object {
            Write-Host "  [WEB] $_" -ForegroundColor DarkMagenta
        }
    }

    Start-Sleep -Milliseconds 500

    # Verifier si les jobs tournent
    if ($backendJob.State -ne 'Running' -and $frontendJob.State -ne 'Running') {
        Write-Host "`n[!] Les services se sont arretes" -ForegroundColor Yellow
        break
    }
}

# Nettoyage
Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue
Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
Write-Host "`nServices arretes. A bientot!" -ForegroundColor Magenta
