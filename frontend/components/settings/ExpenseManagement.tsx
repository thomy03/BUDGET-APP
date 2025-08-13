'use client';

import { useState, useEffect } from 'react';
import { ConfigOut } from '../../lib/api';
import FixedExpenses from '../FixedExpenses';
import { Card, LoadingSpinner } from '../ui';
import { api } from '../../lib/api';

interface ExpenseManagementProps {
  config?: ConfigOut;
  onDataChange?: () => void;
}

interface TagStats {
  tag: string;
  count: number;
  total_amount: number;
  is_fixed: boolean;
  is_variable: boolean;
  ai_generated: boolean;
}

export function ExpenseManagement({ config, onDataChange }: ExpenseManagementProps) {
  const [tagStats, setTagStats] = useState<TagStats[]>([]);
  const [loadingTags, setLoadingTags] = useState(true);

  useEffect(() => {
    loadTagStats();
  }, []);

  const loadTagStats = async () => {
    try {
      setLoadingTags(true);
      const response = await api.get('/tags/stats');
      setTagStats(response.data.tags || []);
    } catch (error) {
      console.error('Erreur chargement tags:', error);
    } finally {
      setLoadingTags(false);
    }
  };

  const fixedTags = tagStats.filter(t => t.is_fixed);
  const variableTags = tagStats.filter(t => t.is_variable);
  const aiGeneratedTags = tagStats.filter(t => t.ai_generated);
  const customTags = tagStats.filter(t => !t.ai_generated);

  return (
    <div className="space-y-8">
      {/* Dépenses Fixes */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">💳</span>
              Dépenses Fixes Récurrentes
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Gérez vos dépenses récurrentes automatiques (loyer, abonnements, assurances, etc.)
            </p>
          </div>
          <FixedExpenses config={config} onDataChange={onDataChange} />
        </div>
      </Card>

      {/* Classification des Dépenses */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">📊</span>
              Classification des Dépenses
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Vue d'ensemble de vos dépenses classées par type et origine
            </p>
          </div>
          
          {loadingTags ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="Chargement des classifications..." />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Dépenses Fixes vs Variables */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-800">Par Type</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">🔒</span>
                      <span className="font-medium">Dépenses Fixes</span>
                    </div>
                    <span className="text-sm text-gray-600">{fixedTags.length} catégories</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="text-green-600">📈</span>
                      <span className="font-medium">Dépenses Variables</span>
                    </div>
                    <span className="text-sm text-gray-600">{variableTags.length} catégories</span>
                  </div>
                </div>
              </div>

              {/* IA vs Personnalisés */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-800">Par Origine</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="text-purple-600">🤖</span>
                      <span className="font-medium">Tags IA</span>
                    </div>
                    <span className="text-sm text-gray-600">{aiGeneratedTags.length} tags</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-orange-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="text-orange-600">✏️</span>
                      <span className="font-medium">Tags Personnalisés</span>
                    </div>
                    <span className="text-sm text-gray-600">{customTags.length} tags</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Tags Personnalisables */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="text-xl font-semibold text-gray-900 flex items-center">
              <span className="mr-2">🏷️</span>
              Tags et Catégories
            </h3>
            <p className="text-gray-600 text-sm mt-1">
              Personnalisez les catégories et l'apprentissage de l'IA
            </p>
          </div>
          
          <div className="text-center py-6">
            <p className="text-gray-600 mb-4">
              Pour gérer vos tags et catégories, utilisez l'onglet <strong>"Tags & Catégories"</strong>
            </p>
            <p className="text-sm text-gray-500">
              L'IA apprend de vos corrections pour améliorer la catégorisation automatique
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}