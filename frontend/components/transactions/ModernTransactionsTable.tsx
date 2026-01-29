'use client';

import { useState, useMemo } from 'react';
import { Tx } from '../../lib/api';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface ModernTransactionsTableProps {
  rows: Tx[];
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
  onBulkUnexcludeAll?: () => void;
}

export function ModernTransactionsTable({ 
  rows, 
  onToggle, 
  onSaveTags,
  onBulkUnexcludeAll
}: ModernTransactionsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [editingTags, setEditingTags] = useState<{ [key: number]: string }>({});

  // Calculer les statistiques
  const stats = useMemo(() => {
    const included = rows.filter(r => !r.exclude);
    const excluded = rows.filter(r => r.exclude);
    const income = included.filter(r => r.amount > 0);
    const expenses = included.filter(r => r.amount < 0);
    
    return {
      totalTransactions: rows.length,
      includedCount: included.length,
      excludedCount: excluded.length,
      totalIncome: income.reduce((sum, r) => sum + r.amount, 0),
      totalExpenses: Math.abs(expenses.reduce((sum, r) => sum + r.amount, 0)),
      netBalance: included.reduce((sum, r) => sum + r.amount, 0)
    };
  }, [rows]);

  const toggleExpanded = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const handleTagEdit = (id: number, value: string) => {
    setEditingTags({ ...editingTags, [id]: value });
  };

  const handleTagSave = (id: number) => {
    const tags = editingTags[id];
    if (tags !== undefined) {
      onSaveTags(id, tags);
      const newEditingTags = { ...editingTags };
      delete newEditingTags[id];
      setEditingTags(newEditingTags);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short'
    });
  };

  const formatAmount = (amount: number) => {
    const absAmount = Math.abs(amount);
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(absAmount);
  };

  return (
    <div className="space-y-6">
      {/* En-tête avec statistiques - Mobile optimized */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl md:rounded-2xl p-3 md:p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4">
          <div className="bg-white rounded-lg md:rounded-xl p-2.5 md:p-4 shadow-sm">
            <div className="text-[10px] md:text-xs text-gray-500 font-medium uppercase tracking-wider">Total</div>
            <div className="text-lg md:text-2xl font-bold text-gray-900">{stats.totalTransactions}</div>
            <div className="text-[10px] md:text-xs text-gray-600">transactions</div>
          </div>

          <div className="bg-white rounded-lg md:rounded-xl p-2.5 md:p-4 shadow-sm">
            <div className="text-[10px] md:text-xs text-gray-500 font-medium uppercase tracking-wider">Revenus</div>
            <div className="text-lg md:text-2xl font-bold text-green-600">
              +{formatAmount(stats.totalIncome)}
            </div>
            <div className="text-[10px] md:text-xs text-gray-600">{stats.includedCount} incluses</div>
          </div>

          <div className="bg-white rounded-lg md:rounded-xl p-2.5 md:p-4 shadow-sm">
            <div className="text-[10px] md:text-xs text-gray-500 font-medium uppercase tracking-wider">Dépenses</div>
            <div className="text-lg md:text-2xl font-bold text-red-600">
              -{formatAmount(stats.totalExpenses)}
            </div>
            <div className="text-[10px] md:text-xs text-gray-600">{stats.excludedCount} exclues</div>
          </div>

          <div className="bg-white rounded-lg md:rounded-xl p-2.5 md:p-4 shadow-sm">
            <div className="text-[10px] md:text-xs text-gray-500 font-medium uppercase tracking-wider">Balance</div>
            <div className={`text-lg md:text-2xl font-bold ${stats.netBalance >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
              {stats.netBalance >= 0 ? '+' : ''}{formatAmount(stats.netBalance)}
            </div>
            <div className="text-[10px] md:text-xs text-gray-600">net</div>
          </div>
        </div>

        {/* Bouton réinclure tout */}
        {stats.excludedCount > 0 && (
          <div className="mt-3 md:mt-4 flex justify-end">
            <button
              onClick={onBulkUnexcludeAll}
              className="px-3 md:px-4 py-2 bg-white text-blue-600 font-medium rounded-lg shadow-sm hover:shadow-md transition-all duration-200 text-xs md:text-sm min-h-[44px]"
            >
              Réinclure {stats.excludedCount} transaction{stats.excludedCount > 1 ? 's' : ''}
            </button>
          </div>
        )}
      </div>

      {/* Liste des transactions - Mobile optimized */}
      <div className="bg-white rounded-xl md:rounded-2xl shadow-sm overflow-hidden">
        <div className="divide-y divide-gray-100">
          {rows.map(row => {
            const isExpanded = expandedRows.has(row.id);
            const isEditing = editingTags[row.id] !== undefined;
            const isIncome = row.amount > 0;

            return (
              <div
                key={row.id}
                className={`transition-all duration-200 ${row.exclude ? 'opacity-50 bg-gray-50' : 'hover:bg-gray-50'}`}
              >
                {/* Ligne principale - Stack on mobile */}
                <div className="px-3 md:px-6 py-3 md:py-4">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 md:gap-0">
                    {/* Partie gauche : Date, libellé, montant sur mobile */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-2 md:gap-4">
                        {/* Date - More compact on mobile */}
                        <div className="flex-shrink-0 text-center min-w-[45px] md:min-w-[55px]">
                          <div className="text-xs md:text-sm font-semibold text-gray-900">
                            {formatDate(row.date)}
                          </div>
                        </div>

                        {/* Label and tags */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="text-sm md:text-base font-medium text-gray-900 truncate flex-1">
                              {row.label}
                            </div>
                            {/* Amount on mobile - inline */}
                            <div className={`md:hidden text-right flex-shrink-0 ${isIncome ? 'text-green-600' : 'text-gray-900'}`}>
                              <div className="text-sm font-semibold whitespace-nowrap">
                                {isIncome ? '+' : '-'}{formatAmount(row.amount)}
                              </div>
                            </div>
                          </div>

                          {/* Tags */}
                          <div className="mt-1 flex flex-wrap gap-1">
                            {isEditing ? (
                              <div className="flex items-center gap-2 w-full">
                                <input
                                  type="text"
                                  value={editingTags[row.id]}
                                  onChange={(e) => handleTagEdit(row.id, e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') handleTagSave(row.id);
                                    if (e.key === 'Escape') {
                                      const newEditingTags = { ...editingTags };
                                      delete newEditingTags[row.id];
                                      setEditingTags(newEditingTags);
                                    }
                                  }}
                                  className="flex-1 px-2 py-1.5 text-sm border border-blue-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[44px]"
                                  placeholder="tag1, tag2..."
                                  autoFocus
                                />
                                <button
                                  onClick={() => handleTagSave(row.id)}
                                  className="text-xs text-blue-600 hover:text-blue-800 min-h-[44px] px-2"
                                >
                                  Sauver
                                </button>
                              </div>
                            ) : (
                              <div
                                className="flex flex-wrap gap-1 cursor-pointer min-h-[24px]"
                                onClick={() => {
                                  const currentTags = row.tags?.join(', ') || '';
                                  handleTagEdit(row.id, currentTags);
                                }}
                              >
                                {row.tags && row.tags.length > 0 ? (
                                  row.tags.map((tag, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full"
                                    >
                                      {tag}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-gray-400 italic hover:text-blue-600">
                                    + Ajouter tags
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Partie droite : Montant et actions - Hidden amount on mobile */}
                    <div className="flex items-center justify-end gap-2 md:gap-4 mt-2 md:mt-0">
                      {/* Montant - Desktop only */}
                      <div className={`hidden md:block text-right ${isIncome ? 'text-green-600' : 'text-gray-900'}`}>
                        <div className="text-lg font-semibold">
                          {isIncome ? '+' : '-'}{formatAmount(row.amount)}
                        </div>
                        {row.expense_type && (
                          <div className="text-xs text-gray-500">
                            {row.expense_type === 'FIXED' ? 'Fixe' : 'Variable'}
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {/* Expense type badge on mobile */}
                        {row.expense_type && (
                          <span className="md:hidden text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                            {row.expense_type === 'FIXED' ? 'Fixe' : 'Var'}
                          </span>
                        )}

                        {/* Checkbox exclure */}
                        <label className="relative inline-flex items-center cursor-pointer min-h-[44px] min-w-[44px] justify-center">
                          <input
                            type="checkbox"
                            checked={row.exclude}
                            onChange={() => onToggle(row.id, !row.exclude)}
                            className="sr-only peer"
                            aria-label={row.exclude ? 'Réinclure la transaction' : 'Exclure la transaction'}
                          />
                          <div className="w-9 h-5 md:w-11 md:h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 md:after:h-5 md:after:w-5 after:transition-all peer-checked:bg-red-400"></div>
                        </label>

                        {/* Bouton expand */}
                        <button
                          onClick={() => toggleExpanded(row.id)}
                          className="p-2 rounded-lg hover:bg-gray-100 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                          aria-label={isExpanded ? 'Masquer les détails' : 'Afficher les détails'}
                          aria-expanded={isExpanded}
                        >
                          {isExpanded ? (
                            <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                          ) : (
                            <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Détails expandus - Mobile optimized */}
                {isExpanded && (
                  <div className="px-3 md:px-6 pb-3 md:pb-4 pt-0">
                    <div className="bg-gray-50 rounded-lg p-3 md:p-4 space-y-2 text-xs md:text-sm">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 md:gap-4">
                        <div className="flex justify-between md:block">
                          <span className="text-gray-500">Date d'opération:</span>
                          <span className="md:ml-2 text-gray-900 font-medium md:font-normal">{row.date_op || row.date}</span>
                        </div>
                        <div className="flex justify-between md:block">
                          <span className="text-gray-500">Compte:</span>
                          <span className="md:ml-2 text-gray-900 font-medium md:font-normal">{row.account || 'Principal'}</span>
                        </div>
                        {row.name && (
                          <div className="flex justify-between md:block">
                            <span className="text-gray-500">Nom:</span>
                            <span className="md:ml-2 text-gray-900 font-medium md:font-normal truncate">{row.name}</span>
                          </div>
                        )}
                        {row.category && (
                          <div className="flex justify-between md:block">
                            <span className="text-gray-500">Catégorie:</span>
                            <span className="md:ml-2 text-gray-900 font-medium md:font-normal">{row.category}</span>
                          </div>
                        )}
                      </div>
                      {row.ml_confidence && (
                        <div className="pt-2 border-t border-gray-200 flex justify-between md:block">
                          <span className="text-gray-500">Confiance IA:</span>
                          <span className="md:ml-2 text-gray-900 font-medium md:font-normal">{Math.round(row.ml_confidence * 100)}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}