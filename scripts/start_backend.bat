@echo off
title Backend API - Budget Famille
color 0B

echo ==========================================
echo   BACKEND API - BUDGET FAMILLE v2.3
echo ==========================================

REM Changer vers le dossier du script
cd /d "%~dp0"

REM Aller dans backend
cd backend

echo Activation environnement virtuel...
call .venv\Scripts\activate.bat

echo Demarrage du serveur backend...
echo Backend API disponible sur: http://127.0.0.1:8000
echo Documentation API: http://127.0.0.1:8000/docs
echo.
echo CTRL+C pour arreter le serveur
echo.

python app_windows.py

pause