'use client';

import { useState, useEffect } from 'react';
import { CustomProvision, CustomProvisionCreate, ConfigOut } from '../lib/api';
import { Card, Button, Input, Alert } from './ui';

interface AddProvisionModalProps {
  config?: ConfigOut;
  provision?: CustomProvision; // Pour l'édition
  onClose: () => void;
  onSave: (provision: CustomProvisionCreate) => Promise<void>;
}

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

const ICON_OPTIONS = [
  '💰', '📈', '✈️', '🏗️', '🚨', '🚗', '🏖️', '📚', '🏥', '🎁', '💝', '🎯',
  '💎', '🏠', '🌟', '⚡', '🔥', '🌈', '🚀', '💡', '🎉', '🎊', '🍀', '✨'
];

const COLOR_OPTIONS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b', '#10b981',
  '#059669', '#0891b2', '#0284c7', '#3b82f6', '#6366f1', '#7c3aed',
  '#a855f7', '#c2410c', '#dc2626', '#ea580c', '#ca8a04', '#65a30d'
];

export function AddProvisionModal({ config, provision, onClose, onSave }: AddProvisionModalProps) {
  const [formData, setFormData] = useState<CustomProvisionCreate>({
    name: '',
    description: '',
    percentage: 5,
    base_calculation: 'total',
    fixed_amount: 0,
    split_mode: 'key',
    split_member1: 50,
    split_member2: 50,
    icon: '💰',
    color: '#6366f1',
    display_order: 999,
    is_active: true,
    is_temporary: false,
    category: 'custom',
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (provision) {
      setFormData({
        name: provision.name,
        description: provision.description || '',
        percentage: provision.percentage,
        base_calculation: provision.base_calculation,
        fixed_amount: provision.fixed_amount || 0,
        split_mode: provision.split_mode,
        split_member1: provision.split_member1,
        split_member2: provision.split_member2,
        icon: provision.icon,
        color: provision.color,
        display_order: provision.display_order,
        is_active: provision.is_active,
        is_temporary: provision.is_temporary,
        start_date: provision.start_date,
        end_date: provision.end_date,
        target_amount: provision.target_amount,
        category: provision.category,
      });
      setShowAdvanced(Boolean(
        provision.start_date || 
        provision.end_date || 
        provision.target_amount ||
        provision.base_calculation === 'fixed' ||
        provision.split_mode === 'custom'
      ));
    }
  }, [provision]);

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

    return (base * formData.percentage / 100) / 12;
  };

  const calculateMemberSplit = (monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (formData.split_mode) {
      case 'key':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError('Le nom est obligatoire');
      return;
    }

    if (formData.base_calculation === 'fixed' && (!formData.fixed_amount || formData.fixed_amount <= 0)) {
      setError('Un montant fixe positif est requis');
      return;
    }

    if (formData.split_mode === 'custom') {
      const total = formData.split_member1 + formData.split_member2;
      if (Math.abs(total - 100) > 0.01) {
        setError('Les pourcentages doivent totaliser 100%');
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

  const handlePresetSelect = (preset: typeof PRESET_PROVISIONS[0]) => {
    setFormData(prev => ({
      ...prev,
      name: preset.name,
      icon: preset.icon,
      color: preset.color,
      category: preset.category,
    }));
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const monthlyAmount = calculatePreviewAmount();
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
              {provision ? 'Modifier la provision' : 'Nouvelle Provision'}
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
          {!provision && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Modèles prédéfinis
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {PRESET_PROVISIONS.map((preset, index) => (
                  <Button
                    key={index}
                    type="button"
                    onClick={() => handlePresetSelect(preset)}
                    className="p-2 text-xs border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    <span className="text-base mb-1">{preset.icon}</span>
                    <div className="text-gray-700">{preset.name}</div>
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
                  Nom de la provision *
                </label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Ex: Investissement, Voyage..."
                  required
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description (optionnel)
                </label>
                <Input
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Ex: Pour nos prochaines vacances..."
                />
              </div>

              {/* Icon */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Icône
                </label>
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-2xl p-2 border rounded-lg" style={{ backgroundColor: formData.color + '20' }}>
                    {formData.icon}
                  </span>
                  <Input
                    value={formData.icon}
                    onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
                    className="w-20 text-center"
                    placeholder="💰"
                  />
                </div>
                <div className="grid grid-cols-8 gap-1">
                  {ICON_OPTIONS.map((icon, index) => (
                    <Button
                      key={index}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, icon }))}
                      className={`p-1 text-lg hover:bg-gray-100 rounded ${
                        formData.icon === icon ? 'bg-indigo-100 ring-2 ring-indigo-300' : ''
                      }`}
                    >
                      {icon}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Color */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Couleur
                </label>
                <div className="flex items-center space-x-2 mb-2">
                  <div
                    className="w-8 h-8 rounded-full border-2 border-gray-200"
                    style={{ backgroundColor: formData.color }}
                  ></div>
                  <Input
                    type="color"
                    value={formData.color}
                    onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                    className="w-20"
                  />
                </div>
                <div className="grid grid-cols-9 gap-1">
                  {COLOR_OPTIONS.map((color, index) => (
                    <Button
                      key={index}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, color }))}
                      className={`color-option w-6 h-6 rounded-full border-2 ${
                        formData.color === color ? 'border-gray-800 scale-110' : 'border-gray-200'
                      }`}
                      style={{ backgroundColor: color }}
                      aria-label={`Sélectionner la couleur ${color}`}
                    >
                      <span className="sr-only">Couleur {color}</span>
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
              {/* Base Calculation */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Base de calcul
                </label>
                <select
                  value={formData.base_calculation}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    base_calculation: e.target.value as any 
                  }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="total">Revenus totaux</option>
                  <option value="member1">{config?.member1 || 'Membre 1'}</option>
                  <option value="member2">{config?.member2 || 'Membre 2'}</option>
                  <option value="fixed">Montant fixe</option>
                </select>
              </div>

              {/* Percentage or Fixed Amount */}
              {formData.base_calculation === 'fixed' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Montant mensuel fixe (€)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.fixed_amount || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      fixed_amount: parseFloat(e.target.value) || 0 
                    }))}
                    placeholder="100"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Pourcentage ({formData.percentage}%)
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.5"
                    value={formData.percentage}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      percentage: parseFloat(e.target.value) 
                    }))}
                    className="provision-slider w-full"
                    style={{
                      background: `linear-gradient(to right, ${formData.color} 0%, ${formData.color} ${formData.percentage}%, #e5e7eb ${formData.percentage}%, #e5e7eb 100%)`
                    }}
                    aria-label={`Pourcentage: ${formData.percentage}%`}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>
              )}

              {/* Split Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Répartition entre membres
                </label>
                <select
                  value={formData.split_mode}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    split_mode: e.target.value as any 
                  }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="key">Clé globale (selon revenus)</option>
                  <option value="50/50">50/50</option>
                  <option value="100/0">100% {config?.member1 || 'Membre 1'}</option>
                  <option value="0/100">100% {config?.member2 || 'Membre 2'}</option>
                  <option value="custom">Personnalisé</option>
                </select>
              </div>

              {/* Custom Split */}
              {formData.split_mode === 'custom' && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">
                      {config?.member1 || 'Membre 1'} (%)
                    </label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      value={formData.split_member1}
                      onChange={(e) => {
                        const value = parseFloat(e.target.value) || 0;
                        setFormData(prev => ({
                          ...prev,
                          split_member1: value,
                          split_member2: 100 - value,
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
                      value={formData.split_member2}
                      onChange={(e) => {
                        const value = parseFloat(e.target.value) || 0;
                        setFormData(prev => ({
                          ...prev,
                          split_member2: value,
                          split_member1: 100 - value,
                        }));
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Preview */}
              <Card className="p-3 bg-gray-50 border-l-4" style={{ borderLeftColor: formData.color }}>
                <div className="text-sm font-medium text-gray-700 mb-2">Aperçu mensuel</div>
                <div className="text-lg font-bold text-gray-900 mb-2">
                  {formatAmount(monthlyAmount)}
                </div>
                {config && (
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                    <div className="flex justify-between">
                      <span>{config.member1 || 'Membre 1'}:</span>
                      <span className="font-medium">{formatAmount(memberSplit.member1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>{config.member2 || 'Membre 2'}:</span>
                      <span className="font-medium">{formatAmount(memberSplit.member2)}</span>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="mt-6">
            <Button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-indigo-600 hover:text-indigo-700"
            >
              {showAdvanced ? '▼' : '▶'} Options avancées
            </Button>
          </div>

          {showAdvanced && (
            <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Catégorie
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value as any }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="custom">Personnalisé</option>
                    <option value="savings">Épargne</option>
                    <option value="investment">Investissement</option>
                    <option value="project">Projet</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Montant objectif (€)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.target_amount || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      target_amount: e.target.value ? parseFloat(e.target.value) : undefined
                    }))}
                    placeholder="5000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date de début
                  </label>
                  <Input
                    type="date"
                    value={formData.start_date ? formData.start_date.split('T')[0] : ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      start_date: e.target.value || undefined
                    }))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date de fin
                  </label>
                  <Input
                    type="date"
                    value={formData.end_date ? formData.end_date.split('T')[0] : ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      end_date: e.target.value || undefined
                    }))}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={formData.is_temporary}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_temporary: e.target.checked }))}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-gray-700">Provision temporaire</span>
                </label>

                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>
              </div>
            </div>
          )}

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
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {saving ? 'Enregistrement...' : (provision ? 'Modifier' : 'Créer')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}