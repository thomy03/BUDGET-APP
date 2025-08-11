'use client';

import { useState, useEffect } from 'react';
import { api, FixedLine, FixedLineCreate } from '../lib/api';

interface UseFixedExpensesReturn {
  expenses: FixedLine[];
  loading: boolean;
  error: string;
  actionLoading: number | null;
  loadExpenses: () => Promise<void>;
  handleAddExpense: (expenseData: FixedLineCreate) => Promise<void>;
  handleUpdateExpense: (expenseData: FixedLineCreate, editingExpense: FixedLine) => Promise<void>;
  toggleExpenseStatus: (expense: FixedLine) => Promise<void>;
  deleteExpense: (expense: FixedLine) => Promise<void>;
}

export function useFixedExpenses(onDataChange?: () => void): UseFixedExpensesReturn {
  const [expenses, setExpenses] = useState<FixedLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    // Vérifier l'authentification avant de charger
    const token = localStorage.getItem('auth_token');
    if (!token) {
      console.warn('⚠️ Pas de token d\'authentification trouvé');
      setError('Authentification requise - Veuillez vous connecter');
      setLoading(false);
      return;
    }
    
    loadExpenses();
  }, []);

  const loadExpenses = async () => {
    try {
      setLoading(true);
      setError('');
      
      const token = localStorage.getItem('auth_token');
      const tokenType = localStorage.getItem('token_type');
      
      console.log('🔍 Debug loadExpenses:', {
        hasToken: !!token,
        tokenType,
        tokenPrefix: token?.substring(0, 10) + '...',
        url: '/fixed-lines'
      });
      
      const response = await api.get<FixedLine[]>('/fixed-lines');
      console.log('✅ Dépenses fixes chargées:', {
        status: response.status,
        hasData: !!response.data,
        dataType: typeof response.data,
        isArray: Array.isArray(response.data),
        count: Array.isArray(response.data) ? response.data.length : 0,
        data: response.data
      });
      
      const expenses = Array.isArray(response.data) ? response.data : [];
      setExpenses(expenses);
      
      if (!Array.isArray(response.data)) {
        console.warn('⚠️ La réponse n\'est pas un tableau:', response.data);
      }
    } catch (err: any) {
      const errorDetails = {
        status: err.response?.status,
        statusText: err.response?.statusText,
        message: err.message,
        data: err.response?.data,
        url: err.config?.url,
        hasAuth: !!err.config?.headers?.Authorization
      };
      
      console.error('❌ Erreur loadExpenses:', errorDetails);
      
      let errorMessage = 'Erreur lors du chargement des dépenses fixes';
      if (err.response?.status === 401) {
        errorMessage = 'Session expirée - Veuillez vous reconnecter';
      } else if (err.response?.status === 403) {
        errorMessage = 'Accès refusé aux dépenses fixes';
      } else if (err.response?.status === 500) {
        errorMessage = 'Erreur serveur - Réessayez dans quelques instants';
      } else if (err.code === 'ERR_NETWORK') {
        errorMessage = 'Impossible de contacter le serveur';
      } else if (err.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAddExpense = async (expenseData: FixedLineCreate) => {
    try {
      console.log('🔍 Debug création dépense fixe:', {
        data: expenseData,
        url: '/fixed-lines',
        hasToken: !!localStorage.getItem('auth_token')
      });
      
      const response = await api.post<FixedLine>('/fixed-lines', expenseData);
      
      console.log('✅ Dépense fixe créée:', {
        status: response.status,
        data: response.data
      });
      
      setExpenses(prev => [...prev, response.data]);
      onDataChange?.();
    } catch (err: any) {
      console.error('❌ Erreur création dépense fixe:', err);
      
      let errorMessage = 'Erreur lors de la création';
      if (err.response?.status === 401) {
        errorMessage = 'Session expirée - Reconnectez-vous';
      } else if (err.response?.status === 403) {
        errorMessage = 'Accès refusé pour créer une dépense fixe';
      } else if (err.response?.status === 422) {
        errorMessage = 'Données de dépense fixe invalides';
      } else if (err.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      throw new Error(errorMessage);
    }
  };

  const handleUpdateExpense = async (expenseData: FixedLineCreate, editingExpense: FixedLine) => {
    try {
      const response = await api.put<FixedLine>(
        `/fixed-lines/${editingExpense.id}`,
        expenseData
      );
      setExpenses(prev =>
        prev.map(e => (e.id === editingExpense.id ? response.data : e))
      );
      onDataChange?.();
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Erreur lors de la mise à jour');
    }
  };

  const toggleExpenseStatus = async (expense: FixedLine) => {
    try {
      setActionLoading(expense.id);
      const response = await api.patch<FixedLine>(
        `/fixed-lines/${expense.id}`,
        { is_active: !expense.is_active }
      );
      setExpenses(prev =>
        prev.map(e => (e.id === expense.id ? response.data : e))
      );
      onDataChange?.();
    } catch (err: any) {
      setError('Erreur lors de la mise à jour du statut');
    } finally {
      setActionLoading(null);
    }
  };

  const deleteExpense = async (expense: FixedLine) => {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la dépense "${expense.name}" ?`)) {
      return;
    }

    try {
      setActionLoading(expense.id);
      await api.delete(`/fixed-lines/${expense.id}`);
      setExpenses(prev => prev.filter(e => e.id !== expense.id));
      onDataChange?.();
    } catch (err: any) {
      setError('Erreur lors de la suppression');
    } finally {
      setActionLoading(null);
    }
  };

  return {
    expenses,
    loading,
    error,
    actionLoading,
    loadExpenses,
    handleAddExpense,
    handleUpdateExpense,
    toggleExpenseStatus,
    deleteExpense
  };
}
