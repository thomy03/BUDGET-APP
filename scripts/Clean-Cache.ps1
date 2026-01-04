<#
.SYNOPSIS
    Nettoie le cache Next.js et relance l'application
#>

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendPath = Join-Path $ProjectRoot "frontend"

Write-Host "`nNettoyage du cache Next.js..." -ForegroundColor Cyan

# Arreter les processus node
Write-Host "  -> Arret des processus node..." -ForegroundColor White
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# Supprimer le dossier .next
$nextCache = Join-Path $FrontendPath ".next"
if (Test-Path $nextCache) {
    Write-Host "  -> Suppression du dossier .next..." -ForegroundColor White
    Remove-Item -Path $nextCache -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Cache .next supprime" -ForegroundColor Green
} else {
    Write-Host "  -> Pas de cache .next a supprimer" -ForegroundColor Gray
}

# Supprimer node_modules/.cache si existe
$nodeCache = Join-Path $FrontendPath "node_modules\.cache"
if (Test-Path $nodeCache) {
    Write-Host "  -> Suppression du cache node_modules..." -ForegroundColor White
    Remove-Item -Path $nodeCache -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] Cache node_modules supprime" -ForegroundColor Green
}

Write-Host "`n[OK] Cache nettoye!" -ForegroundColor Green
Write-Host "Relancez l'application avec: .\Full-Reset.ps1`n" -ForegroundColor White
