'use client';

import { useEffect, useState, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useGlobalMonthWithUrl } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { useTransactions } from "../../hooks/useTransactions";
import { ModernTransactionsTable } from "../../components/transactions/ModernTransactionsTableWithAI";
import { 
  MagnifyingGlassIcon, 
  FunnelIcon,
  ArrowPathIcon,
  CalendarIcon,
  CurrencyEuroIcon,
  TagIcon
} from '@heroicons/react/24/outline';

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
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
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
                  <p className="text-sm text-gray-500">{month || 'Sélectionnez un mois'}</p>
                </div>
              </div>
              
              <button 
                onClick={() => refresh(isAuthenticated, month)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
                Actualiser
              </button>
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
            />
          </>
        )}
      </div>
    </div>
  );
}