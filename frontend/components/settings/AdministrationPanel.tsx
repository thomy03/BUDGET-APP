'use client';

import APIDebugPanel from '../APIDebugPanel';
import { Card, Alert } from '../ui';

export function AdministrationPanel() {
  return (
    <div className="space-y-6">
      {/* Avertissement */}
      <Alert variant="warning" className="mb-4">
        <div className="flex items-start">
          <span className="mr-2">⚠️</span>
          <div>
            <strong>Zone Technique</strong>
            <p className="text-sm mt-1">
              Ces outils sont destinés au débogage et à la maintenance. 
              Utilisez-les uniquement si vous rencontrez des problèmes techniques.
            </p>
          </div>
        </div>
      </Alert>

      {/* Panel de Debug */}
      <Card className="p-6 bg-gray-50">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <span className="mr-2">🔧</span>
              Outils de Débogage API
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Diagnostics, logs et informations techniques pour résoudre les problèmes
            </p>
          </div>
          <APIDebugPanel />
        </div>
      </Card>
    </div>
  );
}