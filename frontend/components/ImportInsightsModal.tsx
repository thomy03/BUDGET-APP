'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { importAdvisorApi, ImportInsight, ImportAnomalyItem } from '@/lib/api';

interface ImportInsightsModalProps {
  importId: string;
  months: string[];
  isOpen: boolean;
  onClose: () => void;
}

export function ImportInsightsModal({
  importId,
  months,
  isOpen,
  onClose
}: ImportInsightsModalProps) {
  const router = useRouter();
  const [insights, setInsights] = useState<ImportInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollingCount, setPollingCount] = useState(0);

  // Poll for insights
  const fetchInsights = useCallback(async () => {
    if (!importId || months.length === 0) return;

    try {
      // First trigger analysis
      if (pollingCount === 0) {
        await importAdvisorApi.analyze(importId, months[0]);
      }

      // Then poll for results
      const result = await importAdvisorApi.getInsights(importId, months[0]);

      if (result.status === 'ready') {
        setInsights(result);
        setLoading(false);
      } else if (result.status === 'error') {
        setError('Erreur lors de l\'analyse');
        setLoading(false);
      } else {
        // Still processing, continue polling
        setPollingCount(prev => prev + 1);
      }
    } catch (err: any) {
      if (err?.response?.status === 202) {
        // Still processing
        setPollingCount(prev => prev + 1);
      } else {
        console.error('Failed to fetch insights:', err);
        setError('Impossible de charger l\'analyse');
        setLoading(false);
      }
    }
  }, [importId, months, pollingCount]);

  // Polling effect
  useEffect(() => {
    if (!isOpen || !loading) return;

    // Max 15 polling attempts (30 seconds)
    if (pollingCount >= 15) {
      setError('L\'analyse prend trop de temps. Réessayez plus tard.');
      setLoading(false);
      return;
    }

    const timer = setTimeout(fetchInsights, pollingCount === 0 ? 0 : 2000);
    return () => clearTimeout(timer);
  }, [isOpen, loading, pollingCount, fetchInsights]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setInsights(null);
      setLoading(true);
      setError(null);
      setPollingCount(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Severity badge styling
  const getSeverityStyle = (severity: ImportAnomalyItem['severity']) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
      case 'medium':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
      default:
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-500/10 to-purple-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🎯</span>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Analyse de votre import
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {months.length > 0 ? `Mois: ${months.join(', ')}` : 'Analyse en cours...'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-180px)]">
          {loading ? (
            <div className="py-12 text-center">
              <div className="animate-spin w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-300">Analyse en cours...</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                {pollingCount > 0 ? `Tentative ${pollingCount}/15` : 'Initialisation...'}
              </p>
            </div>
          ) : error ? (
            <div className="py-12 text-center">
              <span className="text-4xl mb-4 block">😔</span>
              <p className="text-gray-600 dark:text-gray-300">{error}</p>
              <button
                onClick={() => {
                  setLoading(true);
                  setError(null);
                  setPollingCount(0);
                }}
                className="mt-4 px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
              >
                Réessayer
              </button>
            </div>
          ) : insights ? (
            <div className="space-y-6">
              {/* Narrative Summary */}
              {insights.narrative && (
                <div className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800">
                  <p className="text-gray-700 dark:text-gray-200 leading-relaxed">
                    {insights.narrative}
                  </p>
                </div>
              )}

              {/* Summary Stats */}
              {insights.summary && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
                    <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {insights.summary.total_expenses.toFixed(0)}€
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Dépenses</p>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {insights.summary.total_income.toFixed(0)}€
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Revenus</p>
                  </div>
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
                    <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {insights.summary.transaction_count}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Transactions</p>
                  </div>
                </div>
              )}

              {/* Month Comparison */}
              {insights.comparison && insights.comparison.previous_total && (
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <span>📊</span> Comparaison avec le mois précédent
                  </h3>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Variation</p>
                      <p className={`text-lg font-bold ${
                        (insights.comparison.variance || 0) > 0
                          ? 'text-red-500'
                          : 'text-green-500'
                      }`}>
                        {(insights.comparison.variance || 0) > 0 ? '+' : ''}
                        {insights.comparison.variance?.toFixed(0)}€
                        <span className="text-sm ml-1">
                          ({(insights.comparison.variance_pct || 0) > 0 ? '+' : ''}
                          {insights.comparison.variance_pct?.toFixed(1)}%)
                        </span>
                      </p>
                    </div>
                    {insights.comparison.categories_increased.length > 0 && (
                      <div className="text-right">
                        <p className="text-xs text-gray-500 dark:text-gray-400">En hausse</p>
                        <p className="text-sm text-red-500">
                          {insights.comparison.categories_increased.slice(0, 2).join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Anomalies */}
              {insights.anomalies.length > 0 && (
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <span>⚠️</span> Points d'attention ({insights.anomalies.length})
                  </h3>
                  <div className="space-y-2">
                    {insights.anomalies.map((anomaly, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                      >
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${getSeverityStyle(anomaly.severity)}`}>
                          {anomaly.severity === 'high' ? 'Important' : anomaly.severity === 'medium' ? 'Moyen' : 'Info'}
                        </span>
                        <p className="text-sm text-gray-700 dark:text-gray-200 flex-1">
                          {anomaly.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {insights.recommendations.length > 0 && (
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <span>💡</span> Recommandations
                  </h3>
                  <ul className="space-y-2">
                    {insights.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-200">
                        <span className="text-indigo-500 mt-0.5">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Top Categories */}
              {insights.summary?.top_categories && Object.keys(insights.summary.top_categories).length > 0 && (
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                    <span>📈</span> Top catégories
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(insights.summary.top_categories)
                      .slice(0, 5)
                      .map(([cat, amount]) => (
                        <div key={cat} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-300 capitalize">{cat}</span>
                          <span className="font-medium text-gray-900 dark:text-white">
                            {(amount as number).toFixed(0)}€
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white transition-colors"
            >
              Fermer
            </button>
            <button
              onClick={() => {
                onClose();
                router.push('/transactions');
              }}
              className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
            >
              Voir les transactions
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImportInsightsModal;
