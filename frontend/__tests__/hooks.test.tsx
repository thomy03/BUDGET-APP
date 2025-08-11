import { renderHook, act } from '@testing-library/react-hooks'
import { useAuth } from '../hooks/useAuth'
import { useGlobalMonth } from '../hooks/useGlobalMonth'

// Mock des dépendances
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    query: {},
    pathname: '/',
  }),
}))

jest.mock('../context/AuthContext', () => ({
  useAuthContext: () => ({
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}))

describe('Hooks personnalisés', () => {
  describe('useAuth', () => {
    it('gère correctement le cycle de vie de l\'authentification', () => {
      const { result } = renderHook(() => useAuth())

      // Tester l'état initial
      expect(result.current.isAuthenticated).toBe(false)

      // Simuler une connexion
      act(() => {
        result.current.login({
          username: 'testuser',
          email: 'test@example.com',
          token: 'fake-jwt-token'
        })
      })

      // Vérifier l'état après connexion
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user?.username).toBe('testuser')

      // Simuler une déconnexion
      act(() => {
        result.current.logout()
      })

      // Vérifier l'état après déconnexion
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBeNull()
    })
  })

  describe('useGlobalMonth', () => {
    it('permet de naviguer entre les mois', () => {
      const { result } = renderHook(() => useGlobalMonth())

      // Vérifier le mois initial
      const currentDate = new Date()
      const initialMonth = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}`
      expect(result.current.currentMonth).toBe(initialMonth)

      // Changer de mois
      act(() => {
        result.current.setMonth('2023-06')
      })

      // Vérifier le changement de mois
      expect(result.current.currentMonth).toBe('2023-06')

      // Tester la navigation par incrément
      act(() => {
        result.current.nextMonth()
      })
      expect(result.current.currentMonth).toBe('2023-07')

      act(() => {
        result.current.previousMonth()
      })
      expect(result.current.currentMonth).toBe('2023-06')
    })
  })
})