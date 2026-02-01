'use client';

import { useEffect, useState, useMemo, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useGlobalMonthWithUrl } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { useTransactions } from "../../hooks/useTransactions";
import { ModernTransactionsTable } from "../../components/transactions/ModernTransactionsTableWithAI";
import { autoTagApi, AutoTagSuggestion, AutoTagResult } from "../../lib/api";
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  CalendarIcon,
  CurrencyEuroIcon,
  TagIcon,
  SparklesIcon,
  XMarkIcon,
  CheckIcon,
  CameraIcon
} from '@heroicons/react/24/outline';
import { ReceiptScanner } from '../../components/receipts';
import MonthPicker from '../../components/MonthPicker';

export default function ModernTransactionsPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [month, setMonth] = useGlobalMonthWithUrl();
  const {
    rows,
    loading,
    error,
    calculations,
    globalStats,
    pagination,
    setPage,
    setLimit,
    refresh,
    toggle,
    saveTags,
    bulkUnexcludeAll
  } = useTransactions();
  
  // États pour les filtres
  const [searchText, setSearchText] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filterType, setFilterType] = useState<'all' | 'income' | 'expense'>('all');
  const [filterExclude, setFilterExclude] = useState<'all' | 'included' | 'excluded'>('all');

  // États pour l'auto-tagging
  const [showAutoTagModal, setShowAutoTagModal] = useState(false);
  const [autoTagLoading, setAutoTagLoading] = useState(false);
  const [autoTagResult, setAutoTagResult] = useState<AutoTagResult | null>(null);
  const [autoTagError, setAutoTagError] = useState<string | null>(null);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  const [applyingTags, setApplyingTags] = useState(false);

  // État pour le scanner de tickets OCR
  const [showReceiptScanner, setShowReceiptScanner] = useState(false);

  // Lecture du paramètre editTx pour ouvrir l'édition d'une transaction spécifique (depuis Analytics)
  const editTxParam = searchParams.get('editTx');
  const editTransactionId = editTxParam ? parseInt(editTxParam, 10) : null;

  // Callback pour nettoyer l'URL après l'édition
  const handleEditComplete = useCallback(() => {
    // Supprimer le paramètre editTx de l'URL sans recharger la page
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.delete('editTx');
    window.history.replaceState({}, '', newUrl.toString());
  }, []);

  // Prévisualiser les suggestions d'auto-tagging
  const handlePreviewAutoTag = useCallback(async () => {
    if (!month) return;
    setAutoTagLoading(true);
    setAutoTagError(null);
    try {
      const result = await autoTagApi.preview(month, 0.5);
      setAutoTagResult(result);
      // Sélectionner toutes les suggestions par défaut
      const allIds = new Set(result.suggestions.map(s => s.transaction_id));
      setSelectedSuggestions(allIds);
    } catch (err: any) {
      setAutoTagError(err.message || 'Erreur lors de la prévisualisation');
    } finally {
      setAutoTagLoading(false);
    }
  }, [month]);

  // Appliquer les tags sélectionnés
  const handleApplySelectedTags = useCallback(async () => {
    if (!autoTagResult || selectedSuggestions.size === 0) return;
    setApplyingTags(true);
    try {
      const selectedItems = autoTagResult.suggestions.filter(s => selectedSuggestions.has(s.transaction_id));
      for (const suggestion of selectedItems) {
        // saveTags attend une string (CSV), pas un tableau
        await saveTags(suggestion.transaction_id, suggestion.suggested_tag);
      }
      // Rafraîchir les transactions
      refresh(isAuthenticated, month);
      setShowAutoTagModal(false);
      setAutoTagResult(null);
    } catch (err: any) {
      setAutoTagError(err.message || 'Erreur lors de l\'application des tags');
    } finally {
      setApplyingTags(false);
    }
  }, [autoTagResult, selectedSuggestions, saveTags, refresh, isAuthenticated, month]);

  // Toggle sélection d'une suggestion
  const toggleSuggestion = (id: number) => {
    const newSet = new Set(selectedSuggestions);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedSuggestions(newSet);
  };

  // Sélectionner/désélectionner tout
  const toggleAllSuggestions = () => {
    if (!autoTagResult) return;
    if (selectedSuggestions.size === autoTagResult.suggestions.length) {
      setSelectedSuggestions(new Set());
    } else {
      setSelectedSuggestions(new Set(autoTagResult.suggestions.map(s => s.transaction_id)));
    }
  };

  // Nombre de transactions sans tags (inclut "Non classé" comme non-tagué)
  const untaggedCount = useMemo(() => {
    return rows.filter(r => {
      const tags = r.tags as string[] | string | null | undefined;
      // Pas de tags du tout
      if (!tags || (Array.isArray(tags) && tags.length === 0)) return true;
      // Tous les tags sont vides/null
      if (Array.isArray(tags) && tags.every(t => !t)) return true;
      // Tags est un string "Non classé" (format backend)
      if (typeof tags === 'string') {
        return tags.toLowerCase().trim() === 'non classé' || tags.trim() === '';
      }
      // Tags est un tableau avec uniquement "Non classé"
      if (Array.isArray(tags) && tags.length === 1 && tags[0]?.toLowerCase().trim() === 'non classé') return true;
      return false;
    }).length;
  }, [rows]);
  
  // Appliquer les filtres
  const filteredRows = useMemo(() => {
    let filtered = [...rows];
    
    // Filtre par recherche
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      filtered = filtered.filter(row => 
        row.label?.toLowerCase().includes(searchLower) ||
        row.tags?.some(tag => tag.toLowerCase().includes(searchLower))
      );
    }
    
    // Filtre par type
    if (filterType === 'income') {
      filtered = filtered.filter(row => row.amount >= 0);
    } else if (filterType === 'expense') {
      filtered = filtered.filter(row => row.amount < 0);
    }
    
    // Filtre par exclusion
    if (filterExclude === 'included') {
      filtered = filtered.filter(row => !row.exclude);
    } else if (filterExclude === 'excluded') {
      filtered = filtered.filter(row => row.exclude);
    }
    
    return filtered;
  }, [rows, searchText, filterType, filterExclude]);

  useEffect(() => {
    if (!authLoading) {
      refresh(isAuthenticated, month);
    }
  }, [isAuthenticated, month, authLoading, refresh]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full">
          <div className="text-center">
            <div className="bg-red-100 rounded-full p-3 w-16 h-16 mx-auto mb-4">
              <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentification requise</h2>
            <p className="text-gray-600">Veuillez vous connecter pour accéder aux transactions.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header moderne */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-[100] overflow-visible">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4">
            {/* Ligne supérieure */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 rounded-lg p-2">
                  <CurrencyEuroIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
                  <div className="mt-1 overflow-visible">
                    <MonthPicker
                      currentMonth={month}
                      onMonthChange={setMonth}
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Bouton Scanner Ticket OCR */}
                <button
                  onClick={() => setShowReceiptScanner(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                  title="Scanner un ticket de caisse"
                >
                  <CameraIcon className="h-5 w-5" />
                  <span className="hidden sm:inline">Scanner</span>
                </button>

                {/* Bouton Auto-Tag */}
                {untaggedCount > 0 && (
                  <button
                    onClick={() => {
                      setShowAutoTagModal(true);
                      handlePreviewAutoTag();
                    }}
                    disabled={loading || autoTagLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={`${untaggedCount} transactions sans tag`}
                  >
                    <SparklesIcon className="h-5 w-5" />
                    Auto-Tag
                    <span className="bg-purple-400 text-xs rounded-full px-2 py-0.5">
                      {untaggedCount}
                    </span>
                  </button>
                )}

                <button
                  onClick={() => refresh(isAuthenticated, month)}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
                  Actualiser
                </button>
              </div>
            </div>

            {/* Barre de recherche et filtres */}
            <div className="flex items-center gap-3">
              {/* Recherche */}
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  placeholder="Rechercher par libellé ou tag..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Bouton filtres */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 border rounded-lg transition-colors ${
                  showFilters ? 'bg-blue-50 border-blue-300 text-blue-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <FunnelIcon className="h-5 w-5" />
                Filtres
                {(filterType !== 'all' || filterExclude !== 'all') && (
                  <span className="bg-blue-600 text-white text-xs rounded-full px-2 py-0.5">
                    {(filterType !== 'all' ? 1 : 0) + (filterExclude !== 'all' ? 1 : 0)}
                  </span>
                )}
              </button>
            </div>

            {/* Panneau de filtres */}
            {showFilters && (
              <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Type de transaction</label>
                    <select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value as any)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">Toutes</option>
                      <option value="income">Revenus uniquement</option>
                      <option value="expense">Dépenses uniquement</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Statut d'inclusion</label>
                    <select
                      value={filterExclude}
                      onChange={(e) => setFilterExclude(e.target.value as any)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">Toutes</option>
                      <option value="included">Incluses uniquement</option>
                      <option value="excluded">Exclues uniquement</option>
                    </select>
                  </div>
                </div>
                
                {(filterType !== 'all' || filterExclude !== 'all') && (
                  <button
                    onClick={() => {
                      setFilterType('all');
                      setFilterExclude('all');
                    }}
                    className="mt-3 text-sm text-blue-600 hover:text-blue-800"
                  >
                    Réinitialiser les filtres
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Contenu principal */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Resume global du mois (toutes les pages) */}
        {globalStats && (
          <div className="mb-6 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Resume du mois (toutes transactions)</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">
                  {globalStats.totalIncome.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} EUR
                </p>
                <p className="text-xs text-gray-500 mt-1">Revenus totaux</p>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <p className="text-2xl font-bold text-red-600">
                  {globalStats.totalExpenses.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} EUR
                </p>
                <p className="text-xs text-gray-500 mt-1">Depenses totales</p>
              </div>
              <div className={`text-center p-3 rounded-lg ${globalStats.netBalance >= 0 ? 'bg-blue-50' : 'bg-orange-50'}`}>
                <p className={`text-2xl font-bold ${globalStats.netBalance >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                  {globalStats.netBalance >= 0 ? '+' : ''}{globalStats.netBalance.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} EUR
                </p>
                <p className="text-xs text-gray-500 mt-1">Solde net</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-700">{globalStats.totalCount}</p>
                <p className="text-xs text-gray-500 mt-1">Transactions totales</p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-2xl shadow-sm p-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Chargement des transactions...</p>
            </div>
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm p-12">
            <div className="text-center">
              <div className="bg-gray-100 rounded-full p-3 w-16 h-16 mx-auto mb-4">
                <TagIcon className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Aucune transaction trouvée
              </h3>
              <p className="text-gray-600 mb-6">
                {rows.length > 0 
                  ? "Aucune transaction ne correspond aux filtres sélectionnés."
                  : `Aucune transaction n'a été importée pour ${month}.`
                }
              </p>
              {rows.length > 0 && (
                <button 
                  onClick={() => {
                    setSearchText('');
                    setFilterType('all');
                    setFilterExclude('all');
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Réinitialiser les filtres
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            {filteredRows.length < rows.length && (
              <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm text-blue-800">
                  Affichage de {filteredRows.length} transactions sur {rows.length} total
                </p>
              </div>
            )}
            
            <ModernTransactionsTable
              rows={filteredRows}
              onToggle={toggle}
              onSaveTags={saveTags}
              onBulkUnexcludeAll={bulkUnexcludeAll}
              editTransactionId={editTransactionId}
              onEditComplete={handleEditComplete}
            />

            {/* Contrôles de pagination */}
            {pagination.pages > 1 && (
              <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  {/* Info pagination */}
                  <div className="text-sm text-gray-600">
                    Page <span className="font-semibold text-gray-900">{pagination.page}</span> sur{' '}
                    <span className="font-semibold text-gray-900">{pagination.pages}</span>
                    <span className="text-gray-400 ml-2">
                      ({pagination.total} transactions au total)
                    </span>
                  </div>

                  {/* Contrôles */}
                  <div className="flex items-center gap-4">
                    {/* Sélecteur de limite */}
                    <div className="flex items-center gap-2">
                      <label htmlFor="limit-select" className="text-sm text-gray-600">
                        Afficher
                      </label>
                      <select
                        id="limit-select"
                        value={pagination.limit}
                        onChange={(e) => setLimit(Number(e.target.value))}
                        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      >
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                        <option value={200}>200</option>
                      </select>
                      <span className="text-sm text-gray-600">par page</span>
                    </div>

                    {/* Boutons navigation */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setPage(1)}
                        disabled={!pagination.hasPrev}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        title="Première page"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setPage(pagination.page - 1)}
                        disabled={!pagination.hasPrev}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        title="Page précédente"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                      </button>

                      {/* Numéros de pages */}
                      <div className="flex items-center gap-1 px-2">
                        {Array.from({ length: Math.min(5, pagination.pages) }, (_, i) => {
                          let pageNum: number;
                          if (pagination.pages <= 5) {
                            pageNum = i + 1;
                          } else if (pagination.page <= 3) {
                            pageNum = i + 1;
                          } else if (pagination.page >= pagination.pages - 2) {
                            pageNum = pagination.pages - 4 + i;
                          } else {
                            pageNum = pagination.page - 2 + i;
                          }
                          return (
                            <button
                              key={pageNum}
                              onClick={() => setPage(pageNum)}
                              className={`w-8 h-8 text-sm rounded-lg transition-colors ${
                                pageNum === pagination.page
                                  ? 'bg-blue-600 text-white font-semibold'
                                  : 'text-gray-600 hover:bg-gray-100'
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                      </div>

                      <button
                        onClick={() => setPage(pagination.page + 1)}
                        disabled={!pagination.hasNext}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        title="Page suivante"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setPage(pagination.pages)}
                        disabled={!pagination.hasNext}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        title="Dernière page"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal Auto-Tagging */}
      {showAutoTagModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-purple-600 to-blue-600">
              <div className="flex items-center gap-3">
                <SparklesIcon className="h-6 w-6 text-white" />
                <div>
                  <h2 className="text-lg font-semibold text-white">Auto-Tagging Intelligent</h2>
                  <p className="text-sm text-purple-100">
                    Suggestions basees sur les transactions similaires
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowAutoTagModal(false);
                  setAutoTagResult(null);
                  setAutoTagError(null);
                }}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              >
                <XMarkIcon className="h-5 w-5 text-white" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {autoTagLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mb-4"></div>
                  <p className="text-gray-600">Analyse des patterns en cours...</p>
                </div>
              ) : autoTagError ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                  {autoTagError}
                </div>
              ) : autoTagResult ? (
                <>
                  {/* Stats */}
                  <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <p className="text-2xl font-bold text-gray-900">{autoTagResult.total_untagged}</p>
                        <p className="text-xs text-gray-500">Sans tag</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-purple-600">{autoTagResult.suggestions.length}</p>
                        <p className="text-xs text-gray-500">Suggestions</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-green-600">{selectedSuggestions.size}</p>
                        <p className="text-xs text-gray-500">Selectionnees</p>
                      </div>
                    </div>
                  </div>

                  {autoTagResult.suggestions.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <TagIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                      <p>Aucune suggestion disponible.</p>
                      <p className="text-sm">Taguez d'abord quelques transactions pour entrainer l'IA.</p>
                    </div>
                  ) : (
                    <>
                      {/* Select All */}
                      <div className="flex items-center justify-between mb-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedSuggestions.size === autoTagResult.suggestions.length}
                            onChange={toggleAllSuggestions}
                            className="w-4 h-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
                          />
                          <span className="text-sm text-gray-700">Tout selectionner</span>
                        </label>
                        <span className="text-xs text-gray-500">
                          {selectedSuggestions.size}/{autoTagResult.suggestions.length} selectionnees
                        </span>
                      </div>

                      {/* Suggestions List */}
                      <div className="space-y-2">
                        {autoTagResult.suggestions.map((suggestion) => (
                          <div
                            key={suggestion.transaction_id}
                            className={`border rounded-lg p-3 transition-colors ${
                              selectedSuggestions.has(suggestion.transaction_id)
                                ? 'border-purple-300 bg-purple-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <label className="flex items-start gap-3 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={selectedSuggestions.has(suggestion.transaction_id)}
                                onChange={() => toggleSuggestion(suggestion.transaction_id)}
                                className="w-4 h-4 mt-1 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
                              />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {suggestion.label}
                                </p>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                    {suggestion.suggested_tag}
                                  </span>
                                  <span className={`text-xs ${
                                    suggestion.confidence >= 0.8 ? 'text-green-600' :
                                    suggestion.confidence >= 0.6 ? 'text-amber-700' : 'text-gray-500'
                                  }`}>
                                    {Math.round(suggestion.confidence * 100)}% confiance
                                  </span>
                                  <span className="text-xs text-gray-400">
                                    ({suggestion.match_type})
                                  </span>
                                </div>
                                {suggestion.source_label && (
                                  <p className="text-xs text-gray-400 mt-1 truncate">
                                    Similaire a: {suggestion.source_label}
                                  </p>
                                )}
                              </div>
                            </label>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              ) : null}
            </div>

            {/* Footer */}
            {autoTagResult && autoTagResult.suggestions.length > 0 && (
              <div className="p-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                <button
                  onClick={() => {
                    setShowAutoTagModal(false);
                    setAutoTagResult(null);
                  }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleApplySelectedTags}
                  disabled={applyingTags || selectedSuggestions.size === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {applyingTags ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Application...
                    </>
                  ) : (
                    <>
                      <CheckIcon className="h-5 w-5" />
                      Appliquer {selectedSuggestions.size} tag{selectedSuggestions.size > 1 ? 's' : ''}
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal Scanner de Tickets OCR */}
      {showReceiptScanner && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <CameraIcon className="h-6 w-6 text-emerald-600" />
                Scanner un ticket
              </h2>
              <button
                onClick={() => setShowReceiptScanner(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <XMarkIcon className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4">
              <ReceiptScanner
                onTransactionCreated={(txId) => {
                  // Fermer le modal et rafraîchir les transactions
                  setShowReceiptScanner(false);
                  refresh(isAuthenticated, month);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}