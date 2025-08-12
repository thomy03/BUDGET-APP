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
}

export function TransactionDetailModal({ 
  isOpen, 
  onClose, 
  title, 
  category, 
  categoryName,
  month,
  tagFilter
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
      
      // Ajouter filtre de tag si spécifié
      if (tagFilter) {
        params.tags = tagFilter;
      }
      
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
          {/* En-tête avec résumé amélioré */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="bg-white rounded-lg p-3 shadow-sm">
                <div className="text-xs text-gray-600 uppercase font-medium">Transactions</div>
                <div className="text-2xl font-bold text-gray-900">{transactions.length}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {category === 'provision' ? 'provisions' : category === 'fixed' ? 'charges fixes' : 'variables'}
                </div>
              </div>
              <div className="bg-white rounded-lg p-3 shadow-sm">
                <div className="text-xs text-gray-600 uppercase font-medium">Montant Total</div>
                <div className="text-2xl font-bold text-gray-900">{formatAmount(getTotalAmount())}</div>
                <div className="text-xs text-gray-500 mt-1">somme des montants</div>
              </div>
              <div className="bg-white rounded-lg p-3 shadow-sm">
                <div className="text-xs text-gray-600 uppercase font-medium">Tags Uniques</div>
                <div className="text-2xl font-bold text-gray-900">{Object.keys(subtotals).length}</div>
                <div className="text-xs text-gray-500 mt-1">catégories différentes</div>
              </div>
              <div className="bg-white rounded-lg p-3 shadow-sm">
                <div className="text-xs text-gray-600 uppercase font-medium">Moyenne</div>
                <div className="text-2xl font-bold text-gray-900">
                  {transactions.length > 0 ? formatAmount(getTotalAmount() / transactions.length) : '0.00 €'}
                </div>
                <div className="text-xs text-gray-500 mt-1">par transaction</div>
              </div>
            </div>
          </div>

          {/* Sous-totaux par tag avec design amélioré */}
          {Object.keys(subtotals).length > 1 && (
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <span className="mr-2">🏷️</span>
                Répartition par tag
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(subtotals)
                  .sort(([,a], [,b]) => b - a) // Trier par montant décroissant
                  .map(([tag, amount]) => {
                    const percentage = ((amount / getTotalAmount()) * 100).toFixed(1);
                    const isUntagged = tag === 'Non taggé';
                    return (
                      <div key={tag} className={`rounded-lg p-4 text-center border-2 transition-all duration-200 hover:shadow-md ${
                        isUntagged 
                          ? 'bg-gray-50 border-gray-200 hover:border-gray-300' 
                          : 'bg-blue-50 border-blue-200 hover:border-blue-300'
                      }`}>
                        <div className={`text-sm font-medium mb-1 truncate ${
                          isUntagged ? 'text-gray-700' : 'text-blue-700'
                        }`}>
                          {isUntagged ? '🔄 ' + tag : tag}
                        </div>
                        <div className={`text-lg font-bold ${
                          isUntagged ? 'text-gray-900' : 'text-blue-900'
                        }`}>
                          {formatAmount(amount)}
                        </div>
                        <div className={`text-xs mt-1 ${
                          isUntagged ? 'text-gray-500' : 'text-blue-600'
                        }`}>
                          {percentage}% du total
                        </div>
                        {/* Barre de progression */}
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              isUntagged 
                                ? 'bg-gradient-to-r from-gray-400 to-gray-500' 
                                : 'bg-gradient-to-r from-blue-400 to-blue-600'
                            }`}
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Liste des transactions avec design amélioré */}
          <div>
            <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <span className="mr-2">📊</span>
              Détail des transactions
              <span className="ml-2 text-sm font-normal text-gray-600">({transactions.length} total)</span>
            </h4>
            <div className="max-h-96 overflow-y-auto border-2 border-gray-200 rounded-xl shadow-inner bg-gray-50">
              {transactions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-4">💭</div>
                  <div className="text-lg font-medium">Aucune transaction trouvée</div>
                  <div className="text-sm mt-2">pour cette catégorie et ce mois</div>
                </div>
              ) : (
                <div className="divide-y divide-gray-300">
                  {transactions
                    .sort((a, b) => new Date(b.date_op).getTime() - new Date(a.date_op).getTime()) // Trier par date décroissante
                    .map((tx, index) => {
                      const isRecent = new Date(tx.date_op).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000;
                      return (
                        <div
                          key={tx.id}
                          onClick={() => handleTransactionClick(tx.id)}
                          className={`p-4 cursor-pointer transition-all duration-200 hover:bg-white hover:shadow-md ${
                            index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                          } ${
                            isRecent ? 'border-l-4 border-l-green-400' : ''
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2 mb-1">
                                <div className="text-sm font-medium text-gray-900 truncate flex-1">
                                  {tx.label}
                                </div>
                                {isRecent && (
                                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                                    Récent
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500 mb-2 flex items-center space-x-2">
                                <span>📅 {formatDate(tx.date_op)}</span>
                                <span>•</span>
                                <span>🏷️ {tx.category}</span>
                                {tx.subcategory && (
                                  <>
                                    <span>›</span>
                                    <span>{tx.subcategory}</span>
                                  </>
                                )}
                              </div>
                              {tx.tags && tx.tags.length > 0 ? (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {tx.tags.map((tag, idx) => (
                                    <span
                                      key={idx}
                                      className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <div className="mt-2">
                                  <span className="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">
                                    🔄 Non taggé
                                  </span>
                                </div>
                              )}
                            </div>
                            <div className="text-right ml-4 flex-shrink-0">
                              <div className="text-lg font-bold text-gray-900 mb-1">
                                {formatAmount(tx.amount)}
                              </div>
                              <div className={`text-xs px-2 py-1 rounded-full font-medium ${
                                tx.expense_type === 'FIXED' ? 'bg-blue-100 text-blue-700' :
                                tx.expense_type === 'VARIABLE' ? 'bg-orange-100 text-orange-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {tx.expense_type === 'FIXED' ? '🔒 Fixe' :
                                 tx.expense_type === 'VARIABLE' ? '📊 Variable' :
                                 '🎯 Provision'}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          </div>

          {/* Actions améliorées */}
          <div className="flex flex-col sm:flex-row justify-between items-center pt-6 border-t-2 border-gray-200 space-y-3 sm:space-y-0">
            <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
              <button
                onClick={() => {
                  onClose();
                  router.push(`/transactions?month=${month}&expense_type=${category.toUpperCase()}`);
                }}
                className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors text-sm font-medium"
              >
                <span className="mr-2">🔎</span>
                Voir toutes les transactions {category === 'variable' ? 'variables' : category === 'fixed' ? 'fixes' : 'de provision'}
              </button>
              {tagFilter && (
                <button
                  onClick={() => {
                    onClose();
                    router.push(`/transactions?month=${month}&tags=${tagFilter}`);
                  }}
                  className="inline-flex items-center px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-sm font-medium"
                >
                  <span className="mr-2">🏷️</span>
                  Filtrer par tag: {tagFilter}
                </button>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              Fermer
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}