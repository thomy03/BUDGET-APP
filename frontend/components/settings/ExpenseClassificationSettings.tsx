'use client';

import { useState, useEffect } from 'react';
import { 
  ExpenseClassificationRule, 
  ExpenseClassificationRuleCreate,
  expenseClassificationApi 
} from '../../lib/api';
import { Card, Button, Input, Modal } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';

export function ExpenseClassificationSettings() {
  const [rules, setRules] = useState<ExpenseClassificationRule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUsingDefaults, setIsUsingDefaults] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ExpenseClassificationRule | null>(null);
  const [formData, setFormData] = useState<ExpenseClassificationRuleCreate>({
    name: '',
    description: '',
    keywords: [],
    expense_type: 'variable',
    confidence_threshold: 0.8,
    is_active: true,
    match_type: 'partial',
    case_sensitive: false
  });

  // Charger les règles au montage
  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setIsUsingDefaults(false);
      
      const data = await expenseClassificationApi.getRules();
      setRules(data.sort((a, b) => a.priority - b.priority));
      
      // Détecter si on utilise les règles par défaut
      if (data.length === 5 && data.some(rule => rule.name === 'Abonnements et Services')) {
        setIsUsingDefaults(true);
        setError('API de classification indisponible - Règles par défaut activées');
      }
    } catch (error: any) {
      console.error('Failed to load rules:', error);
      setError('Erreur lors du chargement des règles de classification');
      
      // En cas d'échec complet, au moins afficher quelque chose
      setRules([{
        id: 0,
        name: 'Erreur de chargement',
        description: 'Impossible de charger les règles de classification',
        keywords: [],
        expense_type: 'variable',
        confidence_threshold: 0.5,
        is_active: false,
        priority: 1,
        match_type: 'partial',
        case_sensitive: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateRule = () => {
    setEditingRule(null);
    setFormData({
      name: '',
      description: '',
      keywords: [],
      expense_type: 'variable',
      confidence_threshold: 0.8,
      is_active: true,
      match_type: 'partial',
      case_sensitive: false
    });
    setIsModalOpen(true);
  };

  const handleEditRule = (rule: ExpenseClassificationRule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      keywords: rule.keywords,
      expense_type: rule.expense_type,
      confidence_threshold: rule.confidence_threshold,
      is_active: rule.is_active,
      match_type: rule.match_type,
      case_sensitive: rule.case_sensitive
    });
    setIsModalOpen(true);
  };

  const handleSaveRule = async () => {
    if (isUsingDefaults) {
      alert('Les règles ne peuvent pas être modifiées en mode par défaut. Veuillez vérifier la connexion API.');
      return;
    }
    
    try {
      if (editingRule) {
        await expenseClassificationApi.updateRule(editingRule.id, formData);
      } else {
        await expenseClassificationApi.createRule(formData);
      }
      await loadRules();
      setIsModalOpen(false);
    } catch (error: any) {
      console.error('Failed to save rule:', error);
      setError(`Erreur lors de la sauvegarde : ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette règle ?')) {
      try {
        await expenseClassificationApi.deleteRule(ruleId);
        await loadRules();
      } catch (error) {
        console.error('Failed to delete rule:', error);
      }
    }
  };

  const handleToggleRule = async (rule: ExpenseClassificationRule) => {
    try {
      await expenseClassificationApi.updateRule(rule.id, {
        is_active: !rule.is_active
      });
      await loadRules();
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  };

  const handleKeywordsChange = (value: string) => {
    const keywords = value.split(',').map(k => k.trim()).filter(k => k.length > 0);
    setFormData({ ...formData, keywords });
  };

  if (isLoading) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Chargement des règles...</span>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              🤖 Règles de Classification Automatique
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Configurez les mots-clés pour classifier automatiquement vos dépenses
            </p>
          </div>
          <Button onClick={handleCreateRule} className="flex items-center gap-2">
            <span>➕</span>
            Nouvelle règle
          </Button>
        </div>

        {rules.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune règle configurée
            </h3>
            <p className="text-gray-600 mb-4">
              Créez votre première règle pour automatiser la classification de vos dépenses.
            </p>
            <Button onClick={handleCreateRule}>
              Créer la première règle
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {rules.map((rule, index) => (
              <div
                key={rule.id}
                className={`
                  p-4 border rounded-lg transition-all
                  ${rule.is_active 
                    ? 'border-gray-200 bg-white' 
                    : 'border-gray-100 bg-gray-50 opacity-60'
                  }
                `}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500 font-mono w-6">
                        #{index + 1}
                      </span>
                      <h4 className="font-medium text-gray-900">{rule.name}</h4>
                      <ExpenseTypeBadge
                        type={rule.expense_type}
                        size="sm"
                      />
                    </div>
                    {!rule.is_active && (
                      <span className="px-2 py-1 text-xs bg-gray-200 text-gray-600 rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleRule(rule)}
                      className={`
                        px-3 py-1 text-xs rounded-full transition-colors
                        ${rule.is_active 
                          ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }
                      `}
                    >
                      {rule.is_active ? 'Actif' : 'Inactif'}
                    </button>
                    <button
                      onClick={() => handleEditRule(rule)}
                      className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDeleteRule(rule.id)}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                      title="Supprimer"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Mots-clés:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {rule.keywords.map((keyword, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <span className="text-gray-500">Confiance min.:</span>
                    <div className="mt-1">
                      <span className="font-medium">
                        {Math.round(rule.confidence_threshold * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <span className="text-gray-500">Type de correspondance:</span>
                    <div className="mt-1">
                      <span className="font-medium capitalize">
                        {rule.match_type === 'partial' ? 'Partielle' : 
                         rule.match_type === 'exact' ? 'Exacte' : 'Regex'}
                      </span>
                      {rule.case_sensitive && (
                        <span className="ml-2 text-xs text-gray-500">(Sensible à la casse)</span>
                      )}
                    </div>
                  </div>
                </div>

                {rule.description && (
                  <p className="text-sm text-gray-600 mt-2 italic">
                    {rule.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modal de création/édition de règle */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingRule ? 'Modifier la règle' : 'Nouvelle règle de classification'}
        size="lg"
      >
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nom de la règle *
              </label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Abonnements Netflix"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Type de dépense *
              </label>
              <div className="flex items-center gap-3">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="fixed"
                    checked={formData.expense_type === 'fixed'}
                    onChange={(e) => setFormData({ ...formData, expense_type: e.target.value as 'fixed' | 'variable' })}
                    className="mr-2"
                  />
                  <ExpenseTypeBadge type="fixed" size="sm" />
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="variable"
                    checked={formData.expense_type === 'variable'}
                    onChange={(e) => setFormData({ ...formData, expense_type: e.target.value as 'fixed' | 'variable' })}
                    className="mr-2"
                  />
                  <ExpenseTypeBadge type="variable" size="sm" />
                </label>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Mots-clés (séparés par des virgules) *
            </label>
            <Input
              value={formData.keywords.join(', ')}
              onChange={(e) => handleKeywordsChange(e.target.value)}
              placeholder="netflix, spotify, abonnement, mensuel"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Ces mots-clés seront recherchés dans les libellés des transactions
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (optionnelle)
            </label>
            <Input
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Description de cette règle"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Seuil de confiance minimum
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.1"
                  value={formData.confidence_threshold}
                  onChange={(e) => setFormData({ ...formData, confidence_threshold: parseFloat(e.target.value) })}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-12">
                  {Math.round(formData.confidence_threshold * 100)}%
                </span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Type de correspondance
              </label>
              <select
                value={formData.match_type}
                onChange={(e) => setFormData({ ...formData, match_type: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="partial">Partielle (contient le mot)</option>
                <option value="exact">Exacte (mot complet)</option>
                <option value="regex">Expression régulière</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="mr-2"
              />
              Règle active
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.case_sensitive}
                onChange={(e) => setFormData({ ...formData, case_sensitive: e.target.checked })}
                className="mr-2"
              />
              Sensible à la casse
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <Button
              variant="outline"
              onClick={() => setIsModalOpen(false)}
            >
              Annuler
            </Button>
            <Button
              onClick={handleSaveRule}
              disabled={!formData.name || formData.keywords.length === 0}
            >
              {editingRule ? 'Modifier' : 'Créer'} la règle
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

export default ExpenseClassificationSettings;