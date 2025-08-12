'use client';

import { useState } from 'react';
import { FixedLine, FixedLineCreate, ConfigOut } from '../lib/api';
import { Button, Alert, LoadingSpinner } from './ui';
import AddFixedExpenseModal from './AddFixedExpenseModal';
import { useFixedExpenses } from '../hooks/useFixedExpenses';
import { 
  ExpensesSummary, 
  ExpenseCard, 
  InactiveExpenseCard, 
  ExpensesEmptyState 
} from './fixed-expenses';

interface FixedExpensesProps {
  config?: ConfigOut;
  onDataChange?: () => void;
}

export default function FixedExpenses({ config, onDataChange }: FixedExpensesProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingExpense, setEditingExpense] = useState<FixedLine | null>(null);
  
  const {
    expenses,
    loading,
    error,
    actionLoading,
    handleAddExpense: addExpense,
    handleUpdateExpense,
    toggleExpenseStatus,
    deleteExpense
  } = useFixedExpenses(onDataChange);

  const handleAddExpense = async (expenseData: FixedLineCreate) => {
    await addExpense(expenseData);
    setShowAddModal(false);
  };

  const handleUpdateExpense_ = async (expenseData: FixedLineCreate) => {
    if (!editingExpense) return;
    await handleUpdateExpense(expenseData, editingExpense);
    setEditingExpense(null);
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
            💳 Dépenses Fixes Personnalisables
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Gérez vos dépenses récurrentes avec des calculs personnalisés
          </p>
        </div>
        <Button
          onClick={() => setShowAddModal(true)}
          className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          + Ajouter une dépense
        </Button>
      </div>

      {/* Summary */}
      <ExpensesSummary activeExpenses={activeExpenses} config={config} />

      {/* Active Expenses */}
      {activeExpenses.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Dépenses Actives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeExpenses.map(expense => (
              <ExpenseCard
                key={expense.id}
                expense={expense}
                config={config}
                isLoading={actionLoading === expense.id}
                onEdit={setEditingExpense}
                onToggleStatus={toggleExpenseStatus}
                onDelete={deleteExpense}
              />
            ))}
          </div>
        </div>
      )}

      {/* Inactive Expenses */}
      {inactiveExpenses.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-500">Dépenses Inactives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {inactiveExpenses.map(expense => (
              <InactiveExpenseCard
                key={expense.id}
                expense={expense}
                isLoading={actionLoading === expense.id}
                onToggleStatus={toggleExpenseStatus}
                onDelete={deleteExpense}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {expenses.length === 0 && (
        <ExpensesEmptyState onAddExpense={() => setShowAddModal(true)} />
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
          onSave={handleUpdateExpense_}
        />
      )}
    </div>
  );
}
