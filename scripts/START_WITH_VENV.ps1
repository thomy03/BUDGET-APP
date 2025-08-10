# BUDGET FAMILLE v2.3 - DÉMARRAGE AVEC ENVIRONNEMENT VIRTUEL .venv
# Script PowerShell pour lancement avec .venv selon bonnes pratiques DevOps

Write-Host "🚀 DÉMARRAGE BUDGET FAMILLE v2.3 AVEC .venv" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Vérification .venv
Write-Host "`n1. Vérification environnement virtuel..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "❌ Environnement virtuel .venv non trouvé!" -ForegroundColor Red
    Write-Host "   Exécutez d'abord: .\SETUP_VENV_WINDOWS.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Environnement virtuel .venv trouvé" -ForegroundColor Green

# Configuration politique d'exécution
Write-Host "`n2. Configuration PowerShell..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
    Write-Host "✅ Politique d'exécution configurée" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Continuez si demandé par Windows" -ForegroundColor Yellow
}

# Activation environnement virtuel
Write-Host "`n3. Activation environnement virtuel..." -ForegroundColor Yellow
try {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "✅ Environnement virtuel activé" -ForegroundColor Green
    
    # Vérification
    $pythonPath = (Get-Command python).Source
    if ($pythonPath -like "*\.venv\*") {
        Write-Host "✅ Python pointe vers .venv: $pythonPath" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Python ne pointe pas vers .venv: $pythonPath" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Erreur lors de l'activation de .venv" -ForegroundColor Red
    Write-Host "   Exécutez manuellement: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

# Vérification Node.js pour frontend
Write-Host "`n4. Vérification Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>$null
    if ($nodeVersion) {
        Write-Host "✅ Node.js trouvé: $nodeVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Node.js non trouvé! Installez Node.js 18+ depuis https://nodejs.org" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Node.js non trouvé! Installez Node.js 18+ depuis https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Test des imports Python critiques
Write-Host "`n5. Test des dépendances Python..." -ForegroundColor Yellow
try {
    python -c "import fastapi, uvicorn, pandas; print('✅ Imports critiques OK')" 2>$null
    Write-Host "✅ Toutes les dépendances Python sont disponibles" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Certaines dépendances manquent, installation automatique..." -ForegroundColor Yellow
    python -m pip install -r backend\requirements.txt
}

# Démarrage Backend
Write-Host "`n6. Démarrage Backend..." -ForegroundColor Yellow
Write-Host "Backend sera accessible sur http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Documentation API: http://127.0.0.1:8000/docs" -ForegroundColor Green

# Commande optimisée selon l'analyse GPT-5
Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000" -WindowStyle Normal

# Attendre que le backend démarre
Write-Host "Attente démarrage backend (5 secondes)..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Configuration Frontend
Write-Host "`n7. Configuration Frontend..." -ForegroundColor Yellow
Set-Location frontend

# Installation dépendances npm si nécessaire
if (-not (Test-Path "node_modules")) {
    Write-Host "Installation dépendances Node.js..." -ForegroundColor Cyan
    npm ci
} else {
    Write-Host "✅ Dépendances Node.js déjà installées" -ForegroundColor Green
}

# Configuration variable d'environnement
$env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000"

# Démarrage Frontend
Write-Host "`n8. Démarrage Frontend..." -ForegroundColor Yellow
Write-Host "Frontend sera accessible sur http://localhost:3000" -ForegroundColor Green

Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; `$env:NEXT_PUBLIC_API_BASE='http://127.0.0.1:8000'; npm run dev" -WindowStyle Normal

# Retour à la racine
Set-Location ..

# Instructions finales
Write-Host "`n🎉 APPLICATION DÉMARRÉE AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

Write-Host "`n📋 INFORMATIONS DE CONNEXION:" -ForegroundColor Cyan
Write-Host "• Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "• Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "• Documentation API: http://127.0.0.1:8000/docs" -ForegroundColor White

Write-Host "`n🔑 IDENTIFIANTS DE TEST:" -ForegroundColor Cyan
Write-Host "• Utilisateur: admin" -ForegroundColor White
Write-Host "• Mot de passe: secret" -ForegroundColor White

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "• Laissez les deux fenêtres PowerShell ouvertes" -ForegroundColor White
Write-Host "• Backend utilise l'environnement virtuel .venv" -ForegroundColor White
Write-Host "• Frontend utilise Node.js global" -ForegroundColor White
Write-Host "• Ouvrez http://localhost:3000 dans votre navigateur" -ForegroundColor White

Write-Host "`n🔧 ENVIRONNEMENT VIRTUEL:" -ForegroundColor Cyan
Write-Host "• Activation manuelle: .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "• Installation package: python -m pip install <package>" -ForegroundColor White
Write-Host "• Désactivation: deactivate" -ForegroundColor White

Write-Host "`n🧪 PRÊT POUR LE DÉVELOPPEMENT!" -ForegroundColor Magenta
Write-Host "Environnement virtuel .venv configuré selon les bonnes pratiques DevOps." -ForegroundColor White

Write-Host "`nAppuyez sur une touche pour fermer..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")