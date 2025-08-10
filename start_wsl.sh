#!/bin/bash

echo "🐧 Budget Famille v2.3 - Démarrage WSL"
echo "======================================="
echo

# Vérifier qu'on est dans WSL
if [[ ! -f /proc/version ]] || ! grep -q Microsoft /proc/version; then
    echo "❌ Ce script doit être exécuté dans WSL"
    exit 1
fi

# Aller dans le répertoire backend
cd "$(dirname "$0")/backend"

echo "📦 Configuration Backend..."

# Créer l'environnement virtuel si nécessaire
if [[ ! -d ".venv" ]]; then
    echo "   Création environnement virtuel Python..."
    python3 -m venv .venv
fi

# Activer l'environnement virtuel
echo "   Activation environnement virtuel..."
source .venv/bin/activate

# Mettre à jour pip et installer les dépendances
echo "   Installation dépendances..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Test du backend
echo "   Test configuration backend..."
if python3 -c "import app; print('Backend OK')" >/dev/null 2>&1; then
    echo "✅ Backend configuré avec succès"
else
    echo "❌ Erreur configuration backend"
    python3 -c "import app; print('Backend OK')"
    exit 1
fi

echo
echo "🎨 Configuration Frontend..."

# Aller dans le répertoire frontend
cd "../frontend"

# Installer les dépendances Node.js si nécessaire
if [[ ! -d "node_modules" ]]; then
    echo "   Installation dépendances Node.js..."
    npm install -q
fi

echo "✅ Frontend configuré avec succès"

echo
echo "🔥 Démarrage des services..."

# Démarrer le backend en arrière-plan
echo "   🖥️  Démarrage Backend sur http://127.0.0.1:8000..."
cd "../backend"
source .venv/bin/activate
python3 -m uvicorn app:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Attendre que le backend soit prêt
echo "   ⏳ Attente démarrage backend..."
sleep 5

# Vérifier que le backend répond
if curl -s http://127.0.0.1:8000/docs >/dev/null; then
    echo "✅ Backend démarré avec succès"
else
    echo "⚠️  Backend démarré mais pas encore prêt"
fi

# Démarrer le frontend
echo "   🌐 Démarrage Frontend sur http://localhost:45678..."
cd "../frontend"
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
npm run dev &
FRONTEND_PID=$!

echo
echo "============================================="
echo "✅ DÉMARRAGE WSL TERMINÉ !"
echo "============================================="
echo
echo "🌐 Interface Web: http://localhost:45678"
echo "🔑 Identifiants: admin / secret"  
echo "📚 API Docs: http://127.0.0.1:8000/docs"
echo "📁 Fichier test: test-navigation.csv"
echo
echo "📋 TESTS À EFFECTUER:"
echo "   1. Connexion avec admin/secret"
echo "   2. Import du fichier test-navigation.csv"
echo "   3. Vérification redirection automatique vers le mois"
echo "   4. Test détection doublons (réimport même fichier)"
echo
echo "🛑 Pour arrêter les services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo
echo "💡 Appuyer sur Ctrl+C pour arrêter"

# Attendre l'interruption
trap "echo '🛑 Arrêt des services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Boucle d'attente
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null || ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️  Un service s'est arrêté"
        break
    fi
    sleep 5
done

echo "🏁 Services arrêtés"