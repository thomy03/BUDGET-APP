@echo off
title Budget Famille v2.3 - Demarrage Simple
color 0A

echo.
echo ==========================================
echo   BUDGET FAMILLE v2.3 - VERSION WINDOWS
echo ==========================================
echo.

cd /d "%~dp0"

echo Configuration Backend...
cd backend

echo Verification Python...
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERREUR: Python non trouve. Installez Python depuis python.org
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)
echo Python OK

echo Creation environnement virtuel...
if not exist ".venv" (
    %PYTHON_CMD% -m venv .venv
)

echo Activation environnement virtuel...
call .venv\Scripts\activate.bat

echo Installation dependances (version Windows)...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements_windows.txt

echo Configuration environnement...
if not exist ".env" (
    echo JWT_SECRET_KEY=test_secret_key_for_windows > .env
    echo DB_ENCRYPTION_PASSWORD=not_used >> .env
)

echo.
echo ==========================================
echo   DEMARRAGE BACKEND
echo ==========================================

echo Demarrage serveur backend...
start "Backend API" cmd /k "cd /d \"%cd%\" && .venv\Scripts\activate.bat && %PYTHON_CMD% app_windows.py"

timeout /t 3 /nobreak >nul

cd ..\frontend

echo.
echo ==========================================  
echo   DEMARRAGE FRONTEND
echo ==========================================

echo Verification Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Node.js non trouve. Installez Node.js depuis nodejs.org
    pause
    exit /b 1
)
echo Node.js OK

echo Demarrage serveur frontend...
set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
start "Frontend Next.js" cmd /k "cd /d \"%cd%\" && set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ==========================================
echo   APPLICATION DEMARREE !
echo ==========================================
echo.
color 0E
echo INFORMATIONS:
echo - Frontend: http://localhost:45678
echo - Backend:  http://127.0.0.1:8000  
echo - Identifiants: admin / secret
echo.
echo 2 fenetres CMD sont ouvertes (laissez-les ouvertes)
echo.
echo OUVERTURE DU NAVIGATEUR...
start http://localhost:45678

echo.
echo Appuyez sur une touche pour fermer...
pause >nul