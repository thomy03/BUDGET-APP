'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ConfigOut, FixedLine } from '../lib/api';

interface UseSettingsReturn {
  cfg: ConfigOut | null;
  lines: FixedLine[];
  loading: boolean;
  saving: boolean;
  message: string;
  error: string;
  load: () => Promise<void>;
  save: (formData: FormData) => Promise<void>;
  setMessage: (message: string) => void;
  setError: (error: string) => void;
}

export function useSettings(isAuthenticated: boolean): UseSettingsReturn {
  const [cfg, setCfg] = useState<ConfigOut | null>(null);
  const [lines, setLines] = useState<FixedLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      setLoading(true);
      setError('');
      
      const [configResponse, linesResponse] = await Promise.all([
        api.get<ConfigOut>('/config'),
        api.get<FixedLine[]>('/fixed-lines')
      ]);
      
      setCfg(configResponse.data);
      setLines(linesResponse.data);
    } catch (err: any) {
      console.error('Erreur lors du chargement de la configuration:', err);
      setError('Erreur lors du chargement de la configuration');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const save = async (formData: FormData) => {
    try {
      setSaving(true);
      setError('');
      setMessage('');
      
      const splitMode = formData.get('split_mode') as string || 'revenus';
      
      // Convertir les pourcentages en fractions si mode manuel
      let split1 = 0.5;
      let split2 = 0.5;
      
      if (splitMode === 'manuel') {
        const split1Percent = parseFloat(formData.get('split1') as string) || 50;
        const split2Percent = parseFloat(formData.get('split2') as string) || 50;
        split1 = split1Percent / 100;
        split2 = split2Percent / 100;
      }
      
      const payload = {
        member1: formData.get('member1') as string,
        member2: formData.get('member2') as string,
        rev1: parseFloat(formData.get('rev1') as string) || 0,
        rev2: parseFloat(formData.get('rev2') as string) || 0,
        tax_rate1: parseFloat(formData.get('tax_rate1') as string) || 0,
        tax_rate2: parseFloat(formData.get('tax_rate2') as string) || 0,
        split1,
        split2,
        split_mode: splitMode
      };
      
      console.log('Saving configuration:', payload);
      
      const response = await api.put<ConfigOut>('/config', payload);
      setCfg(response.data);
      
      setMessage('Configuration sauvegardée avec succès !');
      setTimeout(() => setMessage(''), 5000);
    } catch (err: any) {
      console.error('Erreur lors de la sauvegarde:', err);
      setError('Erreur lors de la sauvegarde de la configuration');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      load();
    }
  }, [isAuthenticated, load]);

  return {
    cfg,
    lines,
    loading,
    saving,
    message,
    error,
    load,
    save,
    setMessage,
    setError
  };
}
