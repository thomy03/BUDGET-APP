@echo off
title Budget Famille v2.3 - Démarrage
color 0A

echo.
echo ============================================
echo   BUDGET FAMILLE v2.3 - DEMARRAGE
echo ============================================
echo.

echo [1/4] Configuration environnement Python...
cd /d "%~dp0\backend"

if not exist ".venv" (
    echo    Creation environnement virtuel...
    python -m venv .venv
)

echo    Activation environnement virtuel...
call .venv\Scripts\activate.bat

echo    Installation dependances...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1

echo    Test configuration backend...
python -c "import app; print('Backend OK')" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Probleme configuration backend
    pause
    exit /b 1
)

echo [2/4] Configuration Node.js...
cd /d "%~dp0\frontend"

if not exist "node_modules" (
    echo    Installation dependances Node.js...
    npm install >nul 2>&1
)

echo [3/4] Demarrage Backend...
cd /d "%~dp0\backend"
call .venv\Scripts\activate.bat
echo    Backend demarre sur http://127.0.0.1:8000
start "Backend Server" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000"

echo    Attente demarrage backend...
timeout /t 5 /nobreak >nul

echo [4/4] Demarrage Frontend...
cd /d "%~dp0\frontend"
echo    Frontend demarre sur http://localhost:45678
set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
start "Frontend Server" cmd /k "set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 && npm run dev"

echo.
echo ============================================
echo   DEMARRAGE TERMINE !
echo ============================================
echo.
echo Interface Web: http://localhost:45678
echo Identifiants : admin / secret
echo API Docs     : http://127.0.0.1:8000/docs
echo.
echo TESTS A EFFECTUER:
echo   1. Connexion avec admin/secret
echo   2. Import fichier CSV (test-navigation.csv)
echo   3. Verification redirection automatique
echo   4. Test detection doublons
echo.
echo Appuyer sur une touche pour ouvrir l'interface...
pause >nul

start http://localhost:45678

echo.
echo Services demarres dans des fenetres separees
echo Fermer cette fenetre pour continuer
pause