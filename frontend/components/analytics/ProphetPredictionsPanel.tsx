'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Button, LoadingSpinner, Alert } from '../ui';
import { predictionsApi, BudgetPrediction, PredictionsOverview } from '../../lib/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, ErrorBar, Legend, ComposedChart, Area
} from 'recharts';

interface ProphetPredictionsPanelProps {
  month?: string;
  compact?: boolean;
}

export function ProphetPredictionsPanel({ month: propMonth, compact = false }: ProphetPredictionsPanelProps) {
  const [currentMonth, setCurrentMonth] = useState(
    propMonth || new Date().toISOString().slice(0, 7)
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [predictions, setPredictions] = useState<BudgetPrediction[]>([]);
  const [summary, setSummary] = useState<PredictionsOverview['summary'] | null>(null);

  const loadPredictions = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const data = await predictionsApi.getOverview(currentMonth);
      setPredictions(data.predictions);
      setSummary(data.summary);
    } catch (err: any) {
      console.error('Erreur chargement predictions:', err);
      setError('Erreur lors du chargement des predictions');
    } finally {
      setLoading(false);
    }
  }, [currentMonth]);

  useEffect(() => {
    loadPredictions();
  }, [loadPredictions]);

  // Prepare chart data with confidence intervals
  const chartData = predictions
    .slice(0, compact ? 5 : 10)
    .map(p => ({
      name: p.category.charAt(0).toUpperCase() + p.category.slice(1),
      category: p.category,
      current: p.current_spent,
      predicted: p.predicted_month_end,
      lower: p.confidence_lower,
      upper: p.confidence_upper,
      average: p.monthly_average,
      confidence: Math.round(p.confidence * 100),
      method: p.prediction_method,
      seasonality: p.seasonality_detected,
      trend: p.trend_direction,
      // For error bars
      errorLower: p.predicted_month_end - p.confidence_lower,
      errorUpper: p.confidence_upper - p.predicted_month_end,
    }));

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      case 'stable': return '➡️';
      default: return '❓';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing': return 'text-red-500';
      case 'decreasing': return 'text-green-500';
      case 'stable': return 'text-blue-500';
      default: return 'text-gray-500';
    }
  };

  const getMethodBadge = (method: string) => {
    if (method === 'prophet') {
      return (
        <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs rounded-full">
          Prophet
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded-full">
        Linear
      </span>
    );
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-center py-8">
          <LoadingSpinner text="Chargement des predictions Prophet..." />
        </div>
      </Card>
    );
  }

  if (compact) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🔮</span>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Predictions fin de mois
            </h3>
            {summary?.prediction_method === 'prophet' && (
              <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs rounded-full">
                Prophet AI
              </span>
            )}
          </div>
        </div>

        <div className="space-y-2">
          {predictions.slice(0, 5).map((pred, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
              <div className="flex items-center gap-2">
                <span className={getTrendColor(pred.trend_direction)}>
                  {getTrendIcon(pred.trend_direction)}
                </span>
                <span className="text-sm text-gray-900 dark:text-white capitalize">
                  {pred.category}
                </span>
                {pred.seasonality_detected && (
                  <span title="Saisonnalite detectee" className="text-xs">🌊</span>
                )}
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                  {pred.predicted_month_end.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </p>
                <p className="text-xs text-gray-500">
                  [{pred.confidence_lower.toFixed(0)} - {pred.confidence_upper.toFixed(0)}] EUR
                </p>
              </div>
            </div>
          ))}
        </div>

        {summary && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-between text-xs text-gray-500">
            <span>{summary.total_categories} categories</span>
            <span>
              {summary.prophet_categories || 0} avec Prophet
            </span>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🔮</span>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Predictions Prophet
              </h2>
              {summary?.prediction_method === 'prophet' && (
                <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-sm rounded-full">
                  Prophet AI actif
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Predictions de fin de mois avec intervalles de confiance (5%-95%)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="month"
              value={currentMonth}
              onChange={(e) => setCurrentMonth(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500"
            />
            <Button
              onClick={loadPredictions}
              variant="outline"
              className="flex items-center gap-2"
            >
              🔄 Actualiser
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="error" className="mb-4">
            {error}
          </Alert>
        )}

        {/* Summary stats */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20">
              <p className="text-sm text-purple-600 dark:text-purple-400">Methode</p>
              <p className="text-xl font-bold text-purple-700 dark:text-purple-300 capitalize">
                {summary.prediction_method || 'linear'}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <p className="text-sm text-blue-600 dark:text-blue-400">Categories analysees</p>
              <p className="text-xl font-bold text-blue-700 dark:text-blue-300">
                {summary.total_categories}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20">
              <p className="text-sm text-green-600 dark:text-green-400">Avec Prophet</p>
              <p className="text-xl font-bold text-green-700 dark:text-green-300">
                {summary.prophet_categories || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20">
              <p className="text-sm text-amber-600 dark:text-amber-400">A risque</p>
              <p className="text-xl font-bold text-amber-700 dark:text-amber-300">
                {summary.at_risk_count}
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Chart with confidence intervals */}
      {chartData.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Predictions avec intervalles de confiance
          </h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} layout="vertical" margin={{ left: 100, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `${v}EUR`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={90} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                          <p className="font-semibold text-gray-900 dark:text-white">{data.name}</p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Actuel: {data.current.toFixed(0)}EUR
                          </p>
                          <p className="text-sm text-purple-600">
                            Predit: {data.predicted.toFixed(0)}EUR
                          </p>
                          <p className="text-xs text-gray-500">
                            Intervalle: [{data.lower.toFixed(0)} - {data.upper.toFixed(0)}]EUR
                          </p>
                          <p className="text-xs text-gray-500">
                            Confiance: {data.confidence}%
                          </p>
                          {data.seasonality && (
                            <p className="text-xs text-blue-500 mt-1">
                              🌊 Saisonnalite detectee
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend />
                {/* Confidence interval as area */}
                <Bar dataKey="current" fill="#94A3B8" name="Actuel" radius={[0, 4, 4, 0]} />
                <Bar dataKey="predicted" fill="#8B5CF6" name="Predit (fin mois)" radius={[0, 4, 4, 0]}>
                  <ErrorBar
                    dataKey={(entry: any) => [entry.errorLower, entry.errorUpper]}
                    stroke="#8B5CF6"
                    strokeWidth={2}
                    width={4}
                  />
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-500 text-center mt-2">
            Les barres d'erreur representent l'intervalle de confiance a 90% (5e-95e percentile)
          </p>
        </Card>
      )}

      {/* Detailed predictions list */}
      {predictions.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Detail des predictions ({predictions.length})
          </h3>
          <div className="space-y-3">
            {predictions.map((pred, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  pred.trend_direction === 'increasing'
                    ? 'border-red-200 bg-red-50 dark:bg-red-900/10'
                    : pred.trend_direction === 'decreasing'
                    ? 'border-green-200 bg-green-50 dark:bg-green-900/10'
                    : 'border-gray-200 bg-gray-50 dark:bg-gray-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-xl ${getTrendColor(pred.trend_direction)}`}>
                      {getTrendIcon(pred.trend_direction)}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                          {pred.category}
                        </h4>
                        {getMethodBadge(pred.prediction_method)}
                        {pred.seasonality_detected && (
                          <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded-full">
                            🌊 Saisonnier
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {pred.recommendation}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Actuel</p>
                      <p className="font-semibold text-gray-700 dark:text-gray-300">
                        {pred.current_spent.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Predit</p>
                      <p className="font-bold text-purple-600">
                        {pred.predicted_month_end.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </p>
                      <p className="text-xs text-gray-500">
                        [{pred.confidence_lower.toFixed(0)} - {pred.confidence_upper.toFixed(0)}]
                      </p>
                    </div>
                    <div className="text-right min-w-[80px]">
                      <p className="text-sm text-gray-500">Confiance</p>
                      <div className="flex items-center gap-1">
                        <div className="w-16 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full"
                            style={{ width: `${pred.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-purple-600">
                          {Math.round(pred.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Additional info */}
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center gap-4 text-xs text-gray-500">
                  <span>Moyenne: {pred.monthly_average.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</span>
                  {pred.mae_score > 0 && (
                    <span>MAE: {pred.mae_score.toFixed(0)}EUR</span>
                  )}
                  {pred.seasonal_component !== 0 && (
                    <span>
                      Impact saisonnier: {pred.seasonal_component > 0 ? '+' : ''}{(pred.seasonal_component * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Empty state */}
      {predictions.length === 0 && !error && (
        <Card className="p-6 text-center">
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Pas assez de donnees
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Prophet necessite au moins 6 mois d'historique pour generer des predictions fiables.
          </p>
        </Card>
      )}
    </div>
  );
}
