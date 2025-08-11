'use client';

import { useState, useEffect } from 'react';
import { CustomProvision, CustomProvisionCreate } from '../lib/api';

const DEFAULT_FORM_DATA: CustomProvisionCreate = {
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
};

export function useProvisionForm(provision?: CustomProvision) {
  const [formData, setFormData] = useState<CustomProvisionCreate>(DEFAULT_FORM_DATA);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Initialize form data when provision changes
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
    } else {
      setFormData(DEFAULT_FORM_DATA);
      setShowAdvanced(false);
    }
  }, [provision]);

  const updateFormData = (field: keyof CustomProvisionCreate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(''); // Clear error when user makes changes
  };

  const applyPreset = (preset: Partial<CustomProvisionCreate>) => {
    setFormData(prev => ({ ...prev, ...preset }));
    setError('');
  };

  const validateForm = (): boolean => {
    if (!formData.name.trim()) {
      setError('Le nom est obligatoire');
      return false;
    }

    if (formData.base_calculation === 'fixed' && (!formData.fixed_amount || formData.fixed_amount <= 0)) {
      setError('Un montant fixe positif est requis');
      return false;
    }

    if (formData.split_mode === 'custom') {
      const total = formData.split_member1 + formData.split_member2;
      if (Math.abs(total - 100) > 0.01) {
        setError('La somme des pourcentages doit être égale à 100%');
        return false;
      }
    }

    if (formData.percentage < 0 || formData.percentage > 100) {
      setError('Le pourcentage doit être entre 0 et 100');
      return false;
    }

    return true;
  };

  const handleSubmit = async (onSave: (provision: CustomProvisionCreate) => Promise<void>) => {
    if (!validateForm()) return false;

    try {
      setSaving(true);
      setError('');
      await onSave(formData);
      return true;
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la sauvegarde');
      return false;
    } finally {
      setSaving(false);
    }
  };

  return {
    formData,
    saving,
    error,
    showAdvanced,
    setShowAdvanced,
    updateFormData,
    applyPreset,
    handleSubmit,
    setError
  };
}