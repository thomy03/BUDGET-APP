'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner } from "../components/ui";
import { KeyMetrics, EnhancedDashboard } from "../components/dashboard";
import ProvisionsWidget from "../components/ProvisionsWidget";
import CleanDashboard from "../components/dashboard/CleanDashboard";
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
    <main className="min-h-screen bg-gray-50">
      {error && (
        <div className="container py-4">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
            {error}
          </div>
        </div>
      )}

      {/* NEW CLEAN DASHBOARD - Design épuré et ultra-lisible */}
      <div className="container py-8">
        <CleanDashboard 
          month={month}
          isAuthenticated={isAuthenticated}
        />
      </div>

      {/* Enhanced Dashboard - OLD INTERFACE (can be removed after validation) */}
      {/* <EnhancedDashboard 
        month={month}
        isAuthenticated={isAuthenticated}
      /> */}

      {/* Legacy Components - Hidden for clean design */}
      {false && summary && config && (
        <>
          <ProvisionsWidget config={config} />
          <div className="mt-8 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-600 mb-4">🔍 Métriques de contrôle (legacy)</h3>
            <KeyMetrics 
              summary={summary} 
              config={config} 
              provisions={provisions} 
              fixedExpenses={fixedExpenses}
            />
          </div>
        </>
      )}
    </main>
  );
}