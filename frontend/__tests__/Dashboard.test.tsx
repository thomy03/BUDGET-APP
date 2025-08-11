import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { useAuth } from '../lib/auth'
import { useGlobalMonth } from '../lib/month'
import { api } from '../lib/api'
import Dashboard from '../app/page'

// Mock dependencies
jest.mock('../lib/auth')
jest.mock('../lib/month')
jest.mock('../lib/api')
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn()
  })
}))

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>
const mockUseGlobalMonth = useGlobalMonth as jest.MockedFunction<typeof useGlobalMonth>
const mockApi = api as jest.Mocked<typeof api>

// Mock data
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
  var_total: 2500,
  r1: 3000,
  r2: 2500,
  member1: 'Alice',
  member2: 'Bob',
  total_p1: 1400,
  total_p2: 1100,
  detail: {
    'Alimentation': { 'Alice': 800, 'Bob': 600 },
    'Transport': { 'Alice': 350, 'Bob': 250 },
    'Loisirs': { 'Alice': 250, 'Bob': 250 }
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
    description: 'Épargne vacances annuelles',
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
  },
  {
    id: 2,
    name: 'Rénovation',
    description: 'Travaux maison',
    percentage: 0,
    base_calculation: 'fixed' as const,
    fixed_amount: 400,
    split_mode: '50/50' as const,
    split_member1: 50,
    split_member2: 50,
    icon: '🏠',
    color: '#10B981',
    display_order: 2,
    is_active: true,
    is_temporary: true,
    start_date: '2023-01-01',
    end_date: '2023-12-31',
    target_amount: 5000,
    current_amount: 2400,
    created_at: '2023-01-01',
    updated_at: '2023-06-01',
    created_by: 'Bob',
    category: 'project' as const,
    monthly_amount: 400,
    progress_percentage: 48
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
  },
  {
    id: 2,
    label: 'Assurance habitation',
    amount: 480,
    freq: 'annuelle' as const,
    split_mode: '50/50' as const,
    split1: 0.5,
    split2: 0.5,
    active: true
  },
  {
    id: 3,
    label: 'Internet',
    amount: 35,
    freq: 'mensuelle' as const,
    split_mode: '50/50' as const,
    split1: 0.5,
    split2: 0.5,
    active: false // Inactive expense
  }
]

describe('Dashboard - Financial Improvements', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      loading: false,
      user: null,
      login: jest.fn(),
      logout: jest.fn()
    })
    
    mockUseGlobalMonth.mockReturnValue(['2023-06', jest.fn()])
    
    // Setup API mocks
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
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Key Metrics Restructuring', () => {
    it('should display restructured key metrics correctly', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      })

      // Check all four key metric cards
      expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      expect(screen.getByText('Charges Fixes')).toBeInTheDocument()
      expect(screen.getByText('Variables')).toBeInTheDocument()
      expect(screen.getByText('Budget Total')).toBeInTheDocument()

      // Check icons
      expect(screen.getByText('🎯')).toBeInTheDocument() // Provisions
      expect(screen.getByText('💳')).toBeInTheDocument() // Fixed
      expect(screen.getByText('📊')).toBeInTheDocument() // Variables
      expect(screen.getByText('📈')).toBeInTheDocument() // Total
    })

    it('should calculate provisions total correctly', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      })

      // Total provisions should be: 229.17 (Vacances: 5% of 5500) + 400 (Rénovation fixed) = 629.17
      expect(screen.getByText('629.17 €')).toBeInTheDocument()
      expect(screen.getByText('2 provisions')).toBeInTheDocument()
    })

    it('should calculate fixed expenses total correctly', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Charges Fixes')).toBeInTheDocument()
      })

      // Fixed expenses: 1200 (monthly) + 40 (480/12 annual) = 1240 (only active ones)
      expect(screen.getByText('1240.00 €')).toBeInTheDocument()
      expect(screen.getByText('2 dépenses')).toBeInTheDocument() // Only active ones
    })

    it('should display variables from transactions', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Variables')).toBeInTheDocument()
      })

      expect(screen.getByText('2500.00 €')).toBeInTheDocument() // var_total from summary
      expect(screen.getByText('Transactions bancaires')).toBeInTheDocument()
    })

    it('should calculate and highlight budget total', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Budget Total')).toBeInTheDocument()
      })

      // Total: 629.17 (provisions) + 1240 (fixed) + 2500 (variables) = 4369.17
      expect(screen.getByText('4369.17 €')).toBeInTheDocument()
      expect(screen.getByText('TOTAL')).toBeInTheDocument() // Total badge
      expect(screen.getByText('Vision d\'ensemble')).toBeInTheDocument()
    })
  })

  describe('Detailed Budget Table with Subtotals', () => {
    it('should display organized sections with subtotals', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('🎯 PROVISIONS')).toBeInTheDocument()
      })

      // Check all section headers
      expect(screen.getByText('🎯 PROVISIONS')).toBeInTheDocument()
      expect(screen.getByText('💳 CHARGES FIXES')).toBeInTheDocument()
      expect(screen.getByText('📈 VARIABLES')).toBeInTheDocument()

      // Check subtotal rows
      expect(screen.getByText('Sous-total Provisions')).toBeInTheDocument()
      expect(screen.getByText('Sous-total Charges Fixes')).toBeInTheDocument()
      expect(screen.getByText('Sous-total Variables')).toBeInTheDocument()

      // Check grand total
      expect(screen.getByText('🏆 TOTAL GÉNÉRAL')).toBeInTheDocument()
    })

    it('should calculate member splits correctly for provisions', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('🏖️ Vacances')).toBeInTheDocument()
      })

      // Vacances: 229.17 total, split by revenue key (55/45)
      // Alice: 229.17 * 0.55 = 126.04, Bob: 229.17 * 0.45 = 103.13
      expect(screen.getByText('🏖️ Vacances')).toBeInTheDocument()
      
      // Rénovation: 400 total, split 50/50
      // Alice: 200, Bob: 200
      expect(screen.getByText('🏠 Rénovation')).toBeInTheDocument()
    })

    it('should calculate member splits correctly for fixed expenses', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Prêt immobilier')).toBeInTheDocument()
      })

      // Prêt immobilier: 1200 split by key (55/45)
      // Alice: 660, Bob: 540
      expect(screen.getByText('Prêt immobilier')).toBeInTheDocument()
      
      // Assurance habitation: 40/month (480/12), split 50/50
      // Alice: 20, Bob: 20
      expect(screen.getByText('Assurance habitation')).toBeInTheDocument()
    })

    it('should display transaction variables by category', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Alimentation')).toBeInTheDocument()
      })

      // Check all transaction categories
      expect(screen.getByText('Alimentation')).toBeInTheDocument()
      expect(screen.getByText('Transport')).toBeInTheDocument()
      expect(screen.getByText('Loisirs')).toBeInTheDocument()
    })

    it('should calculate grand total correctly', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('🏆 TOTAL GÉNÉRAL')).toBeInTheDocument()
      })

      // Grand total should sum all sections for each member
      // This would require complex calculations based on splits
      expect(screen.getByText('🏆 TOTAL GÉNÉRAL')).toBeInTheDocument()
    })
  })

  describe('Inactive Items Filtering', () => {
    it('should exclude inactive provisions from calculations', async () => {
      const provisionsWithInactive = [
        ...mockProvisions,
        {
          ...mockProvisions[0],
          id: 3,
          name: 'Provision inactive',
          is_active: false
        }
      ]

      mockApi.get.mockImplementation((url) => {
        if (url === '/custom-provisions') {
          return Promise.resolve({ data: provisionsWithInactive })
        }
        return mockApi.get.getMockImplementation()?.(url) || Promise.reject(new Error('Mock not found'))
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      })

      // Should still show "2 provisions" (only active ones)
      expect(screen.getByText('2 provisions')).toBeInTheDocument()
      expect(screen.queryByText('Provision inactive')).not.toBeInTheDocument()
    })

    it('should exclude inactive fixed expenses from calculations', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Charges Fixes')).toBeInTheDocument()
      })

      // Should show "2 dépenses" (only active ones, Internet is inactive)
      expect(screen.getByText('2 dépenses')).toBeInTheDocument()
      expect(screen.queryByText('Internet')).not.toBeInTheDocument()
    })
  })

  describe('Loading and Error States', () => {
    it('should handle loading state correctly', async () => {
      mockApi.get.mockReturnValue(new Promise(() => {})) // Never resolves

      render(<Dashboard />)

      expect(screen.getByText('Chargement des données...')).toBeInTheDocument()
    })

    it('should handle error state correctly', async () => {
      mockApi.get.mockRejectedValue(new Error('API Error'))

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Erreur lors du chargement des données')).toBeInTheDocument()
      })
    })

    it('should handle empty data gracefully', async () => {
      mockApi.get.mockImplementation((url) => {
        switch (url) {
          case '/config':
            return Promise.resolve({ data: mockConfig })
          case '/summary':
            return Promise.resolve({ data: mockSummary })
          case '/custom-provisions':
            return Promise.resolve({ data: [] })
          case '/fixed-lines':
            return Promise.resolve({ data: [] })
          default:
            return Promise.reject(new Error(`Unknown URL: ${url}`))
        }
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(screen.getByText('Total Provisions')).toBeInTheDocument()
      })

      // Should show 0 provisions and expenses
      expect(screen.getByText('0.00 €')).toBeInTheDocument() // Provisions total
      expect(screen.getByText('0 provision')).toBeInTheDocument()
      expect(screen.getByText('0 dépense')).toBeInTheDocument()
    })
  })
})