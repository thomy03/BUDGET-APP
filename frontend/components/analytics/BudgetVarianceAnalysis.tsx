'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Button, LoadingSpinner, Alert } from '../ui';
import { varianceApi, aiApi, CategoryVariance, GlobalVariance } from '../../lib/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, Legend
} from 'recharts';

interface BudgetVarianceAnalysisProps {
  month?: string;
}

export function BudgetVarianceAnalysis({ month: propMonth }: BudgetVarianceAnalysisProps) {
  const [currentMonth, setCurrentMonth] = useState(
    propMonth || new Date().toISOString().slice(0, 7)
  );
  const [loading, setLoading] = useState(true);
  const [loadingAI, setLoadingAI] = useState(false);
  const [error, setError] = useState('');
  const [globalVariance, setGlobalVariance] = useState<GlobalVariance | null>(null);
  const [categoryVariances, setCategoryVariances] = useState<CategoryVariance[]>([]);
  const [aiExplanation, setAiExplanation] = useState('');
  const [aiModelUsed, setAiModelUsed] = useState('');

  const loadVarianceData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const data = await varianceApi.analyze(currentMonth);
      setGlobalVariance(data.global_variance);
      setCategoryVariances(data.by_category);
    } catch (err: any) {
      console.error('Erreur chargement variance:', err);
      if (err.response?.status === 404) {
        setError('Aucun budget defini pour ce mois. Configurez vos budgets dans les parametres.');
      } else {
        setError('Erreur lors du chargement de l\'analyse');
      }
    } finally {
      setLoading(false);
    }
  }, [currentMonth]);

  useEffect(() => {
    loadVarianceData();
  }, [loadVarianceData]);

  const handleGetAIExplanation = async () => {
    try {
      setLoadingAI(true);
      setError('');
      const response = await aiApi.explainVariance(currentMonth);
      setAiExplanation(response.explanation);
      setAiModelUsed(response.model_used);
    } catch (err: any) {
      console.error('Erreur IA:', err);
      if (err.response?.status === 503) {
        setError('Service IA non configure. Ajoutez OPENROUTER_API_KEY dans le .env');
      } else {
        setError('Erreur lors de la generation de l\'explication IA');
      }
    } finally {
      setLoadingAI(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_budget': return '#10B981'; // vert
      case 'under_budget': return '#3B82F6'; // bleu
      case 'over_budget': return '#EF4444'; // rouge
      default: return '#6B7280'; // gris
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'on_budget': return 'Dans le budget';
      case 'under_budget': return 'Sous le budget';
      case 'over_budget': return 'Depassement';
      case 'no_budget': return 'Pas de budget';
      default: return status;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'on_budget': return '✅';
      case 'under_budget': return '💰';
      case 'over_budget': return '⚠️';
      default: return '❓';
    }
  };

  // Donnees pour le graphique
  const chartData = categoryVariances
    .filter(cv => cv.budgeted > 0) // Uniquement celles avec budget
    .slice(0, 10) // Top 10
    .map(cv => ({
      name: cv.category.charAt(0).toUpperCase() + cv.category.slice(1),
      budget: cv.budgeted,
      reel: cv.actual,
      ecart: cv.variance,
      status: cv.status
    }));

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-center py-8">
          <LoadingSpinner text="Chargement de l'analyse des ecarts..." />
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header avec selection du mois */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              📊 Analyse Budget vs Reel
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Comparez vos depenses reelles avec vos objectifs budgetaires
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="month"
              value={currentMonth}
              onChange={(e) => setCurrentMonth(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
            <Button
              onClick={loadVarianceData}
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

        {/* Resume global */}
        {globalVariance && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <p className="text-sm text-blue-600 dark:text-blue-400">Budget prevu</p>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {globalVariance.budgeted.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
              <p className="text-sm text-gray-600 dark:text-gray-400">Depenses reelles</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {globalVariance.actual.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </p>
            </div>
            <div className={`p-4 rounded-lg ${
              globalVariance.variance > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'
            }`}>
              <p className={`text-sm ${globalVariance.variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                Ecart
              </p>
              <p className={`text-2xl font-bold ${globalVariance.variance > 0 ? 'text-red-700' : 'text-green-700'}`}>
                {globalVariance.variance > 0 ? '+' : ''}
                {globalVariance.variance.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </p>
              <p className={`text-sm ${globalVariance.variance > 0 ? 'text-red-500' : 'text-green-500'}`}>
                ({globalVariance.variance_pct > 0 ? '+' : ''}{globalVariance.variance_pct.toFixed(1)}%)
              </p>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: getStatusColor(globalVariance.status) + '20' }}>
              <p className="text-sm text-gray-600 dark:text-gray-400">Statut global</p>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getStatusIcon(globalVariance.status)}</span>
                <span className="font-bold" style={{ color: getStatusColor(globalVariance.status) }}>
                  {getStatusLabel(globalVariance.status)}
                </span>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Explication IA */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            🤖 Analyse IA
          </h3>
          <Button
            onClick={handleGetAIExplanation}
            disabled={loadingAI || !globalVariance}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            {loadingAI ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Analyse en cours...
              </>
            ) : (
              '✨ Generer une analyse IA'
            )}
          </Button>
        </div>

        {aiExplanation ? (
          <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <div className="prose dark:prose-invert max-w-none">
              <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {aiExplanation}
              </p>
            </div>
            {aiModelUsed && (
              <p className="text-xs text-gray-500 mt-3">
                Genere par {aiModelUsed}
              </p>
            )}
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">
            Cliquez sur le bouton pour generer une analyse intelligente de vos ecarts budgetaires.
          </p>
        )}
      </Card>

      {/* Graphique comparatif */}
      {chartData.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Budget vs Reel par categorie
          </h3>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `${v}€`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }),
                    name === 'budget' ? 'Budget' : 'Reel'
                  ]}
                />
                <Legend />
                <Bar dataKey="budget" fill="#3B82F6" name="Budget" radius={[0, 4, 4, 0]} />
                <Bar dataKey="reel" name="Reel" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getStatusColor(entry.status)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Detail par categorie */}
      {categoryVariances.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Detail par categorie ({categoryVariances.length})
          </h3>
          <div className="space-y-3">
            {categoryVariances.map((cv, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  cv.status === 'over_budget'
                    ? 'border-red-200 bg-red-50 dark:bg-red-900/10'
                    : cv.status === 'under_budget'
                    ? 'border-blue-200 bg-blue-50 dark:bg-blue-900/10'
                    : 'border-gray-200 bg-gray-50 dark:bg-gray-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{getStatusIcon(cv.status)}</span>
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                        {cv.category}
                      </h4>
                      {cv.vs_last_month && (
                        <p className="text-xs text-gray-500">
                          vs mois precedent: {cv.vs_last_month}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Budget</p>
                      <p className="font-semibold text-blue-600">
                        {cv.budgeted.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500">Reel</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {cv.actual.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </p>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <p className="text-sm text-gray-500">Ecart</p>
                      <p className={`font-bold ${cv.variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {cv.variance > 0 ? '+' : ''}
                        {cv.variance.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </p>
                      <p className={`text-xs ${cv.variance > 0 ? 'text-red-500' : 'text-green-500'}`}>
                        ({cv.variance_pct > 0 ? '+' : ''}{cv.variance_pct.toFixed(1)}%)
                      </p>
                    </div>
                  </div>
                </div>

                {/* Barre de progression */}
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>0€</span>
                    <span>Budget: {cv.budgeted.toFixed(0)}€</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3 overflow-hidden">
                    <div
                      className="h-3 rounded-full transition-all"
                      style={{
                        width: `${Math.min((cv.actual / cv.budgeted) * 100, 150)}%`,
                        backgroundColor: getStatusColor(cv.status)
                      }}
                    />
                  </div>
                  {cv.actual > cv.budgeted && (
                    <p className="text-xs text-red-500 mt-1">
                      Depassement de {((cv.actual / cv.budgeted - 1) * 100).toFixed(0)}%
                    </p>
                  )}
                </div>

                {/* Top transactions */}
                {cv.top_transactions && cv.top_transactions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 mb-2">Top transactions:</p>
                    <div className="space-y-1">
                      {cv.top_transactions.slice(0, 3).map((tx: any, txIdx: number) => (
                        <div key={txIdx} className="flex justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
                            {tx.label}
                          </span>
                          <span className="font-mono text-gray-900 dark:text-white">
                            {Math.abs(tx.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Message si pas de budgets */}
      {categoryVariances.length === 0 && !error && (
        <Card className="p-6 text-center">
          <div className="text-4xl mb-4">📝</div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Aucun budget configure
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Definissez des objectifs de budget par categorie pour voir l'analyse des ecarts.
          </p>
          <Button
            onClick={() => window.location.href = '/settings'}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Configurer mes budgets
          </Button>
        </Card>
      )}
    </div>
  );
}
