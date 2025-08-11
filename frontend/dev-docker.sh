#!/bin/bash
# Script de gestion automatisée du container de développement Next.js
# Solution Docker pour contourner le problème WSL2 + Next.js

case "$1" in
  start)
    echo "🚀 Démarrage du serveur Next.js en Docker..."
    
    # Supprimer l'ancien container s'il existe
    docker stop budget-frontend 2>/dev/null && docker rm budget-frontend 2>/dev/null
    
    # Build l'image
    docker build -f Dockerfile.dev -t budget-frontend-dev .
    
    # Lancer le container
    docker run -d --network=host \
      -v $(pwd):/app \
      -v /app/node_modules \
      -v /app/.next \
      -e NEXT_PUBLIC_API_BASE=http://localhost:8000 \
      --name budget-frontend budget-frontend-dev
    
    echo "✅ Serveur disponible sur http://localhost:45678"
    echo "📋 Utilisez './dev-docker.sh logs' pour voir les logs"
    ;;
    
  stop)
    echo "🛑 Arrêt du serveur..."
    docker stop budget-frontend && docker rm budget-frontend
    echo "✅ Serveur arrêté"
    ;;
    
  restart)
    echo "🔄 Redémarrage du serveur..."
    docker stop budget-frontend && docker rm budget-frontend
    docker run -d --network=host \
      -v $(pwd):/app \
      -v /app/node_modules \
      -v /app/.next \
      -e NEXT_PUBLIC_API_BASE=http://localhost:8000 \
      --name budget-frontend budget-frontend-dev
    echo "✅ Serveur redémarré sur http://localhost:45678"
    ;;
    
  logs)
    echo "📜 Logs du container :"
    docker logs budget-frontend
    ;;
    
  status)
    echo "📊 Statut du container :"
    docker ps | grep budget-frontend || echo "❌ Container non démarré"
    ;;
    
  shell)
    echo "🐚 Connexion au container..."
    docker exec -it budget-frontend sh
    ;;
    
  rebuild)
    echo "🔄 Rebuild complet (sans cache)..."
    docker stop budget-frontend 2>/dev/null && docker rm budget-frontend 2>/dev/null
    docker build -f Dockerfile.dev -t budget-frontend-dev . --no-cache
    docker run -d --network=host \
      -v $(pwd):/app \
      -v /app/node_modules \
      -v /app/.next \
      -e NEXT_PUBLIC_API_BASE=http://localhost:8000 \
      --name budget-frontend budget-frontend-dev
    echo "✅ Rebuild terminé - serveur sur http://localhost:45678"
    ;;
    
  clean)
    echo "🧹 Nettoyage complet..."
    docker stop budget-frontend 2>/dev/null && docker rm budget-frontend 2>/dev/null
    docker rmi budget-frontend-dev 2>/dev/null
    echo "✅ Nettoyage terminé"
    ;;
    
  *)
    echo "🐳 GESTION DOCKER - BUDGET FAMILLE FRONTEND"
    echo ""
    echo "Usage: $0 {command}"
    echo ""
    echo "Commandes disponibles :"
    echo "  start    - Démarrer le serveur de développement"
    echo "  stop     - Arrêter le serveur"
    echo "  restart  - Redémarrer le serveur"
    echo "  logs     - Afficher les logs"
    echo "  status   - Statut du container"
    echo "  shell    - Ouvrir un shell dans le container"
    echo "  rebuild  - Rebuild complet sans cache"
    echo "  clean    - Supprimer container et image"
    echo ""
    echo "Exemple : ./dev-docker.sh start"
    exit 1
    ;;
esac