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
    const date = new Date(dateStr);
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
      {/* En-tête avec statistiques */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total</div>
            <div className="text-2xl font-bold text-gray-900">{stats.totalTransactions}</div>
            <div className="text-xs text-gray-600">transactions</div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">Revenus</div>
            <div className="text-2xl font-bold text-green-600">
              +{formatAmount(stats.totalIncome)}
            </div>
            <div className="text-xs text-gray-600">{stats.includedCount} incluses</div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">Dépenses</div>
            <div className="text-2xl font-bold text-red-600">
              -{formatAmount(stats.totalExpenses)}
            </div>
            <div className="text-xs text-gray-600">{stats.excludedCount} exclues</div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">Balance</div>
            <div className={`text-2xl font-bold ${stats.netBalance >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
              {stats.netBalance >= 0 ? '+' : ''}{formatAmount(stats.netBalance)}
            </div>
            <div className="text-xs text-gray-600">net</div>
          </div>
        </div>

        {/* Bouton réinclure tout */}
        {stats.excludedCount > 0 && (
          <div className="mt-4 flex justify-end">
            <button
              onClick={onBulkUnexcludeAll}
              className="px-4 py-2 bg-white text-blue-600 font-medium rounded-lg shadow-sm hover:shadow-md transition-all duration-200 text-sm"
            >
              Réinclure {stats.excludedCount} transaction{stats.excludedCount > 1 ? 's' : ''}
            </button>
          </div>
        )}
      </div>

      {/* Liste des transactions */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
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
                {/* Ligne principale */}
                <div className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    {/* Partie gauche : Date et libellé */}
                    <div className="flex-1 min-w-0 pr-4">
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 text-center">
                          <div className="text-sm font-semibold text-gray-900">
                            {formatDate(row.date)}
                          </div>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="text-base font-medium text-gray-900 truncate">
                            {row.label}
                          </div>
                          
                          {/* Tags */}
                          <div className="mt-1 flex flex-wrap gap-1">
                            {isEditing ? (
                              <div className="flex items-center gap-2">
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
                                  className="px-2 py-1 text-sm border border-blue-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="tag1, tag2..."
                                  autoFocus
                                />
                                <button
                                  onClick={() => handleTagSave(row.id)}
                                  className="text-xs text-blue-600 hover:text-blue-800"
                                >
                                  Sauver
                                </button>
                              </div>
                            ) : (
                              <div 
                                className="flex flex-wrap gap-1 cursor-pointer"
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
                                    + Ajouter des tags
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Partie droite : Montant et actions */}
                    <div className="flex items-center gap-4">
                      {/* Montant */}
                      <div className={`text-right ${isIncome ? 'text-green-600' : 'text-gray-900'}`}>
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
                        {/* Checkbox exclure */}
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={row.exclude}
                            onChange={() => onToggle(row.id, !row.exclude)}
                            className="sr-only peer"
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-400"></div>
                        </label>

                        {/* Bouton expand */}
                        <button
                          onClick={() => toggleExpanded(row.id)}
                          className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
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

                {/* Détails expandus */}
                {isExpanded && (
                  <div className="px-6 pb-4 pt-0">
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-gray-500">Date d'opération:</span>
                          <span className="ml-2 text-gray-900">{row.date_op || row.date}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Compte:</span>
                          <span className="ml-2 text-gray-900">{row.account || 'Principal'}</span>
                        </div>
                        {row.name && (
                          <div>
                            <span className="text-gray-500">Nom:</span>
                            <span className="ml-2 text-gray-900">{row.name}</span>
                          </div>
                        )}
                        {row.category && (
                          <div>
                            <span className="text-gray-500">Catégorie:</span>
                            <span className="ml-2 text-gray-900">{row.category}</span>
                          </div>
                        )}
                      </div>
                      {row.ml_confidence && (
                        <div className="pt-2 border-t border-gray-200">
                          <span className="text-gray-500">Confiance IA:</span>
                          <span className="ml-2 text-gray-900">{Math.round(row.ml_confidence * 100)}%</span>
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