import { useState, useEffect, useMemo } from 'react';
import { api } from '../lib/api';

export interface CleanDashboardData {
  revenue: {
    gross: number;
    net: number;
    member1: { gross: number; net: number; name: string };
    member2: { gross: number; net: number; name: string };
  };
  provisions: {
    total: number;
    count: number;
    items: ProvisionItem[];
  };
  expenses: {
    total: number;
    fixed: number;
    variable: number;
    count: number;
    items: ExpenseItem[];
  };
  accountBalance: {
    current: number;
    endOfMonth: number;
  };
  familyProvision: {
    needed: number;
    status: 'surplus' | 'balanced' | 'deficit';
    member1: number;
    member2: number;
    // Détail par membre
    detail: {
      provisions: {
        total: number;
        member1: number;
        member2: number;
      };
      expenses: {
        total: number;  // Dépenses totales (part de chaque membre)
        member1: number;
        member2: number;
      };
    };
  };
}

export interface ProvisionItem {
  id: number;
  name: string;
  currentAmount: number;
  targetAmount?: number;
  percentage?: number;
  progress: number;
  category: string;
  totalProvisionedSinceJanuary?: number;
  monthProgress?: number;
}

export interface ExpenseItem {
  id: number;
  name: string;
  amount: number;
  category: string;
  type: 'fixed' | 'variable';
  tag?: string;
}

/**
 * Hook optimisé pour le dashboard épuré
 * Focus sur les données essentielles avec calculs simplifiés
 */
export const useCleanDashboard = (month: string, isAuthenticated: boolean) => {
  const [data, setData] = useState<CleanDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fonction de chargement des données
  const loadDashboardData = async () => {
    if (!isAuthenticated || !month) return;

    try {
      setLoading(true);
      setError(null);

      // Chargement parallèle des données essentielles + transactions réelles
      // IMPORTANT: limit=500 pour récupérer TOUTES les transactions du mois (défaut API = 50)
      const [configResponse, provisionsResponse, summaryResponse, transactionsResponse] = await Promise.all([
        api.get('/config'),
        api.get('/custom-provisions'),
        api.get(`/summary?month=${month}`),
        api.get(`/transactions?month=${month}&limit=500`)  // Récupérer toutes les transactions
      ]);

      const config = configResponse.data;
      const provisions = provisionsResponse.data;
      const summary = summaryResponse.data;
      // L'API retourne maintenant un objet paginé { items: [...], total, page, ... }
      const transactionsData = transactionsResponse.data || {};
      const transactions = transactionsData.items || transactionsData || [];
      // Pour l'instant, on utilise une valeur par défaut pour le solde
      const balance = { account_balance: 0 };

      // Calculs des revenus nets avec taux d'imposition
      const rev1Gross = config.rev1 || 0;
      const rev2Gross = config.rev2 || 0;
      const tax1 = (config.tax_rate1 || 0) / 100;
      const tax2 = (config.tax_rate2 || 0) / 100;

      const rev1Net = rev1Gross * (1 - tax1);
      const rev2Net = rev2Gross * (1 - tax2);
      const totalGrossRevenue = rev1Gross + rev2Gross;
      const totalNetRevenue = rev1Net + rev2Net;

      // Calcul du mois actuel pour la progression annuelle
      const currentMonth = new Date(month).getMonth() + 1; // 1-12
      const monthProgress = currentMonth / 12; // Progression dans l'année

      const provisionItems: ProvisionItem[] = provisions.map((p: any) => {
        const monthlyAmount = p.monthly_amount || p.current_amount || 0;
        const targetAmount = p.target_amount || 0;
        const totalProvisionedSinceJanuary = monthlyAmount * currentMonth; // Total depuis janvier

        return {
          id: p.id,
          name: p.name,
          currentAmount: monthlyAmount,
          targetAmount: targetAmount,
          percentage: p.percentage,
          progress: targetAmount > 0 ? (totalProvisionedSinceJanuary / targetAmount) * 100 : monthProgress * 100,
          category: p.category || 'Autre',
          totalProvisionedSinceJanuary: totalProvisionedSinceJanuary,
          monthProgress: monthProgress * 100
        };
      });

      // CORRECTION: Calculer totalProvisions depuis les items chargés pour garantir la cohérence
      // Avant: utilisait summary.provisions_total qui pouvait différer de /custom-provisions
      const totalProvisions = provisionItems.reduce((sum, p) => sum + p.currentAmount, 0);

      // ===== CORRECTION: Calcul des dépenses depuis les TRANSACTIONS RÉELLES =====
      // Filtrer les transactions: montant négatif (dépenses) ET non exclues
      const expenseTransactions = transactions.filter((t: any) =>
        t.amount < 0 && !t.exclude
      );

      // Calculer le total réel des dépenses
      const realExpensesTotal = expenseTransactions.reduce(
        (sum: number, t: any) => sum + Math.abs(t.amount),
        0
      );

      // Séparer fixes et variables si nécessaire
      const fixedExpensesTotal = expenseTransactions
        .filter((t: any) => t.expense_type === 'FIXED')
        .reduce((sum: number, t: any) => sum + Math.abs(t.amount), 0);
      const variableExpensesTotal = expenseTransactions
        .filter((t: any) => t.expense_type !== 'FIXED')
        .reduce((sum: number, t: any) => sum + Math.abs(t.amount), 0);

      // Total = dépenses réelles (pas les charges configurées)
      const totalExpenses = realExpensesTotal;

      // ===== AVOIRS: Calculer les crédits/revenus sur le compte =====
      // Filtrer les transactions: montant positif (avoirs/crédits) ET non exclues
      const creditTransactions = transactions.filter((t: any) =>
        t.amount > 0 && !t.exclude
      );

      // Total des avoirs (crédits reçus sur le compte)
      const totalCredits = creditTransactions.reduce(
        (sum: number, t: any) => sum + t.amount,
        0
      );

      // Solde de compte (donné par l'utilisateur)
      const currentAccountBalance = balance.account_balance || 0;

      // **CALCUL CLEF** : Montant à provisionner par la famille
      // Formule: Provisions + Dépenses = Total que la famille doit financer
      // Note: Les crédits sur le compte (salaires) sont la FAÇON dont la famille finance, pas une réduction
      const familyProvisionNeeded = totalProvisions + totalExpenses;
      
      // Répartition du montant selon les revenus nets
      const netRatio1 = totalNetRevenue > 0 ? rev1Net / totalNetRevenue : 0.5;
      const netRatio2 = totalNetRevenue > 0 ? rev2Net / totalNetRevenue : 0.5;

      const familyMember1 = familyProvisionNeeded * netRatio1;
      const familyMember2 = familyProvisionNeeded * netRatio2;

      // ===== DÉTAIL PAR MEMBRE: Provisions et Dépenses séparément =====
      // Provisions par membre (réparties selon le ratio des revenus nets)
      const provisionsMember1 = totalProvisions * netRatio1;
      const provisionsMember2 = totalProvisions * netRatio2;

      // Dépenses par membre (réparties selon le ratio des revenus nets)
      // On utilise totalExpenses directement (pas netExpenses) car les crédits sont les salaires
      const expensesMember1 = totalExpenses * netRatio1;
      const expensesMember2 = totalExpenses * netRatio2;

      // Statut de la situation familiale
      const getFamilyStatus = (needed: number, revenue: number): 'surplus' | 'balanced' | 'deficit' => {
        const ratio = needed / revenue;
        if (ratio <= 0.8) return 'surplus';      // Moins de 80% du revenu
        if (ratio <= 1.0) return 'balanced';     // Entre 80% et 100%
        return 'deficit';                        // Plus que le revenu
      };

      const dashboardData: CleanDashboardData = {
        revenue: {
          gross: totalGrossRevenue,
          net: totalNetRevenue,
          member1: {
            gross: rev1Gross,
            net: rev1Net,
            name: config.member1 || 'Membre 1'
          },
          member2: {
            gross: rev2Gross,
            net: rev2Net,
            name: config.member2 || 'Membre 2'
          }
        },
        provisions: {
          total: totalProvisions,
          count: provisions.length,
          items: provisionItems
        },
        expenses: {
          total: totalExpenses,
          fixed: fixedExpensesTotal,
          variable: variableExpensesTotal,
          count: expenseTransactions.length,  // Nombre réel de transactions dépenses
          items: [] // À implémenter pour le drill-down
        },
        accountBalance: {
          current: currentAccountBalance,
          endOfMonth: currentAccountBalance // Simplifié pour l'instant
        },
        familyProvision: {
          needed: familyProvisionNeeded,
          status: getFamilyStatus(familyProvisionNeeded, totalNetRevenue),
          member1: familyMember1,
          member2: familyMember2,
          // Détail des provisions et dépenses par membre
          detail: {
            provisions: {
              total: totalProvisions,
              member1: provisionsMember1,
              member2: provisionsMember2
            },
            expenses: {
              total: totalExpenses,  // Dépenses totales (transactions négatives non exclues)
              member1: expensesMember1,
              member2: expensesMember2
            }
          }
        }
      };

      setData(dashboardData);
    } catch (err: any) {
      console.error('Erreur chargement dashboard:', err);
      setError(err.message || 'Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  // Chargement initial et rechargement sur changement de mois
  useEffect(() => {
    loadDashboardData();
  }, [month, isAuthenticated]);

  // Méthodes utilitaires
  const reload = () => {
    loadDashboardData();
  };

  // Formatters utilitaires
  const formatters = useMemo(() => ({
    currency: (amount: number) => {
      return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(Math.abs(amount));
    },
    
    percentage: (value: number) => {
      return `${Math.round(value)}%`;
    },
    
    compactCurrency: (amount: number) => {
      const abs = Math.abs(amount);
      if (abs >= 1000) {
        return `${(abs / 1000).toFixed(1)}k€`;
      }
      return `${abs.toFixed(0)}€`;
    }
  }), []);

  return {
    data,
    loading,
    error,
    reload,
    formatters
  };
};

export default useCleanDashboard;