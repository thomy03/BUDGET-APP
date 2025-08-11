'use client';

import { Card, Button } from '../ui';

interface ExpensesEmptyStateProps {
  onAddExpense: () => void;
}

export function ExpensesEmptyState({ onAddExpense }: ExpensesEmptyStateProps) {
  return (
    <Card className="p-8 text-center">
      <div className="text-6xl mb-4">💳</div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Aucune dépense fixe configurée
      </h3>
      <p className="text-gray-600 mb-4">
        Ajoutez vos dépenses fixes récurrentes pour un suivi automatique de votre budget.
      </p>
      <Button
        onClick={onAddExpense}
        className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg"
      >
        Ajouter ma première dépense
      </Button>
    </Card>
  );
}
