'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner } from "../components/ui";
import { UltraModernDashboard } from "../components/dashboard";

export default function DashboardPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();

  // Redirection si non authentifie
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifie (redirection en cours)
  if (!isAuthenticated) {
    return null;
  }

  // ULTRA MODERN DASHBOARD - Design glassmorphism avec graphiques avancés
  return (
    <UltraModernDashboard
      month={month}
      isAuthenticated={isAuthenticated}
    />
  );
}