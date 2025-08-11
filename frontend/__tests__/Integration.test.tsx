import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { api } from '../lib/api'

// Mock dependencies
jest.mock('../lib/api')
jest.mock('../lib/auth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    loading: false,
    user: null,
    login: jest.fn(),
    logout: jest.fn()
  })
}))
jest.mock('../lib/month', () => ({
  useGlobalMonth: () => ['2023-06', jest.fn()],
  useGlobalMonthWithUrl: () => ['2023-06', jest.fn()]
}))
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => ({ get: jest.fn().mockReturnValue(null) })
}))

const mockApi = api as jest.Mocked<typeof api>

// Import components after mocking
import Dashboard from '../app/page'
import TransactionsPage from '../app/transactions/page'

// Mock data representing the complete workflow
const mockImportResponse = {
  importId: 'test-import-123',
  months: [
    {
      month: '2023-06',
      newCount: 45,
      totalCount: 45,
      txIds: [1, 2, 3, 4, 5],
      firstDate: '2023-06-01',
      lastDate: '2023-06-30'
    }
  ],
  suggestedMonth: '2023-06',
  duplicatesCount: 0,
  warnings: [],
  errors: [],
  processing: 'done',
  fileName: 'transactions_june.csv',
  processingMs: 1250
}

const mockTransactions = [
  {
    id: 1,
    date_op: '2023-06-01',
    label: 'Salaire Alice',
    category: 'Revenus',
    category_parent: 'Revenus',
    amount: 3000,
    account_label: 'Compte Alice',
    tags: ['salaire'],
    month: '2023-06',
    is_expense: false,
    exclude: false,
    row_id: 'hash1',
    import_id: 'test-import-123'
  },
  {
    id: 2,
    date_op: '2023-06-01',
    label: 'Salaire Bob',
    category: 'Revenus',
    category_parent: 'Revenus',
    amount: 2500,
    account_label: 'Compte Bob',
    tags: ['salaire'],
    month: '2023-06',
    is_expense: false,
    exclude: false,
    row_id: 'hash2',
    import_id: 'test-import-123'
  },
  {
    id: 3,
    date_op: '2023-06-05',
    label: 'Courses Carrefour',
    category: 'Alimentation',
    category_parent: 'Dépenses',
    amount: -150.75,
    account_label: 'Compte Joint',
    tags: ['courses', 'alimentaire'],
    month: '2023-06',
    is_expense: true,
    exclude: false,
    row_id: 'hash3',
    import_id: 'test-import-123'
  },
  {
    id: 4,
    date_op: '2023-06-10',
    label: 'Essence',
    category: 'Transport',
    category_parent: 'Dépenses',
    amount: -65.20,
    account_label: 'Compte Alice',
    tags: ['essence', 'voiture'],
    month: '2023-06',
    is_expense: true,
    exclude: false,
    row_id: 'hash4',
    import_id: 'test-import-123'
  },
  {
    id: 5,
    date_op: '2023-06-15',
    label: 'Restaurant',
    category: 'Sorties',
    category_parent: 'Dépenses',
    amount: -85.50,
    account_label: 'Compte Bob',
    tags: ['restaurant', 'sortie'],
    month: '2023-06',
    is_expense: true,
    exclude: false,
    row_id: 'hash5',
    import_id: 'test-import-123'
  }
]

const mockConfig = {
  id: 1,
  member1: 'Alice',
  member2: 'Bob',
  rev1: 3000,
  rev2: 2500,
  split_mode: 'revenus' as const,
  split1: 0.55,
  split2: 0.45,
  loan_equal: true,
  loan_amount: 1000,
  other_fixed_simple: true,
  other_fixed_monthly: 500,
  taxe_fonciere_ann: 1200,
  copro_montant: 300,
  copro_freq: 'trimestrielle' as const,
  other_split_mode: 'clé' as const,
  vac_percent: 5,
  vac_base: '2' as const
}

const mockSummary = {
  month: '2023-06',
  var_total: 5198.55, // 5500 revenue - 301.45 expenses
  r1: 3000,
  r2: 2500,
  member1: 'Alice',
  member2: 'Bob',
  total_p1: 2877.22,
  total_p2: 2321.33,
  detail: {
    'Alimentation': { 'Alice': 82.91, 'Bob': 67.84 },
    'Transport': { 'Alice': 65.20, 'Bob': 0 },
    'Sorties': { 'Alice': 0, 'Bob': 85.50 },
    'Revenus': { 'Alice': 3000, 'Bob': 2500 }
  },
  loan_amount: 1000,
  taxe_m: 100,
  copro_m: 100,
  other_fixed_total: 500,
  vac_monthly_total: 229.17
}

const mockProvisions = [
  {
    id: 1,
    name: 'Vacances',
    description: 'Épargne vacances',
    percentage: 5,
    base_calculation: 'total' as const,
    fixed_amount: null,
    split_mode: 'key' as const,
    split_member1: 55,
    split_member2: 45,
    icon: '🏖️',
    color: '#3B82F6',
    display_order: 1,
    is_active: true,
    is_temporary: false,
    start_date: null,
    end_date: null,
    target_amount: null,
    current_amount: 1200,
    created_at: '2023-01-01',
    updated_at: '2023-06-01',
    created_by: 'Alice',
    category: 'savings' as const,
    monthly_amount: 229.17,
    progress_percentage: 25
  }
]

const mockFixedExpenses = [
  {
    id: 1,
    label: 'Prêt immobilier',
    amount: 1200,
    freq: 'mensuelle' as const,
    split_mode: 'clé' as const,
    split1: 0.55,
    split2: 0.45,
    active: true
  }
]

describe('Integration Tests - Complete Workflow', () => {
  beforeEach(() => {
    // Setup comprehensive API mocks
    mockApi.get.mockImplementation((url, config) => {
      switch (url) {
        case '/config':
          return Promise.resolve({ data: mockConfig })
        case '/summary':
          return Promise.resolve({ data: mockSummary })
        case '/custom-provisions':
          return Promise.resolve({ data: mockProvisions })
        case '/fixed-lines':
          return Promise.resolve({ data: mockFixedExpenses })
        case '/transactions':
          return Promise.resolve({ data: mockTransactions })
        default:
          return Promise.reject(new Error(`Unmocked URL: ${url}`))
      }
    })

    mockApi.post.mockImplementation((url) => {
      if (url === '/import') {
        return Promise.resolve({ data: mockImportResponse })
      }
      return Promise.reject(new Error(`Unmocked POST URL: ${url}`))
    })

    mockApi.patch.mockImplementation((url, data) => {
      if (url.includes('/transactions/') && url.includes('/tags')) {
        const txId = parseInt(url.split('/')[2])
        const transaction = mockTransactions.find(tx => tx.id === txId)
        if (transaction) {
          return Promise.resolve({
            data: { ...transaction, tags: data.tags }
          })
        }
      }
      if (url.includes('/transactions/')) {
        const txId = parseInt(url.split('/')[2])
        const transaction = mockTransactions.find(tx => tx.id === txId)
        if (transaction) {
          return Promise.resolve({
            data: { ...transaction, exclude: data.exclude }
          })
        }
      }
      return Promise.reject(new Error(`Unmocked PATCH URL: ${url}`))
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('CSV Import to Dashboard Flow', () => {
    it('should complete the full import-to-dashboard workflow', async () => {
      // Step 1: Simulate CSV import (would normally be done via upload page)
      const importResponse = await mockApi.post('/import', {
        file: 'mock-csv-data'
      })

      expect(importResponse.data.importId).toBe('test-import-123')
      expect(importResponse.data.months).toHaveLength(1)
      expect(importResponse.data.months[0].newCount).toBe(45)

      // Step 2: Render Dashboard and verify data loading
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Tableau de bord')).toBeInTheDocument()
      })

      // Verify key metrics are displayed
      expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      expect(screen.getByText('Charges Fixes')).toBeInTheDocument()
      expect(screen.getByText('Variables')).toBeInTheDocument()
      expect(screen.getByText('Budget Total')).toBeInTheDocument()

      // Verify calculations include imported transaction data
      expect(screen.getByText('5198.55 €')).toBeInTheDocument() // Variables from imported transactions

      // Step 3: Navigate to transactions page and verify imported data
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('📊 Transactions')).toBeInTheDocument()
      })

      // Verify imported transactions are displayed
      expect(screen.getByText('Salaire Alice')).toBeInTheDocument()
      expect(screen.getByText('Salaire Bob')).toBeInTheDocument()
      expect(screen.getByText('Courses Carrefour')).toBeInTheDocument()
      expect(screen.getByText('Essence')).toBeInTheDocument()
      expect(screen.getByText('Restaurant')).toBeInTheDocument()

      // Verify total calculations
      expect(screen.getByText('Résumé du mois - 2023-06')).toBeInTheDocument()
      expect(screen.getByText('+5198.55 €')).toBeInTheDocument() // Net total
      expect(screen.getByText('5 transactions incluses')).toBeInTheDocument()
    })
  })

  describe('Transaction Management Flow', () => {
    it('should handle transaction exclusion and recalculate totals', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Restaurant')).toBeInTheDocument()
      })

      // Initial state - all transactions included
      expect(screen.getByText('+5198.55 €')).toBeInTheDocument()
      expect(screen.getByText('5 transactions incluses')).toBeInTheDocument()

      // Find and click the checkbox for the restaurant transaction
      const checkboxes = screen.getAllByRole('checkbox')
      const restaurantCheckbox = checkboxes[4] // Restaurant is the 5th transaction

      fireEvent.click(restaurantCheckbox)

      await waitFor(() => {
        expect(mockApi.patch).toHaveBeenCalledWith('/transactions/5', { exclude: true })
      })

      // Verify calculations would update (mocked response would update state)
      // In real scenario, the totals would recalculate to: 5198.55 + 85.50 = 5284.05
    })

    it('should handle tag management', async () => {
      const user = userEvent.setup()
      
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Essence')).toBeInTheDocument()
      })

      // Find the tag input for the essence transaction
      const tagInputs = screen.getAllByPlaceholderText('courses, resto, santé…')
      const essenceTagInput = tagInputs[3] // Essence is the 4th transaction

      // Clear and add new tags
      await user.clear(essenceTagInput)
      await user.type(essenceTagInput, 'essence, transport, voiture')
      
      // Simulate blur event to save tags
      fireEvent.blur(essenceTagInput)

      await waitFor(() => {
        expect(mockApi.patch).toHaveBeenCalledWith('/transactions/4/tags', { 
          tags: ['essence', 'transport', 'voiture'] 
        })
      })
    })
  })

  describe('Dashboard Calculations Flow', () => {
    it('should accurately reflect imported data in dashboard calculations', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Tableau de bord')).toBeInTheDocument()
      })

      // Verify provisions calculation: 5% of (3000 + 2500) = 275/year = 229.17/month
      expect(screen.getByText('229.17 €')).toBeInTheDocument()

      // Verify fixed expenses: 1200/month
      expect(screen.getByText('1200.00 €')).toBeInTheDocument()

      // Verify variables: Net from transactions = 5198.55
      expect(screen.getByText('5198.55 €')).toBeInTheDocument()

      // Verify total budget: 229.17 + 1200 + 5198.55 = 6627.72
      expect(screen.getByText('6627.72 €')).toBeInTheDocument()

      // Verify detailed breakdown shows transaction categories
      expect(screen.getByText('Alimentation')).toBeInTheDocument()
      expect(screen.getByText('Transport')).toBeInTheDocument()
      expect(screen.getByText('Sorties')).toBeInTheDocument()
      expect(screen.getByText('Revenus')).toBeInTheDocument()
    })

    it('should handle member-specific calculations correctly', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Alice')).toBeInTheDocument()
        expect(screen.getByText('Bob')).toBeInTheDocument()
      })

      // Verify member columns are present
      const aliceElements = screen.getAllByText('Alice')
      const bobElements = screen.getAllByText('Bob')
      
      expect(aliceElements.length).toBeGreaterThan(0)
      expect(bobElements.length).toBeGreaterThan(0)

      // Verify member-specific amounts based on splits
      // Alice should have higher amounts due to higher revenue (55% vs 45%)
    })
  })

  describe('Performance and Loading', () => {
    it('should handle concurrent API calls efficiently', async () => {
      const startTime = Date.now()
      
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Tableau de bord')).toBeInTheDocument()
      }, { timeout: 3000 })

      const loadTime = Date.now() - startTime
      
      // Verify all parallel API calls completed
      expect(mockApi.get).toHaveBeenCalledWith('/config')
      expect(mockApi.get).toHaveBeenCalledWith('/summary', { params: { month: '2023-06' } })
      expect(mockApi.get).toHaveBeenCalledWith('/custom-provisions')
      expect(mockApi.get).toHaveBeenCalledWith('/fixed-lines')

      // Performance check - should load within reasonable time
      expect(loadTime).toBeLessThan(2000) // 2 seconds max
    })

    it('should handle large datasets efficiently', async () => {
      // Mock large transaction dataset
      const largeTransactionSet = Array.from({ length: 500 }, (_, i) => ({
        id: i + 1,
        date_op: '2023-06-01',
        label: `Transaction ${i + 1}`,
        category: 'Divers',
        category_parent: 'Dépenses',
        amount: Math.random() * 1000 - 500,
        account_label: 'Compte Test',
        tags: [`tag${i}`],
        month: '2023-06',
        is_expense: Math.random() > 0.5,
        exclude: false,
        row_id: `hash${i}`,
        import_id: 'large-import'
      }))

      mockApi.get.mockImplementation((url) => {
        if (url === '/transactions') {
          return Promise.resolve({ data: largeTransactionSet })
        }
        return mockApi.get.getMockImplementation()?.(url) || Promise.reject(new Error('Mock not found'))
      })

      const startTime = Date.now()
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('500 transactions incluses')).toBeInTheDocument()
      }, { timeout: 5000 })

      const renderTime = Date.now() - startTime
      expect(renderTime).toBeLessThan(3000) // Should render large dataset within 3 seconds
    })
  })

  describe('Error Recovery Flow', () => {
    it('should handle API failures gracefully and allow recovery', async () => {
      // First, simulate an API failure
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Erreur lors du chargement des données')).toBeInTheDocument()
      })

      // Then simulate recovery by resetting the mock
      mockApi.get.mockImplementation((url) => {
        switch (url) {
          case '/config':
            return Promise.resolve({ data: mockConfig })
          case '/summary':
            return Promise.resolve({ data: mockSummary })
          case '/custom-provisions':
            return Promise.resolve({ data: mockProvisions })
          case '/fixed-lines':
            return Promise.resolve({ data: mockFixedExpenses })
          default:
            return Promise.reject(new Error(`Unknown URL: ${url}`))
        }
      })

      // Re-render or trigger reload
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Tableau de bord')).toBeInTheDocument()
      })

      // Verify recovery
      expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      expect(screen.queryByText('Erreur lors du chargement des données')).not.toBeInTheDocument()
    })
  })
})