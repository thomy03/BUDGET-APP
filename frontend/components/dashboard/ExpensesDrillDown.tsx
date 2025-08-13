'use client';

import React, { useState, useEffect } from 'react';
import { Card, LoadingSpinner } from '../ui';
import { FadeIn, SlideIn } from '../ui/AnimatedComponents';
import { api } from '../../lib/api';

// Icônes SVG simplifiées
const ChevronRightIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const ArrowLeftIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

interface ExpensesDrillDownProps {
  month: string;
  type: 'variable' | 'fixed';
  onClose: () => void;
}

interface TagSummary {
  tag: string;
  count: number;
  total: number;
  percentage: number;
  ai_classified: number;
  manual_classified: number;
}

interface Transaction {
  id: number;
  amount: number;
  description: string;
  date: string;
  tags: string[];
  ai_classified: boolean;
}

export const ExpensesDrillDown: React.FC<ExpensesDrillDownProps> = ({
  month,
  type,
  onClose
}) => {
  const [currentLevel, setCurrentLevel] = useState<'overview' | 'transactions'>('overview');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [tagsSummary, setTagsSummary] = useState<TagSummary[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Chargement du résumé des tags
  useEffect(() => {
    loadTagsSummary();
  }, [month, type]);

  const loadTagsSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Appel simplifié directement aux transactions avec filtres
      const params = new URLSearchParams({
        month: month,
        is_expense: 'true' // Uniquement les dépenses (montants négatifs)
      });
      
      // Ajouter le filtre expense_type seulement s'il est supporté par l'API
      // Sinon on filtre côté frontend
      // params.append('expense_type', type.toUpperCase());
      
      const response = await api.get(`/transactions?${params.toString()}`);
      const transactions = response.data || [];
      
      // Regrouper les transactions par tag
      const tagGroups: Record<string, { transactions: any[], total: number, count: number }> = {};
      
      transactions.forEach((tx: any) => {
        // Filtrer uniquement les transactions non exclues ET qui sont des dépenses (montants négatifs)
        if (tx.exclude || tx.amount >= 0) return;
        
        // Vérifier que le type de dépense correspond au filtre demandé
        const txExpenseType = tx.expense_type ? tx.expense_type.toLowerCase() : null;
        const requestedType = type.toLowerCase();
        
        // Filtrer selon le type de dépense si disponible
        if (txExpenseType && txExpenseType !== requestedType) {
          return;
        }
        
        const tags = tx.tags && tx.tags.length > 0 ? tx.tags : ['Non classé'];
        
        tags.forEach((tag: string) => {
          if (!tagGroups[tag]) {
            tagGroups[tag] = { transactions: [], total: 0, count: 0 };
          }
          tagGroups[tag].transactions.push(tx);
          tagGroups[tag].total += Math.abs(tx.amount || 0); // Math.abs car amount est négatif pour les dépenses
          tagGroups[tag].count += 1;
        });
      });
      
      // Calculer le total global pour les pourcentages
      const totalAmount = Object.values(tagGroups).reduce((sum, group) => sum + group.total, 0);
      
      // Créer les résumés par tag
      const tagSummaries: TagSummary[] = Object.entries(tagGroups).map(([tag, group]) => ({
        tag: tag,
        count: group.count,
        total: group.total,
        percentage: totalAmount > 0 ? (group.total / totalAmount) * 100 : 0,
        ai_classified: 1, // Simplifié pour l'instant
        manual_classified: 0
      }));
      
      // Debug temporaire
      console.log(`[${type}] Total des dépenses calculé:`, totalAmount);
      console.log(`[${type}] Nombre de tags trouvés:`, tagSummaries.length);
      console.log(`[${type}] Détail par tag:`, tagSummaries.map(t => ({ tag: t.tag, total: t.total, count: t.count })));
      
      // Trier par montant décroissant
      tagSummaries.sort((a, b) => b.total - a.total);
      setTagsSummary(tagSummaries);
      
    } catch (err: any) {
      console.error('Erreur chargement tags:', err);
      setError('Impossible de charger les données');
    } finally {
      setLoading(false);
    }
  };

  const loadTransactionsByTag = async (tag: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Paramètres avec filtres complets
      const params = new URLSearchParams({
        month: month,
        is_expense: 'true' // Uniquement les dépenses (montants négatifs)
      });
      
      if (tag !== 'Non classé') {
        params.append('tag', tag);
      }
      
      const response = await api.get(`/transactions?${params.toString()}`);
      const allTransactions = response.data || [];
      
      // Filtrer les transactions pour ce tag spécifique
      const filteredTransactions = allTransactions.filter((tx: any) => {
        // Exclure les transactions marquées comme exclues OU qui ne sont pas des dépenses
        if (tx.exclude || tx.amount >= 0) return false;
        
        // Vérifier que le type de dépense correspond au filtre demandé
        const txExpenseType = tx.expense_type ? tx.expense_type.toLowerCase() : null;
        const requestedType = type.toLowerCase();
        
        // Filtrer selon le type de dépense si disponible
        if (txExpenseType && txExpenseType !== requestedType) {
          return false;
        }
        
        if (tag === 'Non classé') {
          return !tx.tags || tx.tags.length === 0;
        } else {
          return tx.tags && tx.tags.includes(tag);
        }
      });
      
      setTransactions(filteredTransactions);
      setSelectedTag(tag);
      setCurrentLevel('transactions');
    } catch (err: any) {
      console.error('Erreur chargement transactions:', err);
      setError('Impossible de charger les transactions');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getTitle = () => {
    if (currentLevel === 'transactions') {
      return `${selectedTag} - Transactions`;
    }
    return type === 'variable' ? 'Dépenses Variables' : 'Dépenses Fixes';
  };

  const renderBreadcrumb = () => (
    <div className="flex items-center space-x-2 text-sm text-gray-600 mb-4">
      <button onClick={onClose} className="hover:text-gray-800">
        Dépenses
      </button>
      <ChevronRightIcon className="w-4 h-4" />
      <button 
        onClick={() => setCurrentLevel('overview')} 
        className={currentLevel === 'overview' ? 'text-blue-600 font-medium' : 'hover:text-gray-800'}
      >
        {type === 'variable' ? 'Variables' : 'Fixes'}
      </button>
      {selectedTag && (
        <>
          <ChevronRightIcon className="w-4 h-4" />
          <span className="text-blue-600 font-medium">{selectedTag}</span>
        </>
      )}
    </div>
  );

  if (loading) {
    return (
      <Card className="border-2 border-blue-200 bg-blue-50 p-6">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" text="Chargement..." />
        </div>
      </Card>
    );
  }

  return (
    <Card className="border-2 border-blue-200 bg-blue-50">
      <div className="p-6">
        {/* Header avec navigation */}
        <div className="flex items-center justify-between mb-6">
          <div>
            {renderBreadcrumb()}
            <h3 className="text-xl font-medium text-blue-900">{getTitle()}</h3>
          </div>
          <button
            onClick={() => {
              if (currentLevel === 'transactions') {
                setCurrentLevel('overview');
                setSelectedTag(null);
              } else {
                onClose();
              }
            }}
            className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 text-sm"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            <span>Retour</span>
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Contenu selon le niveau */}
        {currentLevel === 'overview' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <p className="text-blue-700">
                Répartition par catégories - Cliquez pour voir le détail
              </p>
              <div className="text-sm text-blue-600 bg-blue-100 px-3 py-1 rounded-lg">
                Total: {formatCurrency(tagsSummary.reduce((sum, tag) => sum + tag.total, 0))}
              </div>
            </div>
            
            {tagsSummary.map((tagInfo, index) => (
              <SlideIn key={tagInfo.tag} delay={index * 50} direction="up">
                <div 
                  className="bg-white rounded-lg p-4 border border-blue-200 cursor-pointer hover:border-blue-300 hover:shadow-sm transition-all"
                  onClick={() => loadTransactionsByTag(tagInfo.tag)}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-900">{tagInfo.tag}</span>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          {tagInfo.ai_classified > 0 ? 'IA' : 'Manuel'}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600 mt-1">
                        {tagInfo.count} transaction{tagInfo.count > 1 ? 's' : ''} • {tagInfo.percentage.toFixed(1)}%
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <span className="text-lg font-medium text-blue-700">
                        {formatCurrency(tagInfo.total)}
                      </span>
                      <ChevronRightIcon className="w-5 h-5 text-blue-400" />
                    </div>
                  </div>
                </div>
              </SlideIn>
            ))}
          </div>
        )}

        {currentLevel === 'transactions' && (
          <div className="space-y-4">
            <p className="text-blue-700 mb-4">
              {transactions.length} transaction{transactions.length > 1 ? 's' : ''} pour "{selectedTag}"
            </p>
            
            {transactions.map((transaction, index) => (
              <SlideIn key={transaction.id} delay={index * 30} direction="up">
                <div className="bg-white rounded-lg p-4 border border-blue-200">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 mb-1">
                        {transaction.description || transaction.label || 'Description non disponible'}
                      </div>
                      <div className="text-sm text-gray-600">
                        {transaction.date_op ? new Date(transaction.date_op).toLocaleDateString('fr-FR') : 
                         transaction.date ? new Date(transaction.date).toLocaleDateString('fr-FR') : 
                         'Date non disponible'}
                        {transaction.ai_classified && (
                          <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                            Classé par IA
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-lg font-medium text-red-600">
                      {formatCurrency(Math.abs(transaction.amount))}
                    </div>
                  </div>
                </div>
              </SlideIn>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};

export default ExpensesDrillDown;