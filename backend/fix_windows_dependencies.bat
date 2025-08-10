@echo off
REM Script de correction des dépendances Python pour Windows
REM Résout l'erreur "Probleme configuration backend"

echo ===== CORRECTION DÉPENDANCES BACKEND PYTHON =====
echo.

REM Vérification environnement virtuel
if not exist "%VIRTUAL_ENV%" (
    echo ERREUR: Environnement virtuel non activé
    echo Exécutez d'abord: venv\Scripts\activate
    echo Puis relancez ce script.
    pause
    exit /b 1
)

echo Environnement virtuel détecté: %VIRTUAL_ENV%
echo.

REM Mise à jour pip
echo 1/4 - Mise à jour pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERREUR: Mise à jour pip échouée
    pause
    exit /b 1
)

REM Installation dépendances Windows friendly
echo.
echo 2/4 - Installation dépendances Windows...
echo Tentative avec requirements_windows.txt (sans SQLCipher)...
python -m pip install -r requirements_windows.txt
if errorlevel 1 (
    echo.
    echo Échec avec requirements_windows.txt
    echo Tentative avec requirements_minimal.txt...
    python -m pip install -r requirements_minimal.txt
    if errorlevel 1 (
        echo ERREUR: Installation dépendances échouée
        pause
        exit /b 1
    )
)

REM Correction spécifique python-magic sur Windows
echo.
echo 3/4 - Correction python-magic pour Windows...
python -m pip install python-magic-bin
if errorlevel 1 (
    echo Avertissement: python-magic-bin non installé (optionnel)
)

REM Test configuration
echo.
echo 4/4 - Test configuration backend...
python -c "import app; print('✅ Backend OK')"
if errorlevel 1 (
    echo.
    echo ERREUR: Test backend échoué
    echo Détails du problème:
    python diagnostic_windows.py
    pause
    exit /b 1
)

echo.
echo ===== CORRECTION RÉUSSIE =====
echo Le backend Python est maintenant configuré correctement.
echo.
echo Vous pouvez maintenant:
echo 1. Démarrer le backend: python -m uvicorn app:app --host 127.0.0.1 --port 8000
echo 2. Ou utiliser le script de démarrage existant
echo.
echo Note: SQLCipher n'est pas installé (optionnel sur Windows)
echo L'application utilise SQLite standard à la place.
echo.
pause