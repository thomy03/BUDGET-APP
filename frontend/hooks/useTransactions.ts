'use client';

import { useState, useCallback, useMemo } from 'react';
import { api, Tx } from '../lib/api';

interface UseTransactionsReturn {
  rows: Tx[];
  loading: boolean;
  error: string;
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
}

export function useTransactions(): UseTransactionsReturn {
  const [rows, setRows] = useState<Tx[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      const response = await api.get<Tx[]>('/transactions', { params: { month } });
      console.log('✅ Refresh successful - loaded', response.data.length, 'transactions');
      setRows(response.data);
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
      
      const response = await api.patch(`/transactions/${id}/tags`, { tags: tagsCSV });
      
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

  return {
    rows,
    loading,
    error,
    calculations,
    refresh,
    toggle,
    saveTags
  };
}
