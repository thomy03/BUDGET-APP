'use client';

import { FixedLine, ConfigOut } from '../lib/api';

export function useFixedExpenseCalculations(config?: ConfigOut) {
  const calculateMonthlyAmount = (expense: FixedLine): number => {
    if (!config) return 0;

    let base = 0;
    switch (expense.base_calculation) {
      case 'total':
        base = (config.rev1 || 0) + (config.rev2 || 0);
        break;
      case 'member1':
        base = config.rev1 || 0;
        break;
      case 'member2':
        base = config.rev2 || 0;
        break;
      case 'fixed':
        return expense.fixed_amount || 0;
    }

    return (base * expense.percentage / 100) / 12;
  };

  const calculateMemberSplit = (expense: FixedLine, monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (expense.split_mode) {
      case 'key':
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
      case '100/0':
        return { member1: monthlyAmount, member2: 0 };
      case '0/100':
        return { member1: 0, member2: monthlyAmount };
      case 'custom':
        return {
          member1: monthlyAmount * (expense.split_member1 / 100),
          member2: monthlyAmount * (expense.split_member2 / 100),
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getBaseCalculationLabel = (baseCalc: string) => {
    switch (baseCalc) {
      case 'total':
        return 'Revenus totaux';
      case 'member1':
        return config?.member1 || 'Membre 1';
      case 'member2':
        return config?.member2 || 'Membre 2';
      case 'fixed':
        return 'Montant fixe';
      default:
        return baseCalc;
    }
  };

  const getSplitModeLabel = (splitMode: string) => {
    switch (splitMode) {
      case 'key':
        return 'Clé globale';
      case '50/50':
        return '50/50';
      case '100/0':
        return `100% ${config?.member1 || 'Membre 1'}`;
      case '0/100':
        return `100% ${config?.member2 || 'Membre 2'}`;
      case 'custom':
        return 'Personnalisé';
      default:
        return splitMode;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'housing':
        return '🏠';
      case 'transport':
        return '🚗';
      case 'utilities':
        return '⚡';
      case 'insurance':
        return '🛡️';
      case 'subscriptions':
        return '📱';
      case 'food':
        return '🍽️';
      case 'health':
        return '🏥';
      case 'education':
        return '🎓';
      case 'entertainment':
        return '🎬';
      default:
        return '💳';
    }
  };

  return {
    calculateMonthlyAmount,
    calculateMemberSplit,
    formatAmount,
    getBaseCalculationLabel,
    getSplitModeLabel,
    getCategoryIcon
  };
}
