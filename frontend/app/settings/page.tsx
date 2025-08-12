'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Alert, Button } from "../../components/ui";
import { 
  BudgetConfiguration, 
  SettingsLayout, 
  ExpenseManagement, 
  TagsManagement,
  AdvancedConfiguration, 
  AdministrationPanel 
} from "../../components/settings";
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

  // Configuration des sections avec Tags & Catégories en priorité
  const settingsSections = [
    {
      id: 'tags',
      title: 'Tags & Catégories',
      icon: '🏷️',
      description: 'Organisez et gérez vos catégories de transactions avec IA',
      component: <TagsManagement />,
      priority: true
    },
    {
      id: 'budget',
      title: 'Budget & Provisions',
      icon: '📊',
      description: 'Configuration de vos revenus, budget mensuel et répartition des dépenses',
      component: (
        <BudgetConfiguration
          cfg={cfg}
          saving={saving}
          onSave={save}
        />
      )
    },
    {
      id: 'expenses',
      title: 'Mes Dépenses',
      icon: '💳',
      description: 'Gestion de vos dépenses fixes et provisions personnalisées',
      component: (
        <ExpenseManagement 
          config={cfg} 
          onDataChange={load} 
        />
      )
    },
    {
      id: 'advanced',
      title: 'Configuration IA',
      icon: '⚙️',
      description: 'Intelligence IA, Import/Export et outils de diagnostic',
      component: <AdvancedConfiguration />
    }
  ];

  return (
    <>
      {/* Messages globaux */}
      {message && (
        <Alert variant="success" className="mb-4">
          {message}
        </Alert>
      )}

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <SettingsLayout 
        sections={settingsSections}
        defaultTab="tags"
      >
        <Button 
          onClick={load}
          variant="outline"
          className="flex items-center gap-2"
        >
          <span>🔄</span>
          Actualiser
        </Button>
      </SettingsLayout>
    </>
  );
}
