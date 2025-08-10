# Script PowerShell pour corriger les dépendances Python sur Windows
# Résout l'erreur "Probleme configuration backend"

Write-Host "===== CORRECTION DÉPENDANCES BACKEND PYTHON =====" -ForegroundColor Green
Write-Host ""

# Vérification environnement virtuel
if (-not $env:VIRTUAL_ENV) {
    Write-Host "ERREUR: Environnement virtuel non activé" -ForegroundColor Red
    Write-Host "Exécutez d'abord: venv\Scripts\activate" -ForegroundColor Yellow
    Write-Host "Puis relancez ce script." -ForegroundColor Yellow
    Read-Host "Appuyez sur Entrée pour continuer"
    exit 1
}

Write-Host "Environnement virtuel détecté: $env:VIRTUAL_ENV" -ForegroundColor Green
Write-Host ""

try {
    # Mise à jour pip
    Write-Host "1/4 - Mise à jour pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Mise à jour pip échouée"
    }
    Write-Host "✅ pip mis à jour" -ForegroundColor Green

    # Installation dépendances Windows friendly
    Write-Host ""
    Write-Host "2/4 - Installation dépendances Windows..." -ForegroundColor Cyan
    
    # Tentative avec requirements_windows.txt
    Write-Host "Tentative avec requirements_windows.txt (sans SQLCipher)..." -ForegroundColor Yellow
    python -m pip install -r requirements_windows.txt
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Échec avec requirements_windows.txt" -ForegroundColor Yellow
        Write-Host "Tentative avec requirements_minimal.txt..." -ForegroundColor Yellow
        python -m pip install -r requirements_minimal.txt
        
        if ($LASTEXITCODE -ne 0) {
            throw "Installation dépendances échouée"
        }
    }
    Write-Host "✅ Dépendances installées" -ForegroundColor Green

    # Correction spécifique python-magic sur Windows
    Write-Host ""
    Write-Host "3/4 - Correction python-magic pour Windows..." -ForegroundColor Cyan
    python -m pip install python-magic-bin
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ python-magic-bin installé" -ForegroundColor Green
    } else {
        Write-Host "⚠️  python-magic-bin non installé (optionnel)" -ForegroundColor Yellow
    }

    # Test configuration
    Write-Host ""
    Write-Host "4/4 - Test configuration backend..." -ForegroundColor Cyan
    $testResult = python -c "import app; print('✅ Backend OK')" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERREUR: Test backend échoué" -ForegroundColor Red
        Write-Host "Détails du problème:" -ForegroundColor Yellow
        python diagnostic_windows.py
        Read-Host "Appuyez sur Entrée pour continuer"
        exit 1
    }

    Write-Host $testResult -ForegroundColor Green

    # Succès
    Write-Host ""
    Write-Host "===== CORRECTION RÉUSSIE =====" -ForegroundColor Green
    Write-Host "Le backend Python est maintenant configuré correctement." -ForegroundColor Green
    Write-Host ""
    Write-Host "Vous pouvez maintenant:" -ForegroundColor Cyan
    Write-Host "1. Démarrer le backend: python -m uvicorn app:app --host 127.0.0.1 --port 8000" -ForegroundColor White
    Write-Host "2. Ou utiliser le script de démarrage existant" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: SQLCipher n'est pas installé (optionnel sur Windows)" -ForegroundColor Yellow
    Write-Host "L'application utilise SQLite standard à la place." -ForegroundColor Yellow

} catch {
    Write-Host ""
    Write-Host "ERREUR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solutions alternatives:" -ForegroundColor Yellow
    Write-Host "1. Exécutez: python diagnostic_windows.py" -ForegroundColor White
    Write-Host "2. Consultez GUIDE_DEPANNAGE_WINDOWS.md" -ForegroundColor White
    Write-Host "3. Installez manuellement: pip install -r requirements_minimal.txt" -ForegroundColor White
}

Write-Host ""
Read-Host "Appuyez sur Entrée pour continuer"