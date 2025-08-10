@echo off
echo ====================================
echo   Budget Famille v2.3 - Test Mode
echo   Validation Import CSV
echo ====================================
echo.

REM Vérification Python
python3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python 3 non trouve
    echo Veuillez installer Python 3.8+ 
    pause
    exit /b 1
)

REM Création environnement virtuel si nécessaire
if not exist ".venv" (
    echo Creation environnement virtuel...
    python3 -m venv .venv
)

REM Activation environnement
echo Activation environnement virtuel...
call .venv\Scripts\activate.bat

REM Installation dépendances
echo Installation des dependances...
pip install -r requirements.txt

REM Configuration mode test
set APP_ENV=test
set BUDGET_DATA_DIR=%CD%\data-test

REM Création dossier test si nécessaire
if not exist "data-test" mkdir data-test

echo.
echo ====================================
echo   Environnement pret pour les tests
echo ====================================
echo.
echo Fichiers de test disponibles dans:
echo   tests\csv-samples\
echo.
echo Guide de validation:
echo   GUIDE_VALIDATION_UTILISATEUR_V2.3.md
echo.
echo Demarrage du backend...
echo.

REM Lancement backend
python3 backend/app_simple.py

pause