'use client';

import { FixedLine } from '../../lib/api';
import { Card, Button } from '../ui';
import { useFixedExpenseCalculations } from '../../hooks/useFixedExpenseCalculations';

interface ExpenseCardProps {
  expense: FixedLine;
  config?: any;
  isLoading: boolean;
  onEdit: (expense: FixedLine) => void;
  onToggleStatus: (expense: FixedLine) => void;
  onDelete: (expense: FixedLine) => void;
}

export function ExpenseCard({ 
  expense, 
  config, 
  isLoading, 
  onEdit, 
  onToggleStatus, 
  onDelete 
}: ExpenseCardProps) {
  const {
    calculateMonthlyAmount,
    calculateMemberSplit,
    formatAmount,
    getFrequencyLabel,
    getSplitModeLabel,
    getCategoryIcon
  } = useFixedExpenseCalculations(config);

  const monthlyAmount = calculateMonthlyAmount(expense);
  const memberSplit = calculateMemberSplit(expense, monthlyAmount);

  return (
    <Card
      className="expense-card p-4 border-l-4 expense-appear"
      style={{ borderLeftColor: expense.color }}
      role="article"
      aria-labelledby={`expense-${expense.id}-name`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-2xl" role="img" aria-label="icon">
            {getCategoryIcon(expense.category || 'autres')}
          </span>
          <div>
            <h4 
              id={`expense-${expense.id}-name`}
              className="font-semibold text-gray-900"
            >
              {expense.label}
            </h4>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => onEdit(expense)}
            disabled={isLoading}
            className="icon-hover text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded transition-all"
            aria-label={`Modifier la dépense ${expense.label}`}
          >
            ✏️
          </Button>
          <Button
            onClick={() => onToggleStatus(expense)}
            disabled={isLoading}
            className={`icon-hover text-xs px-2 py-1 rounded transition-all ${
              expense.active
                ? 'bg-orange-100 hover:bg-orange-200 text-orange-700'
                : 'bg-green-100 hover:bg-green-200 text-green-700'
            }`}
            aria-label={`${expense.active ? 'Désactiver' : 'Activer'} la dépense ${expense.label}`}
          >
            {isLoading ? '...' : expense.active ? '⏸️' : '▶️'}
          </Button>
          <Button
            onClick={() => onDelete(expense)}
            disabled={isLoading}
            className="icon-hover text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded transition-all"
            aria-label={`Supprimer la dépense ${expense.label}`}
          >
            🗑️
          </Button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-600">Fréquence</p>
          <p className="font-medium">
            {getFrequencyLabel(expense.freq)} - {formatAmount(expense.amount)}
          </p>
        </div>
        <div>
          <p className="text-gray-600">Répartition</p>
          <p className="font-medium">{getSplitModeLabel(expense.split_mode)}</p>
        </div>
      </div>

      <div className="mt-4 bg-gray-50 rounded-lg p-3">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Montant mensuel</span>
          <span className="text-lg font-bold text-red-600">
            -{formatAmount(monthlyAmount)}
          </span>
        </div>
        
        {config && (
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
            <div className="flex justify-between">
              <span>{config.member1 || 'Membre 1'}:</span>
              <span className="font-medium text-red-600">-{formatAmount(memberSplit.member1)}</span>
            </div>
            <div className="flex justify-between">
              <span>{config.member2 || 'Membre 2'}:</span>
              <span className="font-medium text-red-600">-{formatAmount(memberSplit.member2)}</span>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
