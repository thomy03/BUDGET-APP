# BUDGET FAMILLE v2.3 - SETUP ENVIRONNEMENT VIRTUEL
# Script PowerShell pour créer .venv selon les bonnes pratiques DevOps

Write-Host "🔧 CRÉATION ENVIRONNEMENT VIRTUEL .venv" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# Étape 1: Vérification Python
Write-Host "`n1. Vérification Python..." -ForegroundColor Yellow
try {
    $pythonVersion = py -0p 2>$null
    if ($pythonVersion) {
        Write-Host "✅ Versions Python disponibles:" -ForegroundColor Green
        py -0p
        $pythonCmd = "py -3.11"  # Priorise Python 3.11 si disponible
    } else {
        $pythonStandard = python --version 2>$null
        if ($pythonStandard) {
            Write-Host "✅ Python trouvé: $pythonStandard" -ForegroundColor Green
            $pythonCmd = "python"
        } else {
            Write-Host "❌ Python non trouvé! Installez Python 3.11+ depuis https://python.org" -ForegroundColor Red
            Write-Host "   Cochez 'Add Python to PATH' lors de l'installation" -ForegroundColor Yellow
            exit 1
        }
    }
} catch {
    Write-Host "❌ Python non trouvé! Installez Python 3.11+ depuis https://python.org" -ForegroundColor Red
    exit 1
}

# Étape 2: Nettoyage (si .venv existe déjà)
Write-Host "`n2. Nettoyage environnement existant..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "⚠️  Environnement .venv existant détecté" -ForegroundColor Yellow
    $response = Read-Host "Voulez-vous le supprimer et recréer? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "🗑️  Suppression .venv..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
        Write-Host "✅ .venv supprimé" -ForegroundColor Green
    } else {
        Write-Host "❌ Opération annulée" -ForegroundColor Red
        exit 1
    }
}

# Étape 3: Création .venv
Write-Host "`n3. Création environnement virtuel .venv..." -ForegroundColor Yellow
try {
    Write-Host "Commande: $pythonCmd -m venv .venv" -ForegroundColor Cyan
    Invoke-Expression "$pythonCmd -m venv .venv"
    Write-Host "✅ Environnement virtuel .venv créé" -ForegroundColor Green
} catch {
    Write-Host "❌ Erreur lors de la création de .venv" -ForegroundColor Red
    Write-Host "   Vérifiez que Python est correctement installé" -ForegroundColor Yellow
    exit 1
}

# Étape 4: Configuration politique d'exécution
Write-Host "`n4. Configuration PowerShell..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
    Write-Host "✅ Politique d'exécution configurée pour cette session" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Impossible de modifier la politique d'exécution" -ForegroundColor Yellow
    Write-Host "   Continuez manuellement si nécessaire" -ForegroundColor Cyan
}

# Étape 5: Activation .venv
Write-Host "`n5. Activation environnement virtuel..." -ForegroundColor Yellow
try {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "✅ Environnement virtuel activé" -ForegroundColor Green
    
    # Vérification
    $pythonPath = (Get-Command python).Source
    Write-Host "📍 Python actif: $pythonPath" -ForegroundColor Cyan
    $pythonVersion = python -V
    Write-Host "📋 Version: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Erreur lors de l'activation" -ForegroundColor Red
    Write-Host "   Essayez manuellement: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

# Étape 6: Mise à jour pip et outils
Write-Host "`n6. Mise à jour des outils Python..." -ForegroundColor Yellow
try {
    Write-Host "Mise à jour pip, setuptools, wheel..." -ForegroundColor Cyan
    python -m pip install --upgrade pip setuptools wheel
    Write-Host "✅ Outils Python mis à jour" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Avertissement: Impossible de mettre à jour pip" -ForegroundColor Yellow
}

# Étape 7: Installation dépendances backend
Write-Host "`n7. Installation dépendances backend..." -ForegroundColor Yellow
if (Test-Path "backend\requirements.txt") {
    try {
        Write-Host "Installation depuis backend\requirements.txt..." -ForegroundColor Cyan
        python -m pip install -r backend\requirements.txt
        Write-Host "✅ Dépendances backend installées" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur lors de l'installation des dépendances" -ForegroundColor Red
        Write-Host "   Essayez manuellement: python -m pip install -r backend\requirements.txt" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Fichier backend\requirements.txt non trouvé" -ForegroundColor Yellow
}

# Étape 8: Test de fonctionnement
Write-Host "`n8. Test des imports critiques..." -ForegroundColor Yellow
try {
    python -c "import fastapi, uvicorn; print('✅ FastAPI et Uvicorn OK')"
    python -c "import pandas; print('✅ Pandas OK')"
    python -c "import sqlalchemy; print('✅ SQLAlchemy OK')"
    Write-Host "✅ Tous les imports critiques fonctionnent" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Certains imports ont échoué, mais l'environnement est créé" -ForegroundColor Yellow
}

# Étape 9: Instructions finales
Write-Host "`n🎉 ENVIRONNEMENT VIRTUEL .venv CRÉÉ AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

Write-Host "`n📋 COMMANDES POUR UTILISER L'ENVIRONNEMENT:" -ForegroundColor Cyan
Write-Host "1. Activation (à faire à chaque nouvelle session PowerShell):" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow

Write-Host "`n2. Lancement Backend (depuis la racine):" -ForegroundColor White
Write-Host "   uvicorn app.main:app --app-dir backend --reload --port 8000" -ForegroundColor Yellow

Write-Host "`n3. Lancement Backend (depuis backend/):" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Yellow
Write-Host "   uvicorn app.main:app --reload --port 8000" -ForegroundColor Yellow

Write-Host "`n4. Lancement Frontend:" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Yellow
Write-Host "   npm ci" -ForegroundColor Yellow
Write-Host "   npm run dev" -ForegroundColor Yellow

Write-Host "`n🔗 URLS D'ACCÈS:" -ForegroundColor Cyan
Write-Host "• Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "• Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "• Documentation API: http://127.0.0.1:8000/docs" -ForegroundColor White

Write-Host "`n⚠️  NOTES IMPORTANTES:" -ForegroundColor Yellow
Write-Host "• L'environnement .venv est créé à la RACINE du projet" -ForegroundColor White
Write-Host "• Activez l'environnement à chaque nouvelle session PowerShell" -ForegroundColor White
Write-Host "• Utilisez toujours 'python -m pip' pour installer des packages" -ForegroundColor White

Write-Host "`n🧪 PRÊT POUR LE DÉVELOPPEMENT!" -ForegroundColor Magenta
Write-Host "Votre environnement virtuel est configuré selon les bonnes pratiques DevOps." -ForegroundColor White

Write-Host "`nAppuyez sur une touche pour fermer..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")