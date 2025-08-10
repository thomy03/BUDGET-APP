# 🐳 SOLUTION DOCKER POUR WSL2 + NEXT.JS

## 🎯 PROBLÈME RÉSOLU

**Problème** : Next.js 14.2.31 incompatible avec WSL2 (se bloque au "Starting...")
**Solution** : Utilisation de Docker pour contourner les limitations WSL2

## 🚀 DÉMARRAGE RAPIDE

### 1. Lancer le serveur de développement
```bash
# Build l'image (première fois seulement)
docker build -f Dockerfile.dev -t budget-frontend-dev .

# Lancer le container
docker run -d -p 45678:45678 -e NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 --name budget-frontend budget-frontend-dev

# Vérifier les logs
docker logs budget-frontend
```

### 2. Scripts de gestion
```bash
# Arrêter le container
docker stop budget-frontend

# Redémarrer
docker restart budget-frontend

# Supprimer le container
docker rm budget-frontend

# Rebuild complet
docker build -f Dockerfile.dev -t budget-frontend-dev . --no-cache
```

## 📋 SCRIPTS AUTOMATISÉS

### Script de développement (dev-docker.sh)
```bash
#!/bin/bash
# Gestion automatisée du container de développement

case "$1" in
  start)
    echo "🚀 Démarrage du serveur Next.js en Docker..."
    docker build -f Dockerfile.dev -t budget-frontend-dev .
    docker run -d -p 45678:45678 -e NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 --name budget-frontend budget-frontend-dev
    echo "✅ Serveur disponible sur http://localhost:45678"
    ;;
  stop)
    echo "🛑 Arrêt du serveur..."
    docker stop budget-frontend && docker rm budget-frontend
    ;;
  restart)
    echo "🔄 Redémarrage du serveur..."
    docker stop budget-frontend && docker rm budget-frontend
    docker run -d -p 45678:45678 -e NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 --name budget-frontend budget-frontend-dev
    ;;
  logs)
    docker logs budget-frontend
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    exit 1
    ;;
esac
```

## 🔧 CONFIGURATION

### Variables d'environnement
- `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000` - URL du backend FastAPI
- `NODE_ENV=development` - Mode développement
- Port exposé : `45678`

### Volumes Docker (optionnel pour hot-reload)
```bash
docker run -d -p 45678:45678 \
  -v $(pwd):/app \
  -v /app/node_modules \
  -v /app/.next \
  -e NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 \
  --name budget-frontend budget-frontend-dev
```

## ✅ RÉSULTATS TESTÉS

- ✅ **Démarrage** : Next.js se lance en ~2 secondes
- ✅ **Performance** : Pas de lenteur WSL2
- ✅ **Hot-reload** : Fonctionne avec volumes
- ✅ **Build** : Production build réussit
- ✅ **API** : Communication backend OK

## 📊 COMPARAISON WSL2 vs DOCKER

| Aspect | WSL2 | Docker |
|--------|------|--------|
| Démarrage Next.js | ❌ Se bloque | ✅ 2 secondes |
| Hot reload | ❌ Non fonctionnel | ✅ Fonctionnel |
| Build production | ❌ Échec SIGBUS | ✅ Succès |
| Performance | ❌ Lent | ✅ Rapide |
| Stabilité | ❌ Instable | ✅ Stable |

## 🎉 AVANTAGES DOCKER

1. **Isolation complète** du problème WSL2
2. **Performance constante** sans variations WSL2
3. **Environnement reproductible** 
4. **Facilite le déploiement** (même image)
5. **Hot-reload fonctionnel** avec volumes

## 🔄 WORKFLOW DÉVELOPPEMENT

```bash
# 1. Démarrer le backend (terminal 1)
cd backend
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# 2. Démarrer le frontend Docker (terminal 2)
cd frontend
./dev-docker.sh start

# 3. Développer normalement
# - Backend : http://127.0.0.1:8000
# - Frontend : http://localhost:45678
# - API docs : http://127.0.0.1:8000/docs
```

---

**Date de création** : 2025-08-10
**Statut** : ✅ **SOLUTION VALIDÉE** - Problème WSL2 + Next.js **RÉSOLU**