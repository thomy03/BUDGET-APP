"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth";
import { Button, Input, Card, LoadingSpinner, Alert } from "../../components/ui";
import { api } from "../../lib/api";

interface RegisterFormData {
  username: string;
  password: string;
  confirmPassword: string;
  email: string;
  fullName: string;
}

export default function RegisterPage() {
  const [formData, setFormData] = useState<RegisterFormData>({
    username: "",
    password: "",
    confirmPassword: "",
    email: "",
    fullName: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();
  const { isAuthenticated, loading } = useAuth();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !loading) {
      window.location.href = "/";
    }
  }, [isAuthenticated, loading, router]);

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
    setIsLoading(true);

    try {
      // Validation
      if (!formData.username.trim()) {
        setError("Le nom d'utilisateur est requis");
        setIsLoading(false);
        return;
      }

      if (formData.username.trim().length < 3) {
        setError("Le nom d'utilisateur doit contenir au moins 3 caractères");
        setIsLoading(false);
        return;
      }

      if (!formData.password) {
        setError("Le mot de passe est requis");
        setIsLoading(false);
        return;
      }

      if (formData.password.length < 6) {
        setError("Le mot de passe doit contenir au moins 6 caractères");
        setIsLoading(false);
        return;
      }

      if (formData.password !== formData.confirmPassword) {
        setError("Les mots de passe ne correspondent pas");
        setIsLoading(false);
        return;
      }

      // Register API call
      const response = await api.post("/api/v1/auth/register", {
        username: formData.username.trim().toLowerCase(),
        password: formData.password,
        email: formData.email.trim() || null,
        full_name: formData.fullName.trim() || null,
      });

      if (response.data.access_token) {
        // Save auth data
        localStorage.setItem("auth_token", response.data.access_token);
        localStorage.setItem("token_type", response.data.token_type);
        localStorage.setItem("username", response.data.user.username);
        
        // Set API header
        api.defaults.headers.common["Authorization"] = `${response.data.token_type} ${response.data.access_token}`;
        
        // Redirect to dashboard
        window.location.href = "/";
      }
    } catch (error: any) {
      console.error("Registration error:", error);
      
      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else if (error.response?.status === 400) {
        setError("Ce nom d'utilisateur ou email existe déjà");
      } else {
        setError("Erreur lors de l'inscription. Veuillez réessayer.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-50 to-zinc-100 p-4">
      <div className="w-full max-w-md">
        <Card padding="lg" shadow="lg">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500 text-white rounded-2xl mb-4 text-2xl">
              ✨
            </div>
            <h1 className="text-2xl font-bold text-zinc-900">
              Créer un compte
            </h1>
            <p className="text-zinc-500 mt-2">
              Budget Famille
            </p>
          </div>
        
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Nom d'utilisateur *"
              name="username"
              type="text"
              autoComplete="username"
              required
              placeholder="ex: thomas"
              value={formData.username}
              onChange={handleInputChange}
              disabled={isLoading}
              leftIcon="👤"
            />

            <Input
              label="Nom complet"
              name="fullName"
              type="text"
              autoComplete="name"
              placeholder="ex: Thomas Kadouch"
              value={formData.fullName}
              onChange={handleInputChange}
              disabled={isLoading}
              leftIcon="📝"
            />

            <Input
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="ex: thomas@email.com"
              value={formData.email}
              onChange={handleInputChange}
              disabled={isLoading}
              leftIcon="📧"
            />
            
            <Input
              label="Mot de passe *"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              placeholder="Min. 6 caractères"
              value={formData.password}
              onChange={handleInputChange}
              disabled={isLoading}
              leftIcon="🔐"
              rightIcon={showPassword ? "🙈" : "👁️"}
              onRightIconClick={() => setShowPassword(!showPassword)}
            />

            <Input
              label="Confirmer le mot de passe *"
              name="confirmPassword"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              placeholder="Répétez le mot de passe"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              disabled={isLoading}
              leftIcon="🔐"
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
              loading={isLoading}
              className="w-full bg-emerald-500 hover:bg-emerald-600"
            >
              {!isLoading && (
                <>
                  <span>✨</span>
                  <span>Créer mon compte</span>
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-zinc-600">
              Déjà un compte ?{" "}
              <Link href="/login" className="text-emerald-600 hover:text-emerald-700 font-medium">
                Se connecter
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
