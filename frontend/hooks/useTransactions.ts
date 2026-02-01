'use client';

import { useState, useCallback, useMemo } from 'react';
import { api, Tx, PaginatedResponse, transactionsApi } from '../lib/api';

// Pagination metadata type
interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  pages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// Global stats for all transactions in the month (not just current page)
interface GlobalStats {
  totalExpenses: number;
  totalIncome: number;
  netBalance: number;
  totalCount: number;
}

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
  // Global stats for ALL transactions in the month (not just current page)
  globalStats: GlobalStats | null;
  // Pagination
  pagination: PaginationMeta;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  // Actions
  refresh: (isAuthenticated: boolean, month: string | null) => Promise<void>;
  toggle: (id: number, exclude: boolean) => Promise<void>;
  saveTags: (id: number, tagsCSV: string) => Promise<void>;
  bulkUnexcludeAll: () => Promise<void>;
  updateExpenseType: (id: number, expenseType: 'fixed' | 'variable') => Promise<void>;
}

export function useTransactions(): UseTransactionsReturn {
  const [rows, setRows] = useState<Tx[]>([]);
  const [allRows, setAllRows] = useState<Tx[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoClassifying, setAutoClassifying] = useState(false);
  const [autoClassificationResults, setAutoClassificationResults] = useState<{
    totalAnalyzed: number;
    autoApplied: number;
    pendingReview: number;
    processingTimeMs: number;
  } | null>(null);

  // Global stats for all transactions in the month
  const [globalStats, setGlobalStats] = useState<GlobalStats | null>(null);

  // Pagination state
  const [pagination, setPagination] = useState<PaginationMeta>({
    total: 0,
    page: 1,
    limit: 50,
    pages: 0,
    hasNext: false,
    hasPrev: false
  });

  // Current month for pagination changes
  const [currentMonth, setCurrentMonth] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

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

  // Internal refresh function that uses current pagination state
  const loadTransactions = useCallback(async (auth: boolean, month: string, page: number, limit: number) => {
    if (!auth || !month) {
      console.log('🚫 Load skipped - Auth:', auth, 'Month:', month);
      return;
    }

    console.log(`🔄 Loading transactions for ${month} (page ${page}, limit ${limit})`);
    try {
      setLoading(true);
      setError('');

      // Use paginated API
      const response = await transactionsApi.list(month, { page, limit });
      console.log(`✅ Loaded ${response.items.length}/${response.total} transactions (page ${response.page}/${response.pages})`);

      setRows(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        limit: response.limit,
        pages: response.pages,
        hasNext: response.has_next,
        hasPrev: response.has_prev
      });

      return response;
    } catch (err) {
      console.error('❌ Load error:', err);
      setError('Erreur lors du chargement des transactions');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async (authStatus: boolean, month: string | null) => {
    if (!authStatus || !month) {
      console.log('🚫 Refresh skipped - Auth:', authStatus, 'Month:', month);
      return;
    }

    // Store for pagination changes
    setCurrentMonth(month);
    setIsAuthenticated(authStatus);

    console.log('🔄 Starting refresh for month:', month);
    try {
      setLoading(true);
      setError(''); // Clear any previous errors

      // 1. Charger les transactions avec pagination ET les stats globales en parallele
      const [response, allTransactionsRes] = await Promise.all([
        transactionsApi.list(month, { page: pagination.page, limit: pagination.limit }),
        // Charger TOUTES les transactions pour les stats globales (limit=500)
        api.get(`/transactions?month=${month}&limit=500`).catch(() => ({ data: { items: [] } }))
      ]);

      console.log(`✅ Refresh successful - loaded ${response.items.length}/${response.total} transactions`);
      setRows(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        limit: response.limit,
        pages: response.pages,
        hasNext: response.has_next,
        hasPrev: response.has_prev
      });

      // 1b. Calculer les stats globales depuis toutes les transactions
      const allData = allTransactionsRes?.data || {};
      const allTransactions = allData.items || allData || [];
      const includedTx = allTransactions.filter((tx: any) => !tx.exclude);
      const globalExpenses = includedTx
        .filter((tx: any) => tx.amount < 0)
        .reduce((sum: number, tx: any) => sum + Math.abs(tx.amount), 0);
      const globalIncome = includedTx
        .filter((tx: any) => tx.amount > 0)
        .reduce((sum: number, tx: any) => sum + tx.amount, 0);

      setGlobalStats({
        totalExpenses: globalExpenses,
        totalIncome: globalIncome,
        netBalance: globalIncome - globalExpenses,
        totalCount: allTransactions.length
      });

      // Store all transactions for auto-tagging
      setAllRows(allTransactions);

      // 2. Auto-classification automatique en arrière-plan
      if (response.items.length > 0) {
        console.log('🤖 Starting auto-classification for', response.items.length, 'transactions');
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
            const updatedResponse = await transactionsApi.list(month, { page: pagination.page, limit: pagination.limit });
            setRows(updatedResponse.items);
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
  }, [pagination.page, pagination.limit]);

  // Pagination controls
  const setPage = useCallback((newPage: number) => {
    if (newPage < 1 || newPage > pagination.pages) return;
    setPagination(prev => ({ ...prev, page: newPage }));
    if (currentMonth && isAuthenticated) {
      loadTransactions(isAuthenticated, currentMonth, newPage, pagination.limit);
    }
  }, [currentMonth, isAuthenticated, pagination.pages, pagination.limit, loadTransactions]);

  const setLimit = useCallback((newLimit: number) => {
    setPagination(prev => ({ ...prev, limit: newLimit, page: 1 }));
    if (currentMonth && isAuthenticated) {
      loadTransactions(isAuthenticated, currentMonth, 1, newLimit);
    }
  }, [currentMonth, isAuthenticated, loadTransactions]);

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
      const tags = tagsCSV.split(',').map(s => s.trim()).filter(Boolean);

      console.log('🏷️ Saving tags for transaction', id, ':', tags, '(raw:', tagsCSV, ')');

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

  const bulkUnexcludeAll = async () => {
    try {
      // Trouver toutes les transactions exclues
      const excludedTransactions = rows.filter(tx => tx.exclude);
      
      if (excludedTransactions.length === 0) {
        console.log('Aucune transaction exclue à réinclure');
        return;
      }
      
      // Créer les requêtes pour réinclure toutes les transactions exclues
      const updates = excludedTransactions.map(tx => 
        api.patch(`/transactions/${tx.id}`, { exclude: false })
      );
      
      await Promise.all(updates);
      
      // Mettre à jour l'état local
      setRows(prev => prev.map(tx => 
        tx.exclude ? { ...tx, exclude: false } : tx
      ));
      
      console.log(`✅ ${excludedTransactions.length} transactions réincluses`);
    } catch (err: any) {
      console.error('Erreur lors de la réinclusion en masse:', err);
      setError('Erreur lors de la réinclusion en masse des transactions');
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
    allRows,
    loading,
    error,
    autoClassifying,
    autoClassificationResults,
    calculations,
    // Global stats for ALL transactions in the month
    globalStats,
    // Pagination
    pagination,
    setPage,
    setLimit,
    // Actions
    refresh,
    toggle,
    saveTags,
    bulkUnexcludeAll,
    updateExpenseType
  };
}
