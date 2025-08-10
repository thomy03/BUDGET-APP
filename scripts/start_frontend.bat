@echo off
title Frontend - Budget Famille
color 0E

echo ==========================================
echo   FRONTEND - BUDGET FAMILLE v2.3
echo ==========================================

REM Changer vers le dossier du script
cd /d "%~dp0"

REM Aller dans frontend
cd frontend

echo Configuration variable d'environnement...
set NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000

echo Demarrage du serveur frontend...
echo Frontend disponible sur: http://localhost:45678
echo.
echo CTRL+C pour arreter le serveur
echo.

npm run dev

pause