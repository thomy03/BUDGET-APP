/**
 * Comprehensive tests for critical frontend components
 * Focuses on high-impact UI elements and business logic
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Import components to test
import { MonthPicker } from '../components/MonthPicker'
import { ProvisionsWidget } from '../components/ProvisionsWidget'
import { FixedExpenses } from '../components/FixedExpenses'
import { CsvImportProgress } from '../components/CsvImportProgress'
import { ImportSuccessBanner } from '../components/ImportSuccessBanner'

// Mock API and utilities
jest.mock('../lib/api', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  }
}))

jest.mock('../lib/month', () => ({
  useGlobalMonth: () => ({
    currentMonth: '2024-01',
    setCurrentMonth: jest.fn(),
    formatMonth: (month: string) => month,
    getPreviousMonth: (month: string) => '2023-12',
    getNextMonth: (month: string) => '2024-02'
  })
}))

describe('MonthPicker Component', () => {
  const defaultProps = {
    currentMonth: '2024-01',
    onMonthChange: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('should render current month correctly', () => {
    render(<MonthPicker {...defaultProps} />)
    
    // Should display current month
    expect(screen.getByDisplayValue('2024-01')).toBeInTheDocument()
  })

  test('should call onMonthChange when month input changes', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker {...defaultProps} onMonthChange={onMonthChange} />)
    
    const monthInput = screen.getByDisplayValue('2024-01')
    await user.clear(monthInput)
    await user.type(monthInput, '2024-02')
    
    await waitFor(() => {
      expect(onMonthChange).toHaveBeenCalledWith('2024-02')
    })
  })

  test('should navigate to previous month when clicking previous button', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker {...defaultProps} onMonthChange={onMonthChange} />)
    
    const prevButton = screen.getByRole('button', { name: /précédent|previous/i })
    await user.click(prevButton)
    
    expect(onMonthChange).toHaveBeenCalledWith('2023-12')
  })

  test('should navigate to next month when clicking next button', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker {...defaultProps} onMonthChange={onMonthChange} />)
    
    const nextButton = screen.getByRole('button', { name: /suivant|next/i })
    await user.click(nextButton)
    
    expect(onMonthChange).toHaveBeenCalledWith('2024-02')
  })

  test('should handle invalid month format gracefully', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker {...defaultProps} onMonthChange={onMonthChange} />)
    
    const monthInput = screen.getByDisplayValue('2024-01')
    await user.clear(monthInput)
    await user.type(monthInput, 'invalid-date')
    
    // Should not call onMonthChange with invalid format
    await waitFor(() => {
      expect(onMonthChange).not.toHaveBeenCalledWith('invalid-date')
    })
  })
})

describe('ProvisionsWidget Component', () => {
  const mockProvisions = [
    {
      id: 1,
      name: 'Épargne vacances',
      monthlyAmount: 200,
      member1Share: 100,
      member2Share: 100,
      isActive: true,
      icon: '🏖️',
      color: '#3b82f6'
    },
    {
      id: 2,
      name: 'Fonds d\'urgence',
      monthlyAmount: 150,
      member1Share: 90,
      member2Share: 60,
      isActive: true,
      icon: '🚨',
      color: '#ef4444'
    }
  ]

  const defaultProps = {
    provisions: mockProvisions,
    totalAmount: 350,
    onProvisionUpdate: jest.fn(),
    isLoading: false
  }

  test('should render all active provisions', () => {
    render(<ProvisionsWidget {...defaultProps} />)
    
    expect(screen.getByText('Épargne vacances')).toBeInTheDocument()
    expect(screen.getByText('Fonds d\'urgence')).toBeInTheDocument()
    expect(screen.getByText('🏖️')).toBeInTheDocument()
    expect(screen.getByText('🚨')).toBeInTheDocument()
  })

  test('should display correct total amount', () => {
    render(<ProvisionsWidget {...defaultProps} />)
    
    expect(screen.getByText('350,00 €')).toBeInTheDocument()
  })

  test('should show member splits correctly', () => {
    render(<ProvisionsWidget {...defaultProps} />)
    
    // Should show individual member amounts
    expect(screen.getByText('100,00 €')).toBeInTheDocument() // Alice's vacation
    expect(screen.getByText('90,00 €')).toBeInTheDocument() // Alice's emergency
  })

  test('should handle loading state', () => {
    render(<ProvisionsWidget {...defaultProps} isLoading={true} />)
    
    expect(screen.getByText('Chargement...')).toBeInTheDocument()
  })

  test('should handle empty provisions list', () => {
    render(<ProvisionsWidget {...defaultProps} provisions={[]} totalAmount={0} />)
    
    expect(screen.getByText('Aucune provision configurée')).toBeInTheDocument()
  })
})

describe('FixedExpenses Component', () => {
  const mockFixedExpenses = [
    {
      id: 1,
      label: 'Loyer',
      amount: 1200,
      frequency: 'mensuelle',
      category: 'logement',
      member1Share: 600,
      member2Share: 600,
      isActive: true
    },
    {
      id: 2,
      label: 'Assurance auto',
      amount: 60,
      frequency: 'mensuelle',
      category: 'transport',
      member1Share: 35,
      member2Share: 25,
      isActive: true
    }
  ]

  const defaultProps = {
    fixedExpenses: mockFixedExpenses,
    totalAmount: 1260,
    onExpenseUpdate: jest.fn(),
    isLoading: false
  }

  test('should render all active fixed expenses', () => {
    render(<FixedExpenses {...defaultProps} />)
    
    expect(screen.getByText('Loyer')).toBeInTheDocument()
    expect(screen.getByText('Assurance auto')).toBeInTheDocument()
  })

  test('should display correct amounts and splits', () => {
    render(<FixedExpenses {...defaultProps} />)
    
    expect(screen.getByText('1 200,00 €')).toBeInTheDocument() // Rent amount
    expect(screen.getByText('60,00 €')).toBeInTheDocument() // Insurance amount
    expect(screen.getByText('1 260,00 €')).toBeInTheDocument() // Total amount
  })

  test('should show frequency information', () => {
    render(<FixedExpenses {...defaultProps} />)
    
    expect(screen.getByText(/mensuelle/i)).toBeInTheDocument()
  })

  test('should group expenses by category', () => {
    render(<FixedExpenses {...defaultProps} />)
    
    expect(screen.getByText('Logement')).toBeInTheDocument()
    expect(screen.getByText('Transport')).toBeInTheDocument()
  })

  test('should handle adding new expense', async () => {
    const user = userEvent.setup()
    const onExpenseUpdate = jest.fn()
    
    render(<FixedExpenses {...defaultProps} onExpenseUpdate={onExpenseUpdate} />)
    
    const addButton = screen.getByRole('button', { name: /ajouter|add/i })
    await user.click(addButton)
    
    // Should open add expense modal
    expect(screen.getByText('Nouvelle dépense fixe')).toBeInTheDocument()
  })
})

describe('CsvImportProgress Component', () => {
  const defaultProps = {
    progress: 50,
    currentStep: 'validation',
    totalSteps: 4,
    errors: [],
    warnings: [],
    isComplete: false
  }

  test('should display current progress percentage', () => {
    render(<CsvImportProgress {...defaultProps} />)
    
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  test('should show current step information', () => {
    render(<CsvImportProgress {...defaultProps} />)
    
    expect(screen.getByText(/validation/i)).toBeInTheDocument()
    expect(screen.getByText('Étape 2 sur 4')).toBeInTheDocument()
  })

  test('should display errors when present', () => {
    const propsWithErrors = {
      ...defaultProps,
      errors: ['Fichier corrompu', 'Format non supporté']
    }
    
    render(<CsvImportProgress {...propsWithErrors} />)
    
    expect(screen.getByText('Fichier corrompu')).toBeInTheDocument()
    expect(screen.getByText('Format non supporté')).toBeInTheDocument()
  })

  test('should display warnings when present', () => {
    const propsWithWarnings = {
      ...defaultProps,
      warnings: ['Lignes dupliquées détectées', 'Catégories manquantes']
    }
    
    render(<CsvImportProgress {...propsWithWarnings} />)
    
    expect(screen.getByText('Lignes dupliquées détectées')).toBeInTheDocument()
    expect(screen.getByText('Catégories manquantes')).toBeInTheDocument()
  })

  test('should show completion state', () => {
    const completeProps = {
      ...defaultProps,
      progress: 100,
      currentStep: 'complete',
      isComplete: true
    }
    
    render(<CsvImportProgress {...completeProps} />)
    
    expect(screen.getByText('Import terminé avec succès')).toBeInTheDocument()
  })
})

describe('ImportSuccessBanner Component', () => {
  const defaultProps = {
    importResult: {
      importedCount: 125,
      duplicatesCount: 3,
      errorsCount: 0,
      monthsAffected: ['2024-01', '2024-02'],
      processingTimeMs: 1250
    },
    onClose: jest.fn()
  }

  test('should display import statistics', () => {
    render(<ImportSuccessBanner {...defaultProps} />)
    
    expect(screen.getByText('125 transactions importées')).toBeInTheDocument()
    expect(screen.getByText('3 doublons détectés')).toBeInTheDocument()
    expect(screen.getByText('2024-01, 2024-02')).toBeInTheDocument()
  })

  test('should show processing time', () => {
    render(<ImportSuccessBanner {...defaultProps} />)
    
    expect(screen.getByText(/1\.25s/)).toBeInTheDocument()
  })

  test('should handle close action', async () => {
    const user = userEvent.setup()
    const onClose = jest.fn()
    
    render(<ImportSuccessBanner {...defaultProps} onClose={onClose} />)
    
    const closeButton = screen.getByRole('button', { name: /fermer|close/i })
    await user.click(closeButton)
    
    expect(onClose).toHaveBeenCalled()
  })

  test('should highlight errors if present', () => {
    const propsWithErrors = {
      ...defaultProps,
      importResult: {
        ...defaultProps.importResult,
        errorsCount: 5
      }
    }
    
    render(<ImportSuccessBanner {...propsWithErrors} />)
    
    expect(screen.getByText('5 erreurs')).toBeInTheDocument()
    // Should have error styling
    expect(screen.getByText('5 erreurs').closest('.text-red-600')).toBeInTheDocument()
  })
})

// Integration test for component interactions
describe('Component Integration', () => {
  test('should handle month change propagation between components', async () => {
    const user = userEvent.setup()
    let currentMonth = '2024-01'
    const setCurrentMonth = jest.fn((newMonth) => {
      currentMonth = newMonth
    })

    // Mock a parent component that uses both MonthPicker and ProvisionsWidget
    const TestParent = () => {
      return (
        <div>
          <MonthPicker 
            currentMonth={currentMonth} 
            onMonthChange={setCurrentMonth} 
          />
          <ProvisionsWidget 
            provisions={[]} 
            totalAmount={0} 
            onProvisionUpdate={jest.fn()} 
          />
        </div>
      )
    }

    render(<TestParent />)

    // Change month in picker
    const monthInput = screen.getByDisplayValue('2024-01')
    await user.clear(monthInput)
    await user.type(monthInput, '2024-03')

    expect(setCurrentMonth).toHaveBeenCalledWith('2024-03')
  })
})

// Performance and accessibility tests
describe('Accessibility and Performance', () => {
  test('should have proper ARIA labels', () => {
    const { container } = render(
      <MonthPicker currentMonth="2024-01" onMonthChange={jest.fn()} />
    )
    
    // Check for ARIA attributes
    const monthInput = container.querySelector('input[type="month"]')
    expect(monthInput).toHaveAttribute('aria-label')
  })

  test('should support keyboard navigation', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker currentMonth="2024-01" onMonthChange={onMonthChange} />)
    
    // Should be focusable with keyboard
    const monthInput = screen.getByDisplayValue('2024-01')
    await user.tab()
    
    expect(monthInput).toHaveFocus()
  })

  test('should handle large datasets efficiently', () => {
    // Test with large provisions list
    const largeProvisionsList = Array.from({ length: 100 }, (_, i) => ({
      id: i + 1,
      name: `Provision ${i + 1}`,
      monthlyAmount: 50 + i,
      member1Share: 25 + i/2,
      member2Share: 25 + i/2,
      isActive: true,
      icon: '💰',
      color: '#3b82f6'
    }))

    const start = performance.now()
    render(
      <ProvisionsWidget 
        provisions={largeProvisionsList}
        totalAmount={largeProvisionsList.reduce((sum, p) => sum + p.monthlyAmount, 0)}
        onProvisionUpdate={jest.fn()}
      />
    )
    const end = performance.now()
    
    // Should render within reasonable time (< 100ms)
    expect(end - start).toBeLessThan(100)
  })
})

// Error boundary and edge cases
describe('Error Handling and Edge Cases', () => {
  test('should handle null/undefined props gracefully', () => {
    // Should not crash with minimal props
    expect(() => {
      render(<ProvisionsWidget provisions={[]} totalAmount={0} onProvisionUpdate={jest.fn()} />)
    }).not.toThrow()
  })

  test('should handle network errors gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {})
    
    // Mock failed API call
    const mockApi = require('../lib/api').api
    mockApi.get.mockRejectedValue(new Error('Network error'))
    
    // Component should still render without crashing
    render(<ProvisionsWidget provisions={[]} totalAmount={0} onProvisionUpdate={jest.fn()} />)
    
    // Wait for any async effects
    await waitFor(() => {
      expect(screen.getByText(/provisions/i)).toBeInTheDocument()
    })
    
    consoleError.mockRestore()
  })

  test('should validate input data types', async () => {
    const user = userEvent.setup()
    const onMonthChange = jest.fn()
    
    render(<MonthPicker currentMonth="2024-01" onMonthChange={onMonthChange} />)
    
    const monthInput = screen.getByDisplayValue('2024-01')
    
    // Try invalid input
    await user.clear(monthInput)
    await user.type(monthInput, 'not-a-date')
    
    // Should not call onChange with invalid data
    expect(onMonthChange).not.toHaveBeenCalledWith('not-a-date')
  })
})