## Instructions
Redémarrer le serveur backend (port 8000) 
Redémarrer le serveur frontend (port 45678) via le docker

**Solution optimisée pour Windows/WSL2** avec résolution du problème Next.js :

1. **Backend (WSL2 natif)** :
```bash
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. **Frontend (Docker container)** :
```bash
cd frontend
./dev-docker.sh start
```

3. **Accès** :
- Interface : http://localhost:45678
- API : http://0.0.0.0:8000
- Documentation API : http://0.0.0.0:8000/docs