'use client';

import { FixedLine } from '../../lib/api';
import { Card, Button } from '../ui';
import { useFixedExpenseCalculations } from '../../hooks/useFixedExpenseCalculations';

interface InactiveExpenseCardProps {
  expense: FixedLine;
  isLoading: boolean;
  onToggleStatus: (expense: FixedLine) => void;
  onDelete: (expense: FixedLine) => void;
}

export function InactiveExpenseCard({ 
  expense, 
  isLoading, 
  onToggleStatus, 
  onDelete 
}: InactiveExpenseCardProps) {
  const { getCategoryIcon } = useFixedExpenseCalculations();
  
  return (
    <Card className="p-4 opacity-60 hover:opacity-80 transition-opacity">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-2xl grayscale" role="img" aria-label="icon">
            {expense.icon || getCategoryIcon(expense.category)}
          </span>
          <div>
            <h4 className="font-semibold text-gray-700">{expense.name}</h4>
            <p className="text-sm text-gray-500">Inactive</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={() => onToggleStatus(expense)}
            disabled={isLoading}
            className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-2 py-1 rounded"
          >
            ▶️ Activer
          </Button>
          <Button
            onClick={() => onDelete(expense)}
            disabled={isLoading}
            className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded"
          >
            🗑️
          </Button>
        </div>
      </div>
    </Card>
  );
}
