#!/bin/bash

# Script de validation complète de la solution Docker pour le frontend Next.js
# Budget Famille v2.3 - Solution WSL2 + Docker

echo "🧪 VALIDATION SOLUTION DOCKER - BUDGET FAMILLE FRONTEND"
echo "=========================================================="
echo ""

# Variables de test
FRONTEND_PORT=45678
BACKEND_PORT=8000
TEST_RESULTS=""

# Fonction de log des résultats
log_test() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "SUCCESS" ]; then
        echo "✅ $test_name: $message"
        TEST_RESULTS="$TEST_RESULTS\n✅ $test_name: $message"
    else
        echo "❌ $test_name: $message"
        TEST_RESULTS="$TEST_RESULTS\n❌ $test_name: $message"
    fi
}

# Test 1: Vérification des fichiers Docker
echo "📋 Test 1: Vérification des fichiers Docker..."
if [ -f "Dockerfile.dev" ] && [ -f "dev-docker.sh" ]; then
    log_test "Fichiers Docker" "SUCCESS" "Dockerfile.dev et dev-docker.sh présents"
else
    log_test "Fichiers Docker" "FAILURE" "Fichiers manquants"
    exit 1
fi

# Test 2: Droits d'exécution du script
echo "📋 Test 2: Vérification des droits d'exécution..."
if [ -x "dev-docker.sh" ]; then
    log_test "Droits script" "SUCCESS" "Script dev-docker.sh exécutable"
else
    log_test "Droits script" "FAILURE" "Script non exécutable"
    chmod +x dev-docker.sh
    log_test "Correction droits" "SUCCESS" "Droits corrigés automatiquement"
fi

# Test 3: Build de l'image Docker
echo "📋 Test 3: Build de l'image Docker..."
if docker build -f Dockerfile.dev -t budget-frontend-dev . &>/dev/null; then
    log_test "Build Docker" "SUCCESS" "Image budget-frontend-dev créée"
else
    log_test "Build Docker" "FAILURE" "Échec du build Docker"
    exit 1
fi

# Test 4: Nettoyage des containers existants
echo "📋 Test 4: Nettoyage des containers existants..."
docker stop budget-frontend &>/dev/null && docker rm budget-frontend &>/dev/null
log_test "Nettoyage" "SUCCESS" "Containers précédents nettoyés"

# Test 5: Démarrage du container
echo "📋 Test 5: Démarrage du container frontend..."
if docker run -d --network=host \
    -v $(pwd):/app \
    -v /app/node_modules \
    -v /app/.next \
    -e NEXT_PUBLIC_API_BASE=http://localhost:$BACKEND_PORT \
    --name budget-frontend budget-frontend-dev; then
    log_test "Démarrage container" "SUCCESS" "Container démarré sur port $FRONTEND_PORT"
else
    log_test "Démarrage container" "FAILURE" "Échec du démarrage"
    exit 1
fi

# Attendre que Next.js soit prêt
echo "⏳ Attente du démarrage de Next.js..."
sleep 10

# Test 6: Vérification du statut du container
echo "📋 Test 6: Vérification du statut du container..."
if docker ps | grep budget-frontend | grep "Up" &>/dev/null; then
    log_test "Statut container" "SUCCESS" "Container en fonctionnement"
else
    log_test "Statut container" "FAILURE" "Container non fonctionnel"
    echo "📜 Logs du container:"
    docker logs budget-frontend
    exit 1
fi

# Test 7: Test de connectivité frontend
echo "📋 Test 7: Test de connectivité frontend..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT | grep -q "200"; then
    log_test "Connectivité frontend" "SUCCESS" "Frontend accessible sur port $FRONTEND_PORT"
else
    log_test "Connectivité frontend" "FAILURE" "Frontend non accessible"
fi

# Test 8: Test de connectivité backend depuis le container
echo "📋 Test 8: Test de connectivité vers backend..."
if docker exec budget-frontend wget -q -O - http://localhost:$BACKEND_PORT/health &>/dev/null; then
    log_test "Connectivité backend" "SUCCESS" "Backend accessible depuis container Docker"
else
    log_test "Connectivité backend" "FAILURE" "Backend non accessible (démarrer backend sur port $BACKEND_PORT)"
fi

# Test 9: Vérification de la configuration API
echo "📋 Test 9: Vérification de la configuration API..."
if docker exec budget-frontend env | grep "NEXT_PUBLIC_API_BASE=http://localhost:$BACKEND_PORT" &>/dev/null; then
    log_test "Configuration API" "SUCCESS" "Variable d'environnement API correcte"
else
    log_test "Configuration API" "FAILURE" "Variable d'environnement API incorrecte"
fi

# Test 10: Test des volumes montés
echo "📋 Test 10: Test des volumes montés..."
if docker exec budget-frontend ls -la /app/package.json &>/dev/null; then
    log_test "Volumes montés" "SUCCESS" "Code source accessible dans container"
else
    log_test "Volumes montés" "FAILURE" "Problème de montage des volumes"
fi

echo ""
echo "🎯 RÉSUMÉ DES TESTS:"
echo "==================="
echo -e "$TEST_RESULTS"

echo ""
echo "🚀 COMMANDES UTILES:"
echo "===================="
echo "Démarrer:    ./dev-docker.sh start"
echo "Arrêter:     ./dev-docker.sh stop"
echo "Redémarrer:  ./dev-docker.sh restart"
echo "Logs:        ./dev-docker.sh logs"
echo "Statut:      ./dev-docker.sh status"
echo "Shell:       ./dev-docker.sh shell"
echo "Rebuild:     ./dev-docker.sh rebuild"
echo "Nettoyer:    ./dev-docker.sh clean"

echo ""
echo "🌐 URLs IMPORTANTES:"
echo "===================="
echo "Frontend Docker: http://localhost:$FRONTEND_PORT"
echo "Backend WSL2:    http://localhost:$BACKEND_PORT"
echo "API Docs:        http://localhost:$BACKEND_PORT/docs"

echo ""
echo "✅ Validation terminée !"