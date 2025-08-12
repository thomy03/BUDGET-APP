'use client';

import { useState, useEffect } from 'react';
import { Card, Button } from '../ui';
import { TagSourceBadge, TagSource } from '../ui/TagSourceBadge';
import { ConfidenceIndicator, ConfidenceStats } from '../ui/ConfidenceIndicator';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';

interface TagStats {
  totalTags: number;
  aiGeneratedTags: number;
  manualTags: number;
  modifiedTags: number;
  totalTransactions: number;
  averageConfidence: number;
  confidenceDistribution: {
    high: number;
    medium: number;
    low: number;
    total: number;
  };
  topUsedTags: Array<{
    name: string;
    count: number;
    source: TagSource;
    expenseType: 'fixed' | 'variable';
    confidence?: number;
  }>;
  recentActivity: Array<{
    date: string;
    action: 'created' | 'modified' | 'applied';
    tagName: string;
    source: TagSource;
  }>;
  accuracyRate: number;
  sourceDistribution: {
    ai_pattern: number;
    web_research: number;
    manual: number;
    modified: number;
  };
}

interface TagsStatsDashboardProps {
  className?: string;
}

export function TagsStatsDashboard({ className = '' }: TagsStatsDashboardProps) {
  const [stats, setStats] = useState<TagStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  // Load stats on mount
  useEffect(() => {
    loadStats();
  }, [refreshKey]);

  const loadStats = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      // Simulate API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Mock data - replace with actual API call
      const mockStats: TagStats = {
        totalTags: 47,
        aiGeneratedTags: 34,
        manualTags: 10,
        modifiedTags: 3,
        totalTransactions: 1248,
        averageConfidence: 0.84,
        confidenceDistribution: {
          high: 28,
          medium: 15,
          low: 4,
          total: 47
        },
        topUsedTags: [
          { name: 'streaming', count: 156, source: 'ai_pattern', expenseType: 'fixed', confidence: 0.92 },
          { name: 'alimentation', count: 134, source: 'web_research', expenseType: 'variable', confidence: 0.87 },
          { name: 'transport', count: 98, source: 'modified', expenseType: 'variable', confidence: 0.73 },
          { name: 'utilities', count: 87, source: 'ai_pattern', expenseType: 'fixed', confidence: 0.96 },
          { name: 'loisirs', count: 65, source: 'manual', expenseType: 'variable' }
        ],
        recentActivity: [
          { date: '2024-01-15', action: 'created', tagName: 'sport', source: 'ai_pattern' },
          { date: '2024-01-15', action: 'applied', tagName: 'streaming', source: 'ai_pattern' },
          { date: '2024-01-14', action: 'modified', tagName: 'transport', source: 'modified' },
          { date: '2024-01-14', action: 'created', tagName: 'pharmacie', source: 'web_research' }
        ],
        accuracyRate: 87,
        sourceDistribution: {
          ai_pattern: 23,
          web_research: 11,
          manual: 10,
          modified: 3
        }
      };
      
      setStats(mockStats);
      
    } catch (err) {
      setError('Erreur lors du chargement des statistiques');
      console.error('Load stats error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const refresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Chargement des statistiques...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center py-4">
          <span className="text-red-600 text-sm">{error}</span>
          <Button onClick={refresh} variant="outline" className="ml-3">
            Réessayer
          </Button>
        </div>
      </Card>
    );
  }

  if (!stats) return null;

  const getSourcePercentage = (count: number) => 
    Math.round((count / stats.totalTags) * 100);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <Card className="p-6 bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Vue d'ensemble des Tags
            </h2>
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                <span>{stats.totalTags} tags total</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span>{stats.totalTransactions} transactions</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                <span>{stats.accuracyRate}% de précision</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Time Range Selector */}
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
            >
              <option value="7d">7 derniers jours</option>
              <option value="30d">30 derniers jours</option>
              <option value="90d">90 derniers jours</option>
              <option value="all">Tout</option>
            </select>
            <Button onClick={refresh} variant="outline" size="sm">
              <span className="mr-2">🔄</span>
              Actualiser
            </Button>
          </div>
        </div>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Tags */}
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-lg">🏷️</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.totalTags}</div>
              <div className="text-sm text-gray-600">Tags total</div>
            </div>
          </div>
        </Card>

        {/* AI Generated */}
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              <span className="text-lg">🤖</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-emerald-600">{stats.aiGeneratedTags}</div>
              <div className="text-sm text-gray-600">Générés par IA</div>
            </div>
          </div>
        </Card>

        {/* Average Confidence */}
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <span className="text-lg">📊</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-gray-900">
                  {Math.round(stats.averageConfidence * 100)}%
                </span>
                <ConfidenceIndicator 
                  confidence={stats.averageConfidence} 
                  size="xs" 
                  variant="circle"
                  showPercentage={false}
                />
              </div>
              <div className="text-sm text-gray-600">Confiance moyenne</div>
            </div>
          </div>
        </Card>

        {/* Transactions Tagged */}
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <span className="text-lg">💳</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats.totalTransactions}</div>
              <div className="text-sm text-gray-600">Transactions</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Source Distribution */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Répartition par source</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(stats.sourceDistribution).map(([source, count]) => (
            <div key={source} className="text-center">
              <div className="mb-2">
                <TagSourceBadge 
                  source={source as TagSource} 
                  size="sm" 
                  showLabel={false}
                />
              </div>
              <div className="text-2xl font-bold text-gray-900">{count}</div>
              <div className="text-sm text-gray-600">{getSourcePercentage(count)}%</div>
              <div className="text-xs text-gray-500 capitalize">
                {source.replace('_', ' ')}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Confidence Distribution */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Distribution des niveaux de confiance</h3>
        <ConfidenceStats stats={stats.confidenceDistribution} />
      </Card>

      {/* Top Used Tags */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Tags les plus utilisés</h3>
        <div className="space-y-3">
          {stats.topUsedTags.map((tag, index) => (
            <div key={tag.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-bold text-blue-600">
                  {index + 1}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">{tag.name}</span>
                  <TagSourceBadge source={tag.source} size="xs" />
                  <ExpenseTypeBadge type={tag.expenseType} size="sm" />
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                {tag.confidence && (
                  <ConfidenceIndicator 
                    confidence={tag.confidence} 
                    size="xs" 
                    showPercentage={true}
                  />
                )}
                <div className="flex items-center gap-1">
                  <span>📊</span>
                  <span className="font-medium">{tag.count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent Activity */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Activité récente</h3>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => {
              // TODO: Navigate to full activity log
              console.log('Navigate to activity log');
            }}
          >
            Voir tout
          </Button>
        </div>
        <div className="space-y-3">
          {stats.recentActivity.map((activity, index) => (
            <div key={index} className="flex items-center gap-3 p-3 border-l-2 border-gray-200 bg-gray-50 rounded-r-lg hover:shadow-sm transition-all">
              <div className="text-sm text-gray-500">
                {new Date(activity.date).toLocaleDateString('fr-FR', {
                  day: 'numeric',
                  month: 'short'
                })}
              </div>
              <div className="flex items-center gap-2">
                {activity.action === 'created' && <span>✨</span>}
                {activity.action === 'modified' && <span>✏️</span>}
                {activity.action === 'applied' && <span>🎯</span>}
                <span className="text-sm capitalize text-gray-700">
                  {activity.action === 'created' && 'Créé'}
                  {activity.action === 'modified' && 'Modifié'}
                  {activity.action === 'applied' && 'Appliqué'}
                </span>
              </div>
              <span className="font-medium text-gray-900">{activity.tagName}</span>
              <TagSourceBadge source={activity.source} size="xs" />
            </div>
          ))}
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions rapides</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Button 
            variant="outline" 
            className="flex flex-col items-center gap-2 h-20 text-center"
            onClick={() => {
              // TODO: Trigger AI classification on all untagged transactions
              console.log('Run AI classification');
            }}
          >
            <span className="text-xl">🤖</span>
            <span className="text-sm">Classification IA</span>
          </Button>

          <Button 
            variant="outline" 
            className="flex flex-col items-center gap-2 h-20 text-center"
            onClick={() => {
              // TODO: Open tag merge dialog
              console.log('Open tag merge');
            }}
          >
            <span className="text-xl">🔗</span>
            <span className="text-sm">Fusionner tags</span>
          </Button>

          <Button 
            variant="outline" 
            className="flex flex-col items-center gap-2 h-20 text-center"
            onClick={() => {
              // TODO: Open bulk edit dialog
              console.log('Open bulk edit');
            }}
          >
            <span className="text-xl">✏️</span>
            <span className="text-sm">Édition groupée</span>
          </Button>

          <Button 
            variant="outline" 
            className="flex flex-col items-center gap-2 h-20 text-center"
            onClick={() => {
              // TODO: Export tags data
              console.log('Export tags');
            }}
          >
            <span className="text-xl">📁</span>
            <span className="text-sm">Exporter données</span>
          </Button>
        </div>
      </Card>
    </div>
  );
}