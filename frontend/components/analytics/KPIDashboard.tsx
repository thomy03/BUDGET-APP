'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '../ui';
import { api } from '../../lib/api';

interface KPIData {
  period_start: string;
  period_end: string;
  total_expenses: number;
  total_income: number;
  net_balance: number;
  avg_monthly_expenses: number;
  avg_monthly_income: number;
  top_expense_category: string | null;
  top_expense_amount: number;
  transaction_count: number;
  expense_trend: string;
}

interface KPIDashboardProps {
  period?: string;
  className?: string;
}

export function KPIDashboard({ period = "last3", className = "" }: KPIDashboardProps) {
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const loadKPIs = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await api.get(`/analytics/kpis?months=${period}`);
        setKpiData(response.data);
      } catch (err: any) {
        console.error('Erreur chargement KPIs:', err);
        setError(err.response?.data?.detail || "Erreur lors du chargement des KPIs");
      } finally {
        setLoading(false);
      }
    };

    loadKPIs();
  }, [period]);

  if (loading) {
    return (
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
        {[...Array(8)].map((_, i) => (
          <Card key={i} className="p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 border-red-200 bg-red-50 ${className}`}>
        <p className="text-red-600">{error}</p>
      </Card>
    );
  }

  if (!kpiData) return null;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR' 
    }).format(amount);
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return '📈';
      case 'down': return '📉';
      default: return '📊';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return 'text-red-600';
      case 'down': return 'text-green-600';
      default: return 'text-blue-600';
    }
  };

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* Total Dépenses */}
      <Card className="p-6 bg-gradient-to-r from-red-50 to-red-100 border-red-200">
        <h3 className="text-sm font-medium text-red-600 mb-1">Total Dépenses</h3>
        <p className="text-2xl font-bold text-red-900">
          {formatCurrency(kpiData.total_expenses)}
        </p>
        <p className="text-sm text-red-600 mt-1">
          Moy. mensuelle: {formatCurrency(kpiData.avg_monthly_expenses)}
        </p>
      </Card>

      {/* Total Revenus */}
      <Card className="p-6 bg-gradient-to-r from-green-50 to-green-100 border-green-200">
        <h3 className="text-sm font-medium text-green-600 mb-1">Total Revenus</h3>
        <p className="text-2xl font-bold text-green-900">
          {formatCurrency(kpiData.total_income)}
        </p>
        <p className="text-sm text-green-600 mt-1">
          Moy. mensuelle: {formatCurrency(kpiData.avg_monthly_income)}
        </p>
      </Card>

      {/* Solde Net */}
      <Card className={`p-6 bg-gradient-to-r ${
        kpiData.net_balance >= 0 
          ? 'from-blue-50 to-blue-100 border-blue-200' 
          : 'from-orange-50 to-orange-100 border-orange-200'
      }`}>
        <h3 className={`text-sm font-medium mb-1 ${
          kpiData.net_balance >= 0 ? 'text-blue-600' : 'text-orange-600'
        }`}>
          Solde Net
        </h3>
        <p className={`text-2xl font-bold ${
          kpiData.net_balance >= 0 ? 'text-blue-900' : 'text-orange-900'
        }`}>
          {formatCurrency(kpiData.net_balance)}
        </p>
        <p className={`text-sm mt-1 ${
          kpiData.net_balance >= 0 ? 'text-blue-600' : 'text-orange-600'
        }`}>
          {kpiData.net_balance >= 0 ? 'Excédent' : 'Déficit'}
        </p>
      </Card>

      {/* Tendance */}
      <Card className="p-6 bg-gradient-to-r from-purple-50 to-purple-100 border-purple-200">
        <h3 className="text-sm font-medium text-purple-600 mb-1">Tendance</h3>
        <p className={`text-2xl font-bold ${getTrendColor(kpiData.expense_trend)}`}>
          {getTrendIcon(kpiData.expense_trend)}
        </p>
        <p className="text-sm text-purple-600 mt-1 capitalize">
          {kpiData.expense_trend === 'up' ? 'En hausse' : 
           kpiData.expense_trend === 'down' ? 'En baisse' : 'Stable'}
        </p>
      </Card>

      {/* Top Catégorie */}
      <Card className="p-6 bg-gradient-to-r from-yellow-50 to-yellow-100 border-yellow-200">
        <h3 className="text-sm font-medium text-yellow-600 mb-1">Top Catégorie</h3>
        <p className="text-lg font-bold text-yellow-900">
          {kpiData.top_expense_category || 'Aucune'}
        </p>
        {kpiData.top_expense_amount > 0 && (
          <p className="text-sm text-yellow-600 mt-1">
            {formatCurrency(kpiData.top_expense_amount)}
          </p>
        )}
      </Card>

      {/* Nombre de transactions */}
      <Card className="p-6 bg-gradient-to-r from-indigo-50 to-indigo-100 border-indigo-200">
        <h3 className="text-sm font-medium text-indigo-600 mb-1">Transactions</h3>
        <p className="text-2xl font-bold text-indigo-900">
          {kpiData.transaction_count}
        </p>
        <p className="text-sm text-indigo-600 mt-1">
          {kpiData.period_start} → {kpiData.period_end}
        </p>
      </Card>

      {/* Période analysée - span sur 2 colonnes */}
      <Card className="p-6 bg-gradient-to-r from-gray-50 to-gray-100 border-gray-200 md:col-span-2">
        <h3 className="text-sm font-medium text-gray-600 mb-1">Période Analysée</h3>
        <p className="text-xl font-bold text-gray-900">
          {kpiData.period_start} → {kpiData.period_end}
        </p>
        <div className="flex justify-between mt-2 text-sm text-gray-600">
          <span>Revenus: {formatCurrency(kpiData.total_income)}</span>
          <span>Dépenses: {formatCurrency(kpiData.total_expenses)}</span>
          <span className={kpiData.net_balance >= 0 ? 'text-green-600' : 'text-red-600'}>
            Net: {formatCurrency(kpiData.net_balance)}
          </span>
        </div>
      </Card>
    </div>
  );
}

export default KPIDashboard;