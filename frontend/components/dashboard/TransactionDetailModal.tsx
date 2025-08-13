'use client';

import React, { useState, useEffect } from 'react';
import { Modal, LoadingSpinner } from '../ui';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';

interface Transaction {
  id: number;
  month: string;
  date_op: string;
  date_valeur: string;
  amount: number;
  label: string;
  category: string;
  subcategory: string;
  is_expense: boolean;
  exclude: boolean;
  expense_type: string;
  tags: string[];
}

interface TransactionDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  category: 'provision' | 'fixed' | 'variable';
  categoryName?: string;
  month: string;
  tagFilter?: string;
  onOpenHierarchicalNavigation?: (title: string, initialCategory?: string, initialFilters?: any) => void;
}

export function TransactionDetailModal({ 
  isOpen, 
  onClose, 
  title, 
  category, 
  categoryName,
  month,
  tagFilter,
  onOpenHierarchicalNavigation
}: TransactionDetailModalProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [subtotals, setSubtotals] = useState<{ [key: string]: number }>({});
  const router = useRouter();

  const loadTransactions = async () => {
    if (!isOpen) return;
    
    setLoading(true);
    setError('');
    
    try {
      let params: any = { month };
      
      // Filtrer selon le type de catégorie
      if (category === 'provision') {
        params.expense_type = 'PROVISION';
      } else if (category === 'fixed') {
        params.expense_type = 'FIXED';
      } else if (category === 'variable') {
        params.expense_type = 'VARIABLE';
      }
      
      // Ajouter filtre de tag si spécifié (support pour tags multiples séparés par virgule)
      if (tagFilter) {
        params.tag = tagFilter;
      }
      
      console.log('🔍 Modal filtering params:', params);
      
      const response = await api.get<Transaction[]>('/transactions', { params });
      const txs = response.data.filter(t => !t.exclude && t.is_expense);
      
      setTransactions(txs);
      
      // Calculer les sous-totaux par tag
      const tagSubtotals: { [key: string]: number } = {};
      txs.forEach(tx => {
        if (tx.tags && tx.tags.length > 0) {
          tx.tags.forEach(tag => {
            tagSubtotals[tag] = (tagSubtotals[tag] || 0) + Math.abs(tx.amount);
          });
        } else {
          tagSubtotals['Non taggé'] = (tagSubtotals['Non taggé'] || 0) + Math.abs(tx.amount);
        }
      });
      
      setSubtotals(tagSubtotals);
      
    } catch (err: any) {
      setError('Erreur lors du chargement des transactions');
      console.error('Error loading transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [isOpen, month, category, tagFilter]);

  const handleTransactionClick = (transactionId: number) => {
    onClose();
    router.push(`/transactions?highlight=${transactionId}`);
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  const formatAmount = (amount: number) => {
    return Math.abs(amount).toFixed(2) + ' €';
  };

  const getTotalAmount = () => {
    return transactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={title}
      size="xl"
    >
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="md" text="Chargement des transactions..." />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
          {error}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Modern Summary Header */}
          <div className="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 rounded-2xl p-6 border-2 border-blue-100/50 shadow-lg backdrop-blur-sm">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="group bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-105 border border-gray-100/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors duration-300">
                    <span className="text-lg text-blue-600">📊</span>
                  </div>
                  <div className="text-xs text-blue-600 uppercase font-semibold tracking-wider">Total</div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">{transactions.length}</div>
                <div className="text-xs text-gray-600 font-medium">
                  {category === 'provision' ? 'provisions' : category === 'fixed' ? 'charges fixes' : 'variables'}
                </div>
              </div>
              
              <div className="group bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-105 border border-gray-100/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors duration-300">
                    <span className="text-lg text-green-600">💰</span>
                  </div>
                  <div className="text-xs text-green-600 uppercase font-semibold tracking-wider">Montant</div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">{formatAmount(getTotalAmount())}</div>
                <div className="text-xs text-gray-600 font-medium">somme totale</div>
              </div>
              
              <div className="group bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-105 border border-gray-100/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors duration-300">
                    <span className="text-lg text-purple-600">🏷️</span>
                  </div>
                  <div className="text-xs text-purple-600 uppercase font-semibold tracking-wider">Tags</div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">{Object.keys(subtotals).length}</div>
                <div className="text-xs text-gray-600 font-medium">catégories</div>
              </div>
              
              <div className="group bg-white/80 backdrop-blur-sm rounded-xl p-4 shadow-md hover:shadow-xl transition-all duration-300 hover:scale-105 border border-gray-100/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="p-2 bg-orange-100 rounded-lg group-hover:bg-orange-200 transition-colors duration-300">
                    <span className="text-lg text-orange-600">📈</span>
                  </div>
                  <div className="text-xs text-orange-600 uppercase font-semibold tracking-wider">Moyenne</div>
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {transactions.length > 0 ? formatAmount(getTotalAmount() / transactions.length) : '0.00 €'}
                </div>
                <div className="text-xs text-gray-600 font-medium">par transaction</div>
              </div>
            </div>
          </div>

          {/* Modern Tag Distribution */}
          {Object.keys(subtotals).length > 1 && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h4 className="text-xl font-bold text-gray-900 flex items-center">
                  <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg mr-3">
                    <span className="text-white text-lg">🏷️</span>
                  </div>
                  Répartition par Tag
                </h4>
                <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  {Object.keys(subtotals).length} tags
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(subtotals)
                  .sort(([,a], [,b]) => b - a)
                  .map(([tag, amount]) => {
                    const percentage = ((amount / getTotalAmount()) * 100).toFixed(1);
                    const isUntagged = tag === 'Non taggé';
                    return (
                      <div key={tag} className={`group relative overflow-hidden rounded-xl p-5 border-2 transition-all duration-300 hover:shadow-xl hover:scale-105 ${
                        isUntagged 
                          ? 'bg-gradient-to-br from-gray-50 to-gray-100 border-gray-200 hover:border-gray-300' 
                          : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 border-blue-200 hover:border-blue-300'
                      }`}>
                        <div className="relative z-10">
                          <div className="flex items-center justify-between mb-3">
                            <div className={`text-sm font-bold truncate flex-1 ${
                              isUntagged ? 'text-gray-700' : 'text-blue-800'
                            }`} title={tag}>
                              {isUntagged ? '🔄 ' + tag : tag}
                            </div>
                            <div className={`text-xs px-2 py-1 rounded-full font-medium ${
                              isUntagged ? 'bg-gray-200 text-gray-600' : 'bg-blue-200 text-blue-700'
                            }`}>
                              {percentage}%
                            </div>
                          </div>
                          <div className={`text-xl font-bold mb-3 ${
                            isUntagged ? 'text-gray-900' : 'text-blue-900'
                          }`}>
                            {formatAmount(amount)}
                          </div>
                          {/* Modern progress bar */}
                          <div className="relative">
                            <div className="w-full bg-gray-200/50 rounded-full h-3 overflow-hidden">
                              <div 
                                className={`h-full rounded-full transition-all duration-500 ease-out ${
                                  isUntagged 
                                    ? 'bg-gradient-to-r from-gray-400 via-gray-500 to-gray-600 shadow-inner' 
                                    : 'bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-600 shadow-inner'
                                }`}
                                style={{ width: `${percentage}%` }}
                              ></div>
                            </div>
                            <div className={`absolute inset-0 rounded-full opacity-0 group-hover:opacity-20 transition-opacity duration-300 ${
                              isUntagged ? 'bg-gray-400' : 'bg-blue-400'
                            }`}></div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Modern Transaction Cards */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <h4 className="text-xl font-bold text-gray-900 flex items-center">
                <div className="p-2 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg mr-3">
                  <span className="text-white text-lg">📊</span>
                </div>
                Transactions Détaillées
              </h4>
              <div className="flex items-center space-x-2">
                <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  {transactions.length} transactions
                </div>
                <div className="text-sm font-bold text-green-600 bg-green-100 px-3 py-1 rounded-full">
                  {formatAmount(getTotalAmount())}
                </div>
              </div>
            </div>
            
            <div className="max-h-[500px] overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
              {transactions.length === 0 ? (
                <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl border-2 border-dashed border-gray-200">
                  <div className="text-6xl mb-4 opacity-50">💭</div>
                  <div className="text-xl font-semibold text-gray-700 mb-2">Aucune transaction</div>
                  <div className="text-gray-500">pour cette catégorie et ce mois</div>
                </div>
              ) : (
                transactions
                  .sort((a, b) => new Date(b.date_op).getTime() - new Date(a.date_op).getTime())
                  .map((tx, index) => {
                    const isRecent = new Date(tx.date_op).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000;
                    return (
                      <div
                        key={tx.id}
                        onClick={() => handleTransactionClick(tx.id)}
                        className={`group relative overflow-hidden bg-white rounded-xl border-2 border-gray-100 p-5 cursor-pointer transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-blue-200 ${
                          isRecent ? 'ring-2 ring-green-200 border-green-200' : ''
                        }`}
                      >
                        {/* Recent indicator */}
                        {isRecent && (
                          <div className="absolute top-0 right-0 w-0 h-0 border-l-[30px] border-l-transparent border-t-[30px] border-t-green-400">
                            <div className="absolute -top-7 -right-1 text-xs text-white font-bold transform rotate-45">
                              NEW
                            </div>
                          </div>
                        )}
                        
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0 pr-4">
                            {/* Transaction title */}
                            <div className="flex items-start justify-between mb-3">
                              <h5 className="text-base font-semibold text-gray-900 truncate flex-1 group-hover:text-blue-700 transition-colors duration-200" title={tx.label}>
                                {tx.label}
                              </h5>
                            </div>
                            
                            {/* Metadata row */}
                            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mb-3">
                              <div className="flex items-center space-x-1 bg-gray-100 px-2 py-1 rounded-full">
                                <span>📅</span>
                                <span className="font-medium">{formatDate(tx.date_op)}</span>
                              </div>
                              <div className="flex items-center space-x-1 bg-blue-100 px-2 py-1 rounded-full text-blue-700">
                                <span>🏷️</span>
                                <span className="font-medium">{tx.category}</span>
                                {tx.subcategory && (
                                  <>
                                    <span className="text-blue-400">›</span>
                                    <span>{tx.subcategory}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            
                            {/* Tags */}
                            <div className="flex flex-wrap gap-1.5">
                              {tx.tags && tx.tags.length > 0 ? (
                                tx.tags.map((tag, idx) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 text-xs px-3 py-1 rounded-full font-medium border border-blue-200 hover:from-blue-100 hover:to-indigo-100 transition-colors duration-200"
                                  >
                                    {tag}
                                  </span>
                                ))
                              ) : (
                                <span className="inline-flex items-center bg-gray-100 text-gray-600 text-xs px-3 py-1 rounded-full font-medium">
                                  <span className="mr-1">🔄</span>
                                  Non taggé
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {/* Amount and type */}
                          <div className="text-right flex-shrink-0 space-y-2">
                            <div className="text-xl font-bold text-gray-900">
                              {formatAmount(tx.amount)}
                            </div>
                            <div className={`inline-flex items-center text-xs px-3 py-1.5 rounded-full font-semibold ${
                              tx.expense_type === 'FIXED' ? 'bg-gradient-to-r from-blue-100 to-blue-200 text-blue-800' :
                              tx.expense_type === 'VARIABLE' ? 'bg-gradient-to-r from-orange-100 to-orange-200 text-orange-800' :
                              'bg-gradient-to-r from-green-100 to-green-200 text-green-800'
                            }`}>
                              <span className="mr-1">
                                {tx.expense_type === 'FIXED' ? '🔒' :
                                 tx.expense_type === 'VARIABLE' ? '📊' :
                                 '🎯'}
                              </span>
                              {tx.expense_type === 'FIXED' ? 'Fixe' :
                               tx.expense_type === 'VARIABLE' ? 'Variable' :
                               'Provision'}
                            </div>
                          </div>
                        </div>
                        
                        {/* Hover effect overlay */}
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none rounded-xl"></div>
                      </div>
                    );
                  })
              )}
            </div>
          </div>

          {/* Modern Action Buttons */}
          <div className="flex flex-col sm:flex-row justify-between items-center pt-8 border-t-2 border-gradient-to-r from-gray-200 via-gray-100 to-gray-200 space-y-4 sm:space-y-0">
            <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
              {/* Hierarchical Navigation Button */}
              {onOpenHierarchicalNavigation && (
                <button
                  onClick={() => {
                    onClose();
                    onOpenHierarchicalNavigation(
                      `Navigation Hiérarchique - ${title}`,
                      categoryName,
                      {
                        expense_type: category.toUpperCase(),
                        ...(tagFilter && { tag: tagFilter })
                      }
                    );
                  }}
                  className="group inline-flex items-center px-5 py-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl hover:from-purple-600 hover:to-purple-700 transition-all duration-300 text-sm font-semibold shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <span className="mr-2 text-lg group-hover:scale-110 transition-transform duration-300">🗂️</span>
                  Navigation Hiérarchique
                </button>
              )}
              <button
                onClick={() => {
                  onClose();
                  router.push(`/transactions?month=${month}&expense_type=${category.toUpperCase()}`);
                }}
                className="group inline-flex items-center px-5 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-300 text-sm font-semibold shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span className="mr-2 text-lg group-hover:scale-110 transition-transform duration-300">🔍</span>
                Voir toutes les {category === 'variable' ? 'variables' : category === 'fixed' ? 'fixes' : 'provisions'}
              </button>
              {tagFilter && (
                <button
                  onClick={() => {
                    onClose();
                    router.push(`/transactions?month=${month}&tag=${encodeURIComponent(tagFilter)}`);
                  }}
                  className="group inline-flex items-center px-5 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl hover:from-green-600 hover:to-green-700 transition-all duration-300 text-sm font-semibold shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <span className="mr-2 text-lg group-hover:scale-110 transition-transform duration-300">🏷️</span>
                  <span className="truncate max-w-[200px]">
                    {tagFilter.includes(',') ? 
                      `Tags: ${tagFilter.split(',').map(t => t.trim()).join(', ')}` : 
                      `Tag: ${tagFilter}`
                    }
                  </span>
                </button>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-8 py-3 bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 rounded-xl hover:from-gray-200 hover:to-gray-300 transition-all duration-300 font-semibold shadow-md hover:shadow-lg transform hover:scale-105"
            >
              Fermer
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}