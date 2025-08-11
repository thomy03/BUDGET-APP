'use client';

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card } from '../ui';
import { api } from '../../lib/api';

interface MonthlyTrend {
  month: string;
  total_expenses: number;
  total_income: number;
  net: number;
  transaction_count: number;
}

interface TrendsChartProps {
  period?: string;
  height?: number;
  className?: string;
}

export function TrendsChart({ period = "last6", height = 400, className = "" }: TrendsChartProps) {
  const [trendsData, setTrendsData] = useState<MonthlyTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const loadTrends = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await api.get(`/analytics/trends?months=${period}`);
        setTrendsData(response.data);
      } catch (err: any) {
        console.error('Erreur chargement tendances:', err);
        setError(err.response?.data?.detail || "Erreur lors du chargement des tendances");
      } finally {
        setLoading(false);
      }
    };

    loadTrends();
  }, [period]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(Math.abs(value));
  };

  const formatMonth = (month: string) => {
    const [year, monthNum] = month.split('-');
    const monthNames = [
      'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
      'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'
    ];
    if (!year || !monthNum) return month; // Fallback si format invalide
    return `${monthNames[parseInt(monthNum) - 1] || monthNum} ${year.slice(2)}`;
  };

  // Transformation des données pour le graphique
  const chartData = trendsData.map(trend => ({
    month: formatMonth(trend.month),
    'Dépenses': Math.abs(trend.total_expenses),
    'Revenus': trend.total_income,
    'Net': trend.net,
    'Transactions': trend.transaction_count
  }));

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
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

  if (!chartData.length) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Tendances Mensuelles</h3>
        <div className="text-center py-8 text-gray-500">
          <p>Aucune donnée disponible pour cette période</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Tendances Mensuelles</h3>
        <p className="text-sm text-gray-600">
          Évolution des revenus, dépenses et solde net sur {trendsData.length} mois
        </p>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{
              top: 5,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="month" 
              stroke="#666"
              fontSize={12}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tickFormatter={formatCurrency}
            />
            <Tooltip 
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name
              ]}
              labelFormatter={(label) => `Mois: ${label}`}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="Revenus" 
              stroke="#10b981" 
              strokeWidth={3}
              dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line 
              type="monotone" 
              dataKey="Dépenses" 
              stroke="#ef4444" 
              strokeWidth={3}
              dot={{ fill: '#ef4444', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line 
              type="monotone" 
              dataKey="Net" 
              stroke="#3b82f6" 
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Résumé en bas */}
      <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
        <div className="text-center">
          <div className="text-sm text-gray-600">Revenus Moyens</div>
          <div className="text-lg font-semibold text-green-600">
            {formatCurrency(chartData.reduce((sum, d) => sum + d.Revenus, 0) / chartData.length)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">Dépenses Moyennes</div>
          <div className="text-lg font-semibold text-red-600">
            {formatCurrency(chartData.reduce((sum, d) => sum + d.Dépenses, 0) / chartData.length)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-600">Solde Moyen</div>
          <div className={`text-lg font-semibold ${
            chartData.reduce((sum, d) => sum + d.Net, 0) / chartData.length >= 0 
              ? 'text-blue-600' : 'text-orange-600'
          }`}>
            {formatCurrency(chartData.reduce((sum, d) => sum + d.Net, 0) / chartData.length)}
          </div>
        </div>
      </div>
    </Card>
  );
}

export default TrendsChart;