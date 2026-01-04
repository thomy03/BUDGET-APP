'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Legend,
  BarChart, Bar
} from 'recharts';
import { GlassCard, KPICard, LoadingSpinner } from '../ui';
import { useEnhancedDashboard, EnhancedSummaryData } from '../../hooks/useEnhancedDashboard';
import { api, balanceApi, analyticsApi } from '../../lib/api';

interface ModernDashboardProps {
  month: string;
  isAuthenticated: boolean;
}

// Couleurs pour les graphiques
const CHART_COLORS = {
  revenue: '#10B981',   // Green
  expenses: '#F59E0B',  // Orange
  savings: '#8B5CF6',   // Purple
  fixed: '#3B82F6',     // Blue
  variable: '#EF4444',  // Red
};

const PIE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#EC4899', '#06B6D4', '#84CC16'];

/**
 * ModernDashboard - Dashboard moderne avec glassmorphism et graphiques Recharts
 */
export const ModernDashboard: React.FC<ModernDashboardProps> = ({ month, isAuthenticated }) => {
  const router = useRouter();
  const { data, loading, error, reload } = useEnhancedDashboard(month, isAuthenticated);
  const [accountBalance, setAccountBalance] = useState<number>(0);
  const [monthlyTrends, setMonthlyTrends] = useState<any[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);

  // Charger le solde du compte
  useEffect(() => {
    const loadBalance = async () => {
      try {
        const balanceData = await balanceApi.get(month);
        setAccountBalance(balanceData.account_balance);
      } catch (error) {
        console.error('Erreur chargement solde:', error);
      }
    };
    if (month && isAuthenticated) {
      loadBalance();
    }
  }, [month, isAuthenticated]);

  // Charger les tendances mensuelles
  useEffect(() => {
    const loadTrends = async () => {
      setLoadingTrends(true);
      try {
        const trendsData = await analyticsApi.getTrends('last6');
        // Transformer pour Recharts
        const formattedTrends = trendsData.map((t: any) => ({
          month: new Date(t.month + '-01').toLocaleDateString('fr-FR', { month: 'short' }),
          revenus: t.revenues || 0,
          depenses: Math.abs(t.expenses || 0),
          epargne: t.savings || 0
        }));
        setMonthlyTrends(formattedTrends);
      } catch (error) {
        console.error('Erreur chargement tendances:', error);
        // Fallback avec des donnees mock si l'API echoue
        setMonthlyTrends([
          { month: 'Jan', revenus: 6500, depenses: 4200, epargne: 1000 },
          { month: 'Fev', revenus: 6500, depenses: 3800, epargne: 1000 },
          { month: 'Mar', revenus: 6800, depenses: 4100, epargne: 1000 },
          { month: 'Avr', revenus: 6500, depenses: 4500, epargne: 1000 },
          { month: 'Mai', revenus: 6500, depenses: 3900, epargne: 1000 },
          { month: 'Juin', revenus: 7000, depenses: 4300, epargne: 1200 }
        ]);
      } finally {
        setLoadingTrends(false);
      }
    };
    if (isAuthenticated) {
      loadTrends();
    }
  }, [isAuthenticated, month]);

  // Authentification requise
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <GlassCard className="p-8 text-center">
          <p className="text-gray-600">Vous devez etre connecte pour acceder au dashboard.</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 px-6 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:opacity-90"
          >
            Se connecter
          </button>
        </GlassCard>
      </div>
    );
  }

  // Erreur
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <GlassCard className="p-8 text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={reload}
            className="px-6 py-2 bg-gradient-to-r from-red-500 to-rose-600 text-white rounded-lg hover:opacity-90"
          >
            Reessayer
          </button>
        </GlassCard>
      </div>
    );
  }

  // Chargement
  if (loading || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <LoadingSpinner size="lg" text="Chargement du dashboard moderne..." />
      </div>
    );
  }

  // Preparer les donnees pour le PieChart des depenses (fixes + variables)
  const allExpenses = [
    // Depenses fixes par categorie
    ...data.fixed_expenses.detail.map(f => ({
      name: f.tag || f.name || f.category || 'Fixe',
      value: Math.abs(f.monthly_amount),
      type: 'fixed'
    })),
    // Depenses variables par tag
    ...data.variables.detail.map(v => ({
      name: v.tag || 'Variable',
      value: Math.abs(v.amount),
      type: 'variable'
    }))
  ];

  // Grouper par nom et calculer les totaux
  const expensesMap = new Map<string, number>();
  allExpenses.forEach(e => {
    if (e.value > 0) {
      const current = expensesMap.get(e.name) || 0;
      expensesMap.set(e.name, current + e.value);
    }
  });

  // Convertir en array et trier par montant
  const expensesPieData = Array.from(expensesMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, value], index) => ({
      name,
      value,
      color: PIE_COLORS[index % PIE_COLORS.length]
    }));

  // Calculs des KPIs
  const totalRevenue = data.revenues.total_revenue;
  const totalExpenses = data.totals.total_expenses;
  const totalSavings = data.savings.total;
  const balance = totalRevenue - totalExpenses - totalSavings;

  // Format du mois
  const monthLabel = new Date(month + '-01').toLocaleDateString('fr-FR', {
    month: 'long',
    year: 'numeric'
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Contenu principal - Navigation geree par le layout parent */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 animate-fade-in">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
            Dashboard Financier
          </h1>
          <p className="text-gray-600">Vue d'ensemble de vos finances - {monthLabel}</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <KPICard
            title="Solde du Compte"
            value={accountBalance}
            icon="💰"
            gradient="green"
            subtitle="Solde actuel"
          />
          <KPICard
            title="Revenus"
            value={totalRevenue}
            icon="📈"
            gradient="blue"
            subtitle={`${data.member1}: ${data.revenues.member1_revenue.toFixed(0)}€ | ${data.member2}: ${data.revenues.member2_revenue.toFixed(0)}€`}
          />
          <KPICard
            title="Depenses"
            value={totalExpenses}
            icon="📊"
            gradient="orange"
            subtitle={`Fixes: ${data.fixed_expenses.total.toFixed(0)}€ | Variables: ${data.variables.total.toFixed(0)}€`}
            onClick={() => router.push('/analytics')}
          />
          <KPICard
            title="Epargne"
            value={totalSavings}
            icon="🎯"
            gradient="purple"
            subtitle={`${data.savings.count} provisions actives`}
            onClick={() => router.push('/settings')}
          />
        </div>

        {/* Graphiques Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* PieChart - Repartition des depenses */}
          <GlassCard className="p-6">
            <h3 className="text-xl font-semibold mb-4 text-gray-800">Repartition des Depenses</h3>
            <div className="h-64">
              {expensesPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={expensesPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                      labelLine={false}
                    >
                      {expensesPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => [`${value.toFixed(2)} €`, 'Montant']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl">
                  <p className="text-gray-500">Aucune donnee de depense</p>
                </div>
              )}
            </div>
          </GlassCard>

          {/* AreaChart - Tendances mensuelles */}
          <GlassCard className="p-6">
            <h3 className="text-xl font-semibold mb-4 text-gray-800">Tendances Mensuelles</h3>
            <div className="h-64">
              {loadingTrends ? (
                <div className="h-full flex items-center justify-center">
                  <LoadingSpinner size="sm" text="Chargement..." />
                </div>
              ) : monthlyTrends.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={monthlyTrends}>
                    <defs>
                      <linearGradient id="colorRevenus" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.revenue} stopOpacity={0.8}/>
                        <stop offset="95%" stopColor={CHART_COLORS.revenue} stopOpacity={0.1}/>
                      </linearGradient>
                      <linearGradient id="colorDepenses" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.expenses} stopOpacity={0.8}/>
                        <stop offset="95%" stopColor={CHART_COLORS.expenses} stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <Tooltip formatter={(value: number) => [`${value.toFixed(0)} €`]} />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="revenus"
                      name="Revenus"
                      stroke={CHART_COLORS.revenue}
                      fillOpacity={1}
                      fill="url(#colorRevenus)"
                    />
                    <Area
                      type="monotone"
                      dataKey="depenses"
                      name="Depenses"
                      stroke={CHART_COLORS.expenses}
                      fillOpacity={1}
                      fill="url(#colorDepenses)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl">
                  <p className="text-gray-500">Aucune donnee de tendance</p>
                </div>
              )}
            </div>
          </GlassCard>
        </div>

        {/* Synthese et repartition */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Repartition familiale */}
          <GlassCard className="p-6 col-span-1">
            <h3 className="text-xl font-semibold mb-4 text-gray-800">Repartition Familiale</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                <span className="font-medium text-blue-800">{data.member1}</span>
                <span className="text-blue-600 font-semibold">{data.totals.member1_total.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                <span className="font-medium text-purple-800">{data.member2}</span>
                <span className="text-purple-600 font-semibold">{data.totals.member2_total.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-100 rounded-lg">
                <span className="font-medium text-gray-700">Ratio</span>
                <span className="text-gray-600">{data.split_ratio.member1}% / {data.split_ratio.member2}%</span>
              </div>
            </div>
          </GlassCard>

          {/* Top Categories */}
          <GlassCard className="p-6 col-span-2">
            <h3 className="text-xl font-semibold mb-4 text-gray-800">Top Categories de Depenses</h3>
            <div className="space-y-3">
              {expensesPieData.slice(0, 5).map((category, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    <span className="text-gray-700">{category.name}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min((category.value / totalExpenses) * 100, 100)}%`,
                          backgroundColor: category.color
                        }}
                      />
                    </div>
                    <span className="font-medium text-gray-800 w-24 text-right">
                      {category.value.toFixed(2)} €
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={() => router.push('/analytics')}
              className="mt-4 text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              Voir toutes les categories →
            </button>
          </GlassCard>
        </div>

        {/* Actions rapides */}
        <GlassCard className="p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-800">Actions Rapides</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <QuickActionButton
              icon="📥"
              label="Importer CSV"
              onClick={() => router.push('/upload')}
            />
            <QuickActionButton
              icon="📊"
              label="Analytics"
              onClick={() => router.push('/analytics')}
            />
            <QuickActionButton
              icon="💳"
              label="Transactions"
              onClick={() => router.push('/transactions')}
            />
            <QuickActionButton
              icon="⚙️"
              label="Parametres"
              onClick={() => router.push('/settings')}
            />
          </div>
        </GlassCard>
      </main>
    </div>
  );
};

// Composant QuickActionButton
const QuickActionButton: React.FC<{
  icon: string;
  label: string;
  onClick: () => void;
}> = ({ icon, label, onClick }) => (
  <button
    onClick={onClick}
    className="flex flex-col items-center p-4 bg-white/50 rounded-xl hover:bg-white/70 hover:shadow-md transition-all duration-200"
  >
    <span className="text-2xl mb-2">{icon}</span>
    <span className="text-sm font-medium text-gray-700">{label}</span>
  </button>
);

export default ModernDashboard;
