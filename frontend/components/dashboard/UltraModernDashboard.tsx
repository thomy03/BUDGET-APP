'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useCleanDashboard } from '../../hooks/useCleanDashboard';
import { balanceApi, api, tagCategoryApi } from '../../lib/api';
import { AICoachWidget } from './AICoachWidget';
import { GamificationWidget } from '../gamification';

interface UltraModernDashboardProps {
  month: string;
  isAuthenticated: boolean;
}

// Types pour les catégories
interface TagData {
  name: string;
  total: number;
  count: number;
}

interface CategoryData {
  name: string;
  total: number;
  count: number;
  tags: TagData[];
}

// Mapping ID catégorie → Nom lisible
const CATEGORY_NAMES: Record<string, string> = {
  'alimentation': 'Alimentation',
  'transport': 'Transport',
  'loisirs': 'Loisirs',
  'logement': 'Logement',
  'sante': 'Santé',
  'shopping': 'Shopping',
  'services': 'Services',
  'education': 'Éducation',
  'voyage': 'Voyage',
  'autres': 'Autres',
};

// Couleurs pour les catégories (palette moderne)
const CATEGORY_COLORS = [
  '#6366f1', // Indigo
  '#ec4899', // Pink
  '#f59e0b', // Amber
  '#10b981', // Emerald
  '#8b5cf6', // Violet
  '#ef4444', // Red
  '#06b6d4', // Cyan
  '#84cc16', // Lime
];

// Couleurs du graphique
const CHART_COLORS = {
  expenses: '#f43f5e',    // Rose
  provisions: '#6366f1',  // Indigo
  remaining: '#10b981',   // Émeraude
  deficit: '#f59e0b'      // Ambre
};

// ============================================================================
// COMPOSANT PRINCIPAL - Design Minimaliste Apple-Style
// ============================================================================

export const UltraModernDashboard: React.FC<UltraModernDashboardProps> = ({ month, isAuthenticated }) => {
  const { data, loading, error, formatters, reload } = useCleanDashboard(month, isAuthenticated);

  // État pour le solde modifiable
  const [accountBalance, setAccountBalance] = useState(0);
  const [isEditingBalance, setIsEditingBalance] = useState(false);
  const [balanceInput, setBalanceInput] = useState('');
  const [savingBalance, setSavingBalance] = useState(false);

  // État pour les catégories dépliables
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [categoriesData, setCategoriesData] = useState<CategoryData[]>([]);
  const [tagCategoryMap, setTagCategoryMap] = useState<Record<string, string>>({});

  // Charger le solde du compte
  useEffect(() => {
    const loadBalance = async () => {
      try {
        const balance = await balanceApi.get(month);
        setAccountBalance(balance.account_balance || 0);
        setBalanceInput((balance.account_balance || 0).toString());
      } catch {
        setAccountBalance(0);
        setBalanceInput('0');
      }
    };
    if (isAuthenticated && month) {
      loadBalance();
    }
  }, [month, isAuthenticated]);

  // Charger les mappings tag→catégorie depuis le backend
  useEffect(() => {
    const loadTagCategoryMappings = async () => {
      if (!isAuthenticated) return;
      try {
        const mappings = await tagCategoryApi.getAll();
        setTagCategoryMap(mappings);
        // Synchroniser avec localStorage comme backup
        localStorage.setItem('budget_app_tag_category_map', JSON.stringify(mappings));
        console.log('[Dashboard] Loaded', Object.keys(mappings).length, 'tag-category mappings from backend');
      } catch (err) {
        console.error('Erreur chargement mappings:', err);
        // Fallback sur localStorage
        try {
          const saved = localStorage.getItem('budget_app_tag_category_map');
          if (saved) setTagCategoryMap(JSON.parse(saved));
        } catch {}
      }
    };
    loadTagCategoryMappings();
  }, [isAuthenticated]);

  // Charger les transactions et regrouper par catégorie utilisateur
  useEffect(() => {
    const loadTransactions = async () => {
      if (!isAuthenticated || !month) return;

      try {
        const response = await api.get(`/transactions?month=${month}&limit=500`);
        // L'API retourne maintenant un objet paginé { items: [...], total, page, ... }
        const transactionsData = response.data || {};
        const transactions = transactionsData.items || transactionsData || [];

        // Filtrer uniquement les dépenses (montants négatifs) et non exclues
        const expenses = transactions.filter((t: any) => t.amount < 0 && !t.exclude);

        // Regrouper par catégorie UTILISATEUR (via tagCategoryMap) puis par tag
        const categoryMap = new Map<string, { total: number; count: number; tagsMap: Map<string, { total: number; count: number }> }>();

        expenses.forEach((tx: any) => {
          const tags = tx.tags || [];
          const amount = Math.abs(tx.amount);

          // Trouver la catégorie via le premier tag mappé, sinon utiliser la catégorie bancaire
          let category = 'Non catégorisé';
          for (const tag of tags) {
            const mappedCategoryId = tagCategoryMap[tag.toLowerCase()];
            if (mappedCategoryId) {
              // Utiliser le mapping ou formater l'ID
              category = CATEGORY_NAMES[mappedCategoryId] ||
                         mappedCategoryId.replace('custom_', 'Custom ').replace(/_/g, ' ');
              // Capitaliser si pas trouvé dans le mapping
              if (!CATEGORY_NAMES[mappedCategoryId]) {
                category = category.charAt(0).toUpperCase() + category.slice(1);
              }
              break;
            }
          }
          // Si pas de mapping trouvé, utiliser la catégorie bancaire
          if (category === 'Non catégorisé' && tx.category) {
            category = tx.category;
          }

          if (!categoryMap.has(category)) {
            categoryMap.set(category, { total: 0, count: 0, tagsMap: new Map() });
          }

          const catData = categoryMap.get(category)!;
          catData.total += amount;
          catData.count += 1;

          // Ajouter aux tags (si pas de tag, utiliser "Sans tag")
          const tagList = tags.length > 0 ? tags : ['Sans tag'];
          tagList.forEach((tag: string) => {
            if (!catData.tagsMap.has(tag)) {
              catData.tagsMap.set(tag, { total: 0, count: 0 });
            }
            const tagData = catData.tagsMap.get(tag)!;
            tagData.total += amount / tagList.length; // Diviser si plusieurs tags
            tagData.count += 1;
          });
        });

        // Convertir en array trié par total décroissant
        const categories: CategoryData[] = Array.from(categoryMap.entries())
          .map(([name, data]) => ({
            name,
            total: data.total,
            count: data.count,
            tags: Array.from(data.tagsMap.entries())
              .map(([tagName, tagData]) => ({
                name: tagName,
                total: tagData.total,
                count: tagData.count
              }))
              .sort((a, b) => b.total - a.total)
          }))
          .sort((a, b) => b.total - a.total);

        setCategoriesData(categories);
      } catch (err) {
        console.error('Erreur chargement transactions:', err);
      }
    };

    loadTransactions();
  }, [month, isAuthenticated, tagCategoryMap]);

  // Toggle l'expansion d'une catégorie
  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryName)) {
        newSet.delete(categoryName);
      } else {
        newSet.add(categoryName);
      }
      return newSet;
    });
  };

  // Sauvegarder le solde
  const handleSaveBalance = async () => {
    const value = parseFloat(balanceInput.replace(',', '.'));
    if (isNaN(value)) return;

    setSavingBalance(true);
    try {
      await balanceApi.update(month, { account_balance: value });
      setAccountBalance(value);
      setIsEditingBalance(false);
      reload();
    } catch (err) {
      console.error('Erreur sauvegarde:', err);
    } finally {
      setSavingBalance(false);
    }
  };

  // Loading
  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    );
  }

  // Error
  if (error || !data) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center text-gray-500">
        {error || 'Erreur de chargement'}
      </div>
    );
  }

  const monthLabel = new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  // Calculs - UTILISER les valeurs de useCleanDashboard pour cohérence
  // familyProvision.needed = provisions + dépenses - crédits - solde compte
  // Donc toProvision doit utiliser cette valeur, pas recalculer différemment
  const toProvision = Math.max(0, data.familyProvision.needed);
  const totalNeeded = data.provisions.total + (data.familyProvision.detail?.expenses?.total ?? 0);
  const surplus = -Math.min(0, data.familyProvision.needed);
  const remaining = data.revenue.net - data.expenses.total - data.provisions.total;

  // Données pour le graphique donut
  const chartData = [
    { name: 'Dépenses', value: data.expenses.total, color: CHART_COLORS.expenses },
    { name: 'Provisions', value: data.provisions.total, color: CHART_COLORS.provisions },
    { name: remaining >= 0 ? 'Disponible' : 'Déficit', value: Math.abs(remaining), color: remaining >= 0 ? CHART_COLORS.remaining : CHART_COLORS.deficit }
  ].filter(d => d.value > 0);

  // Pourcentages pour la légende
  const expensePercent = data.revenue.net > 0 ? (data.expenses.total / data.revenue.net * 100).toFixed(0) : 0;
  const provisionPercent = data.revenue.net > 0 ? (data.provisions.total / data.revenue.net * 100).toFixed(0) : 0;
  const remainingPercent = data.revenue.net > 0 ? (Math.abs(remaining) / data.revenue.net * 100).toFixed(0) : 0;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      {/* Header */}
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-light text-gray-900 capitalize">{monthLabel}</h1>
      </header>

      {/* AI Coach Widget + Gamification - Conseils et accomplissements */}
      <section className="mb-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AICoachWidget month={month} />
          <GamificationWidget compact />
        </div>
      </section>

      {/* Solde du compte - Éditable */}
      <section className="mb-12">
        <div className="text-center">
          <p className="text-sm text-gray-400 uppercase tracking-widest mb-3">Solde du compte</p>

          {isEditingBalance ? (
            <div className="inline-flex items-center gap-3">
              <input
                type="text"
                value={balanceInput}
                onChange={(e) => setBalanceInput(e.target.value)}
                className="text-5xl font-extralight text-center bg-transparent border-b-2 border-gray-300 focus:border-gray-900 outline-none w-64 transition-colors"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveBalance();
                  if (e.key === 'Escape') {
                    setIsEditingBalance(false);
                    setBalanceInput(accountBalance.toString());
                  }
                }}
              />
              <span className="text-3xl text-gray-400">€</span>
              <button
                onClick={handleSaveBalance}
                disabled={savingBalance}
                className="ml-2 px-4 py-2 bg-gray-900 text-white text-sm rounded-full hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                {savingBalance ? '...' : 'OK'}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsEditingBalance(true)}
              className="group"
            >
              <span className={`text-5xl font-extralight tabular-nums ${accountBalance >= 0 ? 'text-gray-900' : 'text-rose-600'}`}>
                {accountBalance.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
              </span>
              <span className="ml-3 opacity-0 group-hover:opacity-100 text-gray-400 text-sm transition-opacity">
                modifier
              </span>
            </button>
          )}
        </div>
      </section>

      {/* Graphique + Métriques */}
      <section className="mb-12 grid lg:grid-cols-2 gap-8 items-center">
        {/* Donut Chart */}
        <div className="relative">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => formatters.currency(value)}
                  contentStyle={{
                    backgroundColor: 'white',
                    border: 'none',
                    borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                    padding: '12px 16px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Centre du donut */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <p className="text-xs text-gray-400 uppercase">Revenus</p>
              <p className="text-2xl font-light text-gray-900">{formatters.currency(data.revenue.net)}</p>
            </div>
          </div>
        </div>

        {/* Légende détaillée - Cliquable */}
        <div className="space-y-4">
          <LegendItem
            color={CHART_COLORS.expenses}
            label="Dépenses"
            value={formatters.currency(data.expenses.total)}
            percent={`${expensePercent}%`}
            sublabel={`${data.expenses.count} transactions`}
            href="/analytics"
          />
          <LegendItem
            color={CHART_COLORS.provisions}
            label="Provisions"
            value={formatters.currency(data.provisions.total)}
            percent={`${provisionPercent}%`}
            sublabel={`${data.provisions.count} objectifs d'épargne`}
            href="/settings"
          />
          <LegendItem
            color={remaining >= 0 ? CHART_COLORS.remaining : CHART_COLORS.deficit}
            label={remaining >= 0 ? 'Disponible' : 'Déficit'}
            value={formatters.currency(Math.abs(remaining))}
            percent={`${remainingPercent}%`}
            sublabel={remaining >= 0 ? 'Reste après dépenses et provisions' : 'Montant manquant'}
          />
        </div>
      </section>

      {/* Catégories de dépenses - Dépliable */}
      {categoriesData.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm text-gray-400 uppercase tracking-widest">Top dépenses par catégorie</h2>
            <Link href="/analytics" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              Voir tout →
            </Link>
          </div>
          <div className="space-y-3">
            {categoriesData.slice(0, 5).map((category, index) => (
              <CategoryItem
                key={category.name}
                category={category}
                color={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                isExpanded={expandedCategories.has(category.name)}
                onToggle={() => toggleCategory(category.name)}
                formatCurrency={formatters.currency}
                totalExpenses={data?.expenses.total || 1}
              />
            ))}
          </div>
        </section>
      )}

      {/* À provisionner */}
      <section className="mb-12 p-8 bg-gray-50 rounded-3xl">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 mb-1">À provisionner ce mois</p>
            <p className={`text-4xl font-light ${toProvision > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
              {formatters.currency(toProvision)}
            </p>
            {surplus > 0 && (
              <p className="text-sm text-emerald-600 mt-2">
                Excédent de {formatters.currency(surplus)}
              </p>
            )}
          </div>
          <div className="text-right text-sm text-gray-500">
            <p>Dépenses + Provisions: {formatters.currency(totalNeeded)}</p>
            <p>Solde compte: {formatters.currency(accountBalance)}</p>
          </div>
        </div>
      </section>

      {/* Répartition familiale */}
      <section className="mb-12">
        <h2 className="text-sm text-gray-400 uppercase tracking-widest mb-2">Répartition familiale</h2>
        <p className="text-xs text-gray-400 mb-6">
          Chaque membre contribue proportionnellement à son revenu net
        </p>
        <div className="grid grid-cols-2 gap-6">
          <MemberCard
            name={data.revenue.member1.name}
            amount={toProvision > 0 ? data.familyProvision.member1 : 0}
            income={data.revenue.member1.net}
            formatters={formatters}
            provisionAmount={data.familyProvision.detail?.provisions?.member1 ?? 0}
            expenseAmount={data.familyProvision.detail?.expenses?.member1 ?? 0}
          />
          <MemberCard
            name={data.revenue.member2.name}
            amount={toProvision > 0 ? data.familyProvision.member2 : 0}
            income={data.revenue.member2.net}
            formatters={formatters}
            provisionAmount={data.familyProvision.detail?.provisions?.member2 ?? 0}
            expenseAmount={data.familyProvision.detail?.expenses?.member2 ?? 0}
          />
        </div>
      </section>

      {/* Provisions */}
      {data.provisions.items.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm text-gray-400 uppercase tracking-widest">Provisions actives</h2>
            <Link href="/settings" className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
              Gérer →
            </Link>
          </div>
          <div className="space-y-3">
            {data.provisions.items.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                <span className="text-gray-700">{p.name}</span>
                <span className="font-medium text-gray-900">{formatters.currency(p.currentAmount)}/mois</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Navigation */}
      <nav className="grid grid-cols-4 gap-4">
        <NavLink href="/transactions" label="Transactions" />
        <NavLink href="/analytics" label="Analyses" />
        <NavLink href="/import" label="Import" />
        <NavLink href="/settings" label="Paramètres" />
      </nav>
    </div>
  );
};

// ============================================================================
// COMPOSANTS
// ============================================================================

const LegendItem: React.FC<{
  color: string;
  label: string;
  value: string;
  percent: string;
  sublabel: string;
  href?: string;
}> = ({ color, label, value, percent, sublabel, href }) => {
  const content = (
    <div className={`flex items-start gap-4 p-4 bg-white rounded-xl border border-gray-100 ${href ? 'hover:border-gray-300 hover:shadow-sm cursor-pointer transition-all' : ''}`}>
      <div className="w-3 h-3 rounded-full mt-1.5" style={{ backgroundColor: color }} />
      <div className="flex-1">
        <div className="flex items-baseline justify-between">
          <span className="font-medium text-gray-900">{label}</span>
          <span className="text-lg font-light text-gray-900">{value}</span>
        </div>
        <div className="flex items-baseline justify-between mt-1">
          <span className="text-xs text-gray-400">{sublabel}</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">{percent}</span>
            {href && <span className="text-xs text-gray-400">→</span>}
          </div>
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
};

const MemberCard: React.FC<{
  name: string;
  amount: number;
  income: number;
  formatters: ReturnType<typeof useCleanDashboard>['formatters'];
  provisionAmount?: number;
  expenseAmount?: number;
}> = ({ name, amount, income, formatters, provisionAmount = 0, expenseAmount = 0 }) => {
  const percentage = income > 0 ? (amount / income) * 100 : 0;

  return (
    <div className="p-6 bg-white rounded-2xl border border-gray-100">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center text-white font-medium">
          {name.charAt(0).toUpperCase()}
        </div>
        <span className="font-medium text-gray-900">{name}</span>
      </div>
      <p className="text-2xl font-light text-gray-900 mb-1">{formatters.currency(amount)}</p>
      <p className="text-sm text-gray-400">
        {percentage.toFixed(0)}% de son revenu ({formatters.currency(income)})
      </p>

      {/* Détail Provisions / Dépenses */}
      <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-indigo-600 font-medium">Provisions</span>
          <span className="font-semibold text-indigo-700">{formatters.currency(provisionAmount)}</span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-orange-600 font-medium">Dépenses</span>
          <span className="font-semibold text-orange-700">{formatters.currency(expenseAmount)}</span>
        </div>
      </div>

      {/* Mini barre de progression */}
      <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gray-900 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
};

const NavLink: React.FC<{ href: string; label: string }> = ({ href, label }) => (
  <Link
    href={href}
    className="py-4 text-center text-sm text-gray-600 hover:text-gray-900 border-b-2 border-transparent hover:border-gray-900 transition-all"
  >
    {label}
  </Link>
);

// Composant Catégorie dépliable
const CategoryItem: React.FC<{
  category: CategoryData;
  color: string;
  isExpanded: boolean;
  onToggle: () => void;
  formatCurrency: (amount: number) => string;
  totalExpenses: number;
}> = ({ category, color, isExpanded, onToggle, formatCurrency, totalExpenses }) => {
  const percentage = totalExpenses > 0 ? (category.total / totalExpenses * 100).toFixed(0) : 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden transition-all duration-300 hover:shadow-md">
      {/* En-tête de la catégorie - Toujours visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors"
      >
        {/* Indicateur de couleur */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm"
          style={{ backgroundColor: color }}
        >
          {percentage}%
        </div>

        {/* Infos catégorie */}
        <div className="flex-1 text-left">
          <div className="flex items-baseline justify-between">
            <span className="font-medium text-gray-900 capitalize">{category.name}</span>
            <span className="text-lg font-light text-gray-900">{formatCurrency(category.total)}</span>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-400">{category.count} transaction{category.count > 1 ? 's' : ''}</span>
            <span className="text-xs text-gray-400">{category.tags.length} tag{category.tags.length > 1 ? 's' : ''}</span>
          </div>
        </div>

        {/* Icône expansion */}
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Liste des tags - Dépliable avec animation */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 pb-4 pt-2 border-t border-gray-100 bg-gray-50/50">
          <div className="space-y-2">
            {category.tags.slice(0, 5).map((tag, tagIndex) => {
              const tagPercent = category.total > 0 ? (tag.total / category.total * 100).toFixed(0) : 0;
              return (
                <div
                  key={tag.name}
                  className="flex items-center gap-3 p-2 rounded-xl bg-white hover:bg-gray-50 transition-colors"
                >
                  {/* Barre de progression */}
                  <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${tagPercent}%`,
                        backgroundColor: color,
                        opacity: 1 - (tagIndex * 0.15)
                      }}
                    />
                  </div>

                  {/* Nom du tag */}
                  <span className="flex-1 text-sm text-gray-700 capitalize">{tag.name}</span>

                  {/* Montant */}
                  <span className="text-sm font-medium text-gray-900">{formatCurrency(tag.total)}</span>

                  {/* Pourcentage */}
                  <span className="text-xs text-gray-400 w-10 text-right">{tagPercent}%</span>
                </div>
              );
            })}

            {/* Indication si plus de 5 tags */}
            {category.tags.length > 5 && (
              <Link
                href="/analytics"
                className="block text-center text-xs text-gray-400 hover:text-gray-600 py-2 transition-colors"
              >
                +{category.tags.length - 5} autres tags → Voir dans Analytics
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UltraModernDashboard;
