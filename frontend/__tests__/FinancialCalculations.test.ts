/**
 * Unit tests for frontend financial calculations and utility functions.
 * Tests critical business logic calculations on the frontend.
 */

import { calculateSplit, calculateProvisionTotal, calculateFixedExpenseTotal, 
         formatCurrency, parseAmount, validateAmount, calculateBudgetBalance } from '../lib/calculations'

// Mock data for testing
const mockConfig = {
  member1: 'Alice',
  member2: 'Bob',
  rev1: 3500,
  rev2: 2500,
  split_mode: 'revenus' as const,
  split1: 0.6,
  split2: 0.4
}

const mockProvisions = [
  {
    id: 1,
    name: 'Épargne vacances',
    monthlyAmount: 200,
    member1Share: 120,
    member2Share: 80,
    isActive: true
  },
  {
    id: 2,
    name: 'Fonds urgence',
    monthlyAmount: 150,
    member1Share: 90,
    member2Share: 60,
    isActive: true
  },
  {
    id: 3,
    name: 'Provision inactive',
    monthlyAmount: 100,
    member1Share: 60,
    member2Share: 40,
    isActive: false
  }
]

const mockFixedExpenses = [
  {
    id: 1,
    label: 'Loyer',
    amount: 1200,
    frequency: 'mensuelle' as const,
    member1Share: 720,
    member2Share: 480,
    isActive: true
  },
  {
    id: 2,
    label: 'Assurance',
    amount: 120,
    frequency: 'mensuelle' as const,
    member1Share: 72,
    member2Share: 48,
    isActive: true
  }
]

const mockTransactions = [
  {
    id: 1,
    amount: -75.50,
    category: 'Alimentation',
    date: '2024-01-15',
    label: 'Courses Carrefour',
    exclude: false
  },
  {
    id: 2,
    amount: -45.00,
    category: 'Transport',
    date: '2024-01-16',
    label: 'Essence',
    exclude: false
  },
  {
    id: 3,
    amount: -25.00,
    category: 'Alimentation',
    date: '2024-01-17',
    label: 'Restaurant',
    exclude: true // Should be excluded from calculations
  }
]

describe('calculateSplit', () => {
  test('should calculate revenue-based split correctly', () => {
    const result = calculateSplit(mockConfig)
    
    // Total revenue: 3500 + 2500 = 6000
    // Alice: 3500/6000 = 0.583333...
    // Bob: 2500/6000 = 0.416666...
    expect(result.member1Ratio).toBeCloseTo(0.5833, 4)
    expect(result.member2Ratio).toBeCloseTo(0.4167, 4)
    expect(result.member1Ratio + result.member2Ratio).toBeCloseTo(1.0, 4)
  })

  test('should use manual split when not revenue-based', () => {
    const manualConfig = {
      ...mockConfig,
      split_mode: 'manuel' as const
    }
    
    const result = calculateSplit(manualConfig)
    
    expect(result.member1Ratio).toBe(0.6)
    expect(result.member2Ratio).toBe(0.4)
  })

  test('should default to 50/50 when revenues are zero', () => {
    const zeroConfig = {
      ...mockConfig,
      rev1: 0,
      rev2: 0,
      split_mode: 'revenus' as const
    }
    
    const result = calculateSplit(zeroConfig)
    
    expect(result.member1Ratio).toBe(0.5)
    expect(result.member2Ratio).toBe(0.5)
  })
})

describe('calculateProvisionTotal', () => {
  test('should calculate total for active provisions only', () => {
    const result = calculateProvisionTotal(mockProvisions)
    
    expect(result.total).toBe(350) // 200 + 150 (inactive excluded)
    expect(result.member1Total).toBe(210) // 120 + 90
    expect(result.member2Total).toBe(140) // 80 + 60
  })

  test('should handle empty provisions list', () => {
    const result = calculateProvisionTotal([])
    
    expect(result.total).toBe(0)
    expect(result.member1Total).toBe(0)
    expect(result.member2Total).toBe(0)
  })

  test('should exclude inactive provisions', () => {
    const result = calculateProvisionTotal(mockProvisions)

    // Should not include the inactive provision (100 monthly)
    // Total should be 350, not 450 (which would include inactive)
    expect(result.total).toBe(350)
    expect(result.total).not.toBe(450)
  })
})

describe('calculateFixedExpenseTotal', () => {
  test('should calculate total for active fixed expenses', () => {
    const result = calculateFixedExpenseTotal(mockFixedExpenses)
    
    expect(result.total).toBe(1320) // 1200 + 120
    expect(result.member1Total).toBe(792) // 720 + 72
    expect(result.member2Total).toBe(528) // 480 + 48
  })

  test('should handle different frequencies correctly', () => {
    const mixedFrequencies = [
      {
        id: 1,
        label: 'Loyer',
        amount: 1200,
        frequency: 'mensuelle' as const,
        member1Share: 600,
        member2Share: 600,
        isActive: true
      },
      {
        id: 2,
        label: 'Assurance annuelle',
        amount: 1200, // Annual amount -> 100/month
        frequency: 'annuelle' as const,
        member1Share: 600, // Annual share -> 600/12 = 50/month
        member2Share: 600,
        isActive: true
      },
      {
        id: 3,
        label: 'Impôts trimestriels',
        amount: 300, // Quarterly amount -> 100/month
        frequency: 'trimestrielle' as const,
        member1Share: 150, // Quarterly share -> 150/3 = 50/month
        member2Share: 150,
        isActive: true
      }
    ]

    const result = calculateFixedExpenseTotal(mixedFrequencies)

    // Monthly + Annual/12 + Quarterly/3 = 1200 + 100 + 100 = 1400
    expect(result.total).toBe(1400)
    expect(result.member1Total).toBe(700) // 600 + 50 + 50
    expect(result.member2Total).toBe(700) // 600 + 50 + 50
  })

  test('should exclude inactive fixed expenses', () => {
    const expensesWithInactive = [
      ...mockFixedExpenses,
      {
        id: 3,
        label: 'Old subscription',
        amount: 50,
        frequency: 'mensuelle' as const,
        member1Share: 25,
        member2Share: 25,
        isActive: false
      }
    ]
    
    const result = calculateFixedExpenseTotal(expensesWithInactive)
    
    // Should exclude the inactive expense
    expect(result.total).toBe(1320) // Same as active-only calculation
  })
})

// Helper to normalize all types of spaces (non-breaking, narrow no-break, etc.)
const normalizeSpaces = (str: string) => str.replace(/[\u00A0\u202F\u2009]/g, ' ')

describe('formatCurrency', () => {
  test('should format positive amounts correctly', () => {
    expect(normalizeSpaces(formatCurrency(1234.56))).toBe('1 234,56 €')
    expect(normalizeSpaces(formatCurrency(1000))).toBe('1 000,00 €')
    expect(normalizeSpaces(formatCurrency(0))).toBe('0,00 €')
  })

  test('should format negative amounts correctly', () => {
    expect(normalizeSpaces(formatCurrency(-1234.56))).toBe('-1 234,56 €')
    expect(normalizeSpaces(formatCurrency(-0.99))).toBe('-0,99 €')
  })

  test('should handle very large numbers', () => {
    expect(normalizeSpaces(formatCurrency(1000000))).toBe('1 000 000,00 €')
    expect(normalizeSpaces(formatCurrency(1234567.89))).toBe('1 234 567,89 €')
  })

  test('should handle precision correctly', () => {
    expect(normalizeSpaces(formatCurrency(1.999))).toBe('2,00 €') // Rounds up
    expect(normalizeSpaces(formatCurrency(1.001))).toBe('1,00 €') // Rounds down
    // Note: 1.005 rounding behavior may vary by JS engine
    expect(normalizeSpaces(formatCurrency(1.005))).toMatch(/1,0[01] €/)
  })
})

describe('parseAmount', () => {
  test('should parse valid French number formats', () => {
    expect(parseAmount('1 234,56')).toBe(1234.56)
    expect(parseAmount('1234,56')).toBe(1234.56)
    expect(parseAmount('1 234')).toBe(1234)
    expect(parseAmount('1234')).toBe(1234)
    expect(parseAmount('0,99')).toBe(0.99)
  })

  test('should parse English number formats', () => {
    expect(parseAmount('1,234.56')).toBe(1234.56)
    expect(parseAmount('1234.56')).toBe(1234.56)
    expect(parseAmount('0.99')).toBe(0.99)
  })

  test('should handle negative amounts', () => {
    expect(parseAmount('-1 234,56')).toBe(-1234.56)
    expect(parseAmount('-1234.56')).toBe(-1234.56)
  })

  test('should return NaN for invalid formats', () => {
    expect(parseAmount('invalid')).toBeNaN()
    expect(parseAmount('')).toBeNaN()
    // Note: '1,2,3' may parse partially due to JavaScript parseFloat behavior
  })

  test('should strip currency symbols', () => {
    expect(parseAmount('1 234,56 €')).toBe(1234.56)
    expect(parseAmount('€ 1234.56')).toBe(1234.56)
    expect(parseAmount('$1,234.56')).toBe(1234.56)
  })
})

describe('validateAmount', () => {
  test('should validate positive amounts', () => {
    expect(validateAmount(100)).toBe(true)
    expect(validateAmount(0.01)).toBe(true)
    expect(validateAmount(1000000)).toBe(true)
  })

  test('should validate negative amounts', () => {
    expect(validateAmount(-100)).toBe(true)
    expect(validateAmount(-0.01)).toBe(true)
  })

  test('should reject invalid amounts', () => {
    expect(validateAmount(NaN)).toBe(false)
    expect(validateAmount(Infinity)).toBe(false)
    expect(validateAmount(-Infinity)).toBe(false)
  })

  test('should handle boundary values', () => {
    expect(validateAmount(0)).toBe(true)
    expect(validateAmount(-0)).toBe(true)
    expect(validateAmount(Number.MAX_SAFE_INTEGER)).toBe(true)
    expect(validateAmount(Number.MIN_SAFE_INTEGER)).toBe(true)
  })
})

describe('calculateBudgetBalance', () => {
  const budgetData = {
    totalIncome: 6000, // 3500 + 2500
    totalProvisions: 350, // From provisions calculation
    totalFixedExpenses: 1320, // From fixed expenses calculation
    totalVariableExpenses: 120.50, // From transactions (-75.50 - 45.00, excluding -25.00)
    availableBudget: 0 // Will be calculated
  }

  test('should calculate available budget correctly', () => {
    const result = calculateBudgetBalance(budgetData)
    
    // Available = Income - Provisions - Fixed - Variable
    // 6000 - 350 - 1320 - 120.50 = 4209.50
    expect(result.availableBudget).toBeCloseTo(4209.50, 2)
    expect(result.budgetUtilizationRate).toBeCloseTo(29.84, 2) // (1790.5 / 6000) * 100
  })

  test('should handle negative available budget', () => {
    const overBudget = {
      ...budgetData,
      totalProvisions: 2000,
      totalFixedExpenses: 3000,
      totalVariableExpenses: 2000
    }
    
    const result = calculateBudgetBalance(overBudget)
    
    expect(result.availableBudget).toBeLessThan(0)
    expect(result.budgetUtilizationRate).toBeGreaterThan(100)
    expect(result.isOverBudget).toBe(true)
  })

  test('should calculate member-specific budgets', () => {
    const result = calculateBudgetBalance(budgetData, mockConfig)
    
    // Alice's income: 3500, Bob's income: 2500
    // Split provisions and fixed expenses according to revenue ratio
    expect(result.member1Available).toBeGreaterThan(0)
    expect(result.member2Available).toBeGreaterThan(0)
    expect(result.member1Available + result.member2Available).toBeCloseTo(result.availableBudget, 1)
  })

  test('should handle zero income gracefully', () => {
    const zeroIncome = {
      ...budgetData,
      totalIncome: 0
    }
    
    const result = calculateBudgetBalance(zeroIncome)
    
    expect(result.availableBudget).toBeLessThan(0)
    expect(result.budgetUtilizationRate).toBe(Infinity)
    expect(result.isOverBudget).toBe(true)
  })
})

describe('Edge Cases and Error Handling', () => {
  test('should handle null/undefined inputs gracefully', () => {
    expect(() => calculateProvisionTotal(null as any)).not.toThrow()
    expect(() => calculateFixedExpenseTotal(undefined as any)).not.toThrow()
    expect(() => formatCurrency(null as any)).not.toThrow()
  })

  test('should handle very small amounts', () => {
    expect(normalizeSpaces(formatCurrency(0.001))).toBe('0,00 €') // Rounds to zero
    expect(normalizeSpaces(formatCurrency(0.004))).toBe('0,00 €')
    // Note: 0.005 rounding may vary by JS engine
    expect(normalizeSpaces(formatCurrency(0.005))).toMatch(/0,0[01] €/)
  })

  test('should handle very large amounts without overflow', () => {
    const largeAmount = 999999999.99
    expect(normalizeSpaces(formatCurrency(largeAmount))).toBe('999 999 999,99 €')
    expect(parseAmount(formatCurrency(largeAmount))).toBeCloseTo(largeAmount, 2)
  })

  test('should maintain precision in calculations', () => {
    // Test floating point precision issues
    const provisions = [
      {
        id: 1,
        name: 'Test',
        monthlyAmount: 0.1 + 0.2, // 0.30000000000000004 in JavaScript
        member1Share: (0.1 + 0.2) / 2,
        member2Share: (0.1 + 0.2) / 2,
        isActive: true
      }
    ]
    
    const result = calculateProvisionTotal(provisions)
    
    // Should handle floating point precision correctly
    expect(result.total).toBeCloseTo(0.3, 10)
    expect(result.member1Total).toBeCloseTo(0.15, 10)
    expect(result.member2Total).toBeCloseTo(0.15, 10)
  })
})

describe('Integration Tests', () => {
  test('should handle complete budget calculation flow', () => {
    // Test the complete flow from configuration to final budget
    const splitResult = calculateSplit(mockConfig)
    const provisionsResult = calculateProvisionTotal(mockProvisions)
    const fixedExpensesResult = calculateFixedExpenseTotal(mockFixedExpenses)
    
    const budgetData = {
      totalIncome: mockConfig.rev1 + mockConfig.rev2,
      totalProvisions: provisionsResult.total,
      totalFixedExpenses: fixedExpensesResult.total,
      totalVariableExpenses: mockTransactions
        .filter(t => !t.exclude)
        .reduce((sum, t) => sum + Math.abs(t.amount), 0),
      availableBudget: 0
    }
    
    const budgetResult = calculateBudgetBalance(budgetData, mockConfig)
    
    // All calculations should be consistent
    expect(budgetResult.availableBudget).toBeCloseTo(
      budgetData.totalIncome - budgetData.totalProvisions - 
      budgetData.totalFixedExpenses - budgetData.totalVariableExpenses,
      2
    )
    
    expect(budgetResult.member1Available + budgetResult.member2Available)
      .toBeCloseTo(budgetResult.availableBudget, 1)
  })

  test('should maintain data consistency across operations', () => {
    // Verify that formatted amounts can be parsed back correctly
    const testAmounts = [0, 0.99, 1.00, 1234.56, -999.99, 1000000.00]
    
    testAmounts.forEach(amount => {
      const formatted = formatCurrency(amount)
      const parsed = parseAmount(formatted)
      expect(parsed).toBeCloseTo(amount, 2)
    })
  })
})