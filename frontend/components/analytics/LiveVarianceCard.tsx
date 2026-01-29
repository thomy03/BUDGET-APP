'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { varianceApi, aiApi, categoryBudgetsApi } from '@/lib/api';

interface LiveVarianceCardProps {
  month: string;
  className?: string;
}

interface VarianceData {
  category: string;
  budget: number;
  actual: number;
  variance: number;
  variancePct: number;
}

export function LiveVarianceCard({ month, className = '' }: LiveVarianceCardProps) {
  const [variances, setVariances] = useState<VarianceData[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Calculate overall status
  const overallStatus = variances.length > 0
    ? variances.filter(v => v.variance > 0).length > variances.length / 2
      ? 'over'
      : variances.filter(v => v.variance < 0).length > variances.length / 2
        ? 'under'
        : 'on-track'
    : 'unknown';

  // Load variance data
  const loadVarianceData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Get budgets and actuals
      const [budgetsResponse, varianceResponse] = await Promise.all([
        categoryBudgetsApi.getAll(month, true).catch(() => []),
        varianceApi.analyze(month).catch(() => ({ variances: [] }))
      ]);

      if (varianceResponse?.variances && Array.isArray(varianceResponse.variances)) {
        const processedVariances = varianceResponse.variances.map((v: any) => ({
          category: v.category || v.tag || 'Autre',
          budget: v.budget || v.budget_amount || 0,
          actual: v.actual || v.spent || 0,
          variance: (v.actual || v.spent || 0) - (v.budget || v.budget_amount || 0),
          variancePct: v.budget > 0 ? (((v.actual || v.spent) - v.budget) / v.budget) * 100 : 0
        }));

        setVariances(processedVariances);
      } else if (budgetsResponse && budgetsResponse.length > 0) {
        // Fallback: Calculate from budgets directly
        setVariances(budgetsResponse.map((b: any) => ({
          category: b.category,
          budget: b.budget_amount,
          actual: 0, // Would need to calculate from transactions
          variance: 0,
          variancePct: 0
        })));
      }
    } catch (err) {
      console.error('Failed to load variance data:', err);
      setError('Impossible de charger les données');
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    loadVarianceData();
  }, [loadVarianceData]);

  // Get AI explanation
  const getAIExplanation = async () => {
    try {
      setLoadingExplanation(true);
      const response = await aiApi.explainVariance(month);
      setExplanation(response.explanation || response.analysis || 'Aucune explication disponible.');
    } catch (err) {
      console.error('Failed to get AI explanation:', err);
      setExplanation('Impossible d\'obtenir une explication IA pour le moment.');
    } finally {
      setLoadingExplanation(false);
    }
  };

  // Get status icon and color
  const getStatusDisplay = () => {
    switch (overallStatus) {
      case 'over':
        return { icon: '⚠️', color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20', label: 'Attention' };
      case 'under':
        return { icon: '✨', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20', label: 'Sous budget' };
      case 'on-track':
        return { icon: '👍', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20', label: 'Dans les clous' };
      default:
        return { icon: '📊', color: 'text-gray-500', bg: 'bg-gray-50 dark:bg-gray-800', label: 'Inconnu' };
    }
  };

  const status = getStatusDisplay();

  if (loading) {
    return (
      <div className={`rounded-xl p-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-xl p-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 ${className}`}>
        <p className="text-gray-500 dark:text-gray-400 text-center">{error}</p>
      </div>
    );
  }

  // Calculate totals
  const totalBudget = variances.reduce((sum, v) => sum + v.budget, 0);
  const totalActual = variances.reduce((sum, v) => sum + v.actual, 0);
  const totalVariance = totalActual - totalBudget;
  const totalVariancePct = totalBudget > 0 ? (totalVariance / totalBudget) * 100 : 0;

  return (
    <div className={`rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <span>📈</span> Variation Budget
          </h3>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
            {status.icon} {status.label}
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Budget total</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {totalBudget.toFixed(0)}€
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">Dépensé</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {totalActual.toFixed(0)}€
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 dark:text-gray-400">Écart</p>
            <p className={`text-lg font-semibold ${totalVariance > 0 ? 'text-red-500' : 'text-green-500'}`}>
              {totalVariance > 0 ? '+' : ''}{totalVariance.toFixed(0)}€
              <span className="text-sm ml-1">({totalVariancePct > 0 ? '+' : ''}{totalVariancePct.toFixed(0)}%)</span>
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              totalVariancePct > 0 ? 'bg-red-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(100, Math.abs((totalActual / totalBudget) * 100))}%` }}
          />
        </div>

        {/* Top variances */}
        {variances.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              Principales variations
            </p>
            {variances
              .sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance))
              .slice(0, 3)
              .map((v, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300 capitalize">{v.category}</span>
                  <span className={v.variance > 0 ? 'text-red-500' : 'text-green-500'}>
                    {v.variance > 0 ? '+' : ''}{v.variance.toFixed(0)}€
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* AI Explanation */}
      {explanation && (
        <div className="px-5 py-3 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-100 dark:border-blue-800">
          <div className="flex items-start gap-2">
            <span className="text-lg">🤖</span>
            <p className="text-sm text-blue-700 dark:text-blue-300">{explanation}</p>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <button
          onClick={getAIExplanation}
          disabled={loadingExplanation}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors disabled:opacity-50 flex items-center gap-1"
        >
          {loadingExplanation ? (
            <>
              <span className="animate-spin">⏳</span>
              Analyse en cours...
            </>
          ) : (
            <>
              <span>💡</span>
              {explanation ? 'Actualiser l\'explication' : 'Expliquer avec IA'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default LiveVarianceCard;
