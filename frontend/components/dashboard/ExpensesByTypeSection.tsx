'use client';

import { useState } from 'react';
import { Tx, expenseClassificationApi } from '../../lib/api';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { ExpenseTypeModal } from '../transactions/ExpenseTypeModal';
import { Card } from '../ui';

interface ExpensesByTypeSectionProps {
  transactions: Tx[];
  month: string;
  onTransactionUpdate?: (transactionId: number, updates: Partial<Tx>) => void;
}

interface ExpenseItem {
  id: number;
  label: string;
  amount: number;
  date: string;
  category: string;
  expenseType: 'fixed' | 'variable';
  autoDetected?: boolean;
  confidenceScore?: number;
}

export function ExpensesByTypeSection({ 
  transactions, 
  month, 
  onTransactionUpdate 
}: ExpensesByTypeSectionProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Tx | null>(null);
  const [animatingTransactionId, setAnimatingTransactionId] = useState<number | null>(null);

  // Filtrer et transformer les transactions en dépenses
  const expenses = transactions
    .filter(tx => tx.amount < 0 && !tx.exclude)
    .map(tx => ({
      id: tx.id,
      label: tx.label,
      amount: Math.abs(tx.amount),
      date: tx.date_op,
      category: tx.category,
      expenseType: tx.expense_type || 'variable',
      autoDetected: tx.expense_type_auto_detected,
      confidenceScore: tx.expense_type_confidence,
      originalTransaction: tx
    }));

  // Séparer les dépenses par type
  const fixedExpenses = expenses.filter(exp => exp.expenseType === 'fixed');
  const variableExpenses = expenses.filter(exp => exp.expenseType === 'variable');

  // Calculer les totaux
  const fixedTotal = fixedExpenses.reduce((sum, exp) => sum + exp.amount, 0);
  const variableTotal = variableExpenses.reduce((sum, exp) => sum + exp.amount, 0);

  const handleExpenseTypeToggle = async (expense: ExpenseItem, newType: 'fixed' | 'variable') => {
    if (!expense.originalTransaction) return;

    setAnimatingTransactionId(expense.id);
    
    try {
      const updatedTransaction = await expenseClassificationApi.updateTransactionType(
        expense.id, 
        newType, 
        true
      );
      
      // Animation delay avant mise à jour
      setTimeout(() => {
        onTransactionUpdate?.(expense.id, {
          expense_type: newType,
          expense_type_manual_override: true,
          expense_type_auto_detected: false
        });
        setAnimatingTransactionId(null);
      }, 300);
      
    } catch (error) {
      console.error('Failed to update expense type:', error);
      setAnimatingTransactionId(null);
    }
  };

  const handleBadgeClick = (expense: ExpenseItem) => {
    if (expense.autoDetected && expense.originalTransaction) {
      setSelectedTransaction(expense.originalTransaction);
      setIsModalOpen(true);
    }
  };

  const handleModalConfirm = (selectedType: 'fixed' | 'variable') => {
    if (selectedTransaction) {
      const expense = expenses.find(exp => exp.id === selectedTransaction.id);
      if (expense) {
        handleExpenseTypeToggle(expense, selectedType);
      }
    }
  };

  const ExpenseList = ({ 
    items, 
    type, 
    icon, 
    colorClasses 
  }: { 
    items: ExpenseItem[], 
    type: 'fixed' | 'variable', 
    icon: string, 
    colorClasses: string 
  }) => (
    <div className="space-y-2">
      {items.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">{icon}</div>
          <p className="text-sm">Aucune dépense {type === 'fixed' ? 'fixe' : 'variable'}</p>
        </div>
      ) : (
        items.map((expense) => (
          <div
            key={expense.id}
            className={`
              p-3 border rounded-lg bg-white hover:shadow-md transition-all duration-200
              ${animatingTransactionId === expense.id ? 'transform scale-105 shadow-lg' : ''}
              ${colorClasses}
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-gray-900 truncate">
                    {expense.label}
                  </span>
                  <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">
                    {expense.category}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{expense.date}</span>
                  <span>•</span>
                  <span className="font-mono font-medium">
                    {expense.amount.toFixed(2)} €
                  </span>
                </div>
              </div>
              
              <div className="flex items-center gap-2 ml-4">
                {expense.autoDetected ? (
                  <ExpenseTypeBadge
                    type={expense.expenseType}
                    size="sm"
                    interactive={true}
                    onClick={() => handleBadgeClick(expense)}
                    confidenceScore={expense.confidenceScore}
                    autoDetected={true}
                  />
                ) : (
                  <button
                    onClick={() => handleExpenseTypeToggle(
                      expense, 
                      expense.expenseType === 'fixed' ? 'variable' : 'fixed'
                    )}
                    disabled={animatingTransactionId === expense.id}
                    className="p-1 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    title="Changer le type de dépense"
                  >
                    {expense.expenseType === 'fixed' ? '📌→📊' : '📊→📌'}
                  </button>
                )}
                
                {animatingTransactionId === expense.id && (
                  <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );

  return (
    <>
      <div className="grid md:grid-cols-2 gap-6">
        {/* Section Dépenses Fixes */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">📌</span>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Dépenses Fixes</h3>
                <p className="text-sm text-gray-600">
                  Montants réguliers et prévisibles
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-orange-600">
                {fixedTotal.toFixed(0)} €
              </div>
              <div className="text-sm text-gray-500">
                {fixedExpenses.length} dépense{fixedExpenses.length > 1 ? 's' : ''}
              </div>
            </div>
          </div>
          
          <ExpenseList
            items={fixedExpenses}
            type="fixed"
            icon="📌"
            colorClasses="border-orange-200 hover:border-orange-300"
          />
        </Card>

        {/* Section Dépenses Variables */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Dépenses Variables</h3>
                <p className="text-sm text-gray-600">
                  Montants qui varient selon les besoins
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">
                {variableTotal.toFixed(0)} €
              </div>
              <div className="text-sm text-gray-500">
                {variableExpenses.length} dépense{variableExpenses.length > 1 ? 's' : ''}
              </div>
            </div>
          </div>
          
          <ExpenseList
            items={variableExpenses}
            type="variable"
            icon="📊"
            colorClasses="border-blue-200 hover:border-blue-300"
          />
        </Card>
      </div>

      {/* Résumé global */}
      <Card padding="md" className="mt-4">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <span>📌</span>
              <span className="text-orange-600 font-medium">
                Fixes: {fixedTotal.toFixed(2)} €
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span>📊</span>
              <span className="text-blue-600 font-medium">
                Variables: {variableTotal.toFixed(2)} €
              </span>
            </div>
          </div>
          <div className="text-gray-700 font-semibold">
            Total: {(fixedTotal + variableTotal).toFixed(2)} €
          </div>
        </div>
        
        {/* Barre de progression visuelle */}
        <div className="mt-3 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className="flex h-full">
            <div 
              className="bg-orange-500 transition-all duration-500"
              style={{ 
                width: `${fixedTotal / (fixedTotal + variableTotal) * 100}%` 
              }}
            />
            <div 
              className="bg-blue-500 transition-all duration-500"
              style={{ 
                width: `${variableTotal / (fixedTotal + variableTotal) * 100}%` 
              }}
            />
          </div>
        </div>
      </Card>

      {/* Modal pour les détails de classification IA */}
      {isModalOpen && selectedTransaction && (
        <ExpenseTypeModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedTransaction(null);
          }}
          onConfirm={handleModalConfirm}
          transactionLabel={selectedTransaction.label}
          suggestedType={selectedTransaction.expense_type || 'variable'}
          confidence={selectedTransaction.expense_type_confidence || 0.5}
        />
      )}
    </>
  );
}

export default ExpensesByTypeSection;