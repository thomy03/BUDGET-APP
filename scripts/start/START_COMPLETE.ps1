# ================================================
# SCRIPT DE DÉMARRAGE COMPLET - Budget Famille v2.3
# ================================================

Write-Host "🚀 Démarrage Budget Famille v2.3..." -ForegroundColor Cyan
Write-Host ""

# 1. CONFIGURATION ENVIRONNEMENT BACKEND
Write-Host "📦 Configuration Backend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\backend"

# Vérifier si .venv existe
if (-not (Test-Path ".\.venv")) {
    Write-Host "   Création environnement virtuel Python..." -ForegroundColor Gray
    python -m venv .venv
}

# Activer l'environnement virtuel
Write-Host "   Activation environnement virtuel..." -ForegroundColor Gray
& .\.venv\Scripts\Activate.ps1

# Installer/mettre à jour les dépendances
Write-Host "   Installation dépendances..." -ForegroundColor Gray
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Test du backend
Write-Host "   Test configuration backend..." -ForegroundColor Gray
$backendTest = python -c "import app; print('OK')" 2>&1
if ($backendTest -like "*OK*") {
    Write-Host "✅ Backend configuré avec succès" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur configuration backend: $backendTest" -ForegroundColor Red
    exit 1
}

# 2. CONFIGURATION FRONTEND  
Write-Host ""
Write-Host "🎨 Configuration Frontend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\frontend"

# Installer les dépendances Node.js si nécessaire
if (-not (Test-Path "node_modules")) {
    Write-Host "   Installation dépendances Node.js..." -ForegroundColor Gray
    npm install
}

Write-Host "✅ Frontend configuré avec succès" -ForegroundColor Green

# 3. DÉMARRAGE DES SERVICES
Write-Host ""
Write-Host "🔥 Démarrage des services..." -ForegroundColor Cyan

# Démarrer le backend en arrière-plan
Write-Host "   🖥️  Démarrage Backend sur http://127.0.0.1:8000..." -ForegroundColor Gray
Set-Location -Path "$PSScriptRoot\backend"
& .\.venv\Scripts\Activate.ps1
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& .\.venv\Scripts\Activate.ps1; python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000"

# Attendre que le backend soit prêt
Write-Host "   ⏳ Attente démarrage backend..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Démarrer le frontend
Write-Host "   🌐 Démarrage Frontend sur http://localhost:45678..." -ForegroundColor Gray
Set-Location -Path "$PSScriptRoot\frontend"
$env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:NEXT_PUBLIC_API_BASE='http://127.0.0.1:8000'; npm run dev"

# 4. INFORMATIONS FINALES
Write-Host ""
Write-Host "✅ DÉMARRAGE TERMINÉ !" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Interface Web: " -NoNewline -ForegroundColor White
Write-Host "http://localhost:45678" -ForegroundColor Cyan
Write-Host "🔑 Identifiants: " -NoNewline -ForegroundColor White  
Write-Host "admin / secret" -ForegroundColor Yellow
Write-Host "📚 API Docs: " -NoNewline -ForegroundColor White
Write-Host "http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 TESTS À EFFECTUER:" -ForegroundColor Magenta
Write-Host "   1. Connexion avec admin/secret"
Write-Host "   2. Import d'un fichier CSV"
Write-Host "   3. Vérification redirection automatique vers le mois"
Write-Host "   4. Test détection doublons (réimport même fichier)"
Write-Host ""
Write-Host "⚠️  Fermer ce terminal fermera les services" -ForegroundColor Red
Write-Host "💡 Appuyer sur une touche pour ouvrir l'interface web..."

# Ouvrir automatiquement le navigateur
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:45678"

Write-Host ""
Write-Host "🎉 Prêt pour les tests !" -ForegroundColor Green
Write-Host "Appuyer sur Ctrl+C pour arrêter les services"

# Maintenir le script ouvert
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "🛑 Arrêt des services..." -ForegroundColor Yellow
}