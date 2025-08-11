'use client';

import { Card, Button } from '../ui';

interface ProvisionsEmptyStateProps {
  onAddProvision: () => void;
}

export function ProvisionsEmptyState({ onAddProvision }: ProvisionsEmptyStateProps) {
  return (
    <Card className="p-8 text-center">
      <div className="text-6xl mb-4">🎯</div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Aucune provision configurée
      </h3>
      <p className="text-gray-600 mb-4">
        Créez votre première provision personnalisée pour commencer à épargner selon vos objectifs.
      </p>
      <Button
        onClick={onAddProvision}
        className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg"
      >
        Créer ma première provision
      </Button>
    </Card>
  );
}
