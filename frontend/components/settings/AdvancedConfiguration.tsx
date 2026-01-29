'use client';

import { ExpenseClassificationSettings } from './ExpenseClassificationSettings';
import { TagsImportExport } from './TagsImportExport';
import { AdministrationPanel } from './AdministrationPanel';
import { Card, Button } from '../ui';

export function AdvancedConfiguration() {
  return (
    <div className="space-y-6 xs:space-y-8">
      {/* Intelligence Artificielle */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>🤖</span>
              <span className="truncate">Intelligence Artificielle</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Configuration de la classification automatique des transactions par IA
            </p>
          </div>
          <ExpenseClassificationSettings />
        </div>
      </Card>

      {/* Import/Export */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>📦</span>
              <span className="truncate">Import/Export de Configuration</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Sauvegardez et restaurez vos configurations de tags et paramètres
            </p>
          </div>
          <TagsImportExport />
        </div>
      </Card>

      {/* Outils de Diagnostic */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>🔧</span>
              <span className="truncate">Outils de Diagnostic</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Outils avancés de débogage et maintenance du système
            </p>
          </div>
          <AdministrationPanel />
        </div>
      </Card>
    </div>
  );
}