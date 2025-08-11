'use client';

import { useState, useEffect } from 'react';
import { api, FixedLine, ConfigOut } from '../lib/api';
import { Card, Button, Alert, LoadingSpinner } from './ui';
import AddFixedExpenseModal from './AddFixedExpenseModal';

interface FixedExpensesProps {
  config?: ConfigOut;
  onDataChange?: () => void;
}

export default function FixedExpenses({ config, onDataChange }: FixedExpensesProps) {
  const [expenses, setExpenses] = useState<FixedLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingExpense, setEditingExpense] = useState<FixedLine | null>(null);
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
      
      // Debug: vérifier l'authentification
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
      
      // Vérification robuste de la réponse
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
      
      // Message d'erreur plus descriptif
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

  const handleAddExpense = async (expenseData: Omit<FixedLine, 'id'>) => {
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
      setShowAddModal(false);
      onDataChange?.();
    } catch (err: any) {
      const errorDetails = {
        status: err.response?.status,
        statusText: err.response?.statusText,
        message: err.message,
        data: err.response?.data,
        url: err.config?.url,
        hasAuth: !!err.config?.headers?.Authorization
      };
      
      console.error('❌ Erreur création dépense fixe:', errorDetails);
      
      // Message d'erreur plus descriptif
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

  const handleUpdateExpense = async (expenseData: Omit<FixedLine, 'id'>) => {
    if (!editingExpense) return;

    try {
      // Note: Adapter selon l'API backend disponible
      const response = await api.post<FixedLine>('/fixed-lines', { ...expenseData, id: editingExpense.id });
      setExpenses(prev =>
        prev.map(e => (e.id === editingExpense.id ? response.data : e))
      );
      setEditingExpense(null);
      onDataChange?.();
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Erreur lors de la mise à jour');
    }
  };

  const toggleExpenseStatus = async (expense: FixedLine) => {
    try {
      setActionLoading(expense.id);
      // Note: Adapter selon l'API backend disponible
      const response = await api.post<FixedLine>('/fixed-lines', { ...expense, active: !expense.active });
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
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la dépense fixe "${expense.label}" ?`)) {
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

  const calculateMonthlyAmount = (expense: FixedLine): number => {
    switch (expense.freq) {
      case 'mensuelle':
        return expense.amount;
      case 'trimestrielle':
        return expense.amount / 3;
      case 'annuelle':
        return expense.amount / 12;
      default:
        return expense.amount;
    }
  };

  const calculateMemberSplit = (expense: FixedLine, monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (expense.split_mode) {
      case 'clé':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
          return {
            member1: monthlyAmount * r1,
            member2: monthlyAmount * r2,
          };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case 'm1':
        return { member1: monthlyAmount, member2: 0 };
      case 'm2':
        return { member1: 0, member2: monthlyAmount };
      case 'manuel':
        return {
          member1: monthlyAmount * expense.split1,
          member2: monthlyAmount * expense.split2,
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getFrequencyLabel = (freq: string) => {
    switch (freq) {
      case 'mensuelle':
        return 'Mensuelle';
      case 'trimestrielle':
        return 'Trimestrielle';
      case 'annuelle':
        return 'Annuelle';
      default:
        return freq;
    }
  };

  const getSplitModeLabel = (splitMode: string) => {
    switch (splitMode) {
      case 'clé':
        return 'Clé globale';
      case '50/50':
        return '50/50';
      case 'm1':
        return `100% ${config?.member1 || 'Membre 1'}`;
      case 'm2':
        return `100% ${config?.member2 || 'Membre 2'}`;
      case 'manuel':
        return 'Personnalisé';
      default:
        return splitMode;
    }
  };

  const getCategoryIcon = (label: string) => {
    const lower = label.toLowerCase();
    if (lower.includes('crédit') && lower.includes('immobilier')) return '🏠';
    if (lower.includes('crédit') && lower.includes('voiture')) return '🚗';
    if (lower.includes('edf') || lower.includes('électricité')) return '⚡';
    if (lower.includes('eau')) return '💧';
    if (lower.includes('internet') || lower.includes('box')) return '🌐';
    if (lower.includes('mobile') || lower.includes('forfait')) return '📱';
    if (lower.includes('mutuelle') || lower.includes('assurance')) return '🏥';
    if (lower.includes('abonnement')) return '🎬';
    return '💳';
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  const activeExpenses = expenses.filter(e => e.active);
  const inactiveExpenses = expenses.filter(e => !e.active);
  const totalMonthlyAmount = activeExpenses.reduce((sum, expense) => {
    return sum + calculateMonthlyAmount(expense);
  }, 0);

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="error">
          <div className="space-y-2">
            <p className="font-medium">{error}</p>
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer hover:text-gray-800">Détails techniques</summary>
              <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono">
                <p>API Base: {process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:5000"}</p>
                <p>Token présent: {!!localStorage.getItem('auth_token') ? 'Oui' : 'Non'}</p>
                <p>Endpoint: /fixed-lines</p>
              </div>
            </details>
          </div>
        </Alert>
      )}
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            💳 Dépenses Fixes
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Gérez vos dépenses récurrentes (crédits, abonnements, charges fixes)
          </p>
        </div>
        <Button
          onClick={() => setShowAddModal(true)}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          + Ajouter une dépense fixe
        </Button>
      </div>

      {/* Summary */}
      {activeExpenses.length > 0 && (
        <Card className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium text-emerald-700">Dépenses Actives</p>
              <p className="text-2xl font-bold text-emerald-900">{activeExpenses.length}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-emerald-700">Total Mensuel</p>
              <p className="text-2xl font-bold text-emerald-900">
                {formatAmount(totalMonthlyAmount)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-emerald-700">Total Annuel</p>
              <p className="text-2xl font-bold text-emerald-900">
                {formatAmount(totalMonthlyAmount * 12)}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Active Expenses */}
      {activeExpenses.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Dépenses Actives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeExpenses.map(expense => {
              const monthlyAmount = calculateMonthlyAmount(expense);
              const memberSplit = calculateMemberSplit(expense, monthlyAmount);
              const isLoading = actionLoading === expense.id;

              return (
                <Card
                  key={expense.id}
                  className="expense-card p-4 border-l-4 expense-appear border-l-emerald-500"
                  role="article"
                  aria-labelledby={`expense-${expense.id}-name`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl" role="img" aria-label="icon">
                        {getCategoryIcon(expense.label)}
                      </span>
                      <div>
                        <h4 
                          id={`expense-${expense.id}-name`}
                          className="font-semibold text-gray-900"
                        >
                          {expense.label}
                        </h4>
                        <p className="text-sm text-gray-600">
                          {getFrequencyLabel(expense.freq)} • {getSplitModeLabel(expense.split_mode)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        onClick={() => setEditingExpense(expense)}
                        disabled={isLoading}
                        className="icon-hover text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded transition-all"
                        aria-label={`Modifier la dépense fixe ${expense.label}`}
                      >
                        ✏️
                      </Button>
                      <Button
                        onClick={() => toggleExpenseStatus(expense)}
                        disabled={isLoading}
                        className={`icon-hover text-xs px-2 py-1 rounded transition-all ${
                          expense.active
                            ? 'bg-orange-100 hover:bg-orange-200 text-orange-700'
                            : 'bg-green-100 hover:bg-green-200 text-green-700'
                        }`}
                        aria-label={`${expense.active ? 'Désactiver' : 'Activer'} la dépense fixe ${expense.label}`}
                      >
                        {isLoading ? '...' : expense.active ? '⏸️' : '▶️'}
                      </Button>
                      <Button
                        onClick={() => deleteExpense(expense)}
                        disabled={isLoading}
                        className="icon-hover text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded transition-all"
                        aria-label={`Supprimer la dépense fixe ${expense.label}`}
                      >
                        🗑️
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Montant original</p>
                      <p className="font-medium">
                        {formatAmount(expense.amount)} ({getFrequencyLabel(expense.freq)})
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Montant mensuel</p>
                      <p className="font-medium">{formatAmount(monthlyAmount)}</p>
                    </div>
                  </div>

                  <div className="mt-4 bg-gray-50 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Répartition mensuelle</span>
                      <span className="text-lg font-bold text-gray-900">
                        {formatAmount(monthlyAmount)}
                      </span>
                    </div>
                    
                    {config && (
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div className="flex justify-between">
                          <span>{config.member1 || 'Membre 1'}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member1)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>{config.member2 || 'Membre 2'}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member2)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Inactive Expenses */}
      {inactiveExpenses.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-500">Dépenses Inactives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {inactiveExpenses.map(expense => (
              <Card
                key={expense.id}
                className="p-4 opacity-60 hover:opacity-80 transition-opacity"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl grayscale" role="img" aria-label="icon">
                      {getCategoryIcon(expense.label)}
                    </span>
                    <div>
                      <h4 className="font-semibold text-gray-700">{expense.label}</h4>
                      <p className="text-sm text-gray-500">Inactive</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      onClick={() => toggleExpenseStatus(expense)}
                      disabled={actionLoading === expense.id}
                      className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-2 py-1 rounded"
                    >
                      ▶️ Activer
                    </Button>
                    <Button
                      onClick={() => deleteExpense(expense)}
                      disabled={actionLoading === expense.id}
                      className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded"
                    >
                      🗑️
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {expenses.length === 0 && (
        <Card className="p-8 text-center">
          <div className="text-6xl mb-4">💳</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Aucune dépense fixe configurée
          </h3>
          <p className="text-gray-600 mb-4">
            Ajoutez vos dépenses récurrentes comme les crédits, abonnements et charges fixes.
          </p>
          <Button
            onClick={() => setShowAddModal(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg"
          >
            Créer ma première dépense fixe
          </Button>
        </Card>
      )}

      {/* Modals */}
      {showAddModal && (
        <AddFixedExpenseModal
          config={config}
          onClose={() => setShowAddModal(false)}
          onSave={handleAddExpense}
        />
      )}

      {editingExpense && (
        <AddFixedExpenseModal
          config={config}
          expense={editingExpense}
          onClose={() => setEditingExpense(null)}
          onSave={handleUpdateExpense}
        />
      )}
    </div>
  );
}