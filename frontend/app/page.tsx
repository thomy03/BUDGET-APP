'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner } from "../components/ui";
import { KeyMetrics, DetailedBudgetTable } from "../components/dashboard";
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

      {/* Key Metrics - Now handles its own loading states */}
      <KeyMetrics 
        summary={summary} 
        config={config} 
        provisions={provisions} 
        fixedExpenses={fixedExpenses}
      />

      {/* Only render these components when we have the basic data */}
      {summary && config ? (
        <>
          {/* Provisions Widget */}
          <ProvisionsWidget config={config} />

          {/* Detailed Budget Table */}
          <DetailedBudgetTable 
            summary={summary} 
            config={config} 
            provisions={provisions} 
            fixedExpenses={fixedExpenses}
            month={month}
          />
        </>
      ) : (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" text="Chargement des données..." />
        </div>
      )}
    </main>
  );
}