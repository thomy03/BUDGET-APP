'use client';

import React from 'react';
import { CustomProvisionCreate } from '../../lib/api';

const PRESET_PROVISIONS = [
  { name: 'Investissement', icon: '📈', color: '#10b981', category: 'investment' as const },
  { name: 'Voyage', icon: '✈️', color: '#3b82f6', category: 'savings' as const },
  { name: 'Rénovation', icon: '🏗️', color: '#f59e0b', category: 'project' as const },
  { name: 'Urgences', icon: '🚨', color: '#ef4444', category: 'savings' as const },
  { name: 'Voiture', icon: '🚗', color: '#8b5cf6', category: 'project' as const },
  { name: 'Vacances', icon: '🏖️', color: '#06b6d4', category: 'savings' as const },
  { name: 'Formation', icon: '📚', color: '#84cc16', category: 'investment' as const },
  { name: 'Santé', icon: '🏥', color: '#f97316', category: 'savings' as const },
];

interface ProvisionPresetsProps {
  onSelect: (preset: Partial<CustomProvisionCreate>) => void;
}

const ProvisionPresets = React.memo<ProvisionPresetsProps>(({ onSelect }) => {
  return (
    <div>
      <h4 className="font-medium mb-3 text-zinc-700">📋 Provisions prédéfinies</h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {PRESET_PROVISIONS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            onClick={() => onSelect({
              name: preset.name,
              icon: preset.icon,
              color: preset.color,
              category: preset.category,
              percentage: 5
            })}
            className="p-3 bg-zinc-50 hover:bg-zinc-100 rounded-lg text-center text-sm border border-zinc-200 hover:border-zinc-300 transition-colors"
          >
            <div className="text-lg mb-1">{preset.icon}</div>
            <div className="text-xs font-medium">{preset.name}</div>
          </button>
        ))}
      </div>
    </div>
  );
});

ProvisionPresets.displayName = 'ProvisionPresets';

export default ProvisionPresets;