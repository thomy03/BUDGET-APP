'use client';

import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card } from '../ui';
import { api } from '../../lib/api';

interface SpendingPattern {
  day_of_week: number;
  day_name: string;
  avg_amount: number;
  transaction_count: number;
}

interface SpendingPatternsProps {
  period?: string;
  className?: string;
}

export function SpendingPatterns({ period = "last3", className = "" }: SpendingPatternsProps) {
  const [patterns, setPatterns] = useState<SpendingPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const loadPatterns = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await api.get(`/analytics/patterns?months=${period}`);
        setPatterns(response.data);
      } catch (err: any) {
        console.error('Erreur chargement patterns:', err);
        setError(err.response?.data?.detail || "Erreur lors du chargement des patterns");
      } finally {
        setLoading(false);
      }
    };

    loadPatterns();
  }, [period]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getDayIcon = (dayName: string) => {
    const icons = {
      'Lundi': '💼',
      'Mardi': '💼', 
      'Mercredi': '💼',
      'Jeudi': '💼',
      'Vendredi': '💼',
      'Samedi': '🛍️',
      'Dimanche': '🏠'
    };
    return icons[dayName as keyof typeof icons] || '📅';
  };

  const getBestDay = () => {
    if (!patterns.length) return null;
    return patterns.reduce((prev, current) => 
      prev.avg_amount < current.avg_amount ? prev : current
    );
  };

  const getWorstDay = () => {
    if (!patterns.length) return null;
    return patterns.reduce((prev, current) => 
      prev.avg_amount > current.avg_amount ? prev : current
    );
  };

  const getMostActiveDay = () => {
    if (!patterns.length) return null;
    return patterns.reduce((prev, current) => 
      prev.transaction_count > current.transaction_count ? prev : current
    );
  };

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-80 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 border-red-200 bg-red-50 ${className}`}>
        <h3 className="text-lg font-semibold text-red-900 mb-2">Erreur</h3>
        <p className="text-red-600">{error}</p>
      </Card>
    );
  }

  if (!patterns.length) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Patterns de Dépense par Jour</h3>
        <div className="text-center py-8 text-gray-500">
          <p>Aucune donnée disponible pour cette période</p>
        </div>
      </Card>
    );
  }

  // Transformation des données pour le graphique
  const chartData = patterns.map(pattern => ({
    ...pattern,
    day: pattern.day_name.substring(0, 3), // Abréger les noms des jours
    amount: Math.abs(pattern.avg_amount)
  }));

  const bestDay = getBestDay();
  const worstDay = getWorstDay();
  const mostActiveDay = getMostActiveDay();

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Patterns de Dépense par Jour</h3>
        <p className="text-sm text-gray-600">
          Analyse des habitudes de dépense par jour de la semaine sur {period.replace('last', '')} derniers mois
        </p>
      </div>

      {/* Graphique en barres */}
      <div className="h-80 mb-6">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="day" 
              stroke="#666"
              fontSize={12}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tickFormatter={formatCurrency}
            />
            <Tooltip 
              formatter={(value: number, name: string) => {
                if (name === 'amount') return [formatCurrency(value), 'Dépense Moyenne'];
                if (name === 'transaction_count') return [value, 'Nb Transactions'];
                return [value, name];
              }}
              labelFormatter={(label) => {
                const fullDay = patterns.find(p => p.day_name.startsWith(label))?.day_name;
                return `${getDayIcon(fullDay || '')} ${fullDay}`;
              }}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
            <Bar 
              dataKey="amount" 
              fill="#3b82f6" 
              name="Dépense Moyenne"
              radius={[4, 4, 0, 0]}
            />
            <Bar 
              dataKey="transaction_count" 
              fill="#10b981" 
              name="Nb Transactions"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Résumé des patterns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200">
        {bestDay && (
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">{getDayIcon(bestDay.day_name)}</span>
              <h4 className="font-semibold text-green-800">Jour le plus économe</h4>
            </div>
            <p className="text-green-900 font-bold">{bestDay.day_name}</p>
            <p className="text-sm text-green-700">
              {formatCurrency(bestDay.avg_amount)} • {bestDay.transaction_count} transactions
            </p>
          </div>
        )}

        {worstDay && (
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">{getDayIcon(worstDay.day_name)}</span>
              <h4 className="font-semibold text-red-800">Jour le plus dépensier</h4>
            </div>
            <p className="text-red-900 font-bold">{worstDay.day_name}</p>
            <p className="text-sm text-red-700">
              {formatCurrency(worstDay.avg_amount)} • {worstDay.transaction_count} transactions
            </p>
          </div>
        )}

        {mostActiveDay && (
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-2">{getDayIcon(mostActiveDay.day_name)}</span>
              <h4 className="font-semibold text-blue-800">Jour le plus actif</h4>
            </div>
            <p className="text-blue-900 font-bold">{mostActiveDay.day_name}</p>
            <p className="text-sm text-blue-700">
              {mostActiveDay.transaction_count} transactions • {formatCurrency(mostActiveDay.avg_amount)}
            </p>
          </div>
        )}
      </div>

      {/* Tableau détaillé */}
      <div className="mt-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Détail par jour de la semaine</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 font-medium text-gray-600">Jour</th>
                <th className="text-right py-2 px-3 font-medium text-gray-600">Dépense Moyenne</th>
                <th className="text-right py-2 px-3 font-medium text-gray-600">Transactions</th>
                <th className="text-right py-2 px-3 font-medium text-gray-600">Total Estimé</th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((pattern) => (
                <tr key={pattern.day_of_week} className="border-b border-gray-100">
                  <td className="py-2 px-3 flex items-center">
                    <span className="text-lg mr-2">{getDayIcon(pattern.day_name)}</span>
                    <span className="font-medium">{pattern.day_name}</span>
                  </td>
                  <td className="text-right py-2 px-3 font-mono">
                    {formatCurrency(pattern.avg_amount)}
                  </td>
                  <td className="text-right py-2 px-3 text-gray-600">
                    {pattern.transaction_count}
                  </td>
                  <td className="text-right py-2 px-3 font-mono font-semibold">
                    {formatCurrency(pattern.avg_amount * pattern.transaction_count)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Insights et conseils */}
      <div className="mt-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
        <h4 className="font-semibold text-amber-800 mb-2">💡 Insights</h4>
        <div className="text-sm text-amber-700 space-y-1">
          <p>
            • Vos dépenses sont {worstDay && bestDay && worstDay.avg_amount > bestDay.avg_amount * 1.5 ? 'très variables' : 'assez stables'} selon les jours de la semaine
          </p>
          <p>
            • Le {worstDay?.day_name} est votre jour de dépense le plus élevé avec {worstDay && formatCurrency(worstDay.avg_amount)}
          </p>
          <p>
            • Vous êtes le plus actif financièrement le {mostActiveDay?.day_name} avec {mostActiveDay?.transaction_count} transactions en moyenne
          </p>
        </div>
      </div>
    </Card>
  );
}

export default SpendingPatterns;