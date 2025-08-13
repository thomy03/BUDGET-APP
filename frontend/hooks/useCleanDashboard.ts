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

      // Chargement parallèle des données essentielles
      const [configResponse, provisionsResponse, summaryResponse, balanceResponse] = await Promise.all([
        api.get('/config'),
        api.get('/custom-provisions'),
        api.get(`/summary?month=${month}`),
        api.get(`/api/balance/${month}`)
      ]);

      const config = configResponse.data;
      const provisions = provisionsResponse.data;
      const summary = summaryResponse.data;
      const balance = balanceResponse.data;

      // Calculs des revenus nets avec taux d'imposition
      const rev1Gross = config.rev1 || 0;
      const rev2Gross = config.rev2 || 0;
      const tax1 = (config.tax_rate1 || 0) / 100;
      const tax2 = (config.tax_rate2 || 0) / 100;
      
      const rev1Net = rev1Gross * (1 - tax1);
      const rev2Net = rev2Gross * (1 - tax2);
      const totalGrossRevenue = rev1Gross + rev2Gross;
      const totalNetRevenue = rev1Net + rev2Net;

      // Calculs des provisions avec montants actuels
      const totalProvisions = summary.provisions_total || 0;

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
          totalProvisionedSinceJanuary: totalProvisionedSinceJanuary, // Nouveau champ
          monthProgress: monthProgress * 100 // Nouveau champ pour affichage
        };
      });

      // Dépenses totales (fixes + variables)
      const fixedExpensesTotal = summary.fixed_lines_total || 0;
      const variableExpensesTotal = Math.abs(summary.var_total || 0); // var_total est négatif
      const totalExpenses = fixedExpensesTotal + variableExpensesTotal;

      // Solde de compte (donné par l'utilisateur)
      const currentAccountBalance = balance.account_balance || 0;

      // **CALCUL CLEF** : Montant à provisionner par la famille
      // Formule: Provisions + Dépenses - Solde compte = Montant à apporter
      const familyProvisionNeeded = totalProvisions + totalExpenses - currentAccountBalance;
      
      // Répartition du montant selon les revenus nets
      const netRatio1 = totalNetRevenue > 0 ? rev1Net / totalNetRevenue : 0.5;
      const netRatio2 = totalNetRevenue > 0 ? rev2Net / totalNetRevenue : 0.5;
      
      const familyMember1 = familyProvisionNeeded * netRatio1;
      const familyMember2 = familyProvisionNeeded * netRatio2;

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
          count: summary.transaction_count || 0,
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
          member2: familyMember2
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