'use client';

import { ExpenseClassificationSettings } from './ExpenseClassificationSettings';
import { TagsImportExport } from './TagsImportExport';
import { AdministrationPanel } from './AdministrationPanel';
import { Card, Button } from '../ui';

export function AdvancedConfiguration() {
  return (
    <div className="space-y-8">
      {/* Intelligence Artificielle */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">🤖</span>
              Intelligence Artificielle
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Configuration de la classification automatique des transactions par IA
            </p>
          </div>
          <ExpenseClassificationSettings />
        </div>
      </Card>

      {/* Import/Export */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">📦</span>
              Import/Export de Configuration
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Sauvegardez et restaurez vos configurations de tags et paramètres
            </p>
          </div>
          <TagsImportExport />
        </div>
      </Card>

      {/* Outils de Diagnostic */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">🔧</span>
              Outils de Diagnostic
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Outils avancés de débogage et maintenance du système
            </p>
          </div>
          <AdministrationPanel />
        </div>
      </Card>
    </div>
  );
}