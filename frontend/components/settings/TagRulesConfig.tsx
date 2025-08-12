'use client';

import { useState, useEffect } from 'react';
import { Card, Button, Alert, ToggleSwitch } from '../ui';
import { TagSourceBadge } from '../ui/TagSourceBadge';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';

interface TagRule {
  id: string;
  name: string;
  conditions: {
    type: 'merchant' | 'amount' | 'description' | 'category';
    operator: 'contains' | 'equals' | 'starts_with' | 'greater_than' | 'less_than';
    value: string | number;
  }[];
  actions: {
    type: 'add_tag' | 'set_expense_type' | 'set_category';
    value: string;
  }[];
  enabled: boolean;
  priority: number;
  created_at: string;
  usage_count: number;
  accuracy_rate: number;
}

interface TagRulesConfigProps {
  className?: string;
}

export function TagRulesConfig({ className = '' }: TagRulesConfigProps) {
  const [rules, setRules] = useState<TagRule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingRule, setEditingRule] = useState<TagRule | null>(null);

  // Load rules on mount
  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // Mock data - replace with actual API call
      const mockRules: TagRule[] = [
        {
          id: '1',
          name: 'Netflix Auto-Tag',
          conditions: [
            { type: 'merchant', operator: 'contains', value: 'NETFLIX' }
          ],
          actions: [
            { type: 'add_tag', value: 'streaming' },
            { type: 'set_expense_type', value: 'fixed' }
          ],
          enabled: true,
          priority: 1,
          created_at: '2024-01-10',
          usage_count: 45,
          accuracy_rate: 98
        },
        {
          id: '2',
          name: 'Supermarket Classification',
          conditions: [
            { type: 'merchant', operator: 'contains', value: 'CARREFOUR' },
            { type: 'merchant', operator: 'contains', value: 'LECLERC' },
            { type: 'merchant', operator: 'contains', value: 'AUCHAN' }
          ],
          actions: [
            { type: 'add_tag', value: 'alimentation' },
            { type: 'set_expense_type', value: 'variable' }
          ],
          enabled: true,
          priority: 2,
          created_at: '2024-01-08',
          usage_count: 127,
          accuracy_rate: 94
        },
        {
          id: '3',
          name: 'High Amount Expenses',
          conditions: [
            { type: 'amount', operator: 'greater_than', value: 500 }
          ],
          actions: [
            { type: 'add_tag', value: 'gros-achat' }
          ],
          enabled: false,
          priority: 3,
          created_at: '2024-01-05',
          usage_count: 8,
          accuracy_rate: 76
        }
      ];
      
      setRules(mockRules);
      
    } catch (err) {
      setError('Erreur lors du chargement des règles');
      console.error('Load rules error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setRules(prev => prev.map(rule => 
        rule.id === ruleId ? { ...rule, enabled } : rule
      ));
    } catch (err) {
      setError('Erreur lors de la mise à jour de la règle');
    }
  };

  const deleteRule = async (ruleId: string) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cette règle ?')) {
      return;
    }

    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setRules(prev => prev.filter(rule => rule.id !== ruleId));
    } catch (err) {
      setError('Erreur lors de la suppression de la règle');
    }
  };

  const getConditionText = (condition: TagRule['conditions'][0]) => {
    const operators = {
      contains: 'contient',
      equals: 'égale',
      starts_with: 'commence par',
      greater_than: 'supérieur à',
      less_than: 'inférieur à'
    };

    const types = {
      merchant: 'Marchand',
      amount: 'Montant',
      description: 'Description',
      category: 'Catégorie'
    };

    return `${types[condition.type]} ${operators[condition.operator]} "${condition.value}"`;
  };

  const getActionText = (action: TagRule['actions'][0]) => {
    const types = {
      add_tag: 'Ajouter tag',
      set_expense_type: 'Définir type',
      set_category: 'Définir catégorie'
    };

    return `${types[action.type]}: ${action.value}`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Chargement des règles...</span>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Règles de Classification Automatique
            </h2>
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span>{rules.filter(r => r.enabled).length} règles actives</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                <span>{rules.reduce((sum, r) => sum + r.usage_count, 0)} applications</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                <span>{Math.round(rules.reduce((sum, r) => sum + r.accuracy_rate, 0) / rules.length)}% précision</span>
              </div>
            </div>
          </div>
          <Button 
            onClick={() => setShowCreateForm(true)} 
            className="bg-purple-600 hover:bg-purple-700"
          >
            <span className="mr-2">+</span>
            Nouvelle règle
          </Button>
        </div>
      </Card>

      {/* Error Messages */}
      {error && (
        <Alert variant="error" className="mb-4">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError('')}
              className="text-red-800 hover:text-red-900"
            >
              ×
            </button>
          </div>
        </Alert>
      )}

      {/* Rules List */}
      <div className="space-y-4">
        {rules.length === 0 ? (
          <Card className="p-8 text-center">
            <div className="text-6xl mb-4">⚙️</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune règle configurée
            </h3>
            <p className="text-gray-600 mb-4">
              Créez des règles pour automatiser la classification de vos transactions.
            </p>
            <Button onClick={() => setShowCreateForm(true)}>
              Créer la première règle
            </Button>
          </Card>
        ) : (
          rules
            .sort((a, b) => a.priority - b.priority)
            .map((rule) => (
              <Card key={rule.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {/* Rule Header */}
                    <div className="flex items-center gap-3 mb-4">
                      <div className="flex items-center gap-2">
                        <ToggleSwitch
                          checked={rule.enabled}
                          onChange={(enabled) => toggleRule(rule.id, enabled)}
                          size="sm"
                        />
                        <h3 className="text-lg font-semibold text-gray-900">
                          {rule.name}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">
                          Priorité {rule.priority}
                        </span>
                        <span>•</span>
                        <span>{rule.usage_count} applications</span>
                        <span>•</span>
                        <span className={rule.accuracy_rate >= 90 ? 'text-green-600' : rule.accuracy_rate >= 80 ? 'text-orange-600' : 'text-red-600'}>
                          {rule.accuracy_rate}% précision
                        </span>
                      </div>
                    </div>

                    {/* Conditions */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Conditions :</h4>
                      <div className="space-y-1">
                        {rule.conditions.map((condition, index) => (
                          <div key={index} className="flex items-center text-sm text-gray-600">
                            <span className="mr-2">•</span>
                            <span>{getConditionText(condition)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Actions :</h4>
                      <div className="flex items-center gap-2 flex-wrap">
                        {rule.actions.map((action, index) => (
                          <span
                            key={index}
                            className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-xs font-medium"
                          >
                            {getActionText(action)}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="text-xs text-gray-500">
                      Créée le {new Date(rule.created_at).toLocaleDateString('fr-FR')}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => setEditingRule(rule)}
                      className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => deleteRule(rule.id)}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                      title="Supprimer"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </Card>
            ))
        )}
      </div>

      {/* Quick Templates */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Modèles de règles rapides</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 rounded-lg bg-gray-50 hover:shadow-sm transition-all cursor-pointer">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🏪</span>
              <span className="font-medium text-gray-900">Supermarchés</span>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Classification automatique des achats alimentaires
            </p>
            <Button size="sm" variant="outline" className="w-full">
              Utiliser ce modèle
            </Button>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg bg-gray-50 hover:shadow-sm transition-all cursor-pointer">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">⛽</span>
              <span className="font-medium text-gray-900">Stations-service</span>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Classification automatique des achats de carburant
            </p>
            <Button size="sm" variant="outline" className="w-full">
              Utiliser ce modèle
            </Button>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg bg-gray-50 hover:shadow-sm transition-all cursor-pointer">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">💳</span>
              <span className="font-medium text-gray-900">Abonnements</span>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Classification des paiements récurrents
            </p>
            <Button size="sm" variant="outline" className="w-full">
              Utiliser ce modèle
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}