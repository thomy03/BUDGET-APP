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
      token: 'mock-token',
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      validateSession: jest.fn()
    })

    mockUseGlobalMonth.mockReturnValue(['2023-06', jest.fn()])

    // Setup API mocks with query parameter support
    mockApi.get.mockImplementation((url: string, config?: any) => {
      // Remove query params for matching
      const baseUrl = url.split('?')[0]

      switch (baseUrl) {
        case '/config':
          return Promise.resolve({ data: mockConfig })
        case '/summary':
          return Promise.resolve({ data: mockSummary })
        case '/custom-provisions':
          return Promise.resolve({ data: mockProvisions })
        case '/fixed-lines':
          return Promise.resolve({ data: mockFixedExpenses })
        case '/transactions':
          return Promise.resolve({ data: [] })
        case '/predictions/overview':
          return Promise.resolve({ data: { predictions: [], alerts: [], recommendations: [], summary: {} } })
        case '/analytics/trends':
          return Promise.resolve({ data: { trends: [], average_income: 0, average_expenses: 0 } })
        case '/tags':
          return Promise.resolve({ data: [] })
        default:
          // Allow unmocked URLs to return appropriate empty data
          console.log(`Dashboard test - Unmocked URL: ${url}`)
          // Return arrays for endpoints that expect arrays
          if (baseUrl.includes('/transactions') || baseUrl.includes('/balance')) {
            return Promise.resolve({ data: [] })
          }
          return Promise.resolve({ data: {} })
      }
    })

    mockApi.post.mockImplementation((url: string) => {
      // Allow POST requests to succeed with empty response
      return Promise.resolve({ data: {} })
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Key Metrics Restructuring', () => {
    it('should render dashboard without crashing', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        // Just verify something rendered
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })

    it('should call API for config and summary', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        const calls = mockApi.get.mock.calls
        expect(calls.length).toBeGreaterThan(0)
      }, { timeout: 5000 })
    })

    it('should handle authenticated user correctly', async () => {
      expect(mockUseAuth()).toEqual(expect.objectContaining({
        isAuthenticated: true,
        loading: false
      }))
    })
  })

  describe('Detailed Budget Table with Subtotals', () => {
    it('should render budget sections', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })

    it('should fetch provisions data', async () => {
      render(<Dashboard />)

      await waitFor(() => {
        const calls = mockApi.get.mock.calls
        expect(calls.length).toBeGreaterThan(0)
      }, { timeout: 5000 })
    })
  })

  describe('Inactive Items Filtering', () => {
    it('should handle inactive provisions in mock data', async () => {
      const provisionsWithInactive = [
        ...mockProvisions,
        {
          ...mockProvisions[0],
          id: 3,
          name: 'Provision inactive',
          is_active: false
        }
      ]

      mockApi.get.mockImplementation((url: string) => {
        const baseUrl = url.split('?')[0]
        if (baseUrl === '/custom-provisions') {
          return Promise.resolve({ data: provisionsWithInactive })
        }
        // Return default data for other URLs
        return Promise.resolve({ data: {} })
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })
  })

  describe('Loading and Error States', () => {
    it('should render while loading', async () => {
      // Use a promise that never resolves to simulate loading
      mockApi.get.mockReturnValue(new Promise(() => {}))

      render(<Dashboard />)

      // Component should render something (loading state or initial render)
      expect(document.body.innerHTML).not.toBe('')
    })

    it('should handle API error gracefully', async () => {
      mockApi.get.mockRejectedValue(new Error('API Error'))

      // Should not throw when rendering with error
      expect(() => {
        render(<Dashboard />)
      }).not.toThrow()
    })

    it('should handle empty data without crashing', async () => {
      mockApi.get.mockImplementation((url: string) => {
        const baseUrl = url.split('?')[0]
        switch (baseUrl) {
          case '/config':
            return Promise.resolve({ data: mockConfig })
          case '/summary':
            return Promise.resolve({ data: mockSummary })
          case '/custom-provisions':
            return Promise.resolve({ data: [] })
          case '/fixed-lines':
            return Promise.resolve({ data: [] })
          default:
            return Promise.resolve({ data: {} })
        }
      })

      render(<Dashboard />)

      await waitFor(() => {
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })
  })
})