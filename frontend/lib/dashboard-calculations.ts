import { CustomProvision, FixedLine, ConfigOut } from './api';

export function calculateMonthlyAmount(expense: FixedLine): number {
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
}

export function calculateProvisionMonthlyAmount(provision: CustomProvision, config: ConfigOut): number {
  let base = 0;
  switch (provision.base_calculation) {
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
      return provision.fixed_amount || 0;
  }
  return (base * provision.percentage / 100) / 12;
}

export function calculateMemberSplit(expense: FixedLine, monthlyAmount: number, config: ConfigOut) {
  switch (expense.split_mode) {
    case 'clé':
      const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
      if (totalRev > 0) {
        const r1 = (config.rev1 || 0) / totalRev;
        const r2 = (config.rev2 || 0) / totalRev;
        return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
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
        member2: monthlyAmount * (expense.split2 / 100) 
      };
    default:
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
  }
}

export function calculateProvisionMemberSplit(provision: CustomProvision, monthlyAmount: number, config: ConfigOut) {
  switch (provision.split_mode) {
    case 'key':
      const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
      if (totalRev > 0) {
        const r1 = (config.rev1 || 0) / totalRev;
        const r2 = (config.rev2 || 0) / totalRev;
        return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
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
        member1: monthlyAmount * (provision.split_member1 / 100),
        member2: monthlyAmount * (provision.split_member2 / 100)
      };
    default:
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
  }
}

export interface BudgetItem {
  name: string;
  member1: number;
  member2: number;
  type: 'provision' | 'fixed' | 'variable';
}

export interface BudgetTotals {
  totalProvisions: number;
  totalFixedExpenses: number;
  totalVariables: number;
  budgetTotal: number;
}

export function calculateBudgetTotals(
  provisions: CustomProvision[],
  fixedExpenses: FixedLine[],
  variablesTotal: number,
  config: ConfigOut
): BudgetTotals {
  // Safe default values
  const safeProvisions = provisions || [];
  const safeFixedExpenses = fixedExpenses || [];
  const safeVariablesTotal = typeof variablesTotal === 'number' && !isNaN(variablesTotal) ? variablesTotal : 0;
  const safeConfig = config || {};

  const activeProvisions = safeProvisions.filter(p => p.is_active);
  const totalProvisions = activeProvisions.reduce((sum, provision) => {
    const monthlyAmount = calculateProvisionMonthlyAmount(provision, safeConfig);
    return sum + (typeof monthlyAmount === 'number' && !isNaN(monthlyAmount) ? monthlyAmount : 0);
  }, 0);

  const activeFixedExpenses = safeFixedExpenses.filter(e => e.active);
  const totalFixedExpenses = activeFixedExpenses.reduce((sum, expense) => {
    const monthlyAmount = calculateMonthlyAmount(expense);
    return sum + (typeof monthlyAmount === 'number' && !isNaN(monthlyAmount) ? monthlyAmount : 0);
  }, 0);

  const totalVariables = safeVariablesTotal;
  const budgetTotal = totalProvisions + totalFixedExpenses + totalVariables;

  return {
    totalProvisions,
    totalFixedExpenses,
    totalVariables,
    budgetTotal
  };
}