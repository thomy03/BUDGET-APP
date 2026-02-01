module.exports = {
  apps: [{
    name: "budget-backend",
    script: "/root/budget-app/backend/venv/bin/uvicorn",
    args: "app:app --host 0.0.0.0 --port 8001",
    cwd: "/root/budget-app/backend",
    interpreter: "none",
    env: {
      JWT_SECRET_KEY: "JarvisBudgetApp2026SecureKeyForKadouchFamily!",
      JWT_ALGORITHM: "HS256",
      ENVIRONMENT: "production"
    }
  }]
};
