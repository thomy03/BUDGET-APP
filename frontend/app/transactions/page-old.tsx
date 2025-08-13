'use client';

import { useEffect, useState, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useGlobalMonthWithUrl } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card, Alert } from "../../components/ui";
import ImportSuccessBanner from "../../components/ImportSuccessBanner";
import { useTransactions } from "../../hooks/useTransactions";
import { useAutoTagging } from "../../hooks/useAutoTagging";
import { TransactionsSummary, TransactionsTable, AutoTaggingButton, AutoTaggingProgress, TransactionFilters, FilterState } from "../../components/transactions";

export default function TransactionsPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [month, setMonth] = useGlobalMonthWithUrl();
  const {
    rows,
    loading,
    error,
    autoClassifying,
    autoClassificationResults,
    calculations,
    refresh,
    toggle,
    saveTags,
    bulkUnexcludeAll,
    updateExpenseType
  } = useTransactions();
  
  // State for filters
  const [filters, setFilters] = useState<FilterState>({
    searchText: '',
    dateFrom: '',
    dateTo: '',
    amountMin: '',
    amountMax: '',
    excludeFilter: 'all',
    transactionType: 'all'
  });
  
  // Apply filters to transactions
  const filteredRows = useMemo(() => {
    let filtered = [...rows];
    
    // Filter by search text (libellé)
    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      filtered = filtered.filter(row => 
        row.label?.toLowerCase().includes(searchLower) ||
        row.name?.toLowerCase().includes(searchLower)
      );
    }
    
    // Filter by date range
    if (filters.dateFrom) {
      filtered = filtered.filter(row => row.date >= filters.dateFrom);
    }
    if (filters.dateTo) {
      filtered = filtered.filter(row => row.date <= filters.dateTo);
    }
    
    // Filter by amount range
    if (filters.amountMin) {
      const min = parseFloat(filters.amountMin);
      filtered = filtered.filter(row => Math.abs(row.amount) >= min);
    }
    if (filters.amountMax) {
      const max = parseFloat(filters.amountMax);
      filtered = filtered.filter(row => Math.abs(row.amount) <= max);
    }
    
    // Filter by transaction type
    if (filters.transactionType === 'income') {
      filtered = filtered.filter(row => row.amount >= 0);
    } else if (filters.transactionType === 'expense') {
      filtered = filtered.filter(row => row.amount < 0);
    }
    
    // Filter by exclusion status
    if (filters.excludeFilter === 'included') {
      filtered = filtered.filter(row => !row.exclude);
    } else if (filters.excludeFilter === 'excluded') {
      filtered = filtered.filter(row => row.exclude);
    }
    
    return filtered;
  }, [rows, filters]);

  // Auto-tagging functionality
  const {
    isProcessing: isAutoTagging,
    progress: autoTaggingProgress,
    stats: autoTaggingStats,
    error: autoTaggingError,
    showProgressModal,
    startAutoTagging,
    cancelAutoTagging,
    closeProgressModal,
    getUntaggedCount,
    resetState: resetAutoTaggingState
  } = useAutoTagging();

  // Paramètres d'URL
  const importId = searchParams.get('importId');
  const tagFilter = searchParams.get('tag');
  
  console.log('📊 Transactions page - Current month:', month, 'ImportId:', importId);

  // Gestionnaire pour les changements de type de dépense (classification IA)
  const handleExpenseTypeChange = async (id: number, expenseType: 'fixed' | 'variable') => {
    console.log(`✨ Expense type changed for transaction ${id}: ${expenseType}`);
    await updateExpenseType(id, expenseType);
  };

  // Gestionnaire pour réinclure toutes les transactions
  const handleBulkUnexcludeAll = async () => {
    console.log(`📊 Réinclusion de toutes les transactions exclues`);
    await bulkUnexcludeAll();
  };

  // Gestionnaire pour démarrer l'auto-tagging
  const handleStartAutoTagging = async () => {
    if (!month) {
      console.error('❌ No month selected for auto-tagging');
      return;
    }

    try {
      await startAutoTagging(month, {
        confidenceThreshold: 0.7,
        includeClassified: false
      });
      
    } catch (error) {
      console.error('❌ Failed to start auto-tagging:', error);
    }
  };

  // Gestionnaire pour la fermeture du modal de progression
  const handleCloseProgressModal = () => {
    closeProgressModal();
    // Refresh transactions when modal closes to show the updated data
    if (!isAutoTagging) {
      refresh(isAuthenticated, month);
    }
  };

  // Calculate untagged count for the button (use filtered rows)
  const untaggedCount = getUntaggedCount(filteredRows);

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
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold text-gray-900">
            📈 Transactions - {month || 'Mois non sélectionné'}
          </h1>
          {tagFilter && (
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                🏷️ Filtre: {tagFilter}
              </span>
              <button 
                onClick={() => router.push('/transactions')}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Supprimer le filtre
              </button>
            </div>
          )}
        </div>
        <button 
          onClick={() => refresh(isAuthenticated, month)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          disabled={loading}
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Filters */}
      {!loading && rows.length > 0 && (
        <TransactionFilters onFiltersChange={setFilters} />
      )}
      
      {/* Auto-tagging button */}
      {!loading && filteredRows.length > 0 && (
        <div className="flex justify-center">
          <AutoTaggingButton
            totalTransactions={filteredRows.length}
            untaggedCount={untaggedCount}
            isProcessing={isAutoTagging}
            onStartAutoTagging={handleStartAutoTagging}
            progress={autoTaggingProgress}
            processedCount={autoTaggingStats.processed}
            statusMessage={autoTaggingStats.processed > 0 ? `Traitement ${autoTaggingStats.processed}/${autoTaggingStats.totalTransactions} transactions...` : undefined}
          />
        </div>
      )}

      {/* Auto-classification status */}
      {autoClassifying && (
        <Alert variant="info">
          🤖 Classification IA en cours... Analyse automatique des transactions non classifiées.
        </Alert>
      )}

      {autoClassificationResults && !autoClassifying && (
        <Alert variant="success">
          ✨ Classification IA terminée en {autoClassificationResults.processingTimeMs.toFixed(0)}ms : 
          <strong> {autoClassificationResults.autoApplied} classifications appliquées</strong> 
          sur {autoClassificationResults.totalAnalyzed} analysées
          {autoClassificationResults.pendingReview > 0 && (
            <span>, {autoClassificationResults.pendingReview} en attente de révision</span>
          )}
        </Alert>
      )}

      {/* Auto-tagging error */}
      {autoTaggingError && (
        <Alert variant="error">
          ❌ Erreur auto-tagging: {autoTaggingError}
        </Alert>
      )}

      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}

      {/* Rappel des totaux du mois */}
      {!loading && rows.length > 0 && (
        <>
          <TransactionsSummary month={month} calculations={calculations} />
          {filteredRows.length < rows.length && (
            <Alert variant="info">
              🔍 Affichage de {filteredRows.length} transactions sur {rows.length} total (filtres actifs)
            </Alert>
          )}
        </>
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
        ) : filteredRows.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">💳</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune transaction trouvée
            </h3>
            <p className="text-gray-600 mb-4">
              {rows.length > 0 
                ? "Aucune transaction ne correspond aux filtres sélectionnés."
                : `Aucune transaction n'a été importée pour le mois de ${month}.`
              }
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
            rows={filteredRows}
            importId={importId}
            calculations={calculations}
            onToggle={toggle}
            onSaveTags={saveTags}
            onExpenseTypeChange={handleExpenseTypeChange}
            onBulkUnexcludeAll={handleBulkUnexcludeAll}
          />
        )}
      </Card>

      {/* Auto-tagging progress modal */}
      <AutoTaggingProgress
        isOpen={showProgressModal}
        stats={autoTaggingStats}
        progressPercentage={autoTaggingProgress}
        isCompleted={!isAutoTagging && autoTaggingProgress === 100}
        hasError={!!autoTaggingError}
        errorMessage={autoTaggingError || undefined}
        onCancel={cancelAutoTagging}
        onClose={handleCloseProgressModal}
      />
    </div>
  );
}
