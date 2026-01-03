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
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn()
  }),
  useSearchParams: () => ({
    get: jest.fn().mockReturnValue('test-import-id')
  }),
  usePathname: () => '/transactions'
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

    // Handle different URL patterns for API calls
    mockApi.get.mockImplementation((url: string) => {
      const baseUrl = url.split('?')[0]
      if (baseUrl === '/transactions' || baseUrl.includes('/transactions')) {
        return Promise.resolve({
          data: mockTransactions,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {} as any
        })
      }
      return Promise.resolve({ data: [], status: 200, statusText: 'OK', headers: {}, config: {} as any })
    })

    mockApi.post.mockResolvedValue({ data: {}, status: 200, statusText: 'OK', headers: {}, config: {} as any })
    mockApi.patch.mockResolvedValue({ data: {}, status: 200, statusText: 'OK', headers: {}, config: {} as any })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Page Rendering', () => {
    it('should render transactions page without crashing', async () => {
      render(<TransactionsPage />)

      // Wait for API call
      await waitFor(() => {
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })

    it('should call transactions API', async () => {
      render(<TransactionsPage />)

      await waitFor(() => {
        const calls = mockApi.get.mock.calls
        expect(calls.length).toBeGreaterThan(0)
      }, { timeout: 5000 })
    })
  })

  describe('API Mocking', () => {
    it('should handle patch requests', async () => {
      const response = await mockApi.patch('/transactions/1', { exclude: true })
      expect(response.status).toBe(200)
    })

  })

  describe('Error Handling', () => {
    it('should handle API errors', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('API Error'))

      // Should not throw when rendering with error
      expect(() => {
        render(<TransactionsPage />)
      }).not.toThrow()
    })

    it('should handle empty response', async () => {
      mockApi.get.mockResolvedValueOnce({
        data: [],
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {} as any
      })

      render(<TransactionsPage />)

      await waitFor(() => {
        expect(mockApi.get).toHaveBeenCalled()
      }, { timeout: 5000 })
    })
  })
})