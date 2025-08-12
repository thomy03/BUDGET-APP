'use client';

import { useState, useEffect } from 'react';
import { FixedLine, FixedLineCreate } from '../lib/api';

const DEFAULT_FORM_DATA: FixedLineCreate = {
  label: '',
  amount: 0,
  freq: 'mensuelle',
  split_mode: 'clé',
  split1: 50,
  split2: 50,
  active: true
};

export function useFixedExpenseForm(expense?: FixedLine) {
  const [formData, setFormData] = useState<FixedLineCreate>(DEFAULT_FORM_DATA);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Initialize form data when expense changes
  useEffect(() => {
    if (expense) {
      setFormData({
        label: expense.label,
        amount: expense.amount,
        freq: expense.freq,
        split_mode: expense.split_mode,
        split1: expense.split1,
        split2: expense.split2,
        active: expense.active
      });
      setShowAdvanced(Boolean(expense.split_mode === 'manuel'));
    } else {
      setFormData(DEFAULT_FORM_DATA);
      setShowAdvanced(false);
    }
  }, [expense]);

  const updateFormData = (field: keyof FixedLineCreate, value: any) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      
      // Auto-adjust split2 when split1 changes in manual mode
      if (field === 'split1' && prev.split_mode === 'manuel') {
        newData.split2 = 100 - Number(value);
      }
      // Auto-adjust split1 when split2 changes in manual mode
      else if (field === 'split2' && prev.split_mode === 'manuel') {
        newData.split1 = 100 - Number(value);
      }
      // Reset splits when changing split mode
      else if (field === 'split_mode') {
        if (value !== 'manuel') {
          newData.split1 = 50;
          newData.split2 = 50;
        }
        setShowAdvanced(value === 'manuel');
      }
      
      return newData;
    });
    setError(''); // Clear error when user makes changes
  };

  const applyPreset = (preset: Partial<FixedLineCreate>) => {
    setFormData(prev => ({ ...prev, ...preset }));
    setError('');
  };

  const validateForm = (): boolean => {
    if (!formData.label.trim()) {
      setError('Le nom de la charge est obligatoire');
      return false;
    }

    if (!formData.amount || formData.amount <= 0) {
      setError('Le montant doit être supérieur à 0');
      return false;
    }

    if (formData.split_mode === 'manuel') {
      const total = formData.split1 + formData.split2;
      if (Math.abs(total - 100) > 0.01) {
        setError('La somme des pourcentages doit être égale à 100');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async (onSave: (expense: FixedLineCreate) => Promise<void>) => {
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