'use client';

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useGlobalMonthWithUrl } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card, Alert } from "../../components/ui";
import ImportSuccessBanner from "../../components/ImportSuccessBanner";
import { useTransactions } from "../../hooks/useTransactions";
import { TransactionsSummary, TransactionsTable } from "../../components/transactions";

export default function TransactionsPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [month, setMonth] = useGlobalMonthWithUrl();
  const {
    rows,
    loading,
    error,
    calculations,
    refresh,
    toggle,
    saveTags
  } = useTransactions();

  // Paramètres d'URL
  const importId = searchParams.get('importId');
  
  console.log('📊 Transactions page - Current month:', month, 'ImportId:', importId);

  useEffect(() => {
    if (!authLoading) {
      refresh(isAuthenticated, month);
    }
  }, [isAuthenticated, month, authLoading, refresh]);

  if (authLoading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner text="Vérification de l'authentification..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Alert variant="warning">
        Veuillez vous connecter pour accéder aux transactions.
      </Alert>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          📈 Transactions - {month || 'Mois non sélectionné'}
        </h1>
        <button 
          onClick={() => refresh(isAuthenticated, month)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          disabled={loading}
        >
          🔄 Actualiser
        </button>
      </div>

      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}

      {/* Rappel des totaux du mois */}
      {!loading && rows.length > 0 && (
        <TransactionsSummary month={month} calculations={calculations} />
      )}

      {/* Bandeau d'import success si importId présent */}
      {importId && (
        <ImportSuccessBanner
          importId={importId}
          currentMonth={month}
          onMonthChange={setMonth}
          onRefresh={() => refresh(isAuthenticated, month)}
        />
      )}

      <Card padding="lg">
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner text="Chargement des transactions..." />
          </div>
        ) : rows.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">💳</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune transaction trouvée
            </h3>
            <p className="text-gray-600 mb-4">
              Aucune transaction n'a été importée pour le mois de {month}.
            </p>
            <button 
              onClick={() => refresh(isAuthenticated, month)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Actualiser
            </button>
          </div>
        ) : (
          <TransactionsTable
            rows={rows}
            importId={importId}
            calculations={calculations}
            onToggle={toggle}
            onSaveTags={saveTags}
          />
        )}
      </Card>
    </div>
  );
}
