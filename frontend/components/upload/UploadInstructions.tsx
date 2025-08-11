'use client';

import React from 'react';
import { Card } from '../ui';

const UploadInstructions = React.memo(() => {
  return (
    <Card padding="lg">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Informations importantes</h3>
        <div className="space-y-4">
          <div className="space-y-3 text-sm text-zinc-600">
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Les doublons sont automatiquement détectés et ignorés</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Vous serez redirigé automatiquement vers le mois le plus pertinent</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Les nouvelles transactions seront mises en évidence</span>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <h4 className="text-sm font-semibold text-blue-800 mb-2">📋 Format de fichier requis</h4>
            <div className="space-y-2 text-xs text-blue-700">
              <div><strong>Colonnes requises :</strong> Date, Description, Montant, Compte</div>
              <div><strong>Formats de date :</strong> DD/MM/YYYY (ex: 15/03/2024) ou YYYY-MM-DD (ex: 2024-03-15)</div>
              <div><strong>Séparateur décimal :</strong> Virgule (,) ou point (.)</div>
              <div><strong>Types acceptés :</strong> CSV, XLSX, XLS (max 10MB)</div>
            </div>
          </div>

          <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
            <h4 className="text-sm font-semibold text-amber-800 mb-2">💡 Conseils pour un import réussi</h4>
            <div className="space-y-1 text-xs text-amber-700">
              <div>• Vérifiez que les dates sont au format français DD/MM/YYYY</div>
              <div>• Assurez-vous que les montants sont numériques (positifs ou négatifs)</div>
              <div>• Les descriptions peuvent contenir des caractères spéciaux</div>
              <div>• Le nom du compte doit être cohérent dans tout le fichier</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
});

UploadInstructions.displayName = 'UploadInstructions';

export default UploadInstructions;