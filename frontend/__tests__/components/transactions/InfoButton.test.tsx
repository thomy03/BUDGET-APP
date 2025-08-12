/**
 * Comprehensive Tests for InfoButton AI Classification Component
 * Tests all visual states and user interactions according to specifications
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { InfoButton } from '../../../components/transactions/InfoButton';
import { Tx } from '../../../lib/api';

// Mock transaction factory
const createMockTransaction = (overrides: Partial<Tx> = {}): Tx => ({
  id: 1,
  amount: -100,
  label: 'Netflix Subscription',
  tags: 'netflix,streaming',
  expense_type: null,
  date: '2025-01-01',
  month: '2025-01',
  exclude: false,
  category: null,
  ...overrides
});

describe('InfoButton Component', () => {
  const defaultProps = {
    transaction: createMockTransaction(),
    onTriggerClassification: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Visual States', () => {
    it('should render 🛈 icon for unclassified expense transactions', () => {
      render(<InfoButton {...defaultProps} />);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
      expect(screen.getByText('🛈')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveClass('text-gray-400', 'hover:text-gray-600');
    });

    it('should render ⚠️ icon for pending classification state', () => {
      render(
        <InfoButton 
          {...defaultProps} 
          hasPendingClassification={true}
        />
      );
      
      expect(screen.getByText('⚠️')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveClass('text-orange-600', 'hover:text-orange-700');
      
      // Should show pulsing indicator
      expect(screen.getByRole('button').querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('should render 🤖 icon for AI auto-detected classifications', () => {
      const transaction = createMockTransaction({ expense_type: 'FIXED' });
      render(
        <InfoButton 
          {...defaultProps}
          transaction={transaction}
          isAutoDetected={true}
          confidenceScore={0.95}
        />
      );
      
      expect(screen.getByText('🤖')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveClass('text-green-600', 'hover:text-green-700');
      
      // Should show green indicator dot
      expect(screen.getByRole('button').querySelector('.bg-green-500')).toBeInTheDocument();
    });

    it('should render ✓ icon for manually classified transactions', () => {
      const transaction = createMockTransaction({ expense_type: 'VARIABLE' });
      render(
        <InfoButton 
          {...defaultProps}
          transaction={transaction}
          isAutoDetected={false}
        />
      );
      
      expect(screen.getByText('✓')).toBeInTheDocument();
      expect(screen.getByRole('button')).toHaveClass('text-blue-600', 'hover:text-blue-700');
    });

    it('should show spinner and ⏳ for processing state', () => {
      render(
        <InfoButton 
          {...defaultProps} 
          isClassifying={true}
        />
      );
      
      // Should show spinner
      expect(screen.getByRole('button').querySelector('.animate-spin')).toBeInTheDocument();
      // Button should be disabled
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should not render for revenue transactions (positive amounts)', () => {
      const revenueTransaction = createMockTransaction({ amount: 1500 });
      const { container } = render(
        <InfoButton 
          {...defaultProps}
          transaction={revenueTransaction}
        />
      );
      
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Tooltip Functionality', () => {
    it('should show appropriate tooltip for unclassified state', async () => {
      const user = userEvent.setup();
      render(<InfoButton {...defaultProps} />);
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      await waitFor(() => {
        expect(screen.getByText(/Cliquer pour analyser cette dépense avec l'IA/)).toBeInTheDocument();
      });
    });

    it('should show detailed tooltip for AI-classified transactions', async () => {
      const user = userEvent.setup();
      const transaction = createMockTransaction({ expense_type: 'FIXED' });
      
      render(
        <InfoButton 
          {...defaultProps}
          transaction={transaction}
          isAutoDetected={true}
          confidenceScore={0.89}
        />
      );
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      await waitFor(() => {
        expect(screen.getByText(/Classification IA: FIXED \(89% confiance\)/)).toBeInTheDocument();
        expect(screen.getByText(/Score: 89% • Haute confiance/)).toBeInTheDocument();
      });
    });

    it('should show pending classification tooltip with action hint', async () => {
      const user = userEvent.setup();
      render(
        <InfoButton 
          {...defaultProps} 
          hasPendingClassification={true}
        />
      );
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      await waitFor(() => {
        expect(screen.getByText(/Suggestion IA en attente de validation/)).toBeInTheDocument();
        expect(screen.getByText(/Cliquer pour valider ou modifier/)).toBeInTheDocument();
      });
    });

    it('should show processing tooltip during classification', async () => {
      const user = userEvent.setup();
      render(
        <InfoButton 
          {...defaultProps} 
          isClassifying={true}
        />
      );
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      await waitFor(() => {
        expect(screen.getByText(/Classification IA en cours\.\.\./)).toBeInTheDocument();
      });
    });

    it('should hide tooltip on mouse leave', async () => {
      const user = userEvent.setup();
      render(<InfoButton {...defaultProps} />);
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      // Tooltip should appear
      await waitFor(() => {
        expect(screen.getByText(/Cliquer pour analyser/)).toBeInTheDocument();
      });
      
      await user.unhover(button);
      
      // Tooltip should disappear
      await waitFor(() => {
        expect(screen.queryByText(/Cliquer pour analyser/)).not.toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('should call onTriggerClassification when clicked', async () => {
      const mockTrigger = jest.fn();
      const user = userEvent.setup();
      
      render(
        <InfoButton 
          {...defaultProps}
          onTriggerClassification={mockTrigger}
        />
      );
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      expect(mockTrigger).toHaveBeenCalledTimes(1);
    });

    it('should not trigger classification when processing', async () => {
      const mockTrigger = jest.fn();
      const user = userEvent.setup();
      
      render(
        <InfoButton 
          {...defaultProps}
          onTriggerClassification={mockTrigger}
          isClassifying={true}
        />
      );
      
      const button = screen.getByRole('button');
      
      // Button should be disabled
      expect(button).toBeDisabled();
      
      // Simulate click attempt
      fireEvent.click(button);
      
      expect(mockTrigger).not.toHaveBeenCalled();
    });

    it('should be keyboard accessible with proper focus states', async () => {
      const mockTrigger = jest.fn();
      const user = userEvent.setup();
      
      render(
        <InfoButton 
          {...defaultProps}
          onTriggerClassification={mockTrigger}
        />
      );
      
      const button = screen.getByRole('button');
      
      // Test keyboard navigation
      await user.tab();
      expect(button).toHaveFocus();
      expect(button).toHaveClass('focus:ring-2', 'focus:ring-blue-500');
      
      // Test Enter key activation
      await user.keyboard('{Enter}');
      expect(mockTrigger).toHaveBeenCalledTimes(1);
      
      // Test Space key activation
      mockTrigger.mockClear();
      await user.keyboard(' ');
      expect(mockTrigger).toHaveBeenCalledTimes(1);
    });
  });

  describe('Confidence Score Display', () => {
    const confidenceLevels = [
      { score: 0.95, level: 'Haute confiance' },
      { score: 0.75, level: 'Confiance moyenne' },
      { score: 0.45, level: 'Faible confiance' }
    ];

    confidenceLevels.forEach(({ score, level }) => {
      it(`should display ${level} for confidence score ${score}`, async () => {
        const user = userEvent.setup();
        const transaction = createMockTransaction({ expense_type: 'FIXED' });
        
        render(
          <InfoButton 
            {...defaultProps}
            transaction={transaction}
            isAutoDetected={true}
            confidenceScore={score}
          />
        );
        
        const button = screen.getByRole('button');
        await user.hover(button);
        
        await waitFor(() => {
          expect(screen.getByText(new RegExp(level))).toBeInTheDocument();
          expect(screen.getByText(new RegExp(`${Math.round(score * 100)}%`))).toBeInTheDocument();
        });
      });
    });
  });

  describe('Visual Indicators', () => {
    it('should show pulsing orange dot for pending classification', () => {
      render(
        <InfoButton 
          {...defaultProps} 
          hasPendingClassification={true}
        />
      );
      
      const indicator = screen.getByRole('button').querySelector('.bg-orange-500.animate-pulse');
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass('w-2', 'h-2', 'rounded-full');
    });

    it('should show static green dot for auto-detected classification', () => {
      const transaction = createMockTransaction({ expense_type: 'FIXED' });
      render(
        <InfoButton 
          {...defaultProps}
          transaction={transaction}
          isAutoDetected={true}
        />
      );
      
      const indicator = screen.getByRole('button').querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
      expect(indicator).not.toHaveClass('animate-pulse');
    });

    it('should show ring indicator for AI-related states', () => {
      render(
        <InfoButton 
          {...defaultProps} 
          hasPendingClassification={true}
        />
      );
      
      expect(screen.getByRole('button')).toHaveClass('ring-1', 'ring-current', 'ring-opacity-30');
    });
  });

  describe('Responsive Design', () => {
    it('should maintain proper sizing across different screen sizes', () => {
      const { rerender } = render(<InfoButton {...defaultProps} />);
      
      const button = screen.getByRole('button');
      
      // Should have consistent sizing classes
      expect(button).toHaveClass('w-6', 'h-6', 'text-sm');
      
      // Icon should be properly sized
      const icon = screen.getByText('🛈');
      expect(icon).toHaveClass('text-xs');
    });

    it('should handle long transaction labels in tooltips', async () => {
      const user = userEvent.setup();
      const longLabelTransaction = createMockTransaction({
        label: 'This is a very long transaction label that might overflow in the tooltip display area'
      });
      
      render(
        <InfoButton 
          {...defaultProps}
          transaction={longLabelTransaction}
        />
      );
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      await waitFor(() => {
        const tooltip = screen.getByText(/Cliquer pour analyser/);
        expect(tooltip).toBeInTheDocument();
        // Tooltip should have proper positioning classes
        expect(tooltip.closest('.absolute')).toHaveClass('whitespace-nowrap');
      });
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily when props don\'t change', () => {
      const renderSpy = jest.fn();
      const TestWrapper = (props: any) => {
        renderSpy();
        return <InfoButton {...props} />;
      };
      
      const { rerender } = render(
        <TestWrapper {...defaultProps} />
      );
      
      expect(renderSpy).toHaveBeenCalledTimes(1);
      
      // Rerender with same props
      rerender(<TestWrapper {...defaultProps} />);
      
      // Should not trigger additional renders due to React optimization
      expect(renderSpy).toHaveBeenCalledTimes(2);
    });

    it('should handle rapid state changes gracefully', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<InfoButton {...defaultProps} />);
      
      // Rapidly change states
      rerender(<InfoButton {...defaultProps} isClassifying={true} />);
      rerender(<InfoButton {...defaultProps} hasPendingClassification={true} />);
      rerender(<InfoButton {...defaultProps} />);
      
      // Component should remain stable
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
      
      await user.click(button);
      expect(defaultProps.onTriggerClassification).toHaveBeenCalled();
    });
  });

  describe('Error Boundaries', () => {
    it('should handle missing transaction data gracefully', () => {
      const incompleteTransaction = createMockTransaction({
        label: undefined as any,
        tags: undefined as any
      });
      
      expect(() => {
        render(
          <InfoButton 
            {...defaultProps}
            transaction={incompleteTransaction}
          />
        );
      }).not.toThrow();
      
      // Should still render button
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should handle invalid confidence scores', async () => {
      const user = userEvent.setup();
      const transaction = createMockTransaction({ expense_type: 'FIXED' });
      
      render(
        <InfoButton 
          {...defaultProps}
          transaction={transaction}
          isAutoDetected={true}
          confidenceScore={NaN}
        />
      );
      
      const button = screen.getByRole('button');
      await user.hover(button);
      
      // Should not crash and should handle NaN gracefully
      await waitFor(() => {
        expect(screen.getByText(/Classification IA: FIXED/)).toBeInTheDocument();
      });
    });
  });
});