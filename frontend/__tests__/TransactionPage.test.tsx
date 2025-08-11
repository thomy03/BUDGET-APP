import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { useAuth } from '../lib/auth'
import { useGlobalMonthWithUrl } from '../lib/month'
import { api } from '../lib/api'
import TransactionsPage from '../app/transactions/page'

// Mock dependencies
jest.mock('../lib/auth')
jest.mock('../lib/month')
jest.mock('../lib/api')
jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: jest.fn().mockReturnValue('test-import-id')
  })
}))

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>
const mockUseGlobalMonthWithUrl = useGlobalMonthWithUrl as jest.MockedFunction<typeof useGlobalMonthWithUrl>
const mockApi = api as jest.Mocked<typeof api>

// Mock transaction data
const mockTransactions = [
  {
    id: 1,
    date_op: '2023-06-01',
    label: 'Salaire',
    category: 'Revenus',
    category_parent: 'Revenus',
    amount: 2500,
    account_label: 'Compte Courant',
    tags: ['salaire'],
    month: '2023-06',
    is_expense: false,
    exclude: false,
    row_id: 'hash1',
    import_id: 'test-import-id'
  },
  {
    id: 2,
    date_op: '2023-06-05',
    label: 'Courses',
    category: 'Alimentation',
    category_parent: 'Dépenses',
    amount: -120.50,
    account_label: 'Compte Courant',
    tags: ['courses', 'alimentaire'],
    month: '2023-06',
    is_expense: true,
    exclude: false,
    row_id: 'hash2',
    import_id: 'test-import-id'
  },
  {
    id: 3,
    date_op: '2023-06-10',
    label: 'Restaurant',
    category: 'Sorties',
    category_parent: 'Dépenses',
    amount: -85.30,
    account_label: 'Compte Courant',
    tags: ['restaurant'],
    month: '2023-06',
    is_expense: true,
    exclude: true,
    row_id: 'hash3',
    import_id: 'test-import-id'
  }
]

describe('TransactionsPage - Financial Improvements', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      loading: false,
      user: null,
      token: 'mock-token',
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      validateSession: jest.fn()
    })
    
    mockUseGlobalMonthWithUrl.mockReturnValue(['2023-06', jest.fn()])
    
    mockApi.get.mockResolvedValue({
      data: mockTransactions,
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as any
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Total Recall Display', () => {
    it('should display month summary card with correct calculations', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Résumé du mois - 2023-06')).toBeInTheDocument()
      })

      // Check total amount (only non-excluded transactions: 2500 - 120.50 = 2379.50)
      expect(screen.getByText('+2379.50 €')).toBeInTheDocument()
      expect(screen.getByText('Total du mois')).toBeInTheDocument()

      // Check included/excluded counts
      expect(screen.getByText('2 transactions incluses (1 exclue)')).toBeInTheDocument()

      // Check income/expense breakdown
      expect(screen.getByText('+2500.00 € revenus')).toBeInTheDocument()
      expect(screen.getByText('-120.50 € dépenses')).toBeInTheDocument()
    })

    it('should recalculate totals when excluding/including transactions', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Résumé du mois - 2023-06')).toBeInTheDocument()
      })

      // Mock API patch response for toggle
      mockApi.patch.mockResolvedValue({
        data: { ...mockTransactions[0], exclude: true },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      })

      // Toggle the salary transaction (exclude it)
      const checkboxes = screen.getAllByRole('checkbox')
      fireEvent.click(checkboxes[0])

      await waitFor(() => {
        expect(mockApi.patch).toHaveBeenCalledWith('/transactions/1', { exclude: true })
      })
    })
  })

  describe('Table Footer Totals', () => {
    it('should display correct totals in table footer', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('TOTAUX DU MOIS')).toBeInTheDocument()
      })

      // Check transaction counts
      expect(screen.getByText('2/3 transactions')).toBeInTheDocument()
      expect(screen.getByText('(1 exclue)')).toBeInTheDocument()

      // Check expense/income breakdown
      expect(screen.getByText('-120.50 €')).toBeInTheDocument() // Expenses
      expect(screen.getByText('+2500.00 €')).toBeInTheDocument() // Income

      // Check net balance (2500 - 120.50 = 2379.50)
      expect(screen.getByText('+2379.50 €')).toBeInTheDocument()

      // Check transaction details
      expect(screen.getByText('Dépenses: 1 transactions')).toBeInTheDocument()
      expect(screen.getByText('Revenus: 1 transactions')).toBeInTheDocument()
      expect(screen.getByText('Solde net:')).toBeInTheDocument()
    })

    it('should handle negative net balance correctly', async () => {
      // Mock data with more expenses than income
      const highExpenseTransactions = [
        ...mockTransactions,
        {
          id: 4,
          date_op: '2023-06-15',
          label: 'Gros achat',
          category: 'Divers',
          category_parent: 'Dépenses',
          amount: -3000,
          account_label: 'Compte Courant',
          tags: ['gros achat'],
          month: '2023-06',
          is_expense: true,
          exclude: false,
          row_id: 'hash4',
          import_id: 'test-import-id'
        }
      ]

      mockApi.get.mockResolvedValueOnce({
        data: highExpenseTransactions,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      })

      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('TOTAUX DU MOIS')).toBeInTheDocument()
      })

      // Net balance should be negative (2500 - 120.50 - 3000 = -620.50)
      const negativeBalanceElements = screen.getAllByText('-620.50 €')
      expect(negativeBalanceElements.length).toBeGreaterThan(0)
    })
  })

  describe('Import Highlighting', () => {
    it('should highlight transactions from import', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getAllByText('Nouveau')).toHaveLength(3) // All transactions have the import_id
      })

      // Check that highlighted rows have the correct styling
      const newBadges = screen.getAllByText('Nouveau')
      newBadges.forEach(badge => {
        expect(badge).toHaveClass('bg-green-200', 'text-green-800')
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty transaction list', async () => {
      mockApi.get.mockResolvedValueOnce({
        data: [],
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      })

      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Aucune transaction pour ce mois')).toBeInTheDocument()
      })

      expect(screen.getByText('Importez un fichier pour commencer')).toBeInTheDocument()
      expect(screen.queryByText('Résumé du mois')).not.toBeInTheDocument()
    })

    it('should handle all transactions excluded', async () => {
      const allExcludedTransactions = mockTransactions.map(tx => ({ ...tx, exclude: true }))
      
      mockApi.get.mockResolvedValueOnce({
        data: allExcludedTransactions,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      })

      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Résumé du mois - 2023-06')).toBeInTheDocument()
      })

      // Total should be 0 when all transactions are excluded
      expect(screen.getByText('0.00 €')).toBeInTheDocument()
      expect(screen.getByText('0 transactions incluses (3 exclues)')).toBeInTheDocument()
    })

    it('should handle loading and error states', async () => {
      // Test loading state
      mockApi.get.mockReturnValue(new Promise(() => {})) // Never resolves

      render(<TransactionsPage />)

      expect(screen.getByText('Chargement des transactions...')).toBeInTheDocument()
      
      // Test error state
      mockApi.get.mockRejectedValue(new Error('API Error'))

      render(<TransactionsPage />)

      await waitFor(() => {
        expect(screen.getByText('Erreur lors du chargement des transactions')).toBeInTheDocument()
      })
    })
  })
})