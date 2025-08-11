/**
 * Centralized calculation utilities for Budget Famille v2.3 Frontend
 * Eliminates duplicate calculation patterns across components
 */

import type { CalculationResult, TransactionData, BudgetConfig, SplitResult } from './types';

/**
 * Round currency amounts to 2 decimal places
 */
export function roundCurrency(amount: number): number {
  return Math.round((amount + Number.EPSILON) * 100) / 100;
}

/**
 * Calculate percentage of a total
 */
export function calculatePercentage(part: number, total: number): number {
  if (total === 0) return 0;
  return roundCurrency((part / total) * 100);
}

/**
 * Calculate amount from percentage
 */
export function calculateAmountFromPercentage(total: number, percentage: number): number {
  return roundCurrency((total * percentage) / 100);
}

/**
 * Calculate split amounts based on split mode
 */
export function calculateSplitAmounts(
  totalAmount: number,
  splitMode: string,
  revenue1: number = 0,
  revenue2: number = 0,
  manualSplit1?: number,
  manualSplit2?: number
): SplitResult {
  let member1Amount: number;
  let member2Amount: number;
  let split1: number;
  let split2: number;

  switch (splitMode) {
    case 'revenus':
    case 'clé':
      const totalRevenue = revenue1 + revenue2;
      if (totalRevenue === 0) {
        // Equal split if no revenues
        member1Amount = totalAmount / 2;
        member2Amount = totalAmount / 2;
        split1 = 50;
        split2 = 50;
      } else {
        split1 = (revenue1 / totalRevenue) * 100;
        split2 = (revenue2 / totalRevenue) * 100;
        member1Amount = calculateAmountFromPercentage(totalAmount, split1);
        member2Amount = calculateAmountFromPercentage(totalAmount, split2);
      }
      break;

    case 'manuel':
      split1 = manualSplit1 || 50;
      split2 = manualSplit2 || 50;
      member1Amount = calculateAmountFromPercentage(totalAmount, split1);
      member2Amount = calculateAmountFromPercentage(totalAmount, split2);
      break;

    case '50/50':
    default:
      split1 = 50;
      split2 = 50;
      member1Amount = totalAmount / 2;
      member2Amount = totalAmount / 2;
      break;

    case '100/0':
      split1 = 100;
      split2 = 0;
      member1Amount = totalAmount;
      member2Amount = 0;
      break;

    case '0/100':
      split1 = 0;
      split2 = 100;
      member1Amount = 0;
      member2Amount = totalAmount;
      break;
  }

  // Ensure amounts are properly rounded and add up to total
  member1Amount = roundCurrency(member1Amount);
  member2Amount = roundCurrency(member2Amount);
  
  const calculatedTotal = member1Amount + member2Amount;
  if (Math.abs(calculatedTotal - totalAmount) > 0.01) {
    const difference = totalAmount - calculatedTotal;
    // Add difference to the larger share
    if (member1Amount >= member2Amount) {
      member1Amount = roundCurrency(member1Amount + difference);
    } else {
      member2Amount = roundCurrency(member2Amount + difference);
    }
  }

  return {
    member1_amount: member1Amount,
    member2_amount: member2Amount,
    total_amount: totalAmount,
    split_percentage1: roundCurrency(split1),
    split_percentage2: roundCurrency(split2)
  };
}

/**
 * Calculate monthly amount from annual based on frequency
 */
export function calculateMonthlyAmount(amount: number, frequency: string): number {
  switch (frequency) {
    case 'mensuelle':
      return amount;
    case 'trimestrielle':
      return roundCurrency(amount / 3);
    case 'annuelle':
      return roundCurrency(amount / 12);
    default:
      return amount;
  }
}

/**
 * Calculate annual amount from monthly based on frequency
 */
export function calculateAnnualAmount(amount: number, frequency: string): number {
  switch (frequency) {
    case 'mensuelle':
      return roundCurrency(amount * 12);
    case 'trimestrielle':
      return roundCurrency(amount * 4);
    case 'annuelle':
      return amount;
    default:
      return amount;
  }
}

/**
 * Calculate transaction totals by category
 */
export function calculateTransactionTotals(
  transactions: TransactionData[],
  groupBy: 'category' | 'account_label' | 'is_expense' = 'category'
): Record<string, CalculationResult> {
  const totals: Record<string, number> = {};

  transactions.forEach(tx => {
    if (tx.exclude) return;

    let key: string;
    switch (groupBy) {
      case 'category':
        key = tx.category || 'Autres';
        break;
      case 'account_label':
        key = tx.account_label || 'Compte inconnu';
        break;
      case 'is_expense':
        key = tx.is_expense ? 'Dépenses' : 'Revenus';
        break;
      default:
        key = 'Total';
    }

    if (!totals[key]) totals[key] = 0;
    totals[key] += Math.abs(tx.amount);
  });

  const results: Record<string, CalculationResult> = {};
  Object.entries(totals).forEach(([key, value]) => {
    results[key] = {
      value: roundCurrency(value),
      formatted: `${roundCurrency(value).toFixed(2).replace('.', ',')} €`
    };
  });

  return results;
}

/**
 * Calculate budget variance
 */
export function calculateBudgetVariance(actual: number, budgeted: number): {
  variance: number;
  variancePercentage: number;
  status: 'over' | 'under' | 'on_target';
} {
  const variance = roundCurrency(actual - budgeted);
  const variancePercentage = budgeted !== 0 ? calculatePercentage(variance, budgeted) : 0;
  
  let status: 'over' | 'under' | 'on_target';
  if (Math.abs(variance) <= 0.01) {
    status = 'on_target';
  } else if (variance > 0) {
    status = 'over';
  } else {
    status = 'under';
  }

  return {
    variance,
    variancePercentage,
    status
  };
}

/**
 * Calculate provision amounts
 */
export function calculateProvisionAmounts(
  provisions: Array<{
    percentage: number;
    base_calculation: 'total' | 'member1' | 'member2' | 'fixed';
    fixed_amount?: number;
    split_mode: string;
    split_member1?: number;
    split_member2?: number;
  }>,
  totalIncome: number,
  member1Income: number,
  member2Income: number
): Array<{
  baseAmount: number;
  member1Amount: number;
  member2Amount: number;
  totalAmount: number;
}> {
  return provisions.map(provision => {
    let baseAmount: number;

    // Calculate base amount
    switch (provision.base_calculation) {
      case 'total':
        baseAmount = calculateAmountFromPercentage(totalIncome, provision.percentage);
        break;
      case 'member1':
        baseAmount = calculateAmountFromPercentage(member1Income, provision.percentage);
        break;
      case 'member2':
        baseAmount = calculateAmountFromPercentage(member2Income, provision.percentage);
        break;
      case 'fixed':
        baseAmount = provision.fixed_amount || 0;
        break;
      default:
        baseAmount = calculateAmountFromPercentage(totalIncome, provision.percentage);
    }

    // Calculate split
    const splitResult = calculateSplitAmounts(
      baseAmount,
      provision.split_mode,
      member1Income,
      member2Income,
      provision.split_member1,
      provision.split_member2
    );

    return {
      baseAmount: roundCurrency(baseAmount),
      member1Amount: splitResult.member1_amount,
      member2Amount: splitResult.member2_amount,
      totalAmount: splitResult.total_amount
    };
  });
}

/**
 * Calculate budget summary
 */
export function calculateBudgetSummary(
  config: BudgetConfig,
  transactions: TransactionData[],
  fixedLines: Array<{
    amount: number;
    freq: string;
    split_mode: string;
    split1?: number;
    split2?: number;
    active: boolean;
  }>,
  provisions: Array<{
    percentage: number;
    base_calculation: 'total' | 'member1' | 'member2' | 'fixed';
    fixed_amount?: number;
    split_mode: string;
    split_member1?: number;
    split_member2?: number;
    is_active: boolean;
  }>
) {
  const { member1, member2, rev1, rev2 } = config;
  const totalIncome = rev1 + rev2;

  // Calculate variable expenses from transactions
  const expenses = transactions.filter(tx => tx.is_expense && !tx.exclude);
  const variableExpenses = expenses.reduce((sum, tx) => sum + Math.abs(tx.amount), 0);

  // Calculate fixed expenses
  const activeFixedLines = fixedLines.filter(line => line.active);
  const fixedExpenses = activeFixedLines.reduce((sum, line) => {
    return sum + calculateMonthlyAmount(line.amount, line.freq);
  }, 0);

  // Calculate variable split
  const variableSplit = calculateSplitAmounts(
    variableExpenses,
    config.split_mode,
    rev1,
    rev2,
    config.split1,
    config.split2
  );

  // Calculate fixed split
  let fixedMember1 = 0;
  let fixedMember2 = 0;
  activeFixedLines.forEach(line => {
    const monthlyAmount = calculateMonthlyAmount(line.amount, line.freq);
    const split = calculateSplitAmounts(
      monthlyAmount,
      line.split_mode,
      rev1,
      rev2,
      line.split1,
      line.split2
    );
    fixedMember1 += split.member1_amount;
    fixedMember2 += split.member2_amount;
  });

  // Calculate provisions
  const activeProvisions = provisions.filter(p => p.is_active);
  const provisionAmounts = calculateProvisionAmounts(
    activeProvisions,
    totalIncome,
    rev1,
    rev2
  );
  
  const totalProvisions = provisionAmounts.reduce((sum, p) => sum + p.totalAmount, 0);
  const provisionsMember1 = provisionAmounts.reduce((sum, p) => sum + p.member1Amount, 0);
  const provisionsMember2 = provisionAmounts.reduce((sum, p) => sum + p.member2Amount, 0);

  // Calculate totals
  const totalExpenses = variableExpenses + fixedExpenses + totalProvisions;
  const member1Share = variableSplit.member1_amount + fixedMember1 + provisionsMember1;
  const member2Share = variableSplit.member2_amount + fixedMember2 + provisionsMember2;

  // Calculate balances
  const member1Balance = rev1 - member1Share;
  const member2Balance = rev2 - member2Share;
  const remainingBudget = totalIncome - totalExpenses;

  return {
    income: {
      member1: rev1,
      member2: rev2,
      total: totalIncome
    },
    expenses: {
      variable: roundCurrency(variableExpenses),
      fixed: roundCurrency(fixedExpenses),
      provisions: roundCurrency(totalProvisions),
      total: roundCurrency(totalExpenses)
    },
    shares: {
      member1: roundCurrency(member1Share),
      member2: roundCurrency(member2Share)
    },
    balances: {
      member1: roundCurrency(member1Balance),
      member2: roundCurrency(member2Balance),
      total: roundCurrency(remainingBudget)
    },
    splits: {
      variable: variableSplit,
      fixed: {
        member1_amount: roundCurrency(fixedMember1),
        member2_amount: roundCurrency(fixedMember2),
        total_amount: roundCurrency(fixedExpenses)
      },
      provisions: {
        member1_amount: roundCurrency(provisionsMember1),
        member2_amount: roundCurrency(provisionsMember2),
        total_amount: roundCurrency(totalProvisions)
      }
    }
  };
}

/**
 * Calculate savings rate
 */
export function calculateSavingsRate(savings: number, income: number): number {
  if (income === 0) return 0;
  return calculatePercentage(savings, income);
}

/**
 * Calculate compound interest
 */
export function calculateCompoundInterest(
  principal: number,
  rate: number,
  time: number,
  compoundingFrequency: number = 12
): {
  finalAmount: number;
  totalInterest: number;
  monthlyBreakdown?: Array<{ month: number; amount: number; interest: number }>;
} {
  const rateDecimal = rate / 100;
  const finalAmount = principal * Math.pow(1 + rateDecimal / compoundingFrequency, compoundingFrequency * time);
  const totalInterest = finalAmount - principal;

  const monthlyBreakdown: Array<{ month: number; amount: number; interest: number }> = [];
  let currentAmount = principal;
  
  for (let month = 1; month <= time * 12; month++) {
    const monthlyRate = rateDecimal / 12;
    const monthlyInterest = currentAmount * monthlyRate;
    currentAmount += monthlyInterest;
    
    monthlyBreakdown.push({
      month,
      amount: roundCurrency(currentAmount),
      interest: roundCurrency(monthlyInterest)
    });
  }

  return {
    finalAmount: roundCurrency(finalAmount),
    totalInterest: roundCurrency(totalInterest),
    monthlyBreakdown
  };
}

/**
 * Calculate loan payment (PMT formula)
 */
export function calculateLoanPayment(
  principal: number,
  rate: number,
  periods: number
): {
  monthlyPayment: number;
  totalPayment: number;
  totalInterest: number;
} {
  const monthlyRate = rate / 100 / 12;
  const monthlyPayment = monthlyRate === 0 
    ? principal / periods
    : principal * (monthlyRate * Math.pow(1 + monthlyRate, periods)) / (Math.pow(1 + monthlyRate, periods) - 1);
  
  const totalPayment = monthlyPayment * periods;
  const totalInterest = totalPayment - principal;

  return {
    monthlyPayment: roundCurrency(monthlyPayment),
    totalPayment: roundCurrency(totalPayment),
    totalInterest: roundCurrency(totalInterest)
  };
}

/**
 * Calculate emergency fund recommendation
 */
export function calculateEmergencyFund(
  monthlyExpenses: number,
  months: number = 6
): {
  recommendedAmount: number;
  monthlyGoal: number;
  timeToGoal: number;
} {
  const recommendedAmount = monthlyExpenses * months;
  const monthlyGoal = recommendedAmount / 12; // Assume 1 year to build
  const timeToGoal = 12; // months

  return {
    recommendedAmount: roundCurrency(recommendedAmount),
    monthlyGoal: roundCurrency(monthlyGoal),
    timeToGoal
  };
}

/**
 * Calculate debt-to-income ratio
 */
export function calculateDebtToIncomeRatio(totalDebtPayments: number, grossIncome: number): {
  ratio: number;
  riskLevel: 'low' | 'moderate' | 'high';
  recommendation: string;
} {
  const ratio = calculatePercentage(totalDebtPayments, grossIncome);
  
  let riskLevel: 'low' | 'moderate' | 'high';
  let recommendation: string;

  if (ratio <= 28) {
    riskLevel = 'low';
    recommendation = 'Excellente gestion de la dette';
  } else if (ratio <= 36) {
    riskLevel = 'moderate';
    recommendation = 'Gestion acceptable, surveillez vos nouvelles dettes';
  } else {
    riskLevel = 'high';
    recommendation = 'Ratio élevé, envisagez de réduire vos dettes';
  }

  return {
    ratio: roundCurrency(ratio),
    riskLevel,
    recommendation
  };
}

/**
 * Calculate financial ratios dashboard
 */
export function calculateFinancialRatios(
  income: number,
  expenses: number,
  savings: number,
  debts: number
): {
  savingsRate: number;
  expenseRatio: number;
  debtRatio: number;
  financialHealth: 'excellent' | 'good' | 'fair' | 'poor';
} {
  const savingsRate = calculateSavingsRate(savings, income);
  const expenseRatio = calculatePercentage(expenses, income);
  const debtRatio = calculatePercentage(debts, income);

  // Calculate overall financial health score
  let healthScore = 0;
  
  // Savings rate scoring (0-40 points)
  if (savingsRate >= 20) healthScore += 40;
  else if (savingsRate >= 15) healthScore += 30;
  else if (savingsRate >= 10) healthScore += 20;
  else if (savingsRate >= 5) healthScore += 10;
  
  // Expense ratio scoring (0-30 points)
  if (expenseRatio <= 70) healthScore += 30;
  else if (expenseRatio <= 80) healthScore += 20;
  else if (expenseRatio <= 90) healthScore += 10;
  
  // Debt ratio scoring (0-30 points)
  if (debtRatio <= 10) healthScore += 30;
  else if (debtRatio <= 20) healthScore += 20;
  else if (debtRatio <= 30) healthScore += 10;

  let financialHealth: 'excellent' | 'good' | 'fair' | 'poor';
  if (healthScore >= 80) financialHealth = 'excellent';
  else if (healthScore >= 60) financialHealth = 'good';
  else if (healthScore >= 40) financialHealth = 'fair';
  else financialHealth = 'poor';

  return {
    savingsRate: roundCurrency(savingsRate),
    expenseRatio: roundCurrency(expenseRatio),
    debtRatio: roundCurrency(debtRatio),
    financialHealth
  };
}