'use client';

import { useState, useCallback, useMemo } from 'react';
import { api, Tx } from '../lib/api';

interface UseTransactionsReturn {
  rows: Tx[];
  loading: boolean;
  error: string;
  autoClassifying: boolean;
  autoClassificationResults: {
    totalAnalyzed: number;
    autoApplied: number;
    pendingReview: number;
    processingTimeMs: number;
  } | null;
  calculations: {
    totalExpenses: number;
    totalIncome: number;
    netBalance: number;
    totalAmount: number;
    includedCount: number;
    excludedCount: number;
    totalCount: number;
  };
  refresh: (isAuthenticated: boolean, month: string | null) => Promise<void>;
  toggle: (id: number, exclude: boolean) => Promise<void>;
  saveTags: (id: number, tagsCSV: string) => Promise<void>;
  bulkToggleIncome: (exclude: boolean) => Promise<void>;
  updateExpenseType: (id: number, expenseType: 'fixed' | 'variable') => Promise<void>;
}

export function useTransactions(): UseTransactionsReturn {
  const [rows, setRows] = useState<Tx[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoClassifying, setAutoClassifying] = useState(false);
  const [autoClassificationResults, setAutoClassificationResults] = useState<{
    totalAnalyzed: number;
    autoApplied: number;
    pendingReview: number;
    processingTimeMs: number;
  } | null>(null);

  // Calculs des totaux
  const calculations = useMemo(() => {
    const includedTransactions = rows.filter(tx => !tx.exclude);
    const excludedCount = rows.filter(tx => tx.exclude).length;
    
    const totalExpenses = includedTransactions
      .filter(tx => tx.amount < 0)
      .reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
    
    const totalIncome = includedTransactions
      .filter(tx => tx.amount > 0)
      .reduce((sum, tx) => sum + tx.amount, 0);
    
    const netBalance = totalIncome - totalExpenses;
    const totalAmount = includedTransactions.reduce((sum, tx) => sum + tx.amount, 0);
    
    return {
      totalExpenses,
      totalIncome,
      netBalance,
      totalAmount,
      includedCount: includedTransactions.length,
      excludedCount,
      totalCount: rows.length
    };
  }, [rows]);

  const refresh = useCallback(async (isAuthenticated: boolean, month: string | null) => {
    if (!isAuthenticated || !month) {
      console.log('🚫 Refresh skipped - Auth:', isAuthenticated, 'Month:', month);
      return;
    }
    
    console.log('🔄 Starting refresh for month:', month);
    try {
      setLoading(true);
      setError(''); // Clear any previous errors
      
      // 1. Charger les transactions
      const response = await api.get<Tx[]>('/transactions', { params: { month } });
      console.log('✅ Refresh successful - loaded', response.data.length, 'transactions');
      setRows(response.data);
      
      // 2. Auto-classification automatique en arrière-plan
      if (response.data.length > 0) {
        console.log('🤖 Starting auto-classification for', response.data.length, 'transactions');
        setAutoClassifying(true);
        
        try {
          const autoClassifyResponse = await api.post('/expense-classification/transactions/auto-classify-on-load', {
            month: month,
            confidence_threshold: 0.7,
            limit: 200,
            include_classified: false
          });
          
          console.log('🚀 Auto-classification completed:', autoClassifyResponse.data);
          
          // Stocker les résultats de la classification
          setAutoClassificationResults({
            totalAnalyzed: autoClassifyResponse.data.total_analyzed,
            autoApplied: autoClassifyResponse.data.auto_applied,
            pendingReview: autoClassifyResponse.data.pending_review,
            processingTimeMs: autoClassifyResponse.data.processing_time_ms
          });
          
          // 3. Si des classifications ont été appliquées, recharger les transactions
          if (autoClassifyResponse.data.auto_applied > 0) {
            console.log(`✨ ${autoClassifyResponse.data.auto_applied} classifications applied - reloading transactions`);
            const updatedResponse = await api.get<Tx[]>('/transactions', { params: { month } });
            setRows(updatedResponse.data);
          }
          
        } catch (classificationErr) {
          console.warn('⚠️ Auto-classification failed (non-critical):', classificationErr);
          // La classification échoue de manière non critique - les transactions sont quand même chargées
        } finally {
          setAutoClassifying(false);
        }
      }
      
    } catch (err) {
      console.error('❌ Refresh error:', err);
      setError('Erreur lors du chargement des transactions');
    } finally {
      setLoading(false);
    }
  }, []);

  const toggle = async (id: number, exclude: boolean) => {
    try {
      const response = await api.patch(`/transactions/${id}`, { exclude });
      setRows(prev => prev.map(x => x.id === id ? response.data : x));
    } catch (err: any) {
      console.error('Erreur toggle:', err);
      
      let errorMessage = 'Erreur lors de la modification';
      
      if (err?.response?.status === 404) {
        errorMessage = `Transaction #${id} introuvable. Veuillez rafraîchir la page.`;
      } else if (err?.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      setError(errorMessage);
    }
  };

  const saveTags = async (id: number, tagsCSV: string) => {
    try {
      const transaction = rows.find(row => row.id === id);
      if (!transaction) {
        setError(`Transaction #${id} introuvable dans la liste actuelle. Veuillez rafraîchir la page.`);
        return;
      }

      const tags = tagsCSV.split(',').map(s => s.trim()).filter(Boolean);
      
      console.log('🏷️ Saving tags for transaction', id, ':', tags);
      
      const response = await api.put(`/transactions/${id}/tag`, { tags: tagsCSV });
      
      console.log('✅ Tags saved successfully:', response.data);
      
      setRows(prev => prev.map(x => x.id === id ? response.data : x));
    } catch (err: any) {
      console.error('Erreur saveTags:', err);
      
      let errorMessage = 'Erreur lors de la sauvegarde des tags';
      
      if (err?.response?.status === 404) {
        errorMessage = `Transaction #${id} introuvable. Veuillez rafraîchir la page.`;
      } else if (err?.response?.status === 400) {
        errorMessage = 'Format de tags invalide';
      } else if (err?.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      setError(errorMessage);
      
      // Revert the UI change if any
      setTimeout(() => setError(''), 5000);
    }
  };

  const bulkToggleIncome = async (exclude: boolean) => {
    try {
      const incomeTransactions = rows.filter(tx => tx.amount >= 0);
      const updates = incomeTransactions.map(tx => 
        api.patch(`/transactions/${tx.id}`, { exclude })
      );
      
      await Promise.all(updates);
      
      // Update local state
      setRows(prev => prev.map(tx => 
        tx.amount >= 0 ? { ...tx, exclude } : tx
      ));
    } catch (err: any) {
      console.error('Error bulk toggling income:', err);
      setError('Erreur lors de la modification en masse des revenus');
    }
  };

  const updateExpenseType = async (id: number, expenseType: 'fixed' | 'variable') => {
    try {
      const response = await api.patch(`/transactions/${id}/expense-type`, {
        expense_type: expenseType.toUpperCase()
      });
      
      setRows(prev => prev.map(x => x.id === id ? response.data : x));
    } catch (err: any) {
      console.error('Error updating expense type:', err);
      setError('Erreur lors de la mise à jour du type de dépense');
    }
  };

  return {
    rows,
    loading,
    error,
    autoClassifying,
    autoClassificationResults,
    calculations,
    refresh,
    toggle,
    saveTags,
    bulkToggleIncome,
    updateExpenseType
  };
}
