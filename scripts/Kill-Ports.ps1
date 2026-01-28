<#
.SYNOPSIS
    Tue les processus utilisant les ports 3000 et 8000
#>

Write-Host "`nArret des processus sur les ports 3000 et 8000..." -ForegroundColor Cyan

# Port 3000
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($port3000) {
    $pids = $port3000.OwningProcess | Select-Object -Unique
    foreach ($pid in $pids) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  -> Port 3000: Arret de $($process.ProcessName) (PID: $pid)" -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] Port 3000 libere" -ForegroundColor Green
} else {
    Write-Host "  -> Port 3000 deja libre" -ForegroundColor Gray
}

# Port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $pids = $port8000.OwningProcess | Select-Object -Unique
    foreach ($pid in $pids) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  -> Port 8000: Arret de $($process.ProcessName) (PID: $pid)" -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] Port 8000 libere" -ForegroundColor Green
} else {
    Write-Host "  -> Port 8000 deja libre" -ForegroundColor Gray
}

# Tuer aussi les processus node et python orphelins lies au projet
Write-Host "`nNettoyage des processus orphelins..." -ForegroundColor Cyan

Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  -> Arret node.exe (PID: $($_.Id))" -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "`n[OK] Ports liberes!" -ForegroundColor Green
Write-Host "Vous pouvez maintenant relancer l'application avec: .\Start-BudgetApp.ps1`n" -ForegroundColor White
