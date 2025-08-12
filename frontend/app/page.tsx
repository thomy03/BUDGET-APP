'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner } from "../components/ui";
import { KeyMetrics, EnhancedDashboard } from "../components/dashboard";
import ProvisionsWidget from "../components/ProvisionsWidget";
import { useDashboardData } from "../hooks/useDashboardData";

export default function DashboardPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();
  const { summary, config, provisions, fixedExpenses, loading, error } = useDashboardData(month, isAuthenticated);

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié (redirection en cours)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">Tableau de bord</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      {/* Enhanced Dashboard - NEW RESTRUCTURED INTERFACE */}
      <EnhancedDashboard 
        month={month}
        isAuthenticated={isAuthenticated}
      />

      {/* Legacy Provisions Widget - Keep for now as complementary info */}
      {summary && config && (
        <ProvisionsWidget config={config} />
      )}

      {/* Legacy Key Metrics - Keep for backward compatibility */}
      {summary && config && (
        <div className="mt-8 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-600 mb-4">🔍 Métriques de contrôle (legacy)</h3>
          <KeyMetrics 
            summary={summary} 
            config={config} 
            provisions={provisions} 
            fixedExpenses={fixedExpenses}
          />
        </div>
      )}
    </main>
  );
}