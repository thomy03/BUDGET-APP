'use client';

import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card } from '../ui';
import { api } from '../../lib/api';

interface CategoryData {
  category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
  avg_transaction: number;
}

interface CategoryChartProps {
  month: string;
  className?: string;
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', 
  '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6b7280'
];

export function CategoryChart({ month, className = "" }: CategoryChartProps) {
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const loadCategoryData = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await api.get(`/analytics/categories?month=${month}`);
        setCategoryData(response.data);
      } catch (err: any) {
        console.error('Erreur chargement catégories:', err);
        setError(err.response?.data?.detail || "Erreur lors du chargement des catégories");
      } finally {
        setLoading(false);
      }
    };

    if (month) {
      loadCategoryData();
    }
  }, [month]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900">{data.category}</p>
          <p className="text-sm text-gray-600">
            Montant: <span className="font-medium">{formatCurrency(data.amount)}</span>
          </p>
          <p className="text-sm text-gray-600">
            Part: <span className="font-medium">{data.percentage.toFixed(1)}%</span>
          </p>
          <p className="text-sm text-gray-600">
            Transactions: <span className="font-medium">{data.transaction_count}</span>
          </p>
          <p className="text-sm text-gray-600">
            Moyenne: <span className="font-medium">{formatCurrency(data.avg_transaction)}</span>
          </p>
        </div>
      );
    }
    return null;
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

  if (!categoryData.length) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Répartition par Catégorie</h3>
        <div className="text-center py-8 text-gray-500">
          <p>Aucune donnée disponible pour ce mois</p>
        </div>
      </Card>
    );
  }

  // Préparation des données pour le graphique
  const chartData = categoryData.map((item, index) => ({
    ...item,
    color: COLORS[index % COLORS.length]
  }));

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Répartition par Catégorie</h3>
        <p className="text-sm text-gray-600">
          {month} • {categoryData.length} catégories • {categoryData.reduce((sum, cat) => sum + cat.transaction_count, 0)} transactions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Graphique en secteurs */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ percentage }) => `${percentage.toFixed(1)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="amount"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Légende détaillée */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Détail des catégories</h4>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {chartData.map((item, index) => (
              <div
                key={item.category}
                className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-4 h-4 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.category}</p>
                    <p className="text-xs text-gray-500">
                      {item.transaction_count} transactions
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {formatCurrency(item.amount)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {item.percentage.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Résumé en bas */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-sm text-gray-600">Total Dépenses</div>
            <div className="text-lg font-semibold text-red-600">
              {formatCurrency(categoryData.reduce((sum, cat) => sum + cat.amount, 0))}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Catégorie Top</div>
            <div className="text-lg font-semibold text-blue-600">
              {categoryData[0]?.category || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Montant Moyen</div>
            <div className="text-lg font-semibold text-green-600">
              {formatCurrency(
                categoryData.reduce((sum, cat) => sum + cat.avg_transaction, 0) / categoryData.length
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default CategoryChart;