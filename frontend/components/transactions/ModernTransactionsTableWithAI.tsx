'use client';

import { useState, useMemo, useEffect } from 'react';
import { Tx, expenseClassificationApi } from '../../lib/api';
import { ChevronDownIcon, ChevronUpIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { useToast } from '../ui';

interface ModernTransactionsTableProps {
  rows: Tx[];
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
  onBulkUnexcludeAll?: () => void;
  editTransactionId?: number | null; // ID de la transaction à éditer automatiquement
  onEditComplete?: () => void; // Callback après édition terminée
}

interface AISuggestion {
  tags: string[];
  confidence: number;
  source?: string;
}

export function ModernTransactionsTable({
  rows,
  onToggle,
  onSaveTags,
  onBulkUnexcludeAll,
  editTransactionId,
  onEditComplete
}: ModernTransactionsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [editingTags, setEditingTags] = useState<{ [key: number]: string }>({});
  const [loadingSuggestions, setLoadingSuggestions] = useState<{ [key: number]: boolean }>({});
  const [suggestions, setSuggestions] = useState<{ [key: number]: AISuggestion }>({});
  const { addToast } = useToast();

  // Auto-ouvrir l'édition pour une transaction spécifique (depuis Analytics)
  useEffect(() => {
    if (editTransactionId && rows.length > 0) {
      const targetRow = rows.find(r => r.id === editTransactionId);
      if (targetRow) {
        // Ouvrir l'édition des tags pour cette transaction
        const currentTags = targetRow.tags?.join(', ') || '';
        setEditingTags(prev => ({ ...prev, [editTransactionId]: currentTags }));
        // Expand la ligne pour plus de visibilité
        setExpandedRows(prev => new Set(prev).add(editTransactionId));

        // Scroll vers la transaction (avec un délai pour le rendu)
        setTimeout(() => {
          const element = document.getElementById(`tx-row-${editTransactionId}`);
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Animation de mise en évidence
            element.classList.add('ring-2', 'ring-purple-500', 'ring-offset-2');
            setTimeout(() => {
              element.classList.remove('ring-2', 'ring-purple-500', 'ring-offset-2');
            }, 3000);
          }
        }, 100);
      }
    }
  }, [editTransactionId, rows]);

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

  // Obtenir les suggestions IA pour une transaction
  const fetchAISuggestions = async (row: Tx) => {
    if (loadingSuggestions[row.id]) return;
    
    setLoadingSuggestions(prev => ({ ...prev, [row.id]: true }));
    
    try {
      // Appel API pour obtenir les suggestions de tags
      const response = await expenseClassificationApi.suggestTags({
        transaction_id: row.id,
        label: row.label || '',
        amount: row.amount,
        existing_tags: row.tags || []
      });
      
      if (response.data?.suggestions?.length > 0) {
        setSuggestions(prev => ({
          ...prev,
          [row.id]: {
            tags: response.data.suggestions,
            confidence: response.data.confidence || 0,
            source: response.data.source // "web", "pattern", "history"
          }
        }));
      }
    } catch (error) {
      console.error('Error fetching AI suggestions:', error);
    } finally {
      setLoadingSuggestions(prev => ({ ...prev, [row.id]: false }));
    }
  };

  const handleTagEdit = (id: number, value: string) => {
    setEditingTags({ ...editingTags, [id]: value });
  };

  const handleTagSave = async (id: number) => {
    const tags = editingTags[id];
    if (tags !== undefined) {
      await onSaveTags(id, tags);
      const newEditingTags = { ...editingTags };
      delete newEditingTags[id];
      setEditingTags(newEditingTags);

      addToast({
        message: "Tags mis à jour avec succès",
        type: "success",
        duration: 2000
      });

      // Si c'était la transaction ouverte depuis Analytics, notifier la fin de l'édition
      if (id === editTransactionId && onEditComplete) {
        onEditComplete();
      }
    }
  };

  const applySuggestion = (rowId: number) => {
    const suggestion = suggestions[rowId];
    if (suggestion) {
      const tagsString = suggestion.tags.join(', ');
      handleTagEdit(rowId, tagsString);
      handleTagSave(rowId);
      
      addToast({
        message: `Tags suggérés appliqués (confiance: ${Math.round(suggestion.confidence * 100)}%)`,
        type: "success",
        duration: 3000
      });
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatDateShort = (dateStr: string) => {
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
            const hasSuggestions = suggestions[row.id];
            const isLoadingSuggestions = loadingSuggestions[row.id];
            
            return (
              <div
                key={row.id}
                id={`tx-row-${row.id}`}
                className={`transition-all duration-200 ${row.exclude ? 'opacity-50 bg-gray-50' : 'hover:bg-gray-50'}`}
              >
                {/* Ligne principale */}
                <div className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    {/* Partie gauche : Date et libellé */}
                    <div className="flex-1 min-w-0 pr-4">
                      <div className="flex items-start gap-4">
                        {/* Colonne Date - visible et formatée */}
                        <div className="flex-shrink-0 w-24 text-center bg-gray-50 rounded-lg px-2 py-1">
                          <div className="text-sm font-semibold text-gray-900">
                            {formatDate(row.date_op || row.date)}
                          </div>
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="text-base font-medium text-gray-900 truncate" title={row.label}>
                            {row.label}
                          </div>
                          
                          {/* Tags avec suggestions IA */}
                          <div className="mt-1">
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
                              <div className="flex items-center gap-2">
                                <div 
                                  className="flex flex-wrap gap-1 cursor-pointer"
                                  onClick={() => {
                                    const currentTags = row.tags?.join(', ') || '';
                                    handleTagEdit(row.id, currentTags);
                                    if (!hasSuggestions && !isLoadingSuggestions) {
                                      fetchAISuggestions(row);
                                    }
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
                                
                                {/* Bouton suggestions IA */}
                                {!row.tags?.length && (
                                  <button
                                    onClick={() => fetchAISuggestions(row)}
                                    disabled={isLoadingSuggestions}
                                    className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full transition-all ${
                                      isLoadingSuggestions 
                                        ? 'bg-gray-100 text-gray-400' 
                                        : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                                    }`}
                                  >
                                    <SparklesIcon className="h-3 w-3" />
                                    {isLoadingSuggestions ? 'Chargement...' : 'Suggestions IA'}
                                  </button>
                                )}
                              </div>
                            )}
                            
                            {/* Affichage des suggestions IA */}
                            {hasSuggestions && !isEditing && (
                              <div className="mt-2 p-2 bg-purple-50 rounded-lg">
                                <div className="flex items-start justify-between">
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <SparklesIcon className="h-4 w-4 text-purple-600" />
                                      <span className="text-xs font-medium text-purple-700">
                                        Suggestions IA ({Math.round(hasSuggestions.confidence * 100)}% confiance)
                                      </span>
                                      {hasSuggestions.source && (
                                        <span className="text-xs text-purple-600">
                                          • Source: {hasSuggestions.source === 'web' ? 'Web' : hasSuggestions.source === 'pattern' ? 'Patterns' : 'Historique'}
                                        </span>
                                      )}
                                    </div>
                                    <div className="mt-1 flex flex-wrap gap-1">
                                      {hasSuggestions.tags.map((tag, idx) => (
                                        <span 
                                          key={idx}
                                          className="px-2 py-0.5 bg-white text-purple-700 text-xs font-medium rounded-full border border-purple-300"
                                        >
                                          {tag}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                  <button
                                    onClick={() => applySuggestion(row.id)}
                                    className="text-xs bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 transition-colors"
                                  >
                                    Appliquer
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Partie droite : Montant et actions */}
                    <div className="flex items-center gap-4">
                      {/* Montant avec indicateur ML */}
                      <div className={`text-right ${isIncome ? 'text-green-600' : 'text-gray-900'}`}>
                        <div className="text-lg font-semibold">
                          {isIncome ? '+' : '-'}{formatAmount(row.amount)}
                        </div>
                        {row.ml_confidence && (
                          <div className="flex items-center justify-end gap-1">
                            <div className={`h-1.5 w-12 bg-gray-200 rounded-full overflow-hidden`}>
                              <div 
                                className={`h-full transition-all duration-300 ${
                                  row.ml_confidence > 0.8 ? 'bg-green-500' : 
                                  row.ml_confidence > 0.6 ? 'bg-yellow-500' : 
                                  'bg-red-500'
                                }`}
                                style={{ width: `${row.ml_confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-500">
                              {Math.round(row.ml_confidence * 100)}%
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {/* Toggle exclure */}
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
                          <span className="ml-2 text-gray-900">{formatDate(row.date_op || row.date)}</span>
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
                        {row.expense_type && (
                          <div>
                            <span className="text-gray-500">Type:</span>
                            <span className="ml-2 text-gray-900">
                              {row.expense_type === 'FIXED' ? 'Dépense fixe' : 'Dépense variable'}
                            </span>
                          </div>
                        )}
                      </div>
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