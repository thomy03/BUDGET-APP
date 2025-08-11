/**
 * Financial calculations and utility functions for the frontend.
 * Contains business logic for budget calculations, formatting, and validation.
 */

export interface Config {
  member1: string
  member2: string
  rev1: number
  rev2: number
  split_mode: 'revenus' | 'manuel'
  split1: number
  split2: number
}

export interface Provision {
  id: number
  name: string
  monthlyAmount: number
  member1Share: number
  member2Share: number
  isActive: boolean
}

export interface FixedExpense {
  id: number
  label: string
  amount: number
  frequency: 'mensuelle' | 'trimestrielle' | 'annuelle'
  member1Share: number
  member2Share: number
  isActive: boolean
}

export interface SplitResult {
  member1Ratio: number
  member2Ratio: number
}

export interface TotalResult {
  total: number
  member1Total: number
  member2Total: number
}

export interface BudgetData {
  totalIncome: number
  totalProvisions: number
  totalFixedExpenses: number
  totalVariableExpenses: number
  availableBudget: number
}

export interface BudgetBalance extends BudgetData {
  budgetUtilizationRate: number
  isOverBudget: boolean
  member1Available?: number
  member2Available?: number
}

/**
 * Calculate split ratios based on configuration.
 */
export function calculateSplit(config: Config): SplitResult {
  if (config.split_mode === 'revenus') {
    const totalRevenue = (config.rev1 || 0) + (config.rev2 || 0)
    if (totalRevenue <= 0) {
      return { member1Ratio: 0.5, member2Ratio: 0.5 }
    }
    const member1Ratio = (config.rev1 || 0) / totalRevenue
    return { member1Ratio, member2Ratio: 1 - member1Ratio }
  } else {
    return { member1Ratio: config.split1, member2Ratio: config.split2 }
  }
}

/**
 * Calculate total provisions amount for active provisions only.
 */
export function calculateProvisionTotal(provisions: Provision[] | null): TotalResult {
  if (!provisions || !Array.isArray(provisions)) {
    return { total: 0, member1Total: 0, member2Total: 0 }
  }

  const activeProvisions = provisions.filter(p => p.isActive)
  
  const total = activeProvisions.reduce((sum, p) => sum + (p.monthlyAmount || 0), 0)
  const member1Total = activeProvisions.reduce((sum, p) => sum + (p.member1Share || 0), 0)
  const member2Total = activeProvisions.reduce((sum, p) => sum + (p.member2Share || 0), 0)

  return { total, member1Total, member2Total }
}

/**
 * Calculate total fixed expenses amount, converting frequencies to monthly.
 */
export function calculateFixedExpenseTotal(expenses: FixedExpense[] | null): TotalResult {
  if (!expenses || !Array.isArray(expenses)) {
    return { total: 0, member1Total: 0, member2Total: 0 }
  }

  const activeExpenses = expenses.filter(e => e.isActive)
  
  let total = 0
  let member1Total = 0
  let member2Total = 0

  activeExpenses.forEach(expense => {
    let monthlyAmount = expense.amount || 0
    let member1Monthly = expense.member1Share || 0
    let member2Monthly = expense.member2Share || 0

    // Convert to monthly based on frequency
    if (expense.frequency === 'trimestrielle') {
      monthlyAmount /= 3
      member1Monthly /= 3
      member2Monthly /= 3
    } else if (expense.frequency === 'annuelle') {
      monthlyAmount /= 12
      member1Monthly /= 12
      member2Monthly /= 12
    }

    total += monthlyAmount
    member1Total += member1Monthly
    member2Total += member2Monthly
  })

  return { total, member1Total, member2Total }
}

/**
 * Format amount as French currency.
 */
export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '0,00 €'
  }

  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

/**
 * Parse amount from string, handling both French and English formats.
 */
export function parseAmount(amountString: string): number {
  if (!amountString || typeof amountString !== 'string') {
    return NaN
  }

  // Remove currency symbols and trim
  let cleaned = amountString.replace(/[€$£¥]/g, '').trim()
  
  // Handle French format (1 234,56 or 1234,56)
  if (cleaned.includes(',') && !cleaned.includes('.')) {
    // French format: replace space thousands separator and comma decimal
    cleaned = cleaned.replace(/\s/g, '').replace(',', '.')
  } else if (cleaned.includes(',') && cleaned.includes('.')) {
    // Ambiguous format, assume English (1,234.56)
    cleaned = cleaned.replace(/,/g, '')
  } else if (cleaned.includes(' ')) {
    // French thousands separator without decimal
    cleaned = cleaned.replace(/\s/g, '')
  }

  return parseFloat(cleaned)
}

/**
 * Validate if amount is a valid number.
 */
export function validateAmount(amount: number): boolean {
  return !isNaN(amount) && isFinite(amount)
}

/**
 * Calculate overall budget balance and utilization.
 */
export function calculateBudgetBalance(budgetData: BudgetData, config?: Config): BudgetBalance {
  const totalExpenses = budgetData.totalProvisions + budgetData.totalFixedExpenses + budgetData.totalVariableExpenses
  const availableBudget = budgetData.totalIncome - totalExpenses
  const budgetUtilizationRate = budgetData.totalIncome > 0 
    ? (totalExpenses / budgetData.totalIncome) * 100 
    : Infinity
  const isOverBudget = budgetUtilizationRate > 100

  let result: BudgetBalance = {
    ...budgetData,
    availableBudget,
    budgetUtilizationRate,
    isOverBudget
  }

  // Calculate member-specific available budgets if config provided
  if (config) {
    const splitResult = calculateSplit(config)
    const member1Income = config.rev1 || 0
    const member2Income = config.rev2 || 0
    
    // Allocate expenses based on split ratios
    const member1Expenses = totalExpenses * splitResult.member1Ratio
    const member2Expenses = totalExpenses * splitResult.member2Ratio
    
    result.member1Available = member1Income - member1Expenses
    result.member2Available = member2Income - member2Expenses
  }

  return result
}

/**
 * Calculate percentage of budget used.
 */
export function calculateBudgetPercentage(used: number, total: number): number {
  if (total <= 0) return 0
  return Math.min((used / total) * 100, 100)
}

/**
 * Format percentage with appropriate precision.
 */
export function formatPercentage(percentage: number, decimals: number = 1): string {
  if (isNaN(percentage) || !isFinite(percentage)) {
    return '0,0%'
  }
  
  return new Intl.NumberFormat('fr-FR', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(percentage / 100)
}

/**
 * Calculate compound interest for provisions with targets.
 */
export function calculateCompoundGrowth(
  principal: number, 
  monthlyContribution: number, 
  annualRate: number, 
  months: number
): { finalAmount: number; totalContributions: number; interestEarned: number } {
  const monthlyRate = annualRate / 12 / 100
  let balance = principal
  const totalContributions = monthlyContribution * months

  for (let i = 0; i < months; i++) {
    balance = balance * (1 + monthlyRate) + monthlyContribution
  }

  const interestEarned = balance - principal - totalContributions

  return {
    finalAmount: balance,
    totalContributions,
    interestEarned
  }
}

/**
 * Get financial health score based on budget metrics.
 */
export function getFinancialHealthScore(budgetBalance: BudgetBalance): {
  score: number
  level: 'excellent' | 'good' | 'fair' | 'poor'
  recommendations: string[]
} {
  const recommendations: string[] = []
  let score = 100

  // Penalize over-budget situations
  if (budgetBalance.isOverBudget) {
    score -= 40
    recommendations.push('Réduisez vos dépenses ou augmentez vos revenus')
  }

  // Evaluate budget utilization
  if (budgetBalance.budgetUtilizationRate > 90) {
    score -= 20
    recommendations.push('Votre budget est très serré, considérez des optimisations')
  } else if (budgetBalance.budgetUtilizationRate > 80) {
    score -= 10
    recommendations.push('Attention à ne pas dépasser votre budget')
  }

  // Evaluate provision ratio
  const provisionRatio = (budgetBalance.totalProvisions / budgetBalance.totalIncome) * 100
  if (provisionRatio < 10) {
    score -= 15
    recommendations.push('Augmentez vos provisions pour l\'épargne et l\'urgence')
  } else if (provisionRatio > 20) {
    score += 10
    recommendations.push('Excellente discipline d\'épargne !')
  }

  // Determine level based on score
  let level: 'excellent' | 'good' | 'fair' | 'poor'
  if (score >= 85) level = 'excellent'
  else if (score >= 70) level = 'good'
  else if (score >= 50) level = 'fair'
  else level = 'poor'

  return { score: Math.max(0, score), level, recommendations }
}

/**
 * Utility function to round to 2 decimal places (financial precision).
 */
export function roundCurrency(amount: number): number {
  return Math.round(amount * 100) / 100
}

/**
 * Compare two amounts with currency precision tolerance.
 */
export function currencyEquals(amount1: number, amount2: number, tolerance: number = 0.01): boolean {
  return Math.abs(amount1 - amount2) < tolerance
}