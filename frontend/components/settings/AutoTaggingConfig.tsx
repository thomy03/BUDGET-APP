'use client';

import { useState, useEffect } from 'react';
import { Card, Button, Alert, ToggleSwitch } from '../ui';
import { ConfidenceIndicator, ConfidenceLegend } from '../ui/ConfidenceIndicator';

interface AutoTaggingSettings {
  enabled: boolean;
  confidenceThreshold: number;
  webResearchEnabled: boolean;
  defaultClassification: 'fixed' | 'variable';
  autoApplyHighConfidence: boolean;
  batchProcessing: boolean;
  learningMode: boolean;
}

interface AutoTaggingConfigProps {
  className?: string;
}

export function AutoTaggingConfig({ className = '' }: AutoTaggingConfigProps) {
  const [settings, setSettings] = useState<AutoTaggingSettings>({
    enabled: true,
    confidenceThreshold: 0.7,
    webResearchEnabled: false,
    defaultClassification: 'variable',
    autoApplyHighConfidence: true,
    batchProcessing: false,
    learningMode: true
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // For now, use default settings
      // const response = await fetch('/api/auto-tagging/settings');
      // const data = await response.json();
      // setSettings(data);
      
    } catch (err) {
      setError('Erreur lors du chargement des paramètres');
      console.error('Load settings error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async () => {
    setIsSaving(true);
    setError('');
    setMessage('');
    
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // const response = await fetch('/api/auto-tagging/settings', {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(settings)
      // });
      
      setMessage('Paramètres sauvegardés avec succès');
      setTimeout(() => setMessage(''), 3000);
      
    } catch (err) {
      setError('Erreur lors de la sauvegarde');
      console.error('Save settings error:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const resetSettings = () => {
    setSettings({
      enabled: true,
      confidenceThreshold: 0.7,
      webResearchEnabled: false,
      defaultClassification: 'variable',
      autoApplyHighConfidence: true,
      batchProcessing: false,
      learningMode: true
    });
  };

  const getConfidenceThresholdLabel = (threshold: number) => {
    if (threshold >= 0.8) return 'Très strict (80%+)';
    if (threshold >= 0.6) return 'Équilibré (60%+)';
    return 'Permissif (50%+)';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Chargement de la configuration...</span>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🤖</span>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Configuration IA Auto-Tagging</h2>
            <p className="text-sm text-gray-600">
              Paramétrez l'intelligence artificielle pour la classification automatique des transactions
            </p>
          </div>
        </div>
      </Card>

      {/* Messages */}
      {message && (
        <Alert variant="success" className="mb-4">
          {message}
        </Alert>
      )}

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Main Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Paramètres généraux</h3>
        
        <div className="space-y-6">
          {/* Enable Auto-Tagging */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Activer l'auto-tagging IA
              </label>
              <p className="text-xs text-gray-500">
                Classification automatique des nouvelles transactions
              </p>
            </div>
            <ToggleSwitch
              enabled={settings.enabled}
              onChange={(enabled) => setSettings(prev => ({ ...prev, enabled }))}
            />
          </div>

          {/* Confidence Threshold */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700">
                Seuil de confiance
              </label>
              <ConfidenceIndicator 
                confidence={settings.confidenceThreshold} 
                size="sm"
                showPercentage={true}
              />
            </div>
            <div className="space-y-2">
              <input
                type="range"
                min="0.3"
                max="0.9"
                step="0.05"
                value={settings.confidenceThreshold}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  confidenceThreshold: parseFloat(e.target.value) 
                }))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>30% (Permissif)</span>
                <span className="font-medium text-gray-700">
                  {getConfidenceThresholdLabel(settings.confidenceThreshold)}
                </span>
                <span>90% (Très strict)</span>
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Les tags avec un niveau de confiance inférieur ne seront pas appliqués automatiquement
            </p>
          </div>

          {/* Web Research */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Recherche web enrichie
              </label>
              <p className="text-xs text-gray-500">
                Utiliser des données web pour améliorer la classification
              </p>
            </div>
            <ToggleSwitch
              enabled={settings.webResearchEnabled}
              onChange={(webResearchEnabled) => setSettings(prev => ({ ...prev, webResearchEnabled }))}
            />
          </div>

          {/* Default Classification */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">
              Classification par défaut
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="defaultClassification"
                  value="fixed"
                  checked={settings.defaultClassification === 'fixed'}
                  onChange={() => setSettings(prev => ({ ...prev, defaultClassification: 'fixed' }))}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Dépenses fixes</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="defaultClassification"
                  value="variable"
                  checked={settings.defaultClassification === 'variable'}
                  onChange={() => setSettings(prev => ({ ...prev, defaultClassification: 'variable' }))}
                  className="w-4 h-4 text-orange-600 border-gray-300 focus:ring-orange-500"
                />
                <span className="text-sm text-gray-700">Dépenses variables</span>
              </label>
            </div>
            <p className="text-xs text-gray-500">
              Type de dépense assigné par défaut pour les nouveaux tags
            </p>
          </div>
        </div>
      </Card>

      {/* Advanced Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Paramètres avancés</h3>
        
        <div className="space-y-6">
          {/* Auto-Apply High Confidence */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Application automatique haute confiance
              </label>
              <p className="text-xs text-gray-500">
                Appliquer automatiquement les tags avec confiance ≥ 80%
              </p>
            </div>
            <ToggleSwitch
              enabled={settings.autoApplyHighConfidence}
              onChange={(autoApplyHighConfidence) => setSettings(prev => ({ ...prev, autoApplyHighConfidence }))}
            />
          </div>

          {/* Batch Processing */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Traitement par lots
              </label>
              <p className="text-xs text-gray-500">
                Traiter plusieurs transactions simultanément
              </p>
            </div>
            <ToggleSwitch
              enabled={settings.batchProcessing}
              onChange={(batchProcessing) => setSettings(prev => ({ ...prev, batchProcessing }))}
            />
          </div>

          {/* Learning Mode */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Mode apprentissage
              </label>
              <p className="text-xs text-gray-500">
                Améliorer la précision en apprenant de vos corrections
              </p>
            </div>
            <ToggleSwitch
              enabled={settings.learningMode}
              onChange={(learningMode) => setSettings(prev => ({ ...prev, learningMode }))}
            />
          </div>
        </div>
      </Card>

      {/* Confidence Legend */}
      <Card className="p-6">
        <ConfidenceLegend />
      </Card>

      {/* Actions */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={resetSettings}
            disabled={isSaving}
          >
            Réinitialiser
          </Button>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={loadSettings}
              disabled={isLoading || isSaving}
            >
              <span className="mr-2">🔄</span>
              Recharger
            </Button>
            
            <Button
              onClick={saveSettings}
              disabled={isSaving}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Sauvegarde...
                </>
              ) : (
                <>
                  <span className="mr-2">💾</span>
                  Sauvegarder
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}