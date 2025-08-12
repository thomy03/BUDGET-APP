'use client';

import { useState, useEffect } from 'react';
import { Card } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { TagInfo } from '../../hooks/useTagsManagement';

interface TagsStatisticsProps {
  tags: TagInfo[];
  isLoading: boolean;
}

interface StatsSummary {
  totalTags: number;
  fixedTags: number;
  variableTags: number;
  totalTransactions: number;
  totalAmount: number;
  averageTransactionsPerTag: number;
  topTags: TagInfo[];
  unusedTags: TagInfo[];
}

export function TagsStatistics({ tags, isLoading }: TagsStatisticsProps) {
  const [stats, setStats] = useState<StatsSummary | null>(null);

  useEffect(() => {
    if (!tags.length) {
      setStats(null);
      return;
    }

    const totalTags = tags.length;
    const fixedTags = tags.filter(t => t.expense_type === 'fixed').length;
    const variableTags = tags.filter(t => t.expense_type === 'variable').length;
    const totalTransactions = tags.reduce((sum, tag) => sum + tag.transaction_count, 0);
    const totalAmount = tags.reduce((sum, tag) => sum + Math.abs(tag.total_amount), 0);
    const averageTransactionsPerTag = totalTransactions / totalTags;

    // Top 10 des tags les plus utilisés
    const topTags = [...tags]
      .sort((a, b) => b.transaction_count - a.transaction_count)
      .slice(0, 10);

    // Tags non utilisés
    const unusedTags = tags.filter(t => t.transaction_count === 0);

    setStats({
      totalTags,
      fixedTags,
      variableTags,
      totalTransactions,
      totalAmount,
      averageTransactionsPerTag,
      topTags,
      unusedTags
    });
  }, [tags]);

  if (isLoading) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Calcul des statistiques...</span>
        </div>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card padding="lg">
        <div className="text-center py-8">
          <div className="text-4xl mb-2">📊</div>
          <p className="text-gray-600">Aucune donnée disponible pour les statistiques</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Vue d'ensemble */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          📊 Vue d'ensemble
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{stats.totalTags}</div>
            <div className="text-sm text-gray-600">Tags total</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">{stats.fixedTags}</div>
            <div className="text-sm text-gray-600">Tags Fixes</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{stats.variableTags}</div>
            <div className="text-sm text-gray-600">Tags Variables</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">{stats.totalTransactions}</div>
            <div className="text-sm text-gray-600">Transactions</div>
          </div>
        </div>
      </Card>

      {/* Top tags */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          🏆 Top 10 des tags les plus utilisés
        </h3>
        <div className="space-y-3">
          {stats.topTags.map((tag, index) => (
            <div key={tag.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600 font-bold text-sm">
                  {index + 1}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{tag.name}</span>
                  <ExpenseTypeBadge type={tag.expense_type} size="sm" />
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>{tag.transaction_count} trans.</span>
                {tag.total_amount !== 0 && (
                  <span className="font-medium">
                    {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}€
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Répartition par type */}
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          📈 Répartition Fixe vs Variable
        </h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border-l-4 border-orange-400 bg-orange-50">
            <div className="flex items-center gap-2">
              <ExpenseTypeBadge type="fixed" size="sm" />
              <span className="font-medium">Dépenses Fixes</span>
            </div>
            <div className="text-right">
              <div className="font-bold text-orange-600">{stats.fixedTags} tags</div>
              <div className="text-sm text-gray-600">
                {((stats.fixedTags / stats.totalTags) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between p-4 border-l-4 border-green-400 bg-green-50">
            <div className="flex items-center gap-2">
              <ExpenseTypeBadge type="variable" size="sm" />
              <span className="font-medium">Dépenses Variables</span>
            </div>
            <div className="text-right">
              <div className="font-bold text-green-600">{stats.variableTags} tags</div>
              <div className="text-sm text-gray-600">
                {((stats.variableTags / stats.totalTags) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Tags non utilisés */}
      {stats.unusedTags.length > 0 && (
        <Card padding="lg">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            ⚠️ Tags non utilisés ({stats.unusedTags.length})
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Ces tags n'ont pas de transactions associées. Vous pouvez les supprimer ou ajouter des règles automatiques.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {stats.unusedTags.map((tag) => (
              <div key={tag.name} className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded">
                <span className="text-sm">{tag.name}</span>
                <ExpenseTypeBadge type={tag.expense_type} size="sm" />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}