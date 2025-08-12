'use client';

import { Card, Button, Input } from '../ui';
import { ConfigOut } from '../../lib/api';

interface BudgetConfigurationProps {
  cfg: ConfigOut | null;
  saving: boolean;
  onSave: (formData: FormData) => void;
}

export function BudgetConfiguration({ cfg, saving, onSave }: BudgetConfigurationProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    onSave(formData);
  };

  if (!cfg) return null;

  const totalRevenue = (cfg.rev1 || 0) + (cfg.rev2 || 0);
  const member1Percentage = totalRevenue > 0 ? ((cfg.rev1 || 0) / totalRevenue * 100).toFixed(1) : '0';
  const member2Percentage = totalRevenue > 0 ? ((cfg.rev2 || 0) / totalRevenue * 100).toFixed(1) : '0';

  return (
    <Card>
      <div className="p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900">
          ⚙️ Configuration du budget familial
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Membres du foyer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nom du premier membre
              </label>
              <Input
                name="member1"
                defaultValue={cfg.member1 || ''}
                placeholder="ex: Sarah"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nom du second membre
              </label>
              <Input
                name="member2"
                defaultValue={cfg.member2 || ''}
                placeholder="ex: Thomas"
                required
              />
            </div>
          </div>

          {/* Revenus */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Revenu mensuel de {cfg.member1 || 'Membre 1'} (€)
              </label>
              <Input
                name="rev1"
                type="number"
                step="0.01"
                defaultValue={cfg.rev1 || ''}
                placeholder="ex: 3000"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Part: {member1Percentage}% du foyer
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Revenu mensuel de {cfg.member2 || 'Membre 2'} (€)
              </label>
              <Input
                name="rev2"
                type="number"
                step="0.01"
                defaultValue={cfg.rev2 || ''}
                placeholder="ex: 2500"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Part: {member2Percentage}% du foyer
              </p>
            </div>
          </div>

          {/* Résumé des revenus */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex justify-between items-center">
              <span className="font-medium text-blue-900">Revenu total du foyer:</span>
              <span className="text-xl font-bold text-blue-900">
                {totalRevenue.toLocaleString('fr-FR', {
                  style: 'currency',
                  currency: 'EUR',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                })}
              </span>
            </div>
          </div>

          {/* Mode de répartition */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mode de répartition des dépenses
            </label>
            <select 
              name="split_mode" 
              defaultValue={cfg.split_mode || 'revenus'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="revenus">Automatique (proportionnel aux revenus)</option>
              <option value="manuel">Personnalisé</option>
            </select>
          </div>

          {/* Bouton de sauvegarde */}
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={saving}
              className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {saving ? 'Sauvegarde...' : '💾 Sauvegarder la configuration'}
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
}
