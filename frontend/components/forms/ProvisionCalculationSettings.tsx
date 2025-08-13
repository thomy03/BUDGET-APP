'use client';

import React from 'react';
import { Input } from '../ui';
import { CustomProvisionCreate, ConfigOut } from '../../lib/api';

interface ProvisionCalculationSettingsProps {
  formData: CustomProvisionCreate;
  config?: ConfigOut;
  onChange: (field: keyof CustomProvisionCreate, value: any) => void;
}

const ProvisionCalculationSettings = React.memo<ProvisionCalculationSettingsProps>(({
  formData,
  config,
  onChange
}) => {
  const calculatePreviewAmount = (): number => {
    if (!config) return 0;

    let base = 0;
    switch (formData.base_calculation) {
      case 'total':
        base = (config.rev1 || 0) + (config.rev2 || 0);
        break;
      case 'member1':
        base = config.rev1 || 0;
        break;
      case 'member2':
        base = config.rev2 || 0;
        break;
      case 'fixed':
        return formData.fixed_amount || 0;
    }

    // Les revenus dans config sont déjà mensuels
    // On applique le pourcentage directement pour obtenir le montant mensuel
    return base * formData.percentage / 100;
  };

  const calculateMemberSplit = (monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (formData.split_mode) {
      case 'key':
        // Calcul basé sur les revenus NETS après impôts pour une répartition plus équitable
        const rev1Net = (config.rev1 || 0) * (1 - (config.tax_rate1 || 0) / 100);
        const rev2Net = (config.rev2 || 0) * (1 - (config.tax_rate2 || 0) / 100);
        const totalRevNet = rev1Net + rev2Net;
        
        if (totalRevNet > 0) {
          const r1 = rev1Net / totalRevNet;
          const r2 = rev2Net / totalRevNet;
          return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '100/0':
        return { member1: monthlyAmount, member2: 0 };
      case '0/100':
        return { member1: 0, member2: monthlyAmount };
      case 'custom':
        return {
          member1: monthlyAmount * (formData.split_member1 / 100),
          member2: monthlyAmount * (formData.split_member2 / 100),
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const previewAmount = calculatePreviewAmount();
  const memberSplit = calculateMemberSplit(previewAmount);

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-zinc-700">💰 Calcul de la provision</h4>
      
      {/* Base Calculation */}
      <div>
        <label className="block text-sm font-medium mb-2">Base de calcul</label>
        <select
          value={formData.base_calculation}
          onChange={(e) => onChange('base_calculation', e.target.value)}
          className="w-full p-3 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="total">Revenus totaux</option>
          <option value="member1">Revenus {config?.member1 || 'Membre 1'}</option>
          <option value="member2">Revenus {config?.member2 || 'Membre 2'}</option>
          <option value="fixed">Montant fixe</option>
        </select>
      </div>

      {/* Percentage or Fixed Amount */}
      {formData.base_calculation === 'fixed' ? (
        <Input
          label="Montant fixe mensuel (€)"
          type="number"
          value={formData.fixed_amount || 0}
          onChange={(e) => onChange('fixed_amount', Number(e.target.value))}
          min="0"
          step="0.01"
        />
      ) : (
        <Input
          label="Pourcentage du revenu mensuel (%)"
          type="number"
          value={formData.percentage}
          onChange={(e) => onChange('percentage', Number(e.target.value))}
          min="0"
          max="100"
          step="0.1"
          hint="Exemple: 10% du revenu mensuel pour l'épargne"
        />
      )}

      {/* Split Mode */}
      <div>
        <label className="block text-sm font-medium mb-2">Répartition</label>
        <select
          value={formData.split_mode}
          onChange={(e) => onChange('split_mode', e.target.value)}
          className="w-full p-3 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="key">Selon la clé de répartition</option>
          <option value="50/50">50/50</option>
          <option value="100/0">100% {config?.member1 || 'Membre 1'}</option>
          <option value="0/100">100% {config?.member2 || 'Membre 2'}</option>
          <option value="custom">Personnalisé</option>
        </select>
      </div>

      {/* Custom Split */}
      {formData.split_mode === 'custom' && (
        <div className="grid grid-cols-2 gap-4">
          <Input
            label={`${config?.member1 || 'Membre 1'} (%)`}
            type="number"
            value={formData.split_member1}
            onChange={(e) => onChange('split_member1', Number(e.target.value))}
            min="0"
            max="100"
          />
          <Input
            label={`${config?.member2 || 'Membre 2'} (%)`}
            type="number"
            value={formData.split_member2}
            onChange={(e) => onChange('split_member2', Number(e.target.value))}
            min="0"
            max="100"
          />
        </div>
      )}

      {/* Preview */}
      {config && (
        <div className="p-4 bg-blue-50 rounded-lg">
          <h5 className="font-medium text-blue-900 mb-2">Aperçu mensuel</h5>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Total mensuel (calculé sur revenus bruts) :</span>
              <span className="font-mono font-semibold">{previewAmount.toFixed(2)} €</span>
            </div>
            <div className="flex justify-between text-blue-800">
              <span>{config.member1} :</span>
              <span className="font-mono">{memberSplit.member1.toFixed(2)} €</span>
            </div>
            <div className="flex justify-between text-blue-800">
              <span>{config.member2} :</span>
              <span className="font-mono">{memberSplit.member2.toFixed(2)} €</span>
            </div>
            {formData.split_mode === 'key' && (config.tax_rate1 > 0 || config.tax_rate2 > 0) && (
              <div className="mt-2 pt-2 border-t border-blue-200 text-xs text-blue-700">
                💡 Répartition basée sur les revenus nets après impôts
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
});

ProvisionCalculationSettings.displayName = 'ProvisionCalculationSettings';

export default ProvisionCalculationSettings;