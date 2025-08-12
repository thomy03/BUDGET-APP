'use client';

import { useState, useEffect } from 'react';
import { Card, Button, Input, Alert, Modal } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { useTagsManagement, TagInfo } from '../../hooks/useTagsManagement';

interface AutoTaggingRule {
  id: string;
  pattern: string;
  tagName: string;
  description: string;
  isActive: boolean;
  matchCount?: number;
}

interface AutoTaggingRulesProps {
  tags: TagInfo[];
  isLoading: boolean;
}

export function AutoTaggingRules({ tags, isLoading }: AutoTaggingRulesProps) {
  const [rules, setRules] = useState<AutoTaggingRule[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AutoTaggingRule | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  // Charger les règles existantes depuis les tags
  useEffect(() => {
    if (!tags.length) return;

    const generatedRules: AutoTaggingRule[] = [];
    
    tags.forEach((tag) => {
      if (tag.associated_labels && tag.associated_labels.length > 0) {
        tag.associated_labels.forEach((label, index) => {
          generatedRules.push({
            id: `${tag.name}-${index}`,
            pattern: label,
            tagName: tag.name,
            description: `Si le libellé contient "${label}", alors assigner le tag "${tag.name}"`,
            isActive: true,
            matchCount: 0 // En production, cela viendrait d'une API
          });
        });
      }
    });

    setRules(generatedRules);
  }, [tags]);

  const handleCreateRule = () => {
    setEditingRule(null);
    setIsCreateModalOpen(true);
  };

  const handleEditRule = (rule: AutoTaggingRule) => {
    setEditingRule(rule);
    setIsCreateModalOpen(true);
  };

  const handleDeleteRule = (ruleId: string) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer cette règle ?')) {
      setRules(rules.filter(rule => rule.id !== ruleId));
    }
  };

  const handleToggleRule = (ruleId: string) => {
    setRules(rules.map(rule => 
      rule.id === ruleId 
        ? { ...rule, isActive: !rule.isActive }
        : rule
    ));
  };

  const handleTestRules = () => {
    setLocalError('Fonctionnalité de test en cours de développement');
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
              🤖 Règles de Tagging Automatique
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Configurez des règles pour assigner automatiquement des tags selon les libellés de transaction
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleTestRules} variant="outline" size="sm">
              🧪 Tester
            </Button>
            <Button onClick={handleCreateRule} className="flex items-center gap-2">
              <span>+</span>
              Nouvelle règle
            </Button>
          </div>
        </div>

        {/* Messages d'erreur */}
        {localError && (
          <Alert variant="error" className="mb-4">
            <div className="flex items-center justify-between">
              <span>{localError}</span>
              <button onClick={() => setLocalError(null)} className="text-red-800 hover:text-red-900">
                ×
              </button>
            </div>
          </Alert>
        )}

        {rules.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune règle configurée
            </h3>
            <p className="text-gray-600 mb-4">
              Créez votre première règle pour automatiser le tagging des transactions.
            </p>
            <Button onClick={handleCreateRule}>
              Créer la première règle
            </Button>
          </div>
        ) : (
          <>
            {/* Statistiques des règles */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <div className="text-xl font-bold text-blue-600">{rules.length}</div>
                <div className="text-sm text-gray-600">Règles total</div>
              </div>
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="text-xl font-bold text-green-600">
                  {rules.filter(r => r.isActive).length}
                </div>
                <div className="text-sm text-gray-600">Règles actives</div>
              </div>
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <div className="text-xl font-bold text-purple-600">
                  {rules.reduce((sum, r) => sum + (r.matchCount || 0), 0)}
                </div>
                <div className="text-sm text-gray-600">Applications</div>
              </div>
            </div>

            {/* Liste des règles */}
            <div className="space-y-3">
              {rules.map((rule) => {
                const associatedTag = tags.find(t => t.name === rule.tagName);
                
                return (
                  <div
                    key={rule.id}
                    className={`
                      p-4 border rounded-lg transition-all
                      ${rule.isActive 
                        ? 'border-green-200 bg-green-50/30' 
                        : 'border-gray-200 bg-gray-50 opacity-60'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`
                            w-3 h-3 rounded-full 
                            ${rule.isActive ? 'bg-green-500' : 'bg-gray-400'}
                          `} />
                          <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                            "{rule.pattern}"
                          </span>
                          <span className="text-gray-400">→</span>
                          {associatedTag && (
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{rule.tagName}</span>
                              <ExpenseTypeBadge type={associatedTag.expense_type} size="sm" />
                            </div>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 ml-6">
                          {rule.description}
                        </p>
                        {rule.matchCount !== undefined && rule.matchCount > 0 && (
                          <div className="text-xs text-purple-600 ml-6 mt-1">
                            {rule.matchCount} transaction(s) correspondante(s)
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        {/* Toggle actif/inactif */}
                        <button
                          onClick={() => handleToggleRule(rule.id)}
                          className={`
                            px-3 py-1 text-xs rounded-full border transition-colors
                            ${rule.isActive 
                              ? 'bg-green-100 border-green-300 text-green-700 hover:bg-green-200'
                              : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'
                            }
                          `}
                        >
                          {rule.isActive ? '✓ Active' : '○ Inactive'}
                        </button>

                        {/* Edit */}
                        <button
                          onClick={() => handleEditRule(rule)}
                          className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                          title="Modifier"
                        >
                          ✏️
                        </button>

                        {/* Delete */}
                        <button
                          onClick={() => handleDeleteRule(rule.id)}
                          className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                          title="Supprimer"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Actions globales */}
            <div className="flex justify-center gap-4 mt-6 pt-4 border-t border-gray-200">
              <Button variant="outline" size="sm">
                📥 Importer des règles
              </Button>
              <Button variant="outline" size="sm">
                📤 Exporter les règles
              </Button>
              <Button variant="outline" size="sm">
                🔄 Appliquer toutes les règles
              </Button>
            </div>
          </>
        )}
      </Card>

      {/* Modal de création/édition (placeholder pour l'instant) */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title={editingRule ? "Modifier la règle" : "Nouvelle règle"}
        size="lg"
      >
        <div className="space-y-4">
          <Alert variant="info">
            Interface de création/édition de règles en cours de développement.
            Les règles actuelles sont générées automatiquement à partir des libellés associés aux tags.
          </Alert>
          <div className="flex justify-end">
            <Button onClick={() => setIsCreateModalOpen(false)}>
              Fermer
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}