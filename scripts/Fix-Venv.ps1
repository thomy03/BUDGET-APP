<#
.SYNOPSIS
    Repare l'environnement virtuel Python (Windows + Python 3.13)
#>

$BackendPath = Join-Path (Split-Path -Parent $PSScriptRoot) "backend"
$VenvPath = Join-Path $BackendPath ".winvenv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "`nReparation de l'environnement virtuel..." -ForegroundColor Cyan

if (Test-Path $PythonExe) {
    Write-Host "  -> Mise a jour de pip..." -ForegroundColor White
    & $PythonExe -m pip install --upgrade pip

    Write-Host "  -> Installation de setuptools et wheel..." -ForegroundColor White
    & $PythonExe -m pip install --upgrade setuptools wheel

    Write-Host "  -> Installation des dependances (requirements_win.txt)..." -ForegroundColor White
    $reqFile = Join-Path $BackendPath "requirements_win.txt"
    if (Test-Path $reqFile) {
        & $PythonExe -m pip install -r $reqFile
    } else {
        Write-Host "[!] Fichier requirements_win.txt non trouve, utilisation de requirements.txt" -ForegroundColor Yellow
        $reqFile = Join-Path $BackendPath "requirements.txt"
        & $PythonExe -m pip install -r $reqFile
    }

    Write-Host "`n[OK] Environnement virtuel repare!" -ForegroundColor Green
} else {
    Write-Host "[ERREUR] Python non trouve: $PythonExe" -ForegroundColor Red
    Write-Host "Creez d'abord l'environnement avec: python -m venv $VenvPath" -ForegroundColor Yellow
}
