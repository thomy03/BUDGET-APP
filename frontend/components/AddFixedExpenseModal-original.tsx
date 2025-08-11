'use client';

import { useState, useEffect } from 'react';
import { FixedLine, ConfigOut } from '../lib/api';
import { Card, Button, Input, Alert } from './ui';

interface AddFixedExpenseModalProps {
  config?: ConfigOut;
  expense?: FixedLine; // Pour l'édition
  onClose: () => void;
  onSave: (expense: Omit<FixedLine, 'id'>) => Promise<void>;
}

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

const ICON_OPTIONS = [
  '🏠', '🚗', '⚡', '💧', '🌐', '📱', '🏥', '🎬', '💳', '🏦',
  '💰', '📊', '🔧', '🍕', '🛒', '⛽', '🚌', '🏋️', '📚', '💡'
];

const CATEGORY_OPTIONS = [
  { value: 'logement', label: 'Logement', icon: '🏠' },
  { value: 'transport', label: 'Transport', icon: '🚗' },
  { value: 'services', label: 'Services', icon: '⚡' },
  { value: 'loisirs', label: 'Loisirs', icon: '🎬' },
  { value: 'autre', label: 'Autre', icon: '💳' },
];

export default function AddFixedExpenseModal({ config, expense, onClose, onSave }: AddFixedExpenseModalProps) {
  const [formData, setFormData] = useState<Omit<FixedLine, 'id'>>({
    label: '',
    amount: 0,
    freq: 'mensuelle',
    split_mode: 'clé',
    split1: 0.5,
    split2: 0.5,
    active: true,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('autre');
  const [selectedIcon, setSelectedIcon] = useState('💳');

  useEffect(() => {
    if (expense) {
      setFormData({
        label: expense.label,
        amount: expense.amount,
        freq: expense.freq,
        split_mode: expense.split_mode,
        split1: expense.split1,
        split2: expense.split2,
        active: expense.active,
      });
      setSelectedIcon(getCategoryIcon(expense.label));
      setShowAdvanced(expense.split_mode === 'manuel');
    }
  }, [expense]);

  const getCategoryIcon = (label: string) => {
    const lower = label.toLowerCase();
    if (lower.includes('crédit') && lower.includes('immobilier')) return '🏠';
    if (lower.includes('crédit') && lower.includes('voiture')) return '🚗';
    if (lower.includes('edf') || lower.includes('électricité')) return '⚡';
    if (lower.includes('eau')) return '💧';
    if (lower.includes('internet') || lower.includes('box')) return '🌐';
    if (lower.includes('mobile') || lower.includes('forfait')) return '📱';
    if (lower.includes('mutuelle') || lower.includes('assurance')) return '🏥';
    if (lower.includes('abonnement')) return '🎬';
    return '💳';
  };

  const calculateMonthlyPreview = (): number => {
    switch (formData.freq) {
      case 'mensuelle':
        return formData.amount;
      case 'trimestrielle':
        return formData.amount / 3;
      case 'annuelle':
        return formData.amount / 12;
      default:
        return formData.amount;
    }
  };

  const calculateMemberSplit = (monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (formData.split_mode) {
      case 'clé':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
          return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case 'm1':
        return { member1: monthlyAmount, member2: 0 };
      case 'm2':
        return { member1: 0, member2: monthlyAmount };
      case 'manuel':
        return {
          member1: monthlyAmount * formData.split1,
          member2: monthlyAmount * formData.split2,
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.label.trim()) {
      setError('Le nom est obligatoire');
      return;
    }

    if (!formData.amount || formData.amount <= 0) {
      setError('Le montant doit être positif');
      return;
    }

    if (formData.split_mode === 'manuel') {
      const total = formData.split1 + formData.split2;
      if (Math.abs(total - 1) > 0.01) {
        setError('Les parts doivent totaliser 100%');
        return;
      }
    }

    try {
      setSaving(true);
      setError('');
      await onSave(formData);
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  const handlePresetSelect = (preset: typeof PRESET_EXPENSES[0]) => {
    setFormData(prev => ({
      ...prev,
      label: preset.label,
      amount: preset.defaultAmount,
      freq: preset.freq,
      split_mode: preset.split_mode,
      split1: preset.split_mode === '50/50' ? 0.5 : prev.split1,
      split2: preset.split_mode === '50/50' ? 0.5 : prev.split2,
    }));
    setSelectedIcon(preset.icon);
    setSelectedCategory(preset.category);
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const monthlyAmount = calculateMonthlyPreview();
  const memberSplit = calculateMemberSplit(monthlyAmount);

  return (
    <div 
      className="modal-overlay fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-content bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 id="modal-title" className="text-xl font-bold text-gray-900">
              {expense ? 'Modifier la dépense fixe' : 'Nouvelle Dépense Fixe'}
            </h2>
            <Button
              type="button"
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-xl icon-hover"
              aria-label="Fermer le modal"
            >
              ✕
            </Button>
          </div>

          {error && <Alert variant="error" className="mb-4">{error}</Alert>}

          {/* Presets */}
          {!expense && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Modèles prédéfinis
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {PRESET_EXPENSES.map((preset, index) => (
                  <Button
                    key={index}
                    type="button"
                    onClick={() => handlePresetSelect(preset)}
                    className="p-2 text-xs border border-gray-200 hover:border-emerald-300 hover:bg-emerald-50 rounded-lg transition-colors"
                  >
                    <span className="text-base mb-1">{preset.icon}</span>
                    <div className="text-gray-700">{preset.label}</div>
                    <div className="text-xs text-gray-500 mt-1">{formatAmount(preset.defaultAmount)}</div>
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Column */}
            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom de la dépense *
                </label>
                <Input
                  value={formData.label}
                  onChange={(e) => setFormData(prev => ({ ...prev, label: e.target.value }))}
                  placeholder="Ex: Crédit immobilier, Forfait mobile..."
                  required
                />
              </div>

              {/* Amount */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Montant (€) *
                </label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.amount || ''}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    amount: parseFloat(e.target.value) || 0 
                  }))}
                  placeholder="100"
                  required
                />
              </div>

              {/* Frequency */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fréquence
                </label>
                <select
                  value={formData.freq}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    freq: e.target.value as any 
                  }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="mensuelle">Mensuelle</option>
                  <option value="trimestrielle">Trimestrielle</option>
                  <option value="annuelle">Annuelle</option>
                </select>
              </div>

              {/* Category & Icon */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Catégorie et Icône
                </label>
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-2xl p-2 border rounded-lg bg-emerald-50">
                    {selectedIcon}
                  </span>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {CATEGORY_OPTIONS.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.icon} {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-10 gap-1">
                  {ICON_OPTIONS.map((icon, index) => (
                    <Button
                      key={index}
                      type="button"
                      onClick={() => setSelectedIcon(icon)}
                      className={`p-1 text-lg hover:bg-gray-100 rounded ${
                        selectedIcon === icon ? 'bg-emerald-100 ring-2 ring-emerald-300' : ''
                      }`}
                    >
                      {icon}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
              {/* Split Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Répartition entre membres
                </label>
                <select
                  value={formData.split_mode}
                  onChange={(e) => {
                    const mode = e.target.value as any;
                    setFormData(prev => ({ 
                      ...prev, 
                      split_mode: mode,
                      split1: mode === '50/50' ? 0.5 : mode === 'm1' ? 1 : mode === 'm2' ? 0 : prev.split1,
                      split2: mode === '50/50' ? 0.5 : mode === 'm1' ? 0 : mode === 'm2' ? 1 : prev.split2,
                    }));
                    setShowAdvanced(mode === 'manuel');
                  }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="clé">Clé globale (selon revenus)</option>
                  <option value="50/50">50/50</option>
                  <option value="m1">100% {config?.member1 || 'Membre 1'}</option>
                  <option value="m2">100% {config?.member2 || 'Membre 2'}</option>
                  <option value="manuel">Personnalisé</option>
                </select>
              </div>

              {/* Custom Split */}
              {formData.split_mode === 'manuel' && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      {config?.member1 || 'Membre 1'} (%)
                    </label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      value={Math.round(formData.split1 * 100)}
                      onChange={(e) => {
                        const value = (parseFloat(e.target.value) || 0) / 100;
                        setFormData(prev => ({
                          ...prev,
                          split1: value,
                          split2: 1 - value,
                        }));
                      }}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      {config?.member2 || 'Membre 2'} (%)
                    </label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      value={Math.round(formData.split2 * 100)}
                      onChange={(e) => {
                        const value = (parseFloat(e.target.value) || 0) / 100;
                        setFormData(prev => ({
                          ...prev,
                          split2: value,
                          split1: 1 - value,
                        }));
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Preview */}
              <Card className="p-3 bg-emerald-50 border-emerald-200">
                <div className="text-sm font-medium text-emerald-700 mb-2">Aperçu</div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Montant {formData.freq}:</span>
                    <span className="font-medium">{formatAmount(formData.amount)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Montant mensuel:</span>
                    <span className="font-bold text-emerald-700">{formatAmount(monthlyAmount)}</span>
                  </div>
                  {config && (
                    <div className="pt-2 border-t border-emerald-200">
                      <div className="grid grid-cols-2 gap-2 text-xs text-emerald-600">
                        <div className="flex justify-between">
                          <span>{config.member1}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member1)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>{config.member2}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member2)}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>

              {/* Active Status */}
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="active"
                  checked={formData.active}
                  onChange={(e) => setFormData(prev => ({ ...prev, active: e.target.checked }))}
                  className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                <label htmlFor="active" className="text-sm text-gray-700">
                  Dépense active (incluse dans les calculs)
                </label>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end space-x-3 mt-6">
            <Button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {saving ? 'Enregistrement...' : (expense ? 'Modifier' : 'Créer')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}