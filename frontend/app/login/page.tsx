"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { Button, Input, Card, LoadingSpinner, Alert } from "../../components/ui";

interface LoginFormData {
  username: string;
  password: string;
}

export default function LoginPage() {
  const [formData, setFormData] = useState<LoginFormData>({
    username: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();
  const { isAuthenticated, loading, login } = useAuth();

  // Rediriger si déjà connecté
  useEffect(() => {
    if (isAuthenticated && !loading) {
      router.push("/");
    }
  }, [isAuthenticated, loading, router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Effacer l'erreur quand l'utilisateur tape
    if (error) {
      setError("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation côté client
    if (!formData.username.trim() || !formData.password.trim()) {
      setError("Veuillez remplir tous les champs");
      return;
    }

    if (formData.username.trim().length < 2) {
      setError("Le nom d'utilisateur doit contenir au moins 2 caractères");
      return;
    }

    if (formData.password.length < 3) {
      setError("Le mot de passe doit contenir au moins 3 caractères");
      return;
    }

    const result = await login(formData.username.trim(), formData.password);
    
    if (result.success) {
      router.push("/");
    } else {
      setError(result.error || "Erreur de connexion");
    }
  };

  // Affichage du loader pendant l'initialisation
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <LoadingSpinner size="lg" text="Vérification de la session..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-50 to-zinc-100">
      <div className="w-full max-w-md">
        <Card padding="lg" shadow="lg">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-zinc-900 text-white rounded-2xl mb-4 text-2xl">
              💶
            </div>
            <h1 className="h1 text-zinc-900">
              Budget Famille
            </h1>
            <p className="subtle mt-2">
              Connexion sécurisée requise
            </p>
          </div>
        
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Nom d'utilisateur"
              name="username"
              type="text"
              autoComplete="username"
              required
              placeholder="Entrez votre nom d'utilisateur"
              value={formData.username}
              onChange={handleInputChange}
              disabled={loading}
              leftIcon="👤"
            />
            
            <Input
              label="Mot de passe"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              placeholder="Entrez votre mot de passe"
              value={formData.password}
              onChange={handleInputChange}
              disabled={loading}
              leftIcon="🔐"
              rightIcon={showPassword ? "🙈" : "👁️"}
              onRightIconClick={() => setShowPassword(!showPassword)}
            />

            {error && (
              <Alert variant="error">
                {error}
              </Alert>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full"
            >
              {!loading && (
                <>
                  <span>🔑</span>
                  <span>Se connecter</span>
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 p-4 bg-zinc-50 rounded-xl text-center">
            <p className="text-xs text-zinc-500 mb-2">
              🔒 Authentification JWT sécurisée
            </p>
            <p className="text-xs text-zinc-600">
              <strong>Identifiants par défaut:</strong><br/>
              Utilisateur: <code className="bg-zinc-200 px-1 rounded">admin</code><br/>
              Mot de passe: <code className="bg-zinc-200 px-1 rounded">secret</code>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}