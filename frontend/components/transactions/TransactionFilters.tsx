'use client';

import React, { useState, useEffect } from 'react';
import { Card, Input } from '../ui';

interface TransactionFiltersProps {
  onFiltersChange: (filters: FilterState) => void;
}

export interface FilterState {
  searchText: string;
  dateFrom: string;
  dateTo: string;
  amountMin: string;
  amountMax: string;
  excludeFilter: 'all' | 'included' | 'excluded';
  transactionType: 'all' | 'income' | 'expense';
}

export function TransactionFilters({ onFiltersChange }: TransactionFiltersProps) {
  const [filters, setFilters] = useState<FilterState>({
    searchText: '',
    dateFrom: '',
    dateTo: '',
    amountMin: '',
    amountMax: '',
    excludeFilter: 'all',
    transactionType: 'all'
  });

  const [isExpanded, setIsExpanded] = useState(false);

  // Notify parent component when filters change
  useEffect(() => {
    onFiltersChange(filters);
  }, [filters, onFiltersChange]);

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleReset = () => {
    setFilters({
      searchText: '',
      dateFrom: '',
      dateTo: '',
      amountMin: '',
      amountMax: '',
      excludeFilter: 'all',
      transactionType: 'all'
    });
  };

  const hasActiveFilters = () => {
    return filters.searchText !== '' ||
           filters.dateFrom !== '' ||
           filters.dateTo !== '' ||
           filters.amountMin !== '' ||
           filters.amountMax !== '' ||
           filters.excludeFilter !== 'all' ||
           filters.transactionType !== 'all';
  };

  return (
    <Card className="mb-6">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">
              🔍 Filtres
            </h3>
            {hasActiveFilters() && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                Actifs
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {hasActiveFilters() && (
              <button
                onClick={handleReset}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Réinitialiser
              </button>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              {isExpanded ? '⬆ Réduire' : '⬇ Développer'}
            </button>
          </div>
        </div>

        {/* Quick search bar - always visible */}
        <div className="mb-3">
          <Input
            type="text"
            placeholder="🔎 Rechercher dans les libellés..."
            value={filters.searchText}
            onChange={(e) => handleFilterChange('searchText', e.target.value)}
            className="w-full"
          />
        </div>

        {/* Advanced filters - collapsible */}
        {isExpanded && (
          <div className="space-y-4 pt-4 border-t border-gray-200">
            {/* Date filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  📅 Date début
                </label>
                <Input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  📅 Date fin
                </label>
                <Input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                  className="w-full"
                />
              </div>
            </div>

            {/* Amount filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  💰 Montant min (€)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={filters.amountMin}
                  onChange={(e) => handleFilterChange('amountMin', e.target.value)}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  💰 Montant max (€)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={filters.amountMax}
                  onChange={(e) => handleFilterChange('amountMax', e.target.value)}
                  className="w-full"
                />
              </div>
            </div>

            {/* Status filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  📊 Type de transaction
                </label>
                <select
                  value={filters.transactionType}
                  onChange={(e) => handleFilterChange('transactionType', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">Toutes</option>
                  <option value="income">💚 Revenus (positifs)</option>
                  <option value="expense">💔 Dépenses (négatives)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ⚡ Statut d'exclusion
                </label>
                <select
                  value={filters.excludeFilter}
                  onChange={(e) => handleFilterChange('excludeFilter', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">Toutes</option>
                  <option value="included">✅ Incluses uniquement</option>
                  <option value="excluded">❌ Exclues uniquement</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Active filters summary */}
        {hasActiveFilters() && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex flex-wrap gap-2">
              {filters.searchText && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs flex items-center gap-1">
                  <span>Libellé: "{filters.searchText}"</span>
                  <button
                    onClick={() => handleFilterChange('searchText', '')}
                    className="ml-1 hover:text-blue-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.dateFrom && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs flex items-center gap-1">
                  <span>Depuis: {filters.dateFrom}</span>
                  <button
                    onClick={() => handleFilterChange('dateFrom', '')}
                    className="ml-1 hover:text-green-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.dateTo && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs flex items-center gap-1">
                  <span>Jusqu'à: {filters.dateTo}</span>
                  <button
                    onClick={() => handleFilterChange('dateTo', '')}
                    className="ml-1 hover:text-green-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.amountMin && (
                <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs flex items-center gap-1">
                  <span>Min: {filters.amountMin}€</span>
                  <button
                    onClick={() => handleFilterChange('amountMin', '')}
                    className="ml-1 hover:text-yellow-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.amountMax && (
                <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs flex items-center gap-1">
                  <span>Max: {filters.amountMax}€</span>
                  <button
                    onClick={() => handleFilterChange('amountMax', '')}
                    className="ml-1 hover:text-yellow-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.transactionType !== 'all' && (
                <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs flex items-center gap-1">
                  <span>{filters.transactionType === 'income' ? 'Revenus' : 'Dépenses'}</span>
                  <button
                    onClick={() => handleFilterChange('transactionType', 'all')}
                    className="ml-1 hover:text-purple-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {filters.excludeFilter !== 'all' && (
                <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs flex items-center gap-1">
                  <span>{filters.excludeFilter === 'included' ? 'Incluses' : 'Exclues'}</span>
                  <button
                    onClick={() => handleFilterChange('excludeFilter', 'all')}
                    className="ml-1 hover:text-red-900"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}