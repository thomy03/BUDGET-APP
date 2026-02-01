'use client';

import React from 'react';
import { CustomProvision, CustomProvisionCreate, ConfigOut } from '../lib/api';
import { Card, Button, Input, Alert } from './ui';
import ProvisionPresets from './forms/ProvisionPresets';
import IconColorPicker from './forms/IconColorPicker';
import ProvisionCalculationSettings from './forms/ProvisionCalculationSettings';
import { useProvisionForm } from '../hooks/useProvisionForm';

interface AddProvisionModalProps {
  config?: ConfigOut;
  provision?: CustomProvision;
  onClose: () => void;
  onSave: (provision: CustomProvisionCreate) => Promise<void>;
}

const AddProvisionModal = React.memo<AddProvisionModalProps>(({ 
  config, 
  provision, 
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
  } = useProvisionForm(provision);

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
            <h2 style={{ color: "#1f2937" }} className="h2">
              {provision ? '✏️ Modifier' : '➕ Nouvelle'} provision
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
            {!provision && (
              <ProvisionPresets onSelect={applyPreset} />
            )}

            {/* Basic Information */}
            <div className="space-y-4">
              <h4 className="font-medium text-zinc-700">📝 Informations de base</h4>
              
              <Input
                label="Nom de la provision *"
                value={formData.name}
                onChange={(e) => updateFormData('name', e.target.value)}
                placeholder="Ex: Épargne vacances"
                required
              />
              
              <Input
                label="Description (optionnelle)"
                value={formData.description}
                onChange={(e) => updateFormData('description', e.target.value)}
                placeholder="Description détaillée de la provision"
              />
            </div>

            {/* Icon and Color */}
            <IconColorPicker
              selectedIcon={formData.icon}
              selectedColor={formData.color}
              onIconChange={(icon) => updateFormData('icon', icon)}
              onColorChange={(color) => updateFormData('color', color)}
            />

            {/* Calculation Settings */}
            <ProvisionCalculationSettings
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
                {provision ? 'Modifier' : 'Créer'} la provision
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
});

AddProvisionModal.displayName = 'AddProvisionModal';

// Advanced Options Component
const AdvancedOptions = React.memo<{
  formData: CustomProvisionCreate;
  onChange: (field: keyof CustomProvisionCreate, value: any) => void;
}>(({ formData, onChange }) => {
  return (
    <div className="space-y-4 p-4 bg-zinc-50 rounded-lg">
      <h5 className="font-medium text-zinc-700">⚙️ Options avancées</h5>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Input
          label="Date de début"
          type="date"
          value={formData.start_date || ''}
          onChange={(e) => onChange('start_date', e.target.value || undefined)}
        />
        
        <Input
          label="Date de fin"
          type="date"
          value={formData.end_date || ''}
          onChange={(e) => onChange('end_date', e.target.value || undefined)}
        />
      </div>
      
      <Input
        label="Objectif montant (€)"
        type="number"
        value={formData.target_amount || ''}
        onChange={(e) => onChange('target_amount', e.target.value ? Number(e.target.value) : undefined)}
        placeholder="Montant cible à atteindre"
        min="0"
        step="0.01"
      />
      
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={formData.is_active}
            onChange={(e) => onChange('is_active', e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm">Provision active</span>
        </label>
        
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={formData.is_temporary}
            onChange={(e) => onChange('is_temporary', e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm">Provision temporaire</span>
        </label>
      </div>
    </div>
  );
});

AdvancedOptions.displayName = 'AdvancedOptions';

export { AddProvisionModal };