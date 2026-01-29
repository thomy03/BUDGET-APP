'use client';

import { useState, useEffect, useMemo } from 'react';
import { Card, Button } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { api } from '../../lib/api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useCategories } from './CategoryManager';

interface TagDetailData {
  name: string;
  expense_type: 'fixed' | 'variable';
  transaction_count: number;
  total_amount: number;
  average_amount: number;
  category?: string;
  patterns: string[];
  transactions: Array<{
    id: number;
    date: string;
    label: string;
    amount: number;
  }>;
  monthly_trend: Array<{
    month: string;
    amount: number;
    count: number;
  }>;
}

interface TagDetailModalProps {
  tagName: string;
  isOpen: boolean;
  onClose: () => void;
  onEdit?: (tagName: string) => void;
  onDelete?: (tagName: string) => void;
  onViewAllTransactions?: (tagName: string) => void;
}

export function TagDetailModal({
  tagName,
  isOpen,
  onClose,
  onEdit,
  onDelete,
  onViewAllTransactions
}: TagDetailModalProps) {
  const [data, setData] = useState<TagDetailData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showCategorySelector, setShowCategorySelector] = useState(false);
  const [categorySaveMessage, setCategorySaveMessage] = useState<string>('');

  // Hook pour gérer les catégories
  const { categories, assignTagToCategory, getTagCategory } = useCategories();

  // Catégorie actuelle du tag
  const currentCategory = useMemo(() => {
    return getTagCategory(tagName);
  }, [tagName, getTagCategory]);

  useEffect(() => {
    if (isOpen && tagName) {
      loadTagDetails();
    }
  }, [isOpen, tagName]);

  const loadTagDetails = async () => {
    setIsLoading(true);
    setError('');

    try {
      let tagInfo: {
        name: string;
        expense_type: string;
        transaction_count: number;
        total_amount: number;
        patterns: string[];
        category?: string;
      } | null = null;

      let tagTransactions: Array<{
        id: number;
        date_op: string;
        label: string;
        amount: number;
        tags: string[];
      }> = [];

      // Essayer de charger les infos du tag depuis /tags
      try {
        const tagsResponse = await api.get<{
          tags: Array<{
            id: number;
            name: string;
            expense_type: string;
            transaction_count: number;
            total_amount: number;
            patterns: string[];
            category?: string;
          }>;
        }>('/tags');

        tagInfo = tagsResponse.data.tags.find(t => t.name === tagName) || null;
      } catch (tagsErr) {
        console.warn('Could not load tags API:', tagsErr);
      }

      // Charger les transactions avec ce tag
      try {
        const transactionsResponse = await api.get<Array<{
          id: number;
          date_op: string;
          label: string;
          amount: number;
          tags: string[];
        }>>('/transactions');

        // L'API retourne maintenant un objet paginé { items: [...], total, page, ... }
        const transactionsData = transactionsResponse.data || {};
        const transactionsArray = (transactionsData as any).items || transactionsData || [];
        tagTransactions = transactionsArray
          .filter((tx: any) => tx.tags?.includes(tagName))
          .sort((a: any, b: any) => new Date(b.date_op).getTime() - new Date(a.date_op).getTime());
      } catch (txErr) {
        console.warn('Could not load transactions:', txErr);
      }

      // Calculer la tendance mensuelle
      const monthlyMap = new Map<string, { amount: number; count: number }>();
      tagTransactions.forEach(tx => {
        const month = tx.date_op.substring(0, 7); // YYYY-MM
        const existing = monthlyMap.get(month) || { amount: 0, count: 0 };
        monthlyMap.set(month, {
          amount: existing.amount + Math.abs(tx.amount),
          count: existing.count + 1
        });
      });

      const monthlyTrend = Array.from(monthlyMap.entries())
        .map(([month, mData]) => ({
          month: new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' }),
          amount: Math.round(mData.amount * 100) / 100,
          count: mData.count
        }))
        .sort((a, b) => a.month.localeCompare(b.month))
        .slice(-6); // 6 derniers mois

      const totalAmount = tagTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

      // Construire les données même si le tag n'est pas dans /tags
      setData({
        name: tagInfo?.name || tagName,
        expense_type: (tagInfo?.expense_type?.toLowerCase() === 'fixed' ? 'fixed' : 'variable') as 'fixed' | 'variable',
        transaction_count: tagTransactions.length || tagInfo?.transaction_count || 0,
        total_amount: totalAmount || tagInfo?.total_amount || 0,
        average_amount: tagTransactions.length > 0 ? totalAmount / tagTransactions.length : 0,
        category: tagInfo?.category,
        patterns: tagInfo?.patterns || [],
        transactions: tagTransactions.slice(0, 10).map(tx => ({
          id: tx.id,
          date: tx.date_op,
          label: tx.label,
          amount: tx.amount
        })),
        monthly_trend: monthlyTrend
      });

      // Si aucune donnée n'a été trouvée, afficher un message mais pas d'erreur bloquante
      if (!tagInfo && tagTransactions.length === 0) {
        setError('Aucune donnée disponible pour ce tag. Vous pouvez quand même lui assigner une catégorie.');
      }

    } catch (err) {
      console.error('Error loading tag details:', err);
      // Créer des données minimales pour permettre l'assignation de catégorie
      setData({
        name: tagName,
        expense_type: 'variable',
        transaction_count: 0,
        total_amount: 0,
        average_amount: 0,
        patterns: [],
        transactions: [],
        monthly_trend: []
      });
      setError('Données non disponibles - L\'assignation de catégorie reste possible');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: currentCategory ? currentCategory.color + '40' : 'rgba(255,255,255,0.2)' }}
              >
                <span className="text-white text-xl">{currentCategory?.icon || '🏷️'}</span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{tagName}</h2>
                <button
                  onClick={() => setShowCategorySelector(!showCategorySelector)}
                  className="text-white/80 text-sm hover:text-white flex items-center gap-1 transition-colors"
                >
                  {currentCategory ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: currentCategory.color }}>
                      {currentCategory.icon} {currentCategory.name}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                      📁 Assigner une catégorie
                    </span>
                  )}
                  <span className="text-xs">▼</span>
                </button>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/20 hover:bg-white/30 text-white transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Category Selector Dropdown */}
          {showCategorySelector && (
            <div className="mt-3 pt-3 border-t border-white/20">
              <div className="text-sm text-white/80 mb-2">Choisir une catégorie :</div>
              <div className="flex flex-wrap gap-2">
                {/* Option "Aucune catégorie" */}
                <button
                  onClick={() => {
                    assignTagToCategory(tagName, null);
                    setShowCategorySelector(false);
                    setCategorySaveMessage('Catégorie retirée !');
                    setTimeout(() => setCategorySaveMessage(''), 2000);
                  }}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    !currentCategory
                      ? 'bg-white text-gray-800 shadow-lg'
                      : 'bg-white/20 text-white hover:bg-white/30'
                  }`}
                >
                  ❌ Aucune
                </button>
                {categories.map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => {
                      assignTagToCategory(tagName, cat.id);
                      setShowCategorySelector(false);
                      setCategorySaveMessage(`Catégorie "${cat.name}" assignée !`);
                      setTimeout(() => setCategorySaveMessage(''), 2000);
                    }}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      currentCategory?.id === cat.id
                        ? 'bg-white text-gray-800 shadow-lg'
                        : 'text-white hover:opacity-90'
                    }`}
                    style={{
                      backgroundColor: currentCategory?.id === cat.id ? 'white' : cat.color
                    }}
                  >
                    {cat.icon} {cat.name}
                  </button>
                ))}
              </div>
              {categorySaveMessage && (
                <div className="mt-2 text-sm text-green-200 font-medium animate-pulse">
                  ✓ {categorySaveMessage}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Chargement...</span>
            </div>
          ) : data ? (
            <div className="space-y-6">
              {/* Message d'avertissement si erreur (non bloquant) */}
              {error && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
                  ⚠️ {error}
                </div>
              )}
              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-blue-600">{data.transaction_count}</div>
                  <div className="text-sm text-gray-600">Transactions</div>
                </div>
                <div className="bg-green-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {data.total_amount.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
                  </div>
                  <div className="text-sm text-gray-600">Total</div>
                </div>
                <div className="bg-purple-50 rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {data.average_amount.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
                  </div>
                  <div className="text-sm text-gray-600">Moyenne</div>
                </div>
                <div className="bg-orange-50 rounded-xl p-4 text-center">
                  <ExpenseTypeBadge type={data.expense_type} size="md" />
                  <div className="text-sm text-gray-600 mt-1">Type</div>
                </div>
              </div>

              {/* Monthly Trend Chart */}
              {data.monthly_trend.length > 1 && (
                <Card className="p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Tendance mensuelle</h3>
                  <div className="h-40">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={data.monthly_trend}>
                        <defs>
                          <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis
                          dataKey="month"
                          tick={{ fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(value) => `${value}€`}
                        />
                        <Tooltip
                          formatter={(value: number) => [`${value.toLocaleString('fr-FR')} €`, 'Montant']}
                          contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                        />
                        <Area
                          type="monotone"
                          dataKey="amount"
                          stroke="#3B82F6"
                          strokeWidth={2}
                          fill="url(#colorAmount)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )}

              {/* Patterns */}
              {data.patterns.length > 0 && (
                <Card className="p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Libellés associés (patterns)</h3>
                  <div className="flex flex-wrap gap-2">
                    {data.patterns.map((pattern, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                      >
                        {pattern}
                      </span>
                    ))}
                  </div>
                </Card>
              )}

              {/* Recent Transactions */}
              <Card className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">
                    Dernières transactions ({Math.min(10, data.transactions.length)})
                  </h3>
                  {data.transaction_count > 10 && onViewAllTransactions && (
                    <button
                      onClick={() => onViewAllTransactions(tagName)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Voir tout →
                    </button>
                  )}
                </div>
                <div className="space-y-2">
                  {data.transactions.length === 0 ? (
                    <div className="text-center py-4 text-gray-500">
                      Aucune transaction récente
                    </div>
                  ) : (
                    data.transactions.map(tx => (
                      <div
                        key={tx.id}
                        className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {tx.label}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(tx.date).toLocaleDateString('fr-FR')}
                          </div>
                        </div>
                        <div className={`text-sm font-semibold ${tx.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {tx.amount < 0 ? '' : '+'}{tx.amount.toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="text-gray-500 mb-4">
                Utilisez le sélecteur de catégorie ci-dessus pour assigner ce tag à une catégorie.
              </div>
              <button
                onClick={() => setShowCategorySelector(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                📁 Choisir une catégorie
              </button>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
          <div className="flex gap-2">
            {onEdit && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onEdit(tagName);
                  onClose();
                }}
              >
                ✏️ Modifier
              </Button>
            )}
            {onDelete && (
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 border-red-300 hover:bg-red-50"
                onClick={() => {
                  if (window.confirm(`Supprimer le tag "${tagName}" ?`)) {
                    onDelete(tagName);
                    onClose();
                  }
                }}
              >
                🗑️ Supprimer
              </Button>
            )}
          </div>
          <Button onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}
