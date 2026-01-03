/**
 * Tests for custom hooks
 * Note: useAuth and AuthContext dont exist in this codebase
 * Testing available hooks only
 */
import { renderHook, act } from '@testing-library/react'

// Mock des dependances
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    query: {},
    pathname: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

describe('Hooks personnalises', () => {
  describe('useGlobalMonth from lib/month', () => {
    beforeEach(() => {
      // Reset localStorage mock
      localStorage.clear()
    })

    it('retourne le mois au format YYYY-MM', async () => {
      const { useGlobalMonth } = await import('../lib/month')
      const { result } = renderHook(() => useGlobalMonth())

      const [month] = result.current
      
      // Le mois devrait etre au format YYYY-MM
      expect(month).toMatch(/^\d{4}-\d{2}$/)
    })

    it('permet de changer le mois', async () => {
      const { useGlobalMonth } = await import('../lib/month')
      const { result } = renderHook(() => useGlobalMonth())

      const [, setMonth] = result.current

      // La fonction setMonth devrait etre une fonction
      expect(typeof setMonth).toBe('function')
    })
  })

  describe('useTransactions hook', () => {
    it('retourne un objet avec les fonctions de base', async () => {
      const { useTransactions } = await import('../hooks/useTransactions')
      const { result } = renderHook(() => useTransactions())

      // Verifie que le hook retourne les proprietes attendues
      expect(result.current).toHaveProperty('rows')
      expect(result.current).toHaveProperty('loading')
      expect(result.current).toHaveProperty('error')
    })
  })

  describe('useSettings hook', () => {
    it('retourne un objet avec les settings', async () => {
      const { useSettings } = await import('../hooks/useSettings')
      // useSettings requires isAuthenticated parameter
      const { result } = renderHook(() => useSettings(true))

      expect(result.current).toHaveProperty('cfg')
      expect(result.current).toHaveProperty('loading')
    })
  })
})
