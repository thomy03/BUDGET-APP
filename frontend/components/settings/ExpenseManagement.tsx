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
    <div className="space-y-6 xs:space-y-8">
      {/* Dépenses Fixes */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>💳</span>
              <span className="truncate">Dépenses Fixes Récurrentes</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Gérez vos dépenses récurrentes automatiques (loyer, abonnements, assurances, etc.)
            </p>
          </div>
          <FixedExpenses config={config} onDataChange={onDataChange} />
        </div>
      </Card>

      {/* Classification des Dépenses */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>📊</span>
              <span className="truncate">Classification des Dépenses</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Vue d'ensemble de vos dépenses classées par type et origine
            </p>
          </div>

          {loadingTags ? (
            <div className="flex justify-center py-6 xs:py-8">
              <LoadingSpinner text="Chargement des classifications..." />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 xs:gap-6">
              {/* Dépenses Fixes vs Variables */}
              <div className="space-y-3">
                <h4 className="text-sm xs:text-base font-medium text-gray-800">Par Type</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-2 xs:p-3 bg-blue-50 rounded-lg gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-blue-600 flex-shrink-0">🔒</span>
                      <span className="text-sm xs:text-base font-medium truncate">Dépenses Fixes</span>
                    </div>
                    <span className="text-xs xs:text-sm text-gray-600 flex-shrink-0">{fixedTags.length} catégories</span>
                  </div>
                  <div className="flex justify-between items-center p-2 xs:p-3 bg-green-50 rounded-lg gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-green-600 flex-shrink-0">📈</span>
                      <span className="text-sm xs:text-base font-medium truncate">Dépenses Variables</span>
                    </div>
                    <span className="text-xs xs:text-sm text-gray-600 flex-shrink-0">{variableTags.length} catégories</span>
                  </div>
                </div>
              </div>

              {/* IA vs Personnalisés */}
              <div className="space-y-3">
                <h4 className="text-sm xs:text-base font-medium text-gray-800">Par Origine</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-2 xs:p-3 bg-purple-50 rounded-lg gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-purple-600 flex-shrink-0">🤖</span>
                      <span className="text-sm xs:text-base font-medium truncate">Tags IA</span>
                    </div>
                    <span className="text-xs xs:text-sm text-gray-600 flex-shrink-0">{aiGeneratedTags.length} tags</span>
                  </div>
                  <div className="flex justify-between items-center p-2 xs:p-3 bg-orange-50 rounded-lg gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-orange-600 flex-shrink-0">✏️</span>
                      <span className="text-sm xs:text-base font-medium truncate">Tags Personnalisés</span>
                    </div>
                    <span className="text-xs xs:text-sm text-gray-600 flex-shrink-0">{customTags.length} tags</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Tags Personnalisables */}
      <Card className="p-3 xs:p-4 md:p-6">
        <div className="space-y-3 xs:space-y-4">
          <div className="border-b pb-2 xs:pb-3">
            <h3 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <span>🏷️</span>
              <span className="truncate">Tags et Catégories</span>
            </h3>
            <p className="text-gray-600 text-xs xs:text-sm mt-1 line-clamp-2">
              Personnalisez les catégories et l'apprentissage de l'IA
            </p>
          </div>

          <div className="text-center py-4 xs:py-6">
            <p className="text-gray-600 mb-3 xs:mb-4 text-sm xs:text-base px-3">
              Pour gérer vos tags et catégories, utilisez l'onglet <strong>"Tags & Catégories"</strong>
            </p>
            <p className="text-xs xs:text-sm text-gray-500 px-3">
              L'IA apprend de vos corrections pour améliorer la catégorisation automatique
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}