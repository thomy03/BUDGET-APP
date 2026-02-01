"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth";
import { Button, Input, Card, LoadingSpinner, Alert } from "../../components/ui";

import { 
  createErrorMessage 
} from "../../lib/utils/errorHandling";
import { 
  userPreferences 
} from "../../lib/utils/storageUtils";

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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const { isAuthenticated, loading, login } = useAuth();

  useEffect(() => {
    const showPasswordPref = userPreferences.get("showPasswordOnLogin", false) as boolean;
    if (showPasswordPref !== undefined) {
      setShowPassword(showPasswordPref);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && !loading) {
      window.location.href = "/";
    }
  }, [isAuthenticated, loading]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    if (error) {
      setError("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      if (!formData.username.trim() || !formData.password.trim()) {
        setError("Veuillez remplir tous les champs");
        setIsSubmitting(false);
        return;
      }

      if (formData.username.trim().length < 2) {
        setError("Le nom d'utilisateur doit contenir au moins 2 caractères");
        setIsSubmitting(false);
        return;
      }

      if (formData.password.length < 3) {
        setError("Le mot de passe doit contenir au moins 3 caractères");
        setIsSubmitting(false);
        return;
      }

      userPreferences.set("showPasswordOnLogin", showPassword);

      console.log("🔐 Attempting login...");
      const result = await login(formData.username.trim(), formData.password);
      console.log("🔐 Login result:", result);
      
      if (result.success) {
        console.log("🔐 Login successful, checking localStorage...");
        const token = localStorage.getItem("auth_token");
        console.log("🔐 Token in localStorage:", token ? "YES" : "NO");
        
        // Small delay to ensure localStorage is fully written
        await new Promise(resolve => setTimeout(resolve, 100));
        
        console.log("🔐 Redirecting to dashboard...");
        window.location.href = "/";
      } else {
        console.log("🔐 Login failed:", result.error);
        setError(result.error || "Erreur de connexion");
        setIsSubmitting(false);
      }
    } catch (error: any) {
      console.error("🔐 Login exception:", error);
      setError(error?.message || "Erreur de connexion inattendue");
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <LoadingSpinner size="lg" text="Vérification de la session..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-50 to-zinc-100 p-4">
      <div className="w-full max-w-md">
        <Card padding="lg" shadow="lg">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-zinc-900 text-white rounded-2xl mb-4 text-2xl">
              💶
            </div>
            <h1 className="text-2xl font-bold text-zinc-900">
              Budget Famille
            </h1>
            <p className="text-zinc-500 mt-2">
              Connexion sécurisée
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
              disabled={isSubmitting}
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
              disabled={isSubmitting}
              leftIcon="🔐"
              rightIcon={showPassword ? "🙈" : "👁️"}
              onRightIconClick={() => {
                setShowPassword(!showPassword);
                userPreferences.set("showPasswordOnLogin", !showPassword);
              }}
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
              loading={isSubmitting}
              className="w-full"
            >
              {!isSubmitting && (
                <>
                  <span>🔑</span>
                  <span>Se connecter</span>
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-zinc-600">
              Pas encore de compte ?{" "}
              <Link href="/register" className="text-emerald-600 hover:text-emerald-700 font-medium">
                Créer un compte
              </Link>
            </p>
          </div>

          <div className="mt-4 p-3 bg-zinc-50 rounded-xl text-center">
            <p className="text-xs text-zinc-500">
              🔒 Connexion sécurisée • Session persistante 30 jours
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
