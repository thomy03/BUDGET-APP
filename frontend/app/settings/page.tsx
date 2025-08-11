'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Alert } from "../../components/ui";
import CustomProvisions from "../../components/CustomProvisions";
import FixedExpenses from "../../components/FixedExpenses";
import APIDebugPanel from "../../components/APIDebugPanel";
import { BudgetConfiguration } from "../../components/settings";
import { useSettings } from "../../hooks/useSettings";

export default function Settings() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const {
    cfg,
    lines,
    loading,
    saving,
    message,
    error,
    load,
    save,
    setMessage,
    setError
  } = useSettings(isAuthenticated);

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  if (authLoading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner text="Vérification de l'authentification..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Redirection en cours
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner text="Chargement de la configuration..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">
          ⚙️ Paramètres
        </h1>
        <button 
          onClick={load}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Messages */}
      {message && (
        <Alert variant="success">
          {message}
        </Alert>
      )}

      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}

      {/* Configuration du budget */}
      <BudgetConfiguration
        cfg={cfg}
        saving={saving}
        onSave={save}
      />

      {/* Dépenses fixes personnalisables */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-gray-900">
          💳 Gestion des Dépenses Fixes
        </h2>
        <FixedExpenses config={cfg} onDataChange={load} />
      </div>

      {/* Provisions personnalisables */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-gray-900">
          🎯 Gestion des Provisions
        </h2>
        <CustomProvisions config={cfg} onDataChange={load} />
      </div>

      {/* Panel de debug API */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-gray-900">
          🔧 Outils de Débogage
        </h2>
        <APIDebugPanel />
      </div>
    </div>
  );
}
