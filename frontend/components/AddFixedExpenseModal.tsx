'use client';

import React from 'react';
import { FixedLine, ConfigOut } from '../lib/api';
import { Card, Button, Input, Alert } from './ui';
import FixedExpensePresets from './forms/FixedExpensePresets';
import FixedExpenseIconCategory from './forms/FixedExpenseIconCategory';
import FixedExpenseCalculationSettings from './forms/FixedExpenseCalculationSettings';
import { useFixedExpenseForm } from '../hooks/useFixedExpenseForm';

interface AddFixedExpenseModalProps {
  config?: ConfigOut;
  expense?: FixedLine;
  onClose: () => void;
  onSave: (expense: Omit<FixedLine, 'id'>) => Promise<void>;
}

const AddFixedExpenseModal = React.memo<AddFixedExpenseModalProps>(({ 
  config, 
  expense, 
  onClose, 
  onSave 
}) => {
  const {
    formData,
    saving,
    error,
    showAdvanced,
    setShowAdvanced,
    updateFormData,
    applyPreset,
    handleSubmit,
    setError
  } = useFixedExpenseForm(expense);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await handleSubmit(onSave);
    if (success) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <Card padding="lg" className="relative">
          <div className="flex items-center justify-between mb-6">
            <h2 className="h2">
              {expense ? '✏️ Modifier' : '➕ Nouvelle'} charge fixe
            </h2>
            <button
              onClick={onClose}
              className="text-zinc-500 hover:text-zinc-700 text-2xl font-bold"
              type="button"
            >
              ×
            </button>
          </div>

          <form onSubmit={onSubmit} className="space-y-6">
            {error && <Alert variant="error">{error}</Alert>}

            {/* Presets */}
            {!expense && (
              <FixedExpensePresets onSelect={applyPreset} />
            )}

            {/* Basic Information */}
            <div className="space-y-4">
              <h4 className="font-medium text-zinc-700">📝 Informations de base</h4>
              
              <Input
                label="Nom de la charge *"
                value={formData.label}
                onChange={(e) => updateFormData('label', e.target.value)}
                placeholder="Ex: Crédit immobilier"
                required
              />
            </div>

            {/* Icon and Category */}
            <FixedExpenseIconCategory
              selectedIcon={formData.icon}
              selectedCategory={formData.category}
              onIconChange={(icon) => updateFormData('icon', icon)}
              onCategoryChange={(category) => updateFormData('category', category)}
            />

            {/* Calculation Settings */}
            <FixedExpenseCalculationSettings
              formData={formData}
              config={config}
              onChange={updateFormData}
            />

            {/* Advanced Options Toggle */}
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium text-zinc-700">Options avancées</span>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                {showAdvanced ? 'Masquer' : 'Afficher'}
              </button>
            </div>

            {/* Advanced Options */}
            {showAdvanced && (
              <AdvancedOptions
                formData={formData}
                onChange={updateFormData}
              />
            )}

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-4 pt-6 border-t">
              <Button
                variant="secondary"
                onClick={onClose}
                disabled={saving}
                type="button"
              >
                Annuler
              </Button>
              <Button
                variant="primary"
                type="submit"
                loading={saving}
                disabled={saving}
              >
                {expense ? 'Modifier' : 'Créer'} la charge
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
});

AddFixedExpenseModal.displayName = 'AddFixedExpenseModal';

// Advanced Options Component
const AdvancedOptions = React.memo<{
  formData: Omit<FixedLine, 'id'>;
  onChange: (field: keyof Omit<FixedLine, 'id'>, value: any) => void;
}>(({ formData, onChange }) => {
  return (
    <div className="space-y-4 p-4 bg-zinc-50 rounded-lg">
      <h5 className="font-medium text-zinc-700">⚙️ Options avancées</h5>
      
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={formData.active}
            onChange={(e) => onChange('active', e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm">Charge active</span>
        </label>
      </div>
    </div>
  );
});

AdvancedOptions.displayName = 'AdvancedOptions';

export default AddFixedExpenseModal;