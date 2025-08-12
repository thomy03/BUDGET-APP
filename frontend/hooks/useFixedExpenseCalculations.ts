'use client';

import { FixedLine, ConfigOut } from '../lib/api';

export function useFixedExpenseCalculations(config?: ConfigOut) {
  const calculateMonthlyAmount = (expense: FixedLine): number => {
    if (!expense?.amount) return 0;

    // Convert to monthly based on frequency
    switch (expense.freq) {
      case 'mensuelle':
        return expense.amount;
      case 'trimestrielle':
        return expense.amount / 3;
      case 'annuelle':
        return expense.amount / 12;
      default:
        return expense.amount;
    }
  };

  const calculateMemberSplit = (expense: FixedLine, monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (expense.split_mode) {
      case 'clé':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
          return {
            member1: monthlyAmount * r1,
            member2: monthlyAmount * r2,
          };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case 'm1':
        return { member1: monthlyAmount, member2: 0 };
      case 'm2':
        return { member1: 0, member2: monthlyAmount };
      case 'manuel':
        return {
          member1: monthlyAmount * (expense.split1 / 100),
          member2: monthlyAmount * (expense.split2 / 100),
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const formatAmount = (amount: number) => {
    // Handle NaN, undefined, null values
    if (!amount || isNaN(amount) || !isFinite(amount)) {
      return '0 €';
    }
    
    try {
      return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(amount);
    } catch (error) {
      // Fallback formatting
      return `${amount.toFixed(0).replace('.', ',')} €`;
    }
  };

  const getFrequencyLabel = (freq: string) => {
    switch (freq) {
      case 'mensuelle':
        return 'Mensuelle';
      case 'trimestrielle':
        return 'Trimestrielle';
      case 'annuelle':
        return 'Annuelle';
      default:
        return freq;
    }
  };

  const getSplitModeLabel = (splitMode: string) => {
    switch (splitMode) {
      case 'clé':
        return 'Clé globale';
      case '50/50':
        return '50/50';
      case 'm1':
        return `100% ${config?.member1 || 'Membre 1'}`;
      case 'm2':
        return `100% ${config?.member2 || 'Membre 2'}`;
      case 'manuel':
        return 'Personnalisé';
      default:
        return splitMode;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'logement':
        return '🏠';
      case 'transport':
        return '🚗';
      case 'services':
        return '⚡';
      case 'loisirs':
        return '🎬';
      case 'santé':
        return '🏥';
      case 'autres':
      default:
        return '💳';
    }
  };

  return {
    calculateMonthlyAmount,
    calculateMemberSplit,
    formatAmount,
    getFrequencyLabel,
    getSplitModeLabel,
    getCategoryIcon
  };
}
