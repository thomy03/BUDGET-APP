import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Alert from '../components/ui/Alert'
import MonthPicker from '../components/MonthPicker'

describe('Composants UI', () => {
  describe('Button', () => {
    it('rend le bouton correctement', () => {
      render(<Button>Cliquez-moi</Button>)
      const buttonElement = screen.getByText('Cliquez-moi')
      expect(buttonElement).toBeInTheDocument()
    })

    it('gère le clic correctement', () => {
      const handleClick = jest.fn()
      render(<Button onClick={handleClick}>Cliquez-moi</Button>)
      const buttonElement = screen.getByText('Cliquez-moi')
      fireEvent.click(buttonElement)
      expect(handleClick).toHaveBeenCalledTimes(1)
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

  describe('Toast', () => {
    it('affiche le message de toast', () => {
      render(<Alert message="Message de test" type="success" />)
      const toastElement = screen.getByText('Message de test')
      expect(toastElement).toBeInTheDocument()
      expect(toastElement).toHaveClass('text-green-800')
    })
  })

  describe('MonthPicker', () => {
    it('rend le sélecteur de mois', () => {
      const handleMonthChange = jest.fn()
      render(<MonthPicker 
        currentMonth="2023-06" 
        onMonthChange={handleMonthChange} 
      />)
      
      const monthDisplay = screen.getByText('Juin 2023')
      expect(monthDisplay).toBeInTheDocument()
    })

    it('navigue entre les mois', () => {
      const handleMonthChange = jest.fn()
      render(<MonthPicker 
        currentMonth="2023-06" 
        onMonthChange={handleMonthChange} 
      />)
      
      const nextMonthButton = screen.getByText('Suivant')
      const previousMonthButton = screen.getByText('Précédent')
      
      fireEvent.click(nextMonthButton)
      expect(handleMonthChange).toHaveBeenCalledWith('2023-07')
      
      fireEvent.click(previousMonthButton)
      expect(handleMonthChange).toHaveBeenCalledWith('2023-05')
    })
  })
})