# BUDGET FAMILLE v2.3 - DÉMARRAGE WINDOWS
# Script PowerShell pour key user testing

Write-Host "🚀 DÉMARRAGE BUDGET FAMILLE v2.3 SÉCURISÉ" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Vérification Python
Write-Host "`n1. Vérification Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion) {
        Write-Host "✅ Python trouvé: $pythonVersion" -ForegroundColor Green
        $pythonCmd = "python"
    } else {
        $python3Version = python3 --version 2>$null
        if ($python3Version) {
            Write-Host "✅ Python3 trouvé: $python3Version" -ForegroundColor Green
            $pythonCmd = "python3"
        } else {
            Write-Host "❌ Python non trouvé! Installez Python 3.8+ depuis https://python.org" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "❌ Python non trouvé! Installez Python 3.8+ depuis https://python.org" -ForegroundColor Red
    exit 1
}

# Vérification Node.js
Write-Host "`n2. Vérification Node.js..." -ForegroundColor Yellow
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

Write-Host "`n3. Configuration Backend..." -ForegroundColor Yellow
Set-Location backend

# Création environnement virtuel
if (-not (Test-Path ".venv")) {
    Write-Host "Création environnement virtuel Python..." -ForegroundColor Cyan
    & $pythonCmd -m venv .venv
}

# Activation environnement virtuel
Write-Host "Activation environnement virtuel..." -ForegroundColor Cyan
.venv\Scripts\Activate.ps1

# Installation dépendances
Write-Host "Installation dépendances Python..." -ForegroundColor Cyan
& $pythonCmd -m pip install --upgrade pip
& $pythonCmd -m pip install -r requirements.txt

# Configuration variables d'environnement
if (-not (Test-Path ".env")) {
    Write-Host "Configuration fichier .env..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
}

Write-Host "`n4. Démarrage Backend..." -ForegroundColor Yellow
Write-Host "Backend démarré sur http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "API Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Green

# Démarrage du serveur FastAPI
Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; .venv\Scripts\Activate.ps1; & $pythonCmd -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

Write-Host "`n5. Configuration Frontend..." -ForegroundColor Yellow
Set-Location ..\frontend

# Installation dépendances npm
Write-Host "Installation dépendances Node.js..." -ForegroundColor Cyan
npm install

# Configuration variables d'environnement
$env:NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000"

Write-Host "`n6. Démarrage Frontend..." -ForegroundColor Yellow
Write-Host "Frontend démarré sur http://localhost:45678" -ForegroundColor Green

# Démarrage du serveur Next.js
Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; `$env:NEXT_PUBLIC_API_BASE='http://127.0.0.1:8000'; npm run dev" -WindowStyle Normal

Write-Host "`n🎉 APPLICATION DÉMARRÉE AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host "`n📋 INFORMATIONS DE CONNEXION:" -ForegroundColor Cyan
Write-Host "• Frontend: http://localhost:45678" -ForegroundColor White
Write-Host "• Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "• Documentation API: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "`n🔑 IDENTIFIANTS DE TEST:" -ForegroundColor Cyan
Write-Host "• Utilisateur: admin" -ForegroundColor White
Write-Host "• Mot de passe: secret" -ForegroundColor White

Write-Host "`n⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "• Laissez les deux fenêtres PowerShell ouvertes" -ForegroundColor White
Write-Host "• Backend et Frontend se lancent automatiquement" -ForegroundColor White
Write-Host "• Ouvrez http://localhost:45678 dans votre navigateur" -ForegroundColor White

Write-Host "`n🧪 PRÊT POUR KEY USER TESTING!" -ForegroundColor Magenta
Write-Host "Testez l'application et signalez tout problème." -ForegroundColor White

# Attendre que l'utilisateur ferme
Write-Host "`nAppuyez sur une touche pour fermer..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")