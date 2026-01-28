'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTagsManagement, TagInfo } from '../../hooks/useTagsManagement';
import { Card, Button, Alert } from '../ui';
import { api, tagCategoryApi, customCategoriesApi } from '../../lib/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area
} from 'recharts';

// ============================================================================
// CATÉGORIES PAR DÉFAUT
// ============================================================================

export const DEFAULT_CATEGORIES = [
  { id: 'alimentation', name: 'Alimentation', icon: '🍕', color: '#10B981' },
  { id: 'transport', name: 'Transport', icon: '🚗', color: '#3B82F6' },
  { id: 'loisirs', name: 'Loisirs', icon: '🎮', color: '#8B5CF6' },
  { id: 'logement', name: 'Logement', icon: '🏠', color: '#F59E0B' },
  { id: 'sante', name: 'Santé', icon: '🏥', color: '#EF4444' },
  { id: 'shopping', name: 'Shopping', icon: '🛒', color: '#EC4899' },
  { id: 'services', name: 'Services', icon: '📱', color: '#6366F1' },
  { id: 'education', name: 'Éducation', icon: '📚', color: '#14B8A6' },
  { id: 'voyage', name: 'Voyage', icon: '✈️', color: '#F97316' },
  { id: 'autres', name: 'Autres', icon: '📦', color: '#6B7280' },
] as const;

export type Category = {
  id: string;
  name: string;
  icon: string;
  color: string;
  isCustom?: boolean;
};

// ============================================================================
// TYPES
// ============================================================================

type MonthlyData = {
  month: string;
  monthLabel: string;
  total: number;
  [key: string]: string | number; // Pour les catégories dynamiques
};

type CategoryStats = {
  total: number;
  count: number;
  tags: string[];
  monthlyData: { month: string; amount: number }[];
};

type YearlyStats = {
  byCategory: Record<string, CategoryStats>;
  byTag: Record<string, { total: number; count: number; monthlyData: { month: string; amount: number }[] }>;
  monthlyTotals: MonthlyData[];
  grandTotal: number;
};

// ============================================================================
// COMPOSANT PRINCIPAL
// ============================================================================

export function SimpleTagsManager() {
  const router = useRouter();
  const { tags, isLoading, error, loadTags, clearError } = useTagsManagement();

  // État local
  const [categories, setCategories] = useState<Category[]>([]);
  const [tagCategoryMap, setTagCategoryMap] = useState<Record<string, string>>({});
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [yearlyStats, setYearlyStats] = useState<YearlyStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [view, setView] = useState<'categories' | 'tags'>('categories');

  // État pour le drill-down par mois
  const [selectedMonthData, setSelectedMonthData] = useState<{
    month: string;
    monthLabel: string;
    tagName: string;
    transactions: any[];
    total: number;
  } | null>(null);

  // Charger les catégories depuis le backend et les mappings
  useEffect(() => {
    const loadData = async () => {
      // Charger les catégories personnalisées depuis le backend (prioritaire)
      try {
        const backendCategories = await customCategoriesApi.getAll();
        if (backendCategories.length > 0) {
          const customCats = backendCategories.map(c => ({
            id: c.id,
            name: c.name,
            icon: c.icon || '📁',
            color: c.color || '#6B7280',
            isCustom: true
          }));
          setCategories([...DEFAULT_CATEGORIES, ...customCats]);
          // Synchroniser avec localStorage pour compatibilité
          localStorage.setItem('budget_app_categories', JSON.stringify(customCats));
          console.log('[TagsManager] Loaded', customCats.length, 'custom categories from backend');
        } else {
          // Fallback sur localStorage si backend vide
          const saved = localStorage.getItem('budget_app_categories');
          if (saved) {
            try {
              const parsed = JSON.parse(saved);
              const localCustomCats = parsed.filter((c: Category) => c.isCustom);
              setCategories([...DEFAULT_CATEGORIES, ...localCustomCats]);
              // Synchroniser vers le backend si des catégories locales existent
              if (localCustomCats.length > 0) {
                await customCategoriesApi.syncAll(localCustomCats.map((c: Category) => ({
                  id: c.id,
                  name: c.name,
                  icon: c.icon,
                  color: c.color
                })));
                console.log('[TagsManager] Synced', localCustomCats.length, 'local categories to backend');
              }
            } catch {
              setCategories([...DEFAULT_CATEGORIES]);
            }
          } else {
            setCategories([...DEFAULT_CATEGORIES]);
          }
        }
      } catch (error) {
        console.error('[TagsManager] Error loading categories from backend:', error);
        // Fallback sur localStorage en cas d'erreur
        const saved = localStorage.getItem('budget_app_categories');
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            setCategories([...DEFAULT_CATEGORIES, ...parsed.filter((c: Category) => c.isCustom)]);
          } catch {
            setCategories([...DEFAULT_CATEGORIES]);
          }
        } else {
          setCategories([...DEFAULT_CATEGORIES]);
        }
      }

      // Charger les mappings tag-catégorie depuis le backend (prioritaire)
      try {
        const backendMappings = await tagCategoryApi.getAll();
        if (Object.keys(backendMappings).length > 0) {
          setTagCategoryMap(backendMappings);
          // Synchroniser avec localStorage pour compatibilité
          localStorage.setItem('budget_app_tag_category_map', JSON.stringify(backendMappings));
          console.log('[TagsManager] Loaded', Object.keys(backendMappings).length, 'mappings from backend');
        } else {
          // Fallback sur localStorage si backend vide
          const savedMap = localStorage.getItem('budget_app_tag_category_map');
          if (savedMap) {
            try {
              const localMappings = JSON.parse(savedMap);
              setTagCategoryMap(localMappings);
              // Synchroniser vers le backend si des mappings locaux existent
              if (Object.keys(localMappings).length > 0) {
                await tagCategoryApi.syncAll(localMappings);
                console.log('[TagsManager] Synced', Object.keys(localMappings).length, 'local mappings to backend');
              }
            } catch {
              setTagCategoryMap({});
            }
          }
        }
      } catch (error) {
        console.error('[TagsManager] Error loading mappings from backend:', error);
        // Fallback sur localStorage en cas d'erreur
        const savedMap = localStorage.getItem('budget_app_tag_category_map');
        if (savedMap) {
          try {
            setTagCategoryMap(JSON.parse(savedMap));
          } catch {
            setTagCategoryMap({});
          }
        }
      }
    };

    loadData();
  }, []);

  // Sauvegarder les catégories personnalisées (localStorage + backend)
  const saveCategories = useCallback(async (newCategories: Category[]) => {
    const customOnly = newCategories.filter(c => c.isCustom);

    // Mise à jour immédiate de l'état local et localStorage
    localStorage.setItem('budget_app_categories', JSON.stringify(customOnly));
    setCategories(newCategories);

    // Synchronisation asynchrone vers le backend
    try {
      if (customOnly.length > 0) {
        await customCategoriesApi.syncAll(customOnly.map(c => ({
          id: c.id,
          name: c.name,
          icon: c.icon,
          color: c.color
        })));
        console.log('[TagsManager] Saved', customOnly.length, 'custom categories to backend');
      }
    } catch (error) {
      console.error('[TagsManager] Error saving categories to backend:', error);
      // Les données sont déjà sauvegardées en localStorage, donc pas de perte
    }
  }, []);

  // Sauvegarder les associations tag-catégorie (localStorage + backend)
  const saveTagCategoryMap = useCallback(async (newMap: Record<string, string>) => {
    // Mise à jour immédiate de l'état local et localStorage
    localStorage.setItem('budget_app_tag_category_map', JSON.stringify(newMap));
    setTagCategoryMap(newMap);

    // Synchronisation asynchrone vers le backend
    try {
      await tagCategoryApi.syncAll(newMap);
      console.log('[TagsManager] Saved', Object.keys(newMap).length, 'mappings to backend');
    } catch (error) {
      console.error('[TagsManager] Error saving mappings to backend:', error);
      // Les données sont déjà sauvegardées en localStorage, donc pas de perte
    }
  }, []);

  // Charger les transactions pour tous les mois de l'année en cours
  useEffect(() => {
    const loadTransactions = async () => {
      setLoadingStats(true);
      try {
        const currentYear = new Date().getFullYear();
        const months = [];
        for (let m = 1; m <= 12; m++) {
          months.push(`${currentYear}-${m.toString().padStart(2, '0')}`);
        }

        // Charger les transactions de façon séquentielle pour éviter les erreurs SQLite
        const allTransactions: any[] = [];
        for (const month of months) {
          try {
            const res = await api.get('/transactions', { params: { month } });
            if (res.data && Array.isArray(res.data)) {
              allTransactions.push(...res.data);
            }
          } catch (err) {
            console.warn(`[TagsManager] Error loading ${month}:`, err);
          }
        }

        setTransactions(allTransactions);
        console.log(`[TagsManager] Loaded ${allTransactions.length} transactions for ${currentYear}`);
      } catch (err) {
        console.error('Erreur chargement transactions:', err);
      } finally {
        setLoadingStats(false);
      }
    };
    loadTransactions();
  }, []);

  // Calculer les stats à partir des transactions et du tagCategoryMap
  const computedStats = useMemo(() => {
    if (!transactions.length) return null;

    const stats: YearlyStats = {
      byCategory: {},
      byTag: {},
      monthlyTotals: [],
      grandTotal: 0
    };

    const monthlyByCategory: Record<string, Record<string, number>> = {};
    const monthlyByTag: Record<string, Record<string, number>> = {};
    const monthlyTotals: Record<string, number> = {};

    // Initialiser les mois
    const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
    const currentYear = new Date().getFullYear();

    months.forEach(m => {
      const key = `${currentYear}-${m}`;
      monthlyTotals[key] = 0;
    });

    transactions.forEach((tx: any) => {
      // Inclure TOUTES les transactions taggées (revenus ET dépenses)
      const amount = Math.abs(tx.amount);
      const txMonth = tx.month || tx.date_op?.substring(0, 7);
      const isExpense = tx.amount < 0;

      // Grand total uniquement pour les dépenses (pour les stats de catégories)
      if (isExpense) {
        stats.grandTotal += amount;
        if (txMonth) {
          monthlyTotals[txMonth] = (monthlyTotals[txMonth] || 0) + amount;
        }
      }

      const txTags = tx.tags || [];
      txTags.forEach((tag: string) => {
        // Stats par tag - inclure revenus et dépenses
        if (!stats.byTag[tag]) {
          stats.byTag[tag] = { total: 0, count: 0, monthlyData: [], isRevenue: !isExpense };
        }
        stats.byTag[tag].total += amount;
        stats.byTag[tag].count += 1;

        // Monthly par tag
        if (txMonth) {
          if (!monthlyByTag[tag]) monthlyByTag[tag] = {};
          monthlyByTag[tag][txMonth] = (monthlyByTag[tag][txMonth] || 0) + amount;
        }

        // Stats par catégorie - SEULEMENT si une catégorie est explicitement assignée
        const categoryId = tagCategoryMap[tag]; // Ne plus mettre 'autres' par défaut
        if (categoryId && isExpense) {
          if (!stats.byCategory[categoryId]) {
            stats.byCategory[categoryId] = { total: 0, count: 0, tags: [], monthlyData: [] };
          }
          stats.byCategory[categoryId].total += amount;
          stats.byCategory[categoryId].count += 1;
          if (!stats.byCategory[categoryId].tags.includes(tag)) {
            stats.byCategory[categoryId].tags.push(tag);
          }

          // Monthly par catégorie
          if (txMonth) {
            if (!monthlyByCategory[categoryId]) monthlyByCategory[categoryId] = {};
            monthlyByCategory[categoryId][txMonth] = (monthlyByCategory[categoryId][txMonth] || 0) + amount;
          }
        }
      });
    });

    // Convertir monthly data
    Object.keys(stats.byCategory).forEach(catId => {
      stats.byCategory[catId].monthlyData = Object.entries(monthlyByCategory[catId] || {})
        .map(([month, amount]) => ({ month, amount }))
        .sort((a, b) => a.month.localeCompare(b.month));
    });

    Object.keys(stats.byTag).forEach(tag => {
      stats.byTag[tag].monthlyData = Object.entries(monthlyByTag[tag] || {})
        .map(([month, amount]) => ({ month, amount }))
        .sort((a, b) => a.month.localeCompare(b.month));
    });

    // Monthly totals pour graphique
    const monthNames = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'];
    stats.monthlyTotals = Object.entries(monthlyTotals)
      .map(([month, total]) => {
        const monthNum = parseInt(month.split('-')[1]) - 1;
        const data: MonthlyData = {
          month,
          monthLabel: monthNames[monthNum] || month,
          total
        };
        // Ajouter les données par catégorie
        Object.entries(monthlyByCategory).forEach(([catId, catMonthly]) => {
          data[catId] = catMonthly[month] || 0;
        });
        return data;
      })
      .sort((a, b) => a.month.localeCompare(b.month));

    return stats;
  }, [transactions, tagCategoryMap]);

  // Tags enrichis avec catégorie
  const enrichedTags = useMemo(() => {
    return tags.map(tag => ({
      ...tag,
      categoryId: tagCategoryMap[tag.name] || undefined
    }));
  }, [tags, tagCategoryMap]);

  // Tags filtrés par catégorie sélectionnée
  const filteredTags = useMemo(() => {
    if (!selectedCategory) return enrichedTags;
    if (selectedCategory === 'uncategorized') {
      return enrichedTags.filter(t => !t.categoryId);
    }
    return enrichedTags.filter(t => t.categoryId === selectedCategory);
  }, [enrichedTags, selectedCategory]);

  // Ajouter une catégorie personnalisée
  const handleAddCategory = () => {
    if (!newCategoryName.trim()) return;

    const newCategory: Category = {
      id: `custom_${Date.now()}`,
      name: newCategoryName.trim(),
      icon: '📁',
      color: '#6B7280',
      isCustom: true
    };

    saveCategories([...categories, newCategory]);
    setNewCategoryName('');
    setShowAddCategory(false);
  };

  // Supprimer une catégorie personnalisée
  const handleDeleteCategory = (categoryId: string) => {
    const category = categories.find(c => c.id === categoryId);
    if (!category?.isCustom) return;

    if (window.confirm(`Supprimer la catégorie "${category.name}" ?`)) {
      const newMap = { ...tagCategoryMap };
      Object.keys(newMap).forEach(tag => {
        if (newMap[tag] === categoryId) {
          delete newMap[tag];
        }
      });
      saveTagCategoryMap(newMap);
      saveCategories(categories.filter(c => c.id !== categoryId));
    }
  };

  // Assigner un tag à une catégorie - met à jour immédiatement
  const handleAssignTag = (tagName: string, categoryId: string | null) => {
    const newMap = { ...tagCategoryMap };
    if (categoryId) {
      newMap[tagName] = categoryId;
    } else {
      delete newMap[tagName];
    }
    saveTagCategoryMap(newMap);
  };

  // Voir les transactions d'un tag
  const handleViewTransactions = (tagName: string) => {
    router.push(`/transactions?tag=${encodeURIComponent(tagName)}`);
  };

  // Handler pour le clic sur une barre du graphique mensuel
  const handleMonthBarClick = useCallback((data: any, tagName: string) => {
    if (!data || !data.activePayload || !data.activePayload[0]) return;

    const monthStr = data.activePayload[0].payload.month;
    const monthNames = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
    const monthNum = parseInt(monthStr.split('-')[1]) - 1;
    const year = monthStr.split('-')[0];
    const monthLabel = `${monthNames[monthNum]} ${year}`;

    // Filtrer les transactions pour ce tag ET ce mois
    const monthTransactions = transactions.filter(tx => {
      const txTags = tx.tags || [];
      const txMonth = tx.month || tx.date_op?.substring(0, 7);
      return txTags.includes(tagName) && txMonth === monthStr;
    });

    const total = monthTransactions.reduce((sum: number, tx: any) => sum + Math.abs(tx.amount), 0);

    setSelectedMonthData({
      month: monthStr,
      monthLabel,
      tagName,
      transactions: monthTransactions,
      total
    });
  }, [transactions]);

  // Obtenir les stats d'une catégorie - calcul basé sur enrichedTags et tagCategoryMap
  const getCategoryStats = useCallback((categoryId: string): CategoryStats => {
    // D'abord récupérer les tags assignés à cette catégorie
    const tagsInCategory = enrichedTags.filter(t =>
      categoryId === 'uncategorized' ? !t.categoryId : t.categoryId === categoryId
    );

    // Calculer le total à partir des tags enrichis (qui ont les vrais montants)
    const total = tagsInCategory.reduce((sum, t) => sum + Math.abs(t.total_amount || 0), 0);
    const count = tagsInCategory.reduce((sum, t) => sum + (t.transaction_count || 0), 0);
    const tagNames = tagsInCategory.map(t => t.name);

    // Récupérer les données mensuelles si elles existent
    const monthlyData = computedStats?.byCategory[categoryId]?.monthlyData || [];

    return { total, count, tags: tagNames, monthlyData };
  }, [enrichedTags, computedStats]);

  // Nombre de tags sans catégorie
  const uncategorizedCount = enrichedTags.filter(t => !t.categoryId).length;

  // Obtenir les tags assignés à une catégorie (depuis tagCategoryMap, indépendamment des transactions)
  const getAssignedTags = useCallback((categoryId: string): string[] => {
    return Object.entries(tagCategoryMap)
      .filter(([_, catId]) => catId === categoryId)
      .map(([tagName, _]) => tagName);
  }, [tagCategoryMap]);

  // Catégorie sélectionnée
  const selectedCategoryData = selectedCategory
    ? categories.find(c => c.id === selectedCategory)
    : null;

  // Données pour le pie chart - basé sur enrichedTags et tagCategoryMap
  const pieChartData = useMemo(() => {
    // Calculer les totaux par catégorie à partir des enrichedTags
    const categoryTotals = new Map<string, number>();

    enrichedTags.forEach(tag => {
      const catId = tag.categoryId || 'autres';
      const current = categoryTotals.get(catId) || 0;
      categoryTotals.set(catId, current + Math.abs(tag.total_amount || 0));
    });

    return categories
      .filter(cat => (categoryTotals.get(cat.id) || 0) > 0)
      .map(cat => ({
        name: cat.name,
        value: categoryTotals.get(cat.id) || 0,
        color: cat.color,
        icon: cat.icon
      }))
      .sort((a, b) => b.value - a.value);
  }, [enrichedTags, categories]);

  // ============================================================================
  // RENDU
  // ============================================================================

  if (isLoading || loadingStats) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Chargement...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Tags & Catégories
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Organisez vos dépenses par catégorie
          </p>
        </div>
        <Button
          onClick={() => setShowAddCategory(true)}
          className="bg-blue-600 hover:bg-blue-700"
        >
          + Nouvelle catégorie
        </Button>
      </div>

      {error && (
        <Alert variant="error">
          <div className="flex justify-between items-center">
            <span>{error}</span>
            <button onClick={clearError} className="text-red-600 hover:text-red-800">×</button>
          </div>
        </Alert>
      )}

      {/* Résumé avec graphique pie */}
      {computedStats && !selectedCategory && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stats résumé */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              📊 Résumé {new Date().getFullYear()}
            </h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <p className="text-gray-500 text-sm">Total dépenses</p>
                <p className="text-2xl font-bold text-red-600">
                  {computedStats.grandTotal.toLocaleString('fr-FR', {
                    style: 'currency',
                    currency: 'EUR',
                    maximumFractionDigits: 0
                  })}
                </p>
              </div>
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <p className="text-gray-500 text-sm">Moyenne/mois</p>
                <p className="text-2xl font-bold text-blue-600">
                  {(computedStats.grandTotal / 12).toLocaleString('fr-FR', {
                    style: 'currency',
                    currency: 'EUR',
                    maximumFractionDigits: 0
                  })}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <p className="text-gray-500 text-sm">Catégories</p>
                <p className="text-2xl font-bold text-green-600">
                  {Object.keys(computedStats.byCategory).length}
                </p>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <p className="text-gray-500 text-sm">Tags utilisés</p>
                <p className="text-2xl font-bold text-purple-600">
                  {Object.keys(computedStats.byTag).length}
                </p>
              </div>
            </div>
          </Card>

          {/* Pie Chart */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              🥧 Répartition par catégorie
            </h3>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieChartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {pieChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* Evolution mensuelle */}
      {computedStats && !selectedCategory && computedStats.monthlyTotals.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            📈 Évolution mensuelle des dépenses
          </h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={computedStats.monthlyTotals}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="monthLabel" />
                <YAxis tickFormatter={(v) => `${(v/1000).toFixed(0)}k€`} />
                <Tooltip
                  formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#3B82F6"
                  fill="#3B82F6"
                  fillOpacity={0.3}
                  name="Total"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Vue navigation */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
        <button
          onClick={() => { setView('categories'); setSelectedCategory(null); }}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            view === 'categories'
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400'
          }`}
        >
          📊 Par Catégorie
        </button>
        <button
          onClick={() => { setView('tags'); setSelectedCategory(null); }}
          className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
            view === 'tags'
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400'
          }`}
        >
          🏷️ Tous les Tags ({tags.length})
        </button>
      </div>

      {/* Vue Catégories - Grille */}
      {view === 'categories' && !selectedCategory && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {categories.map(category => {
            const stats = getCategoryStats(category.id);
            const assignedTags = getAssignedTags(category.id);
            return (
              <Card
                key={category.id}
                className="p-4 cursor-pointer hover:shadow-md transition-shadow border-l-4"
                style={{ borderLeftColor: category.color }}
                onClick={() => setSelectedCategory(category.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{category.icon}</span>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {category.name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {assignedTags.length} tags • {stats.count} trans.
                      </p>
                    </div>
                  </div>
                  {category.isCustom && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteCategory(category.id); }}
                      className="text-gray-400 hover:text-red-500 p-1"
                    >
                      🗑️
                    </button>
                  )}
                </div>

                {/* Tags assignés à cette catégorie */}
                {assignedTags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {assignedTags.slice(0, 5).map(tagName => (
                      <span
                        key={tagName}
                        className="px-2 py-0.5 text-xs rounded-full capitalize"
                        style={{
                          backgroundColor: category.color + '20',
                          color: category.color
                        }}
                      >
                        {tagName}
                      </span>
                    ))}
                    {assignedTags.length > 5 && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">
                        +{assignedTags.length - 5}
                      </span>
                    )}
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-500 text-sm">Total {new Date().getFullYear()}</span>
                    <span className="font-bold text-lg" style={{ color: category.color }}>
                      {stats.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}

          {/* Catégorie "Non classé" */}
          {uncategorizedCount > 0 && (
            <Card
              className="p-4 cursor-pointer hover:shadow-md transition-shadow border-l-4 border-gray-400"
              onClick={() => setSelectedCategory('uncategorized')}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">❓</span>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Non classés
                  </h3>
                  <p className="text-sm text-gray-500">
                    {uncategorizedCount} tags à assigner
                  </p>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Vue détail catégorie avec graphique */}
      {view === 'categories' && selectedCategory && (
        <div className="space-y-4">
          <button
            onClick={() => setSelectedCategory(null)}
            className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
          >
            ← Retour aux catégories
          </button>

          {/* Header catégorie + stats */}
          <Card className="p-6">
            <div className="flex items-center gap-4 mb-6">
              <div
                className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl"
                style={{ backgroundColor: (selectedCategoryData?.color || '#6B7280') + '20' }}
              >
                {selectedCategory === 'uncategorized' ? '❓' : selectedCategoryData?.icon}
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {selectedCategory === 'uncategorized' ? 'Tags non classés' : selectedCategoryData?.name}
                </h3>
                <div className="flex gap-4 mt-1">
                  <span className="text-gray-500">
                    {filteredTags.length} tags
                  </span>
                  <span className="text-gray-500">
                    {getCategoryStats(selectedCategory).count} transactions
                  </span>
                  <span className="font-bold" style={{ color: selectedCategoryData?.color || '#6B7280' }}>
                    {getCategoryStats(selectedCategory).total.toLocaleString('fr-FR', {
                      style: 'currency',
                      currency: 'EUR',
                      maximumFractionDigits: 0
                    })}
                  </span>
                </div>
              </div>
            </div>

            {/* Graphique évolution mensuelle de la catégorie */}
            {selectedCategory !== 'uncategorized' && getCategoryStats(selectedCategory).monthlyData.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Évolution mensuelle
                </h4>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getCategoryStats(selectedCategory).monthlyData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="month"
                        tickFormatter={(m) => {
                          const monthNames = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'];
                          const monthNum = parseInt(m.split('-')[1]) - 1;
                          return monthNames[monthNum] || m;
                        }}
                      />
                      <YAxis tickFormatter={(v) => `${v}€`} />
                      <Tooltip
                        formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                        labelFormatter={(m) => {
                          const monthNames = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
                          const monthNum = parseInt(String(m).split('-')[1]) - 1;
                          return monthNames[monthNum] || m;
                        }}
                      />
                      <Bar
                        dataKey="amount"
                        fill={selectedCategoryData?.color || '#6B7280'}
                        radius={[4, 4, 0, 0]}
                        name="Montant"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Liste des tags */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Tags dans cette catégorie
              </h4>
              {filteredTags.length === 0 ? (
                <p className="text-gray-500 text-center py-4">Aucun tag dans cette catégorie</p>
              ) : (
                filteredTags
                  .sort((a, b) => Math.abs(b.total_amount) - Math.abs(a.total_amount))
                  .map(tag => (
                    <div
                      key={tag.name}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {tag.name}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          tag.expense_type === 'fixed'
                            ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        }`}>
                          {tag.expense_type === 'fixed' ? 'Fixe' : 'Variable'}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-gray-500 text-sm">
                          {tag.transaction_count} trans.
                        </span>
                        <span className="font-semibold text-gray-900 dark:text-white min-w-[100px] text-right">
                          {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                            style: 'currency',
                            currency: 'EUR',
                            maximumFractionDigits: 0
                          })}
                        </span>
                        <div className="flex gap-2">
                          <select
                            value={tag.categoryId || ''}
                            onChange={(e) => handleAssignTag(tag.name, e.target.value || null)}
                            onClick={(e) => e.stopPropagation()}
                            className="text-sm border border-gray-300 rounded px-2 py-1 bg-white dark:bg-gray-700 dark:border-gray-600"
                          >
                            <option value="">-- Catégorie --</option>
                            {categories.map(cat => (
                              <option key={cat.id} value={cat.id}>
                                {cat.icon} {cat.name}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleViewTransactions(tag.name)}
                            className="text-blue-600 hover:text-blue-700 p-1"
                            title="Voir les transactions"
                          >
                            👁️
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Vue tous les tags */}
      {view === 'tags' && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Tous les tags ({tags.length})
            </h3>
            <Button variant="outline" size="sm" onClick={loadTags}>
              🔄 Actualiser
            </Button>
          </div>

          <div className="space-y-2">
            {enrichedTags
              .sort((a, b) => Math.abs(b.total_amount) - Math.abs(a.total_amount))
              .map(tag => {
                const category = categories.find(c => c.id === tag.categoryId);
                return (
                  <div
                    key={tag.name}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {tag.name}
                      </span>
                      {category && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full text-white"
                          style={{ backgroundColor: category.color }}
                        >
                          {category.icon} {category.name}
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        tag.expense_type === 'fixed'
                          ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                          : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      }`}>
                        {tag.expense_type === 'fixed' ? 'Fixe' : 'Variable'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-gray-500 text-sm">
                        {tag.transaction_count} trans.
                      </span>
                      <span className="font-semibold text-gray-900 dark:text-white min-w-[100px] text-right">
                        {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                          style: 'currency',
                          currency: 'EUR',
                          maximumFractionDigits: 0
                        })}
                      </span>
                      <select
                        value={tag.categoryId || ''}
                        onChange={(e) => handleAssignTag(tag.name, e.target.value || null)}
                        className="text-sm border border-gray-300 rounded px-2 py-1 bg-white dark:bg-gray-700 dark:border-gray-600"
                      >
                        <option value="">-- Catégorie --</option>
                        {categories.map(cat => (
                          <option key={cat.id} value={cat.id}>
                            {cat.icon} {cat.name}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleViewTransactions(tag.name)}
                        className="text-blue-600 hover:text-blue-700 p-1"
                        title="Voir les transactions"
                      >
                        👁️
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </Card>
      )}

      {/* Modal ajout catégorie */}
      {showAddCategory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Nouvelle catégorie</h3>
            <input
              type="text"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
              placeholder="Nom de la catégorie..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => { setShowAddCategory(false); setNewCategoryName(''); }}
              >
                Annuler
              </Button>
              <Button
                onClick={handleAddCategory}
                disabled={!newCategoryName.trim()}
              >
                Créer
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

export default SimpleTagsManager;
