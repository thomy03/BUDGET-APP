'use client';

import React from 'react';
import { FixedLine } from '../../lib/api';

const PRESET_EXPENSES = [
  { 
    label: 'Crédit immobilier', 
    icon: '🏠', 
    category: 'logement' as const,
    defaultAmount: 1200,
    freq: 'mensuelle' as const,
    split_mode: 'clé' as const
  },
  { 
    label: 'Crédit voiture', 
    icon: '🚗', 
    category: 'transport' as const,
    defaultAmount: 350,
    freq: 'mensuelle' as const,
    split_mode: 'clé' as const
  },
  { 
    label: 'EDF/Électricité', 
    icon: '⚡', 
    category: 'services' as const,
    defaultAmount: 120,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const
  },
  { 
    label: 'Eau', 
    icon: '💧', 
    category: 'services' as const,
    defaultAmount: 45,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const
  },
  { 
    label: 'Internet/Box', 
    icon: '🌐', 
    category: 'services' as const,
    defaultAmount: 40,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const
  },
  { 
    label: 'Forfaits mobiles', 
    icon: '📱', 
    category: 'services' as const,
    defaultAmount: 80,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const
  },
  { 
    label: 'Mutuelle/Assurance', 
    icon: '🏥', 
    category: 'services' as const,
    defaultAmount: 150,
    freq: 'mensuelle' as const,
    split_mode: 'clé' as const
  },
  { 
    label: 'Abonnements', 
    icon: '🎬', 
    category: 'loisirs' as const,
    defaultAmount: 25,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const
  },
];

interface FixedExpensePresetsProps {
  onSelect: (preset: Partial<Omit<FixedLine, 'id'>>) => void;
}

const FixedExpensePresets = React.memo<FixedExpensePresetsProps>(({ onSelect }) => {
  return (
    <div>
      <h4 className="font-medium mb-3 text-zinc-700">📋 Charges prédéfinies</h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {PRESET_EXPENSES.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => onSelect({
              label: preset.label,
              icon: preset.icon,
              category: preset.category,
              amount: preset.defaultAmount,
              freq: preset.freq,
              split_mode: preset.split_mode,
              split1: preset.split_mode === '50/50' ? 0.5 : 0.5,
              split2: preset.split_mode === '50/50' ? 0.5 : 0.5,
              active: true
            })}
            className="p-3 bg-zinc-50 hover:bg-zinc-100 rounded-lg text-center text-sm border border-zinc-200 hover:border-zinc-300 transition-colors"
          >
            <div className="text-lg mb-1">{preset.icon}</div>
            <div className="text-xs font-medium">{preset.label}</div>
            <div className="text-xs text-zinc-600">{preset.defaultAmount} €</div>
          </button>
        ))}
      </div>
    </div>
  );
});

FixedExpensePresets.displayName = 'FixedExpensePresets';

export default FixedExpensePresets;