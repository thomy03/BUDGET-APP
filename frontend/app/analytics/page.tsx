'use client';

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, tagCategoryApi, pdfExportApi } from "../../lib/api";
import { useGlobalMonth } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card } from "../../components/ui";
import { DEFAULT_CATEGORIES } from "../../components/settings/SimpleTagsManager";
import { BudgetVarianceAnalysis, AnomaliesPanel } from "../../components/analytics";

type AnalyticsTab = 'drilldown' | 'budget' | 'anomalies' | 'ai';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area, ComposedChart
} from 'recharts';

// ============================================================================
// TYPES
// ============================================================================

type Transaction = {
  id: number;
  label: string;
  amount: number;
  date_op: string;
  month: string;
  tags: string[];
};

type TagData = {
  name: string;
  total: number;
  count: number;
  categoryId?: string;
  transactions?: Transaction[];
};

type CategoryData = {
  id: string;
  name: string;
  icon: string;
  color: string;
  total: number;
  count: number;
  tags: TagData[];
  monthlyData: { month: string; amount: number }[];
  avgMonthly: number;
  variation: number;
};

type DrillLevel = 'categories' | 'tags' | 'transactions' | 'month-tags' | 'month-transactions' | 'category-month-transactions';

type MonthTagData = {
  month: string;
  monthLabel: string;
  total: number;
  count: number;
  tags: TagData[];
};

type CategoryMonthData = {
  month: string;
  monthLabel: string;
  category: CategoryData;
  tag: TagData;
  transactions: Transaction[];
  total: number;
  count: number;
};

// ============================================================================
// COMPOSANT PRINCIPAL
// ============================================================================

export default function Analytics() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();

  // State
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [tagCategoryMap, setTagCategoryMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Drill-down state
  const [drillLevel, setDrillLevel] = useState<DrillLevel>('categories');
  const [selectedCategory, setSelectedCategory] = useState<CategoryData | null>(null);
  const [selectedTag, setSelectedTag] = useState<TagData | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<MonthTagData | null>(null);
  const [selectedCategoryMonth, setSelectedCategoryMonth] = useState<CategoryMonthData | null>(null);

  // Période pour analyse (1 mois par défaut = mois sélectionné uniquement)
  const [periodMonths, setPeriodMonths] = useState(1);

  // Onglet actif pour la vue principale
  const [activeTab, setActiveTab] = useState<AnalyticsTab>('drilldown');

  // État pour l'édition des tags
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [newTagInput, setNewTagInput] = useState('');
  const [savingTag, setSavingTag] = useState(false);
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  // Ref avec timestamp pour éviter le rechargement des données après une modification de tag
  // On bloque les reloads pendant 2 secondes après une modification
  const lastTagModificationRef = useRef<number>(0);

  // Redirection si non authentifie
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Charger le mapping des categories depuis le backend (avec fallback localStorage)
  useEffect(() => {
    const loadMappings = async () => {
      try {
        // Essayer de charger depuis le backend
        const backendMappings = await tagCategoryApi.getAll();
        if (Object.keys(backendMappings).length > 0) {
          setTagCategoryMap(backendMappings);
          // Synchroniser avec localStorage pour compatibilité
          if (typeof window !== 'undefined') {
            localStorage.setItem('budget_app_tag_category_map', JSON.stringify(backendMappings));
          }
          return;
        }
      } catch (error) {
        console.error('[Analytics] Error loading mappings from backend:', error);
      }

      // Fallback sur localStorage
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('budget_app_tag_category_map');
        if (saved) {
          try {
            setTagCategoryMap(JSON.parse(saved));
          } catch {
            setTagCategoryMap({});
          }
        }
      }
    };

    if (isAuthenticated) {
      loadMappings();
    }
  }, [isAuthenticated]);

  // Generer la liste des mois pour la periode (basee sur le mois selectionne)
  const getMonthsInPeriod = useCallback((numMonths: number): string[] => {
    const months: string[] = [];
    // Utiliser le mois selectionne comme point de reference au lieu de la date actuelle
    const [selectedYear, selectedMonth] = month.split('-').map(Number);
    const baseDate = new Date(selectedYear, selectedMonth - 1, 1);

    for (let i = 0; i < numMonths; i++) {
      const d = new Date(baseDate.getFullYear(), baseDate.getMonth() - i, 1);
      const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      months.push(monthStr);
    }

    return months;
  }, [month]);

  // Charger les transactions mois par mois
  const loadData = useCallback(async () => {
    if (!isAuthenticated) return;

    // Éviter le rechargement si on vient de modifier un tag (dans les 2 dernières secondes)
    const timeSinceLastModification = Date.now() - lastTagModificationRef.current;
    if (timeSinceLastModification < 2000) {
      console.log('[Analytics] loadData SKIPPED (tag modified', timeSinceLastModification, 'ms ago)');
      return;
    }

    console.log('[Analytics] loadData called! periodMonths:', periodMonths);

    try {
      setLoading(true);
      setError("");

      // Obtenir la liste des mois a charger
      const monthsToLoad = getMonthsInPeriod(periodMonths);

      // Charger les transactions pour chaque mois en parallele
      const promises = monthsToLoad.map(m =>
        api.get('/transactions', { params: { month: m } })
          .then(res => {
            // L'API retourne maintenant un objet paginé { items: [...], total, page, ... }
            const data = res.data || {};
            return data.items || data || [];
          })
          .catch(() => []) // Ignorer les erreurs individuelles
      );

      const results = await Promise.all(promises);

      // Combiner toutes les transactions
      const allTransactions = results.flat();

      setTransactions(allTransactions);
    } catch (err: any) {
      setError("Erreur lors du chargement des donnees");
      console.error("Erreur analytics:", err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, periodMonths, getMonthsInPeriod]);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, periodMonths, loadData, month]);

  // Extraire tous les tags uniques des transactions
  useEffect(() => {
    if (transactions.length > 0) {
      const tagsSet = new Set<string>();
      transactions.forEach(tx => {
        (tx.tags || []).forEach(tag => {
          if (tag && tag.toLowerCase() !== 'non classe' && tag.toLowerCase() !== 'non classé') {
            tagsSet.add(tag.toLowerCase());
          }
        });
      });
      setAvailableTags(Array.from(tagsSet).sort());
    }
  }, [transactions]);

  // Handler pour rediriger vers la page Transactions pour modifier le tag
  const handleEditTag = useCallback((tx: Transaction) => {
    // Rediriger vers la page Transactions avec l'ID de la transaction à éditer
    const txMonth = tx.month || tx.date_op?.substring(0, 7) || month;
    router.push(`/transactions?editTx=${tx.id}&month=${txMonth}`);
  }, [router, month]);

  // État pour le message de confirmation
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // État pour le téléchargement PDF
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Handler pour télécharger le PDF
  const handleDownloadPdf = useCallback(async () => {
    setDownloadingPdf(true);
    try {
      await pdfExportApi.downloadAndSave(month);
      setSuccessMessage('PDF téléchargé avec succès !');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error: any) {
      console.error('Erreur téléchargement PDF:', error);
      setSuccessMessage(null);
      alert(error.message || 'Erreur lors du téléchargement du PDF');
    } finally {
      setDownloadingPdf(false);
    }
  }, [month]);

  // Handler pour sauvegarder le nouveau tag
  const handleSaveTag = useCallback(async () => {
    if (!editingTransaction || !newTagInput.trim()) return;

    const oldTag = editingTransaction.tags?.[0]?.toLowerCase() || '';
    const newTag = newTagInput.trim().toLowerCase();
    const tagChanged = oldTag !== newTag;
    const editedTxId = editingTransaction.id;

    setSavingTag(true);
    try {
      // Appeler l'API pour mettre à jour le tag
      const response = await api.patch(`/transactions/${editingTransaction.id}/tags`, {
        tags: [newTag]
      });

      console.log('[Analytics] Tag update response:', response.data);
      console.log('[Analytics] Tag changed:', { oldTag, newTag, tagChanged, txId: editedTxId });

      // Fermer le modal
      setEditingTransaction(null);
      setNewTagInput('');

      // Afficher message de confirmation
      if (tagChanged) {
        setSuccessMessage(`Transaction déplacée vers "${newTag}"`);
        setTimeout(() => setSuccessMessage(null), 3000);

        // *** IMPORTANT: Marquer le timestamp pour bloquer les reloads pendant 2 secondes ***
        lastTagModificationRef.current = Date.now();
        console.log('[Analytics] Tag modification timestamp set:', lastTagModificationRef.current);

        // *** IMPORTANT: Mettre à jour l'état transactions DIRECTEMENT ***
        // Ceci garantit que categoryStats sera recalculé avec les bonnes données
        console.log('[Analytics] Updating transactions state for tx', editedTxId, 'to tag:', newTag);
        setTransactions(prevTransactions => {
          const updated = prevTransactions.map(tx =>
            tx.id === editedTxId
              ? { ...tx, tags: [newTag] }
              : tx
          );
          console.log('[Analytics] Transactions state updated. Total:', updated.length, 'Modified tx tags:', updated.find(t => t.id === editedTxId)?.tags);
          return updated;
        });

        // Mettre à jour immédiatement la liste locale pour retirer la transaction de la vue actuelle
        const txAmount = Math.abs(editingTransaction.amount);

        if (selectedTag && selectedTag.transactions) {
          const updatedTransactions = selectedTag.transactions.filter(tx => tx.id !== editedTxId);
          const newTotal = updatedTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
          setSelectedTag({
            ...selectedTag,
            transactions: updatedTransactions,
            count: updatedTransactions.length,
            total: newTotal
          });

          // *** IMPORTANT: Mettre à jour aussi selectedCategory pour refléter le changement ***
          if (selectedCategory) {
            const updatedTags = selectedCategory.tags.map(tag => {
              if (tag.name === selectedTag.name) {
                // Retirer la transaction de l'ancien tag
                return {
                  ...tag,
                  transactions: updatedTransactions,
                  count: updatedTransactions.length,
                  total: newTotal
                };
              }
              return tag;
            });

            // Calculer le nouveau total de la catégorie
            const newCategoryTotal = updatedTags.reduce((sum, tag) => sum + tag.total, 0);
            const newCategoryCount = updatedTags.reduce((sum, tag) => sum + tag.count, 0);

            console.log('[Analytics] Updating selectedCategory after tag change:', {
              oldTotal: selectedCategory.total,
              newTotal: newCategoryTotal,
              tagName: selectedTag.name
            });

            setSelectedCategory({
              ...selectedCategory,
              tags: updatedTags,
              total: newCategoryTotal,
              count: newCategoryCount
            });
          }
        }

        if (selectedCategoryMonth && selectedCategoryMonth.transactions) {
          const updatedTransactions = selectedCategoryMonth.transactions.filter(tx => tx.id !== editedTxId);
          const newTotal = updatedTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
          setSelectedCategoryMonth({
            ...selectedCategoryMonth,
            transactions: updatedTransactions,
            count: updatedTransactions.length,
            total: newTotal,
            tag: {
              ...selectedCategoryMonth.tag,
              transactions: updatedTransactions,
              count: updatedTransactions.length,
              total: newTotal
            }
          });

          // *** IMPORTANT: Mettre à jour aussi selectedCategory pour category-month view ***
          if (selectedCategory) {
            const updatedTags = selectedCategory.tags.map(tag => {
              if (tag.name === selectedCategoryMonth.tag.name) {
                const updatedTagTransactions = (tag.transactions || []).filter(tx => tx.id !== editedTxId);
                return {
                  ...tag,
                  transactions: updatedTagTransactions,
                  count: updatedTagTransactions.length,
                  total: updatedTagTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0)
                };
              }
              return tag;
            });

            const newCategoryTotal = updatedTags.reduce((sum, tag) => sum + tag.total, 0);
            const newCategoryCount = updatedTags.reduce((sum, tag) => sum + tag.count, 0);

            setSelectedCategory({
              ...selectedCategory,
              tags: updatedTags,
              total: newCategoryTotal,
              count: newCategoryCount
            });
          }
        }
      } else {
        setSuccessMessage('Tag mis à jour');
        setTimeout(() => setSuccessMessage(null), 2000);
      }

      // Note: On ne recharge plus les données via loadData() car on a déjà mis à jour l'état local
      // Cela évite les problèmes de timing et garantit une mise à jour instantanée

    } catch (error: any) {
      console.error('Erreur lors de la mise à jour du tag:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Erreur inconnue';
      alert(`Erreur lors de la mise à jour du tag: ${errorMessage}`);
    } finally {
      setSavingTag(false);
    }
  }, [editingTransaction, newTagInput, selectedTag, selectedCategoryMonth, selectedCategory]);

  // Handler pour fermer le modal
  const handleCloseEditModal = useCallback(() => {
    setEditingTransaction(null);
    setNewTagInput('');
  }, []);

  // Calculer les statistiques par categorie
  // NOTE: Inclut tous les tags, meme non categorises (dans "autres")
  const categoryStats = useMemo((): CategoryData[] => {
    if (!transactions.length) return [];

    // Agregation par tag (exclure les transactions sans tags)
    const tagMap = new Map<string, { total: number; count: number; monthly: Map<string, number>; transactions: Transaction[] }>();

    transactions.forEach(tx => {
      if (tx.amount >= 0) return; // Ignorer les revenus

      const amount = Math.abs(tx.amount);
      const txMonth = tx.month || tx.date_op?.substring(0, 7);
      const txTags = tx.tags || [];

      // Exclure les transactions sans tags
      if (txTags.length === 0) return;

      txTags.forEach(tag => {
        // Ignorer les tags "Non classe" ou vides
        if (!tag || tag.toLowerCase() === 'non classe' || tag.toLowerCase() === 'non classé') return;

        if (!tagMap.has(tag)) {
          tagMap.set(tag, { total: 0, count: 0, monthly: new Map(), transactions: [] });
        }
        const data = tagMap.get(tag)!;
        data.total += amount;
        data.count += 1;
        data.transactions.push(tx);

        if (txMonth) {
          data.monthly.set(txMonth, (data.monthly.get(txMonth) || 0) + amount);
        }
      });
    });

    // Grouper par categorie (inclure 'autres' pour les tags non mappes)
    const categoryMap = new Map<string, {
      total: number;
      count: number;
      tags: TagData[];
      monthly: Map<string, number>;
    }>();

    // Initialiser toutes les categories
    DEFAULT_CATEGORIES.forEach(cat => {
      categoryMap.set(cat.id, { total: 0, count: 0, tags: [], monthly: new Map() });
    });

    tagMap.forEach((data, tagName) => {
      const categoryId = tagCategoryMap[tagName] || 'autres';

      if (!categoryMap.has(categoryId)) {
        categoryMap.set(categoryId, { total: 0, count: 0, tags: [], monthly: new Map() });
      }

      const catData = categoryMap.get(categoryId)!;
      catData.total += data.total;
      catData.count += data.count;
      catData.tags.push({
        name: tagName,
        total: data.total,
        count: data.count,
        categoryId,
        transactions: data.transactions
      });

      // Agregation mensuelle pour la categorie
      data.monthly.forEach((amount, month) => {
        catData.monthly.set(month, (catData.monthly.get(month) || 0) + amount);
      });
    });

    // Convertir en array avec calculs de variation
    const result: CategoryData[] = [];

    DEFAULT_CATEGORIES.forEach(cat => {
      const data = categoryMap.get(cat.id);
      if (!data || data.total === 0) return;

      const monthlyData = Array.from(data.monthly.entries())
        .map(([month, amount]) => ({ month, amount }))
        .sort((a, b) => a.month.localeCompare(b.month));

      const avgMonthly = monthlyData.length > 0
        ? monthlyData.reduce((sum, m) => sum + m.amount, 0) / monthlyData.length
        : 0;

      // Calculer la variation (dernier mois vs moyenne)
      const lastMonth = monthlyData[monthlyData.length - 1];
      const variation = lastMonth && avgMonthly > 0
        ? ((lastMonth.amount - avgMonthly) / avgMonthly) * 100
        : 0;

      result.push({
        id: cat.id,
        name: cat.name,
        icon: cat.icon,
        color: cat.color,
        total: data.total,
        count: data.count,
        tags: data.tags.sort((a, b) => b.total - a.total),
        monthlyData,
        avgMonthly,
        variation
      });
    });

    return result.sort((a, b) => b.total - a.total);
  }, [transactions, tagCategoryMap]);

  // Synchroniser les états selectedCategory et selectedTag quand categoryStats change
  // Ceci permet de mettre à jour la vue après un changement de tag
  useEffect(() => {
    console.log('[Analytics] Sync useEffect triggered. categoryStats length:', categoryStats.length, 'selectedCategory:', selectedCategory?.id, 'selectedTag:', selectedTag?.name);

    if (!categoryStats.length) return;

    // Mettre à jour selectedCategory si elle existe
    if (selectedCategory) {
      const updatedCategory = categoryStats.find(cat => cat.id === selectedCategory.id);
      if (updatedCategory) {
        // Comparer les tags individuellement pour détecter les changements internes
        // (ex: déplacement d'une transaction d'un tag à un autre dans la même catégorie)
        const tagsChanged = () => {
          if (updatedCategory.tags.length !== selectedCategory.tags.length) return true;
          for (const updatedTag of updatedCategory.tags) {
            const oldTag = selectedCategory.tags.find(t => t.name === updatedTag.name);
            if (!oldTag) return true;
            if (oldTag.total !== updatedTag.total || oldTag.count !== updatedTag.count) return true;
          }
          return false;
        };

        // Vérifier si les données ont changé (y compris les tags individuels)
        if (updatedCategory.total !== selectedCategory.total ||
            updatedCategory.count !== selectedCategory.count ||
            tagsChanged()) {
          console.log('[Analytics] Syncing selectedCategory after tag change');
          setSelectedCategory(updatedCategory);

          // Mettre à jour selectedTag si elle existe dans cette catégorie
          if (selectedTag) {
            const updatedTag = updatedCategory.tags.find(tag => tag.name === selectedTag.name);
            if (updatedTag) {
              if (updatedTag.total !== selectedTag.total ||
                  updatedTag.count !== selectedTag.count) {
                console.log('[Analytics] Syncing selectedTag after tag change');
                setSelectedTag(updatedTag);
              }
            } else {
              // Le tag n'existe plus dans cette catégorie, retourner à la vue catégorie
              console.log('[Analytics] Tag removed from category, going back');
              setSelectedTag(null);
              if (drillLevel === 'transactions') {
                setDrillLevel('tags');
              }
            }
          }
        }
      }
    }

    // Mettre à jour selectedCategoryMonth si elle existe
    if (selectedCategoryMonth && selectedCategory) {
      const updatedCategory = categoryStats.find(cat => cat.id === selectedCategory.id);
      if (updatedCategory) {
        const updatedTag = updatedCategory.tags.find(tag => tag.name === selectedCategoryMonth.tag.name);
        if (updatedTag) {
          // Filtrer les transactions pour le mois spécifique
          const monthTransactions = (updatedTag.transactions || []).filter(tx => {
            const txMonth = tx.month || tx.date_op?.substring(0, 7);
            return txMonth === selectedCategoryMonth.month;
          });
          const newTotal = monthTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

          if (monthTransactions.length !== selectedCategoryMonth.transactions.length ||
              newTotal !== selectedCategoryMonth.total) {
            setSelectedCategoryMonth({
              ...selectedCategoryMonth,
              transactions: monthTransactions,
              count: monthTransactions.length,
              total: newTotal,
              tag: updatedTag
            });
          }
        }
      }
    }
  }, [categoryStats]); // Déclenché uniquement quand categoryStats change

  // Totaux globaux
  const totals = useMemo(() => {
    const total = categoryStats.reduce((sum, cat) => sum + cat.total, 0);
    const avgMonthly = categoryStats.reduce((sum, cat) => sum + cat.avgMonthly, 0);
    const transactionCount = categoryStats.reduce((sum, cat) => sum + cat.count, 0);
    return { total, avgMonthly, transactionCount };
  }, [categoryStats]);

  // Donnees pour le graphique mensuel global
  const monthlyChartData = useMemo(() => {
    const monthlyMap = new Map<string, number>();

    categoryStats.forEach(cat => {
      cat.monthlyData.forEach(m => {
        monthlyMap.set(m.month, (monthlyMap.get(m.month) || 0) + m.amount);
      });
    });

    const monthNames = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aout', 'Sep', 'Oct', 'Nov', 'Dec'];

    return Array.from(monthlyMap.entries())
      .map(([month, total]) => {
        const monthNum = parseInt(month.split('-')[1]) - 1;
        return {
          month,
          monthLabel: monthNames[monthNum] || month,
          total
        };
      })
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [categoryStats]);

  // Calculer les stats par mois pour drill-down
  const getMonthTagsData = useCallback((monthStr: string): MonthTagData => {
    const monthNames = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'];
    const monthNum = parseInt(monthStr.split('-')[1]) - 1;
    const year = monthStr.split('-')[0];
    const monthLabel = `${monthNames[monthNum]} ${year}`;

    // Filtrer les transactions du mois (uniquement depenses taguees et categorisees)
    const monthTransactions = transactions.filter(tx => {
      if (tx.amount >= 0) return false;
      const txMonth = tx.month || tx.date_op?.substring(0, 7);
      if (txMonth !== monthStr) return false;
      const txTags = tx.tags || [];
      if (txTags.length === 0) return false;
      // Verifier qu'au moins un tag est categorise
      return txTags.some(tag => tagCategoryMap[tag] && tagCategoryMap[tag] !== 'autres');
    });

    // Agreger par tag
    const tagMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();

    monthTransactions.forEach(tx => {
      const amount = Math.abs(tx.amount);
      (tx.tags || []).forEach(tag => {
        // Exclure les tags non categorises
        if (!tagCategoryMap[tag] || tagCategoryMap[tag] === 'autres') return;

        if (!tagMap.has(tag)) {
          tagMap.set(tag, { total: 0, count: 0, transactions: [] });
        }
        const data = tagMap.get(tag)!;
        data.total += amount;
        data.count += 1;
        data.transactions.push(tx);
      });
    });

    const tags: TagData[] = Array.from(tagMap.entries())
      .map(([name, data]) => ({
        name,
        total: data.total,
        count: data.count,
        categoryId: tagCategoryMap[name],
        transactions: data.transactions
      }))
      .sort((a, b) => b.total - a.total);

    const total = tags.reduce((sum, t) => sum + t.total, 0);
    const count = tags.reduce((sum, t) => sum + t.count, 0);

    return { month: monthStr, monthLabel, total, count, tags };
  }, [transactions, tagCategoryMap]);

  // Handler pour clic sur barre du graphique
  const handleMonthClick = (data: any) => {
    if (data && data.activePayload && data.activePayload[0]) {
      const monthStr = data.activePayload[0].payload.month;
      const monthData = getMonthTagsData(monthStr);
      setSelectedMonth(monthData);
      setSelectedCategory(null);
      setSelectedTag(null);
      setDrillLevel('month-tags');
    }
  };

  // Navigation drill-down
  const handleCategoryClick = (category: CategoryData) => {
    setSelectedCategory(category);
    setSelectedTag(null);
    setSelectedMonth(null);
    setDrillLevel('tags');
  };

  const handleTagClick = (tag: TagData) => {
    setSelectedTag(tag);
    setDrillLevel('transactions');
  };

  const handleMonthTagClick = (tag: TagData) => {
    setSelectedTag(tag);
    setDrillLevel('month-transactions');
  };

  // Handler pour clic sur le graphique mensuel dans la vue categorie
  const handleCategoryMonthClick = useCallback((data: any, tag: TagData) => {
    console.log('[Analytics] handleCategoryMonthClick called', { data, tag, selectedCategory });
    if (!selectedCategory || !data || !data.activePayload || !data.activePayload[0]) {
      console.log('[Analytics] Early return - missing data:', { selectedCategory: !!selectedCategory, data: !!data, activePayload: data?.activePayload });
      return;
    }

    const monthStr = data.activePayload[0].payload.month;
    console.log('[Analytics] Drill-down to month:', monthStr, 'for tag:', tag.name);
    const monthNames = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'];
    const monthNum = parseInt(monthStr.split('-')[1]) - 1;
    const year = monthStr.split('-')[0];
    const monthLabel = `${monthNames[monthNum]} ${year}`;

    // Filtrer les transactions du tag pour ce mois specifique
    const monthTransactions = (tag.transactions || []).filter(tx => {
      const txMonth = tx.month || tx.date_op?.substring(0, 7);
      return txMonth === monthStr;
    });

    const total = monthTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

    setSelectedCategoryMonth({
      month: monthStr,
      monthLabel,
      category: selectedCategory,
      tag: {
        ...tag,
        transactions: monthTransactions,
        total,
        count: monthTransactions.length
      },
      transactions: monthTransactions,
      total,
      count: monthTransactions.length
    });
    setDrillLevel('category-month-transactions');
  }, [selectedCategory]);

  // Fonction utilitaire pour recalculer une catégorie depuis transactions
  const recalculateCategoryFromTransactions = useCallback((categoryId: string) => {
    if (!categoryId) return null;

    // Recalculer directement depuis les transactions actuelles
    const tagMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();

    transactions.forEach(tx => {
      if (tx.amount >= 0) return;
      const amount = Math.abs(tx.amount);
      const txTags = tx.tags || [];
      if (txTags.length === 0) return;

      txTags.forEach(tag => {
        if (!tag || tag.toLowerCase() === 'non classe' || tag.toLowerCase() === 'non classé') return;
        const tagCategoryId = tagCategoryMap[tag] || 'autres';

        if (tagCategoryId === categoryId) {
          if (!tagMap.has(tag)) {
            tagMap.set(tag, { total: 0, count: 0, transactions: [] });
          }
          const data = tagMap.get(tag)!;
          data.total += amount;
          data.count += 1;
          data.transactions.push(tx);
        }
      });
    });

    const categoryDef = DEFAULT_CATEGORIES.find(c => c.id === categoryId);
    if (!categoryDef) return null;

    const tags: TagData[] = Array.from(tagMap.entries()).map(([name, data]) => ({
      name,
      total: data.total,
      count: data.count,
      categoryId,
      transactions: data.transactions
    })).sort((a, b) => b.total - a.total);

    const total = tags.reduce((sum, t) => sum + t.total, 0);
    const count = tags.reduce((sum, t) => sum + t.count, 0);

    return {
      id: categoryId,
      name: categoryDef.name,
      icon: categoryDef.icon,
      color: categoryDef.color,
      total,
      count,
      tags,
      monthlyData: [],
      avgMonthly: 0,
      variation: 0
    };
  }, [transactions, tagCategoryMap]);

  const handleBack = useCallback(() => {
    if (drillLevel === 'transactions') {
      setSelectedTag(null);
      // *** IMPORTANT: Recalculer selectedCategory DIRECTEMENT depuis transactions ***
      if (selectedCategory) {
        const freshCategory = recalculateCategoryFromTransactions(selectedCategory.id);
        if (freshCategory) {
          console.log('[Analytics] handleBack: Recalculated category from transactions:', {
            id: freshCategory.id,
            total: freshCategory.total,
            tagCount: freshCategory.tags.length
          });
          setSelectedCategory(freshCategory);
        }
      }
      setDrillLevel('tags');
    } else if (drillLevel === 'tags') {
      setSelectedCategory(null);
      setDrillLevel('categories');
    } else if (drillLevel === 'month-transactions') {
      setSelectedTag(null);
      setDrillLevel('month-tags');
    } else if (drillLevel === 'month-tags') {
      setSelectedMonth(null);
      setDrillLevel('categories');
    } else if (drillLevel === 'category-month-transactions') {
      setSelectedCategoryMonth(null);
      // *** IMPORTANT: Recalculer selectedCategory DIRECTEMENT depuis transactions ***
      if (selectedCategory) {
        const freshCategory = recalculateCategoryFromTransactions(selectedCategory.id);
        if (freshCategory) {
          console.log('[Analytics] handleBack: Recalculated category (category-month)');
          setSelectedCategory(freshCategory);
        }
      }
      setDrillLevel('tags');
    }
  }, [drillLevel, selectedCategory, recalculateCategoryFromTransactions]);

  // Rendu conditionnel
  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return null;
  }

  // ============================================================================
  // VUE: TRANSACTIONS (niveau 3)
  // ============================================================================
  if (drillLevel === 'transactions' && selectedTag) {
    return (
      <main className="container mx-auto px-3 md:px-4 py-3 md:py-6 space-y-4 md:space-y-6">
        {/* Breadcrumb */}
        <div className="flex flex-wrap items-center gap-2 text-xs md:text-sm text-gray-600 dark:text-gray-400">
          <button onClick={() => { setDrillLevel('categories'); setSelectedCategory(null); setSelectedTag(null); }}
            className="hover:text-blue-600 min-h-[44px] px-2">Categories</button>
          <span>/</span>
          <button onClick={handleBack} className="hover:text-blue-600 min-h-[44px] px-2 truncate">
            {selectedCategory?.icon} {selectedCategory?.name}
          </button>
          <span>/</span>
          <span className="font-semibold text-gray-900 dark:text-white truncate">{selectedTag.name}</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 md:gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 min-h-[44px] min-w-[44px] flex-shrink-0">
            <span className="text-xl">&#8592;</span>
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white truncate">
              {selectedTag.name}
            </h1>
            <p className="text-xs md:text-base text-gray-500 truncate">
              {selectedTag.count} trans. - {selectedTag.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
            </p>
          </div>
        </div>

        {/* Liste des transactions */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[500px]">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="text-left p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Date</th>
                  <th className="text-left p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Libelle</th>
                  <th className="text-left p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Tag</th>
                  <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Montant</th>
                </tr>
              </thead>
              <tbody>
                {[...(selectedTag.transactions || [])]
                  .sort((a, b) => b.date_op.localeCompare(a.date_op))
                  .map((tx, idx) => (
                    <tr key={tx.id || idx} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="p-2 md:p-4 text-xs md:text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                        {new Date(tx.date_op).toLocaleDateString('fr-FR')}
                      </td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-gray-900 dark:text-white truncate max-w-[150px] md:max-w-none">{tx.label}</td>
                      <td className="p-2 md:p-4">
                        <button
                          onClick={() => handleEditTag(tx)}
                          className="inline-flex items-center gap-1 px-2 py-1.5 text-xs md:text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800/50 transition-colors min-h-[44px]"
                          title="Cliquez pour modifier le tag"
                        >
                          <span className="truncate max-w-[80px] md:max-w-none">{tx.tags?.[0] || 'Non tagué'}</span>
                          <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                      </td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right font-mono text-red-600 whitespace-nowrap">
                        -{Math.abs(tx.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal d'edition de tag */}
        {editingTransaction && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleCloseEditModal}>
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Modifier le tag</h3>
                <button onClick={handleCloseEditModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Transaction:</p>
                <p className="font-medium text-gray-900 dark:text-white truncate">{editingTransaction.label}</p>
                <p className="text-sm text-red-600">
                  {Math.abs(editingTransaction.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nouveau tag:
                </label>
                <input
                  type="text"
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Entrez un tag..."
                  list="available-tags"
                />
                <datalist id="available-tags">
                  {availableTags.map(tag => (
                    <option key={tag} value={tag} />
                  ))}
                </datalist>
              </div>

              {availableTags.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Tags existants:</p>
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto focus:outline-none scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
                    {availableTags.slice(0, 20).map(tag => (
                      <button
                        key={tag}
                        onClick={() => setNewTagInput(tag)}
                        className={`px-2 py-1 text-sm rounded-lg transition-colors ${
                          newTagInput === tag
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleCloseEditModal}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleSaveTag}
                  disabled={savingTag || !newTagInput.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {savingTag ? 'Sauvegarde...' : 'Sauvegarder'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    );
  }

  // ============================================================================
  // VUE: MONTH-TRANSACTIONS (transactions d'un mois pour un tag)
  // ============================================================================
  if (drillLevel === 'month-transactions' && selectedMonth && selectedTag) {
    const categoryInfo = selectedTag.categoryId ? DEFAULT_CATEGORIES.find(c => c.id === selectedTag.categoryId) : null;
    return (
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <button onClick={() => { setDrillLevel('categories'); setSelectedCategory(null); setSelectedTag(null); setSelectedMonth(null); }}
            className="hover:text-blue-600">Vue globale</button>
          <span>/</span>
          <button onClick={() => { setDrillLevel('month-tags'); setSelectedTag(null); }} className="hover:text-blue-600">
            {selectedMonth.monthLabel}
          </button>
          <span>/</span>
          <span className="font-semibold text-gray-900 dark:text-white">{selectedTag.name}</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600">
            <span className="text-xl">&#8592;</span>
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {selectedTag.name} - {selectedMonth.monthLabel}
            </h1>
            <p className="text-gray-500">
              {selectedTag.count} transactions - {selectedTag.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              {categoryInfo && <span className="ml-2" style={{ color: categoryInfo.color }}>{categoryInfo.icon} {categoryInfo.name}</span>}
            </p>
          </div>
        </div>

        {/* Liste des transactions */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Date</th>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Libelle</th>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Tag</th>
                  <th className="text-right p-4 font-medium text-gray-600 dark:text-gray-400">Montant</th>
                </tr>
              </thead>
              <tbody>
                {[...(selectedTag.transactions || [])]
                  .sort((a, b) => b.date_op.localeCompare(a.date_op))
                  .map((tx, idx) => (
                    <tr key={tx.id || idx} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="p-4 text-gray-600 dark:text-gray-400">
                        {new Date(tx.date_op).toLocaleDateString('fr-FR')}
                      </td>
                      <td className="p-4 text-gray-900 dark:text-white">{tx.label}</td>
                      <td className="p-4">
                        <button
                          onClick={() => handleEditTag(tx)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800/50 transition-colors"
                          title="Cliquez pour modifier le tag"
                        >
                          <span>{tx.tags?.[0] || 'Non tagué'}</span>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                      </td>
                      <td className="p-4 text-right font-mono text-red-600">
                        -{Math.abs(tx.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal d'edition de tag */}
        {editingTransaction && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleCloseEditModal}>
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Modifier le tag</h3>
                <button onClick={handleCloseEditModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Transaction:</p>
                <p className="font-medium text-gray-900 dark:text-white truncate">{editingTransaction.label}</p>
                <p className="text-sm text-red-600">
                  {Math.abs(editingTransaction.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nouveau tag:
                </label>
                <input
                  type="text"
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Entrez un tag..."
                  list="available-tags-month"
                />
                <datalist id="available-tags-month">
                  {availableTags.map(tag => (
                    <option key={tag} value={tag} />
                  ))}
                </datalist>
              </div>

              {availableTags.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Tags existants:</p>
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto focus:outline-none scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
                    {availableTags.slice(0, 20).map(tag => (
                      <button
                        key={tag}
                        onClick={() => setNewTagInput(tag)}
                        className={`px-2 py-1 text-sm rounded-lg transition-colors ${
                          newTagInput === tag
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleCloseEditModal}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleSaveTag}
                  disabled={savingTag || !newTagInput.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {savingTag ? 'Sauvegarde...' : 'Sauvegarder'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    );
  }

  // ============================================================================
  // VUE: MONTH-TAGS (tags d'un mois specifique)
  // ============================================================================
  if (drillLevel === 'month-tags' && selectedMonth) {
    return (
      <main className="container mx-auto px-3 md:px-4 py-3 md:py-6 space-y-4 md:space-y-6">
        {/* Breadcrumb */}
        <div className="flex flex-wrap items-center gap-2 text-xs md:text-sm text-gray-600 dark:text-gray-400">
          <button onClick={() => { setDrillLevel('categories'); setSelectedMonth(null); }}
            className="hover:text-blue-600 min-h-[44px] px-2">Vue globale</button>
          <span>/</span>
          <span className="font-semibold text-gray-900 dark:text-white truncate">{selectedMonth.monthLabel}</span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 md:gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 min-h-[44px] min-w-[44px] flex-shrink-0">
            <span className="text-xl">&#8592;</span>
          </button>
          <div
            className="w-12 h-12 md:w-16 md:h-16 rounded-xl flex items-center justify-center text-2xl md:text-3xl bg-gradient-to-br from-blue-500 to-blue-600 text-white flex-shrink-0"
          >
            📅
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white truncate">
              {selectedMonth.monthLabel}
            </h1>
            <div className="flex flex-wrap gap-2 md:gap-4 text-xs md:text-base text-gray-500">
              <span className="whitespace-nowrap">{selectedMonth.tags.length} tags</span>
              <span className="whitespace-nowrap">{selectedMonth.count} trans.</span>
              <span className="font-bold text-red-600 whitespace-nowrap">
                {selectedMonth.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </span>
            </div>
          </div>
        </div>

        {/* Stats cartes */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Total du mois</p>
            <p className="text-lg md:text-2xl font-bold text-red-600">
              {selectedMonth.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
            </p>
          </Card>
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Nombre de tags</p>
            <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">
              {selectedMonth.tags.length}
            </p>
          </Card>
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Transactions</p>
            <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">
              {selectedMonth.count}
            </p>
          </Card>
        </div>

        {/* Pie chart des tags du mois - Cliquable */}
        <Card className="p-4 md:p-6">
          <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-gray-900 dark:text-white">
            Repartition des depenses - {selectedMonth.monthLabel}
            <span className="hidden md:inline text-sm font-normal text-gray-500 ml-2">(cliquez pour voir les transactions)</span>
          </h3>
          <div className="h-[250px] md:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={selectedMonth.tags.slice(0, 8)}
                  dataKey="total"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                  cursor="pointer"
                  onClick={(data, index) => {
                    console.log('[Analytics] Month pie slice clicked:', data, 'index:', index);
                    const tagsSlice = selectedMonth.tags.slice(0, 8);
                    if (data && typeof index === 'number' && tagsSlice[index]) {
                      handleMonthTagClick(tagsSlice[index]);
                    }
                  }}
                >
                  {selectedMonth.tags.slice(0, 8).map((tag, index) => {
                    const cat = DEFAULT_CATEGORIES.find(c => c.id === tag.categoryId);
                    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];
                    return (
                      <Cell
                        key={`cell-${index}`}
                        fill={cat?.color || colors[index % colors.length]}
                        className="hover:opacity-80 transition-opacity"
                      />
                    );
                  })}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      const cat = DEFAULT_CATEGORIES.find(c => c.id === data.categoryId);
                      return (
                        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                          <p className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            {cat && <span>{cat.icon}</span>} {data.name}
                          </p>
                          <p className="text-gray-600 dark:text-gray-400">
                            {data.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">{data.count} transactions</p>
                          <p className="text-xs text-blue-500 mt-1 font-medium">Cliquez pour voir les transactions</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  formatter={(value, entry: any) => {
                    const tag = selectedMonth.tags.find(t => t.name === value);
                    const cat = tag?.categoryId ? DEFAULT_CATEGORIES.find(c => c.id === tag.categoryId) : null;
                    return (
                      <span
                        className="text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (tag) handleMonthTagClick(tag);
                        }}
                      >
                        {cat?.icon} {value}
                      </span>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Liste des tags */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Tags ({selectedMonth.tags.length})
          </h3>
          <div className="space-y-2">
            {selectedMonth.tags.map(tag => {
              const percentage = selectedMonth.total > 0 ? (tag.total / selectedMonth.total) * 100 : 0;
              const categoryInfo = tag.categoryId ? DEFAULT_CATEGORIES.find(c => c.id === tag.categoryId) : null;
              return (
                <div
                  key={tag.name}
                  onClick={() => handleMonthTagClick(tag)}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {categoryInfo && (
                      <span className="text-xl" title={categoryInfo.name}>{categoryInfo.icon}</span>
                    )}
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">{tag.name}</span>
                      <span className="text-sm text-gray-500 ml-2">{tag.count} trans.</span>
                      {categoryInfo && (
                        <span className="text-xs ml-2" style={{ color: categoryInfo.color }}>{categoryInfo.name}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: categoryInfo?.color || '#3B82F6' }}
                      />
                    </div>
                    <span className="text-sm text-gray-500">{percentage.toFixed(1)}%</span>
                    <span className="font-semibold text-gray-900 dark:text-white min-w-[100px] text-right">
                      {tag.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                    </span>
                    <span className="text-gray-400">&#8594;</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </main>
    );
  }

  // ============================================================================
  // VUE: CATEGORY-MONTH-TRANSACTIONS (transactions d'un tag pour un mois specifique depuis vue categorie)
  // ============================================================================
  if (drillLevel === 'category-month-transactions' && selectedCategoryMonth && selectedCategory) {
    return (
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <button onClick={() => { setDrillLevel('categories'); setSelectedCategory(null); setSelectedCategoryMonth(null); }}
            className="hover:text-blue-600">Categories</button>
          <span>/</span>
          <button onClick={() => { setDrillLevel('tags'); setSelectedCategoryMonth(null); }} className="hover:text-blue-600">
            {selectedCategory.icon} {selectedCategory.name}
          </button>
          <span>/</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            {selectedCategoryMonth.tag.name} - {selectedCategoryMonth.monthLabel}
          </span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600">
            <span className="text-xl">&#8592;</span>
          </button>
          <div
            className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl"
            style={{ backgroundColor: selectedCategory.color + '20' }}
          >
            {selectedCategory.icon}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {selectedCategoryMonth.tag.name} - {selectedCategoryMonth.monthLabel}
            </h1>
            <div className="flex gap-4 text-gray-500">
              <span>{selectedCategoryMonth.count} transactions</span>
              <span className="font-bold text-red-600">
                {selectedCategoryMonth.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </span>
            </div>
          </div>
        </div>

        {/* Stats cartes */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-500">Total du mois</p>
            <p className="text-2xl font-bold text-red-600">
              {selectedCategoryMonth.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-500">Transactions</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {selectedCategoryMonth.count}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-500">Moyenne/transaction</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {selectedCategoryMonth.count > 0
                ? (selectedCategoryMonth.total / selectedCategoryMonth.count).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
                : '0 €'}
            </p>
          </Card>
        </div>

        {/* Liste des transactions */}
        <Card className="overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Transactions ({selectedCategoryMonth.count})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Date</th>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Libelle</th>
                  <th className="text-left p-4 font-medium text-gray-600 dark:text-gray-400">Tag</th>
                  <th className="text-right p-4 font-medium text-gray-600 dark:text-gray-400">Montant</th>
                </tr>
              </thead>
              <tbody>
                {[...selectedCategoryMonth.transactions]
                  .sort((a, b) => b.date_op.localeCompare(a.date_op))
                  .map((tx, idx) => (
                    <tr key={tx.id || idx} className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="p-4 text-gray-600 dark:text-gray-400">
                        {new Date(tx.date_op).toLocaleDateString('fr-FR')}
                      </td>
                      <td className="p-4 text-gray-900 dark:text-white">{tx.label}</td>
                      <td className="p-4">
                        <button
                          onClick={() => handleEditTag(tx)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800/50 transition-colors"
                          title="Cliquez pour modifier le tag"
                        >
                          <span>{tx.tags?.[0] || 'Non tagué'}</span>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                      </td>
                      <td className="p-4 text-right font-mono text-red-600">
                        -{Math.abs(tx.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal d'edition de tag */}
        {editingTransaction && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleCloseEditModal}>
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Modifier le tag</h3>
                <button onClick={handleCloseEditModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Transaction:</p>
                <p className="font-medium text-gray-900 dark:text-white truncate">{editingTransaction.label}</p>
                <p className="text-sm text-red-600">
                  {Math.abs(editingTransaction.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nouveau tag:
                </label>
                <input
                  type="text"
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Entrez un tag..."
                  list="available-tags-cat-month"
                />
                <datalist id="available-tags-cat-month">
                  {availableTags.map(tag => (
                    <option key={tag} value={tag} />
                  ))}
                </datalist>
              </div>

              {availableTags.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Tags existants:</p>
                  <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto focus:outline-none scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600">
                    {availableTags.slice(0, 20).map(tag => (
                      <button
                        key={tag}
                        onClick={() => setNewTagInput(tag)}
                        className={`px-2 py-1 text-sm rounded-lg transition-colors ${
                          newTagInput === tag
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleCloseEditModal}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleSaveTag}
                  disabled={savingTag || !newTagInput.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {savingTag ? 'Sauvegarde...' : 'Sauvegarder'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    );
  }

  // ============================================================================
  // VUE: TAGS (niveau 2)
  // ============================================================================
  if (drillLevel === 'tags' && selectedCategory) {
    return (
      <main className="container mx-auto px-3 md:px-4 py-3 md:py-6 space-y-4 md:space-y-6">
        {/* Breadcrumb */}
        <div className="flex flex-wrap items-center gap-2 text-xs md:text-sm text-gray-600 dark:text-gray-400">
          <button onClick={() => { setDrillLevel('categories'); setSelectedCategory(null); }}
            className="hover:text-blue-600 min-h-[44px] px-2">Categories</button>
          <span>/</span>
          <span className="font-semibold text-gray-900 dark:text-white truncate">
            {selectedCategory.icon} {selectedCategory.name}
          </span>
        </div>

        {/* Header */}
        <div className="flex items-center gap-3 md:gap-4">
          <button onClick={handleBack} className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 min-h-[44px] min-w-[44px] flex-shrink-0">
            <span className="text-xl">&#8592;</span>
          </button>
          <div
            className="w-12 h-12 md:w-16 md:h-16 rounded-xl flex items-center justify-center text-2xl md:text-3xl flex-shrink-0"
            style={{ backgroundColor: selectedCategory.color + '20' }}
          >
            {selectedCategory.icon}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white truncate">
              {selectedCategory.name}
            </h1>
            <div className="flex flex-wrap gap-2 md:gap-4 text-xs md:text-base text-gray-500">
              <span className="whitespace-nowrap">{selectedCategory.tags.length} tags</span>
              <span className="whitespace-nowrap">{selectedCategory.count} trans.</span>
              <span className="font-bold whitespace-nowrap" style={{ color: selectedCategory.color }}>
                {selectedCategory.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
              </span>
            </div>
          </div>
        </div>

        {/* Stats cartes */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Total periode</p>
            <p className="text-lg md:text-2xl font-bold" style={{ color: selectedCategory.color }}>
              {selectedCategory.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
            </p>
          </Card>
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Moyenne<span className="hidden xs:inline"> mensuelle</span></p>
            <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">
              {selectedCategory.avgMonthly.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
            </p>
          </Card>
          <Card className="p-3 md:p-4">
            <p className="text-xs md:text-sm text-gray-500">Variation<span className="hidden xs:inline"> vs moyenne</span></p>
            <p className={`text-lg md:text-2xl font-bold ${selectedCategory.variation > 0 ? 'text-red-600' : 'text-green-600'}`}>
              {selectedCategory.variation > 0 ? '+' : ''}{selectedCategory.variation.toFixed(1)}%
            </p>
          </Card>
        </div>

        {/* Graphique evolution mensuelle - cliquable pour voir les transactions du mois */}
        {selectedCategory.monthlyData.length > 0 && (
          <Card className="p-4 md:p-6">
            <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-gray-900 dark:text-white">
              Evolution mensuelle
              <span className="hidden md:inline text-sm font-normal text-gray-500 ml-2">(cliquez sur un mois pour voir le detail)</span>
            </h3>
            <div className="h-[200px] md:h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={selectedCategory.monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="month"
                    tickFormatter={(m) => {
                      const monthNames = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aout', 'Sep', 'Oct', 'Nov', 'Dec'];
                      const monthNum = parseInt(m.split('-')[1]) - 1;
                      return monthNames[monthNum] || m;
                    }}
                  />
                  <YAxis tickFormatter={(v) => `${v}€`} />
                  <Tooltip
                    formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                    labelFormatter={(m) => `Cliquez pour voir ${m}`}
                  />
                  <Bar
                    dataKey="amount"
                    fill={selectedCategory.color}
                    radius={[4, 4, 0, 0]}
                    name="Montant"
                    cursor="pointer"
                    onClick={(data) => {
                      console.log('[Analytics] Category month bar clicked:', data);
                      if (data && data.month) {
                        const monthStr = data.month;
                        const monthNames = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'];
                        const monthNum = parseInt(monthStr.split('-')[1]) - 1;
                        const year = monthStr.split('-')[0];
                        const monthLabel = `${monthNames[monthNum]} ${year}`;

                        // Collecter toutes les transactions de tous les tags pour ce mois
                        const allMonthTransactions: Transaction[] = [];
                        selectedCategory.tags.forEach(tag => {
                          const tagMonthTxs = (tag.transactions || []).filter((tx: any) => {
                            const txMonth = tx.month || tx.date_op?.substring(0, 7);
                            return txMonth === monthStr;
                          });
                          allMonthTransactions.push(...tagMonthTxs);
                        });

                        const total = allMonthTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

                        // Creer un tag "virtuel" pour representer toute la categorie
                        setSelectedCategoryMonth({
                          month: monthStr,
                          monthLabel,
                          category: selectedCategory,
                          tag: {
                            name: `Tous les tags (${selectedCategory.name})`,
                            total,
                            count: allMonthTransactions.length,
                            transactions: allMonthTransactions
                          },
                          transactions: allMonthTransactions,
                          total,
                          count: allMonthTransactions.length
                        });
                        setDrillLevel('category-month-transactions');
                      }
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey={() => selectedCategory.avgMonthly}
                    stroke="#EF4444"
                    strokeDasharray="5 5"
                    name="Moyenne"
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Liste des tags avec graphiques mensuels */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Tags ({selectedCategory.tags.length})
            <span className="text-sm font-normal text-gray-500 ml-2">(cliquez sur un mois du graphique pour filtrer)</span>
          </h3>
          <div className="space-y-4">
            {selectedCategory.tags.map(tag => {
              const percentage = selectedCategory.total > 0 ? (tag.total / selectedCategory.total) * 100 : 0;

              // Calculer les donnees mensuelles pour ce tag
              const tagMonthlyMap = new Map<string, number>();
              (tag.transactions || []).forEach(tx => {
                const txMonth = tx.month || tx.date_op?.substring(0, 7);
                if (txMonth) {
                  tagMonthlyMap.set(txMonth, (tagMonthlyMap.get(txMonth) || 0) + Math.abs(tx.amount));
                }
              });

              const tagMonthlyData = Array.from(tagMonthlyMap.entries())
                .map(([month, amount]) => {
                  const monthNames = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aout', 'Sep', 'Oct', 'Nov', 'Dec'];
                  const monthNum = parseInt(month.split('-')[1]) - 1;
                  return { month, monthLabel: monthNames[monthNum] || month, amount };
                })
                .sort((a, b) => a.month.localeCompare(b.month));

              return (
                <div
                  key={tag.name}
                  className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  {/* Header du tag */}
                  <div
                    onClick={() => handleTagClick(tag)}
                    className="flex items-center justify-between mb-3 cursor-pointer hover:opacity-80"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-900 dark:text-white text-lg">{tag.name}</span>
                      <span className="text-sm text-gray-500">{tag.count} trans.</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: selectedCategory.color }}
                        />
                      </div>
                      <span className="text-sm text-gray-500">{percentage.toFixed(1)}%</span>
                      <span className="font-semibold text-gray-900 dark:text-white min-w-[100px] text-right">
                        {tag.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                      </span>
                      <span className="text-gray-400">&#8594;</span>
                    </div>
                  </div>

                  {/* Mini graphique mensuel cliquable - afficher même avec 1 seul mois */}
                  {tagMonthlyData.length >= 1 && (
                    <div className="h-[120px] mt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={tagMonthlyData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="monthLabel" tick={{ fontSize: 11 }} />
                          <YAxis tickFormatter={(v) => `${v}€`} tick={{ fontSize: 11 }} width={50} />
                          <Tooltip
                            formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                            labelFormatter={(label) => `Cliquez pour voir ${label}`}
                          />
                          <Bar
                            dataKey="amount"
                            fill={selectedCategory.color}
                            radius={[2, 2, 0, 0]}
                            name="Montant"
                            cursor="pointer"
                            onClick={(data) => {
                              console.log('[Analytics] Bar clicked:', data);
                              if (data && data.month) {
                                const monthStr = data.month;
                                const monthNames = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'];
                                const monthNum = parseInt(monthStr.split('-')[1]) - 1;
                                const year = monthStr.split('-')[0];
                                const monthLabel = `${monthNames[monthNum]} ${year}`;

                                const monthTransactions = (tag.transactions || []).filter((tx: any) => {
                                  const txMonth = tx.month || tx.date_op?.substring(0, 7);
                                  return txMonth === monthStr;
                                });

                                const total = monthTransactions.reduce((sum: number, tx: any) => sum + Math.abs(tx.amount), 0);

                                setSelectedCategoryMonth({
                                  month: monthStr,
                                  monthLabel,
                                  category: selectedCategory,
                                  tag: {
                                    ...tag,
                                    transactions: monthTransactions,
                                    total,
                                    count: monthTransactions.length
                                  },
                                  transactions: monthTransactions,
                                  total,
                                  count: monthTransactions.length
                                });
                                setDrillLevel('category-month-transactions');
                              }
                            }}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </main>
    );
  }

  // ============================================================================
  // VUE: CATEGORIES (niveau 1 - defaut)
  // ============================================================================
  return (
    <main className="container mx-auto px-3 md:px-4 py-3 md:py-6 space-y-4 md:space-y-6">
      {/* Toast de confirmation */}
      {successMessage && (
        <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="bg-green-500 text-white px-3 md:px-4 py-2 md:py-3 rounded-lg shadow-lg flex items-center gap-2 text-sm md:text-base">
            <svg className="w-4 h-4 md:w-5 md:h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>{successMessage}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-0">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">
            Analyse des depenses
            {activeTab === 'drilldown' && (
              <span className="ml-2 md:ml-3 text-base md:text-lg font-normal text-blue-600 dark:text-blue-400 block xs:inline mt-1 xs:mt-0">
                {(() => {
                  const monthNames = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'];
                  const [year, monthNum] = month.split('-').map(Number);
                  if (periodMonths === 1) {
                    return `- ${monthNames[monthNum - 1]} ${year}`;
                  } else {
                    const startDate = new Date(year, monthNum - 1 - (periodMonths - 1), 1);
                    const startMonthName = monthNames[startDate.getMonth()];
                    return `- ${startMonthName} ${startDate.getFullYear()} à ${monthNames[monthNum - 1]} ${year}`;
                  }
                })()}
              </span>
            )}
          </h1>
          <p className="text-sm md:text-base text-gray-500 dark:text-gray-400 mt-1">
            {activeTab === 'drilldown' && 'Vue hierarchique: Categories → Tags → Transactions'}
            {activeTab === 'budget' && 'Comparez vos depenses reelles avec vos objectifs budgetaires'}
            {activeTab === 'ai' && 'Insights et predictions intelligentes'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 md:gap-4">
          {activeTab === 'drilldown' && (
            <div className="flex items-center gap-2">
              <span className="text-xs md:text-sm text-gray-500 whitespace-nowrap">Periode:</span>
              <select
                value={periodMonths}
                onChange={(e) => setPeriodMonths(parseInt(e.target.value))}
                className="px-2 md:px-3 py-1.5 md:py-2 text-xs md:text-sm border border-gray-300 rounded-lg bg-white dark:bg-gray-700 dark:border-gray-600 min-h-[44px]"
              >
                <option value={1}>Ce mois</option>
                <option value={3}>3 mois</option>
                <option value={6}>6 mois</option>
                <option value={12}>12 mois</option>
              </select>
            </div>
          )}
          {/* Bouton Export PDF */}
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-2 md:py-2 min-h-[44px] bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white rounded-lg text-xs md:text-sm font-medium transition-colors"
            title="Telecharger le rapport PDF du mois"
          >
            {downloadingPdf ? (
              <>
                <svg className="animate-spin h-4 w-4 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="hidden xs:inline">Export...</span>
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>PDF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Onglets de navigation */}
      <div className="overflow-x-auto -mx-3 md:mx-0 px-3 md:px-0">
        <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg w-fit min-w-full md:min-w-0">
          <button
            onClick={() => setActiveTab('drilldown')}
            className={`flex-1 md:flex-none px-3 md:px-4 py-2 rounded-md text-xs md:text-sm font-medium transition-all whitespace-nowrap min-h-[44px] ${
              activeTab === 'drilldown'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span className="hidden xs:inline">📊 </span>Drill-down<span className="hidden md:inline"> Depenses</span>
          </button>
          <button
            onClick={() => setActiveTab('budget')}
            className={`flex-1 md:flex-none px-3 md:px-4 py-2 rounded-md text-xs md:text-sm font-medium transition-all whitespace-nowrap min-h-[44px] ${
              activeTab === 'budget'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span className="hidden xs:inline">📈 </span>Budget<span className="hidden md:inline"> vs Reel</span>
          </button>
          <button
            onClick={() => setActiveTab('anomalies')}
            className={`flex-1 md:flex-none px-3 md:px-4 py-2 rounded-md text-xs md:text-sm font-medium transition-all whitespace-nowrap min-h-[44px] ${
              activeTab === 'anomalies'
                ? 'bg-white dark:bg-gray-700 text-orange-600 dark:text-orange-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span className="hidden xs:inline">🔍 </span>Anomalies<span className="hidden md:inline"> ML</span>
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`flex-1 md:flex-none px-3 md:px-4 py-2 rounded-md text-xs md:text-sm font-medium transition-all whitespace-nowrap min-h-[44px] ${
              activeTab === 'ai'
                ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span className="hidden xs:inline">🤖 </span>IA<span className="hidden md:inline"> Insights</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 md:p-4">
          <p className="text-sm md:text-base text-red-600">{error}</p>
        </div>
      )}

      {/* Contenu de l'onglet Budget vs Reel */}
      {activeTab === 'budget' && (
        <BudgetVarianceAnalysis month={month} />
      )}

      {/* Contenu de l'onglet Anomalies ML */}
      {activeTab === 'anomalies' && (
        <AnomaliesPanel
          month={month}
          onTransactionClick={(txId) => {
            router.push(`/transactions?editTx=${txId}&month=${month}`);
          }}
        />
      )}

      {/* Contenu de l'onglet IA Insights */}
      {activeTab === 'ai' && (
        <Card className="p-4 md:p-6">
          <div className="text-center py-6 md:py-8">
            <div className="text-5xl md:text-6xl mb-3 md:mb-4">🤖</div>
            <h3 className="text-lg md:text-xl font-semibold text-gray-900 dark:text-white mb-2">
              IA Insights - Bientot disponible
            </h3>
            <p className="text-sm md:text-base text-gray-500 dark:text-gray-400 max-w-md mx-auto px-4">
              Cette section inclura des predictions ML sur vos depenses,
              des alertes intelligentes et des recommandations personnalisees.
            </p>
            <p className="text-xs md:text-sm text-gray-400 mt-3 md:mt-4 px-4">
              En attendant, utilisez l'onglet "Budget vs Reel" pour obtenir des analyses IA de vos ecarts budgetaires.
            </p>
          </div>
        </Card>
      )}

      {/* Contenu de l'onglet Drill-down (existant) */}
      {activeTab === 'drilldown' && loading ? (
        <LoadingSpinner />
      ) : activeTab === 'drilldown' && (
        <>
          {/* Resume global */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-4">
            <Card className="p-3 md:p-6 bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20 border-red-200">
              <h3 className="text-xs md:text-sm font-medium text-red-600 mb-1">Total depenses</h3>
              <p className="text-base md:text-2xl font-bold text-red-900 dark:text-red-300">
                {totals.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
              </p>
            </Card>

            <Card className="p-3 md:p-6 bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200">
              <h3 className="text-xs md:text-sm font-medium text-blue-600 mb-1">Moyenne<span className="hidden xs:inline"> mensuelle</span></h3>
              <p className="text-base md:text-2xl font-bold text-blue-900 dark:text-blue-300">
                {totals.avgMonthly.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
              </p>
            </Card>

            <Card className="p-3 md:p-6 bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200">
              <h3 className="text-xs md:text-sm font-medium text-green-600 mb-1">Categories</h3>
              <p className="text-base md:text-2xl font-bold text-green-900 dark:text-green-300">{categoryStats.length}</p>
            </Card>

            <Card className="p-3 md:p-6 bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200">
              <h3 className="text-xs md:text-sm font-medium text-purple-600 mb-1">Transactions</h3>
              <p className="text-base md:text-2xl font-bold text-purple-900 dark:text-purple-300">{totals.transactionCount}</p>
            </Card>
          </div>

          {/* Graphiques cote a cote */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-6">
            {/* Pie Chart - Cliquable pour drill-down */}
            <Card className="p-4 md:p-6">
              <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-gray-900 dark:text-white">
                Repartition par categorie
                <span className="hidden md:inline text-sm font-normal text-gray-500 ml-2">(cliquez pour voir le detail)</span>
              </h3>
              <div className="h-[250px] md:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryStats}
                      dataKey="total"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                      cursor="pointer"
                      onClick={(data, index) => {
                        console.log('[Analytics] Pie slice clicked:', data, 'index:', index);
                        if (data && typeof index === 'number' && categoryStats[index]) {
                          handleCategoryClick(categoryStats[index]);
                        }
                      }}
                    >
                      {categoryStats.map((cat, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={cat.color}
                          className="hover:opacity-80 transition-opacity"
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
                              <p className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <span>{data.icon}</span> {data.name}
                              </p>
                              <p className="text-gray-600 dark:text-gray-400">
                                {data.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">{data.tags.length} tags • {data.count} trans.</p>
                              <p className="text-xs text-blue-500 mt-1 font-medium">Cliquez pour voir le detail</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Legend
                      layout="vertical"
                      align="right"
                      verticalAlign="middle"
                      formatter={(value, entry: any) => (
                        <span
                          className="text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            const cat = categoryStats.find(c => c.name === value);
                            if (cat) handleCategoryClick(cat);
                          }}
                        >
                          {entry.payload?.icon} {value}
                        </span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Evolution mensuelle - Cliquable pour drill-down */}
            <Card className="p-4 md:p-6">
              <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-gray-900 dark:text-white">
                Evolution mensuelle
                <span className="hidden md:inline text-sm font-normal text-gray-500 ml-2">(cliquez sur un mois pour voir le detail)</span>
              </h3>
              <div className="h-[250px] md:h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monthlyChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="monthLabel" />
                    <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k€`} />
                    <Tooltip
                      formatter={(value: number) => value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      labelFormatter={(label) => `Cliquez pour voir ${label}`}
                    />
                    <Bar
                      dataKey="total"
                      fill="#EF4444"
                      radius={[4, 4, 0, 0]}
                      name="Depenses"
                      cursor="pointer"
                      onClick={(data) => {
                        console.log('[Analytics] Global month bar clicked:', data);
                        if (data && data.month) {
                          const monthData = getMonthTagsData(data.month);
                          setSelectedMonth(monthData);
                          setSelectedCategory(null);
                          setSelectedTag(null);
                          setDrillLevel('month-tags');
                        }
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          {/* Liste des categories avec drill-down */}
          <Card className="p-4 md:p-6">
            <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-gray-900 dark:text-white">
              Categories <span className="hidden md:inline">(cliquez pour voir le detail)</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
              {categoryStats.map(category => (
                <div
                  key={category.id}
                  onClick={() => handleCategoryClick(category)}
                  className="p-3 md:p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md cursor-pointer transition-all min-h-[44px]"
                  style={{ borderLeftWidth: '4px', borderLeftColor: category.color }}
                >
                  <div className="flex items-center gap-2 md:gap-3 mb-2 md:mb-3">
                    <span className="text-xl md:text-2xl flex-shrink-0">{category.icon}</span>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm md:text-base font-semibold text-gray-900 dark:text-white truncate">{category.name}</h4>
                      <p className="text-xs md:text-sm text-gray-500">{category.tags.length} tags - {category.count} trans.</p>
                    </div>
                    <span className="text-gray-400 flex-shrink-0">&#8594;</span>
                  </div>
                  <div className="flex justify-between items-end gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-lg md:text-2xl font-bold truncate" style={{ color: category.color }}>
                        {category.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-xs md:text-sm text-gray-500 truncate">
                        Moy: {category.avgMonthly.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}/mois
                      </p>
                    </div>
                    <div className={`text-xs md:text-sm font-medium px-1.5 md:px-2 py-0.5 md:py-1 rounded flex-shrink-0 ${
                      category.variation > 10 ? 'bg-red-100 text-red-700' :
                        category.variation < -10 ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-700'
                    }`}>
                      {category.variation > 0 ? '+' : ''}{category.variation.toFixed(0)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Tableau detaille */}
          <Card className="overflow-hidden">
            <div className="px-3 md:px-6 py-3 md:py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <h3 className="text-base md:text-lg font-semibold text-gray-900 dark:text-white">Detail par categorie</h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="text-left p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Categorie</th>
                    <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Tags</th>
                    <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Trans.</th>
                    <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">Total</th>
                    <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400 hidden md:table-cell">Moy/mois</th>
                    <th className="text-right p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400 hidden md:table-cell">Var.</th>
                    <th className="w-20 md:w-32 p-2 md:p-4 text-xs md:text-sm font-medium text-gray-600 dark:text-gray-400">%</th>
                  </tr>
                </thead>
                <tbody>
                  {categoryStats.map(cat => {
                    const percentage = totals.total > 0 ? (cat.total / totals.total) * 100 : 0;
                    return (
                      <tr
                        key={cat.id}
                        onClick={() => handleCategoryClick(cat)}
                        className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                      >
                        <td className="p-2 md:p-4">
                          <div className="flex items-center gap-1.5 md:gap-2">
                            <span className="text-base md:text-xl flex-shrink-0">{cat.icon}</span>
                            <span className="text-xs md:text-sm font-medium text-gray-900 dark:text-white truncate">{cat.name}</span>
                          </div>
                        </td>
                        <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-600 dark:text-gray-400">{cat.tags.length}</td>
                        <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-600 dark:text-gray-400">{cat.count}</td>
                        <td className="p-2 md:p-4 text-xs md:text-sm text-right font-mono font-semibold" style={{ color: cat.color }}>
                          {cat.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-600 dark:text-gray-400 hidden md:table-cell">
                          {cat.avgMonthly.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-2 md:p-4 text-xs md:text-sm text-right hidden md:table-cell">
                          <span className={`font-medium ${cat.variation > 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {cat.variation > 0 ? '+' : ''}{cat.variation.toFixed(1)}%
                          </span>
                        </td>
                        <td className="p-2 md:p-4">
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5 md:h-2">
                            <div
                              className="h-1.5 md:h-2 rounded-full"
                              style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: cat.color }}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}

                  {totals.total > 0 && (
                    <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 font-semibold">
                      <td className="p-2 md:p-4 text-xs md:text-sm text-gray-900 dark:text-white">Total</td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-900 dark:text-white">
                        {categoryStats.reduce((sum, c) => sum + c.tags.length, 0)}
                      </td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-900 dark:text-white">{totals.transactionCount}</td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right font-mono text-red-600">
                        {totals.total.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                      </td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right text-gray-900 dark:text-white hidden md:table-cell">
                        {totals.avgMonthly.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })}
                      </td>
                      <td className="p-2 md:p-4 text-xs md:text-sm text-right hidden md:table-cell">-</td>
                      <td className="p-2 md:p-4">
                        <div className="w-full bg-gray-400 dark:bg-gray-500 rounded-full h-1.5 md:h-2" />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </main>
  );
}
