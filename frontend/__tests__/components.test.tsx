import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Alert from '../components/ui/Alert'

// Mock des hooks necessaires pour MonthPicker
jest.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}))

jest.mock('../lib/month', () => ({
  useGlobalMonth: () => ['2023-06', jest.fn()],
  useGlobalMonthWithUrl: () => ['2023-06', jest.fn()],
}))

describe('Composants UI', () => {
  describe('Button', () => {
    it('rend le bouton correctement', () => {
      render(<Button>Cliquez-moi</Button>)
      const buttonElement = screen.getByText('Cliquez-moi')
      expect(buttonElement).toBeInTheDocument()
    })

    it('gere le clic correctement', () => {
      const handleClick = jest.fn()
      render(<Button onClick={handleClick}>Cliquez-moi</Button>)
      const buttonElement = screen.getByText('Cliquez-moi')
      fireEvent.click(buttonElement)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('affiche etat de chargement', () => {
      render(<Button loading>Test</Button>)
      expect(screen.getByText('Chargement...')).toBeInTheDocument()
    })

    it('desactive le bouton quand disabled', () => {
      render(<Button disabled>Desactive</Button>)
      expect(screen.getByRole('button')).toBeDisabled()
    })
  })

  describe('Card', () => {
    it('rend le contenu du card', () => {
      render(
        <Card>
          <div>Contenu du card</div>
        </Card>
      )
      const cardContent = screen.getByText('Contenu du card')
      expect(cardContent).toBeInTheDocument()
    })
  })

  describe('Alert', () => {
    it('affiche le message de succes', () => {
      render(<Alert message="Message de test" type="success" />)
      const alertElement = screen.getByText('Message de test')
      expect(alertElement).toBeInTheDocument()
    })

    it('affiche le message erreur', () => {
      render(<Alert message="Erreur test" type="error" />)
      const alertElement = screen.getByText('Erreur test')
      expect(alertElement).toBeInTheDocument()
    })
  })

  describe('MonthPicker', () => {
    // Note: MonthPicker uses icon buttons with title attributes, not text
    it('rend le selecteur de mois', async () => {
      const MonthPicker = (await import('../components/MonthPicker')).default
      render(<MonthPicker />)

      // Le MonthPicker affiche "Juin 2023" pour 2023-06
      expect(screen.getByText(/Juin/)).toBeInTheDocument()
      expect(screen.getByText(/2023/)).toBeInTheDocument()
    })

    it('a des boutons de navigation', async () => {
      const MonthPicker = (await import('../components/MonthPicker')).default
      render(<MonthPicker />)

      // Les boutons utilisent title pour accessibilite
      const prevButton = screen.getByTitle('Mois precedent')
      const nextButton = screen.getByTitle('Mois suivant')

      expect(prevButton).toBeInTheDocument()
      expect(nextButton).toBeInTheDocument()
    })

    it('navigue au mois precedent avec props', async () => {
      const MonthPicker = (await import('../components/MonthPicker')).default
      const setMonth = jest.fn()

      render(<MonthPicker currentMonth="2023-06" onMonthChange={setMonth} />)

      const prevButton = screen.getByTitle('Mois precedent')
      fireEvent.click(prevButton)

      expect(setMonth).toHaveBeenCalledWith('2023-05')
    })

    it('navigue au mois suivant avec props', async () => {
      const MonthPicker = (await import('../components/MonthPicker')).default
      const setMonth = jest.fn()

      render(<MonthPicker currentMonth="2023-06" onMonthChange={setMonth} />)

      const nextButton = screen.getByTitle('Mois suivant')
      fireEvent.click(nextButton)

      expect(setMonth).toHaveBeenCalledWith('2023-07')
    })
  })
})
