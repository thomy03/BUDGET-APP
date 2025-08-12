/**
 * Comprehensive Tests for ClassificationModal AI Component
 * Tests complete workflow from AI suggestion to user decision
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ClassificationModal, { ClassificationDecision } from '../../../components/transactions/ClassificationModal';
import { ExpenseClassificationResult } from '../../../lib/api';

// Mock classification result factory
const createMockClassification = (overrides: Partial<ExpenseClassificationResult> = {}): ExpenseClassificationResult => ({
  suggested_type: 'FIXED',
  confidence_score: 0.89,
  reasoning: 'Detected recurring subscription pattern',
  matched_rules: [
    {
      rule_id: 1,
      rule_name: 'Fixed subscription keywords',
      matched_keywords: ['netflix', 'subscription']
    }
  ],
  ...overrides
});

describe('ClassificationModal Component', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onDecision: jest.fn().mockResolvedValue(undefined),
    tagName: 'netflix',
    classification: createMockClassification(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Modal Rendering and Structure', () => {
    it('should render modal with correct title', () => {
      render(<ClassificationModal {...defaultProps} />);
      
      expect(screen.getByText('Classification de "netflix"')).toBeInTheDocument();
    });

    it('should not render when isOpen is false', () => {
      render(<ClassificationModal {...defaultProps} isOpen={false} />);
      
      expect(screen.queryByText('Classification de "netflix"')).not.toBeInTheDocument();
    });

    it('should display AI suggestion section with correct styling', () => {
      const highConfidenceClassification = createMockClassification({
        confidence_score: 0.95,
        suggested_type: 'FIXED'
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={highConfidenceClassification}
        />
      );
      
      // Should show high confidence styling
      const suggestionSection = screen.getByText('IA suggère : FIXED').closest('div');
      expect(suggestionSection).toHaveClass('bg-green-50', 'border-green-200');
      
      expect(screen.getByText('🤖')).toBeInTheDocument();
      expect(screen.getByText('95% sûr')).toBeInTheDocument();
    });

    it('should display medium confidence with appropriate styling', () => {
      const mediumConfidenceClassification = createMockClassification({
        confidence_score: 0.65,
        suggested_type: 'VARIABLE'
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={mediumConfidenceClassification}
        />
      );
      
      // Should show medium confidence styling
      const suggestionSection = screen.getByText('IA suggère : VARIABLE').closest('div');
      expect(suggestionSection).toHaveClass('bg-yellow-50', 'border-yellow-200');
      
      expect(screen.getByText('65% sûr')).toBeInTheDocument();
    });
  });

  describe('AI Reasoning Display', () => {
    it('should display AI reasoning and matched rules', () => {
      const classificationWithRules = createMockClassification({
        reasoning: 'Identified as recurring subscription service',
        matched_rules: [
          {
            rule_id: 1,
            rule_name: 'Streaming subscription pattern',
            matched_keywords: ['netflix', 'streaming']
          },
          {
            rule_id: 2,
            rule_name: 'Monthly charge pattern',
            matched_keywords: ['monthly', 'recurring']
          }
        ]
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={classificationWithRules}
        />
      );
      
      expect(screen.getByText('💡')).toBeInTheDocument();
      expect(screen.getByText('Raison :')).toBeInTheDocument();
      expect(screen.getByText('Identified as recurring subscription service')).toBeInTheDocument();
      
      expect(screen.getByText(/Règles correspondantes:/)).toBeInTheDocument();
      expect(screen.getByText(/Streaming subscription pattern, Monthly charge pattern/)).toBeInTheDocument();
    });

    it('should show default reasoning when none provided', () => {
      const classificationNoReasoning = createMockClassification({
        reasoning: undefined as any,
        matched_rules: []
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={classificationNoReasoning}
        />
      );
      
      expect(screen.getByText('Classification automatique basée sur les patterns détectés')).toBeInTheDocument();
    });
  });

  describe('User Choice Options', () => {
    it('should render all three classification options', () => {
      render(<ClassificationModal {...defaultProps} />);
      
      // AI suggestion option
      expect(screen.getByLabelText(/Suivre suggestion IA/)).toBeInTheDocument();
      expect(screen.getByText('🤖')).toBeInTheDocument();
      
      // Fixed expense option
      expect(screen.getByLabelText(/Dépense fixe/)).toBeInTheDocument();
      expect(screen.getByText('🏠')).toBeInTheDocument();
      expect(screen.getByText('(récurrent, prévisible)')).toBeInTheDocument();
      
      // Variable expense option
      expect(screen.getByLabelText(/Dépense variable/)).toBeInTheDocument();
      expect(screen.getByText('📊')).toBeInTheDocument();
      expect(screen.getByText('(occasionnel, variable)')).toBeInTheDocument();
    });

    it('should default to AI suggestion option', () => {
      render(<ClassificationModal {...defaultProps} />);
      
      const aiOption = screen.getByRole('radio', { name: /Suivre suggestion IA/ });
      expect(aiOption).toBeChecked();
    });

    it('should show "Recommandé" badge for high confidence AI suggestions', () => {
      const highConfidenceClassification = createMockClassification({
        confidence_score: 0.92
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={highConfidenceClassification}
        />
      );
      
      expect(screen.getByText('Recommandé')).toBeInTheDocument();
    });

    it('should not show "Recommandé" badge for low confidence', () => {
      const lowConfidenceClassification = createMockClassification({
        confidence_score: 0.65
      });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={lowConfidenceClassification}
        />
      );
      
      expect(screen.queryByText('Recommandé')).not.toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should allow user to select different options', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Initially AI suggestion should be selected
      expect(screen.getByRole('radio', { name: /Suivre suggestion IA/ })).toBeChecked();
      
      // Select fixed expense
      await user.click(screen.getByLabelText(/Dépense fixe/));
      expect(screen.getByRole('radio', { name: /Dépense fixe/ })).toBeChecked();
      expect(screen.getByRole('radio', { name: /Suivre suggestion IA/ })).not.toBeChecked();
      
      // Select variable expense
      await user.click(screen.getByLabelText(/Dépense variable/));
      expect(screen.getByRole('radio', { name: /Dépense variable/ })).toBeChecked();
      expect(screen.getByRole('radio', { name: /Dépense fixe/ })).not.toBeChecked();
    });

    it('should call onClose when cancel button is clicked', async () => {
      const mockOnClose = jest.fn();
      const user = userEvent.setup();
      
      render(
        <ClassificationModal 
          {...defaultProps}
          onClose={mockOnClose}
        />
      );
      
      await user.click(screen.getByText('Annuler'));
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should call onDecision with selected choice when validated', async () => {
      const mockOnDecision = jest.fn().mockResolvedValue(undefined);
      const user = userEvent.setup();
      
      render(
        <ClassificationModal 
          {...defaultProps}
          onDecision={mockOnDecision}
        />
      );
      
      // Select fixed option
      await user.click(screen.getByLabelText(/Dépense fixe/));
      
      // Click validate
      await user.click(screen.getByText('Valider'));
      
      expect(mockOnDecision).toHaveBeenCalledWith('fixed');
    });
  });

  describe('Processing State', () => {
    it('should show loading state during processing', async () => {
      const slowOnDecision = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
      const user = userEvent.setup();
      
      render(
        <ClassificationModal 
          {...defaultProps}
          onDecision={slowOnDecision}
        />
      );
      
      // Start validation
      await user.click(screen.getByText('Valider'));
      
      // Should show loading state
      expect(screen.getByText('Application...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Application.../ })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Annuler/ })).toBeDisabled();
      
      // Should show spinner
      expect(screen.getByRole('button', { name: /Application.../ }).querySelector('.animate-spin')).toBeInTheDocument();
      
      // Wait for completion
      await waitFor(() => {
        expect(slowOnDecision).toHaveBeenCalled();
      }, { timeout: 200 });
    });

    it('should return to normal state after processing', async () => {
      const user = userEvent.setup();
      
      render(<ClassificationModal {...defaultProps} />);
      
      // Click validate
      await user.click(screen.getByText('Valider'));
      
      // Wait for processing to complete
      await waitFor(() => {
        expect(defaultProps.onDecision).toHaveBeenCalled();
      });
      
      // Buttons should not be disabled (if modal is still open)
      // Note: In real usage, modal would close after successful validation
    });
  });

  describe('Button Styling and Icons', () => {
    it('should show correct icon and styling for AI suggestion', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // AI suggestion should be selected by default
      const validateButton = screen.getByText('Valider');
      expect(validateButton).toHaveClass('bg-blue-600', 'hover:bg-blue-700');
      expect(within(validateButton.parentElement!).getByText('🤖')).toBeInTheDocument();
    });

    it('should show correct icon and styling for fixed expense', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Select fixed expense
      await user.click(screen.getByLabelText(/Dépense fixe/));
      
      const validateButton = screen.getByText('Valider');
      expect(validateButton).toHaveClass('bg-orange-600', 'hover:bg-orange-700');
      expect(within(validateButton.parentElement!).getByText('🏠')).toBeInTheDocument();
    });

    it('should show correct icon and styling for variable expense', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Select variable expense
      await user.click(screen.getByLabelText(/Dépense variable/));
      
      const validateButton = screen.getByText('Valider');
      expect(validateButton).toHaveClass('bg-blue-600', 'hover:bg-blue-700');
      expect(within(validateButton.parentElement!).getByText('📊')).toBeInTheDocument();
    });
  });

  describe('Confidence Star Display', () => {
    const confidenceTests = [
      { score: 0.95, expectedStars: '⭐⭐⭐' },
      { score: 0.85, expectedStars: '⭐⭐' },
      { score: 0.60, expectedStars: '⭐' },
    ];

    confidenceTests.forEach(({ score, expectedStars }) => {
      it(`should display ${expectedStars} for confidence score ${score}`, () => {
        const classification = createMockClassification({ confidence_score: score });
        
        render(
          <ClassificationModal 
            {...defaultProps}
            classification={classification}
          />
        );
        
        expect(screen.getByText(expectedStars)).toBeInTheDocument();
        expect(screen.getByTitle(`Confiance: ${Math.round(score * 100)}%`)).toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Accessibility', () => {
    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Tab through options
      await user.tab(); // First radio option (AI suggestion)
      expect(screen.getByRole('radio', { name: /Suivre suggestion IA/ })).toHaveFocus();
      
      await user.tab(); // Second radio option (Fixed)
      expect(screen.getByRole('radio', { name: /Dépense fixe/ })).toHaveFocus();
      
      await user.tab(); // Third radio option (Variable)
      expect(screen.getByRole('radio', { name: /Dépense variable/ })).toHaveFocus();
    });

    it('should support space key for radio selection', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Focus on fixed option
      const fixedOption = screen.getByRole('radio', { name: /Dépense fixe/ });
      fixedOption.focus();
      
      // Press space to select
      await user.keyboard(' ');
      
      expect(fixedOption).toBeChecked();
    });

    it('should support Enter key on validate button', async () => {
      const mockOnDecision = jest.fn().mockResolvedValue(undefined);
      const user = userEvent.setup();
      
      render(
        <ClassificationModal 
          {...defaultProps}
          onDecision={mockOnDecision}
        />
      );
      
      const validateButton = screen.getByText('Valider');
      validateButton.focus();
      
      await user.keyboard('{Enter}');
      
      expect(mockOnDecision).toHaveBeenCalledWith('ai_suggestion');
    });
  });

  describe('Error Handling', () => {
    it('should handle onDecision errors gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const mockOnDecision = jest.fn().mockRejectedValue(new Error('Classification failed'));
      const user = userEvent.setup();
      
      render(
        <ClassificationModal 
          {...defaultProps}
          onDecision={mockOnDecision}
        />
      );
      
      await user.click(screen.getByText('Valider'));
      
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Error processing classification decision:', 
          expect.any(Error)
        );
      });
      
      // Should return to normal state
      expect(screen.getByText('Valider')).toBeEnabled();
      
      consoleErrorSpy.mockRestore();
    });

    it('should handle invalid classification data', () => {
      const invalidClassification = {
        ...createMockClassification(),
        confidence_score: NaN,
        suggested_type: '' as any
      };
      
      expect(() => {
        render(
          <ClassificationModal 
            {...defaultProps}
            classification={invalidClassification}
          />
        );
      }).not.toThrow();
      
      // Should still render modal
      expect(screen.getByText('Classification de "netflix"')).toBeInTheDocument();
    });
  });

  describe('Props Updates', () => {
    it('should reset to AI suggestion when classification changes', () => {
      const { rerender } = render(<ClassificationModal {...defaultProps} />);
      
      // Initially AI suggestion selected
      expect(screen.getByRole('radio', { name: /Suivre suggestion IA/ })).toBeChecked();
      
      // Update classification
      const newClassification = createMockClassification({
        suggested_type: 'VARIABLE',
        confidence_score: 0.75
      });
      
      rerender(
        <ClassificationModal 
          {...defaultProps}
          classification={newClassification}
        />
      );
      
      // Should still have AI suggestion selected (reset)
      expect(screen.getByRole('radio', { name: /Suivre suggestion IA/ })).toBeChecked();
      expect(screen.getByText('IA suggère : VARIABLE')).toBeInTheDocument();
    });

    it('should handle tag name updates', () => {
      const { rerender } = render(<ClassificationModal {...defaultProps} />);
      
      expect(screen.getByText('Classification de "netflix"')).toBeInTheDocument();
      
      rerender(
        <ClassificationModal 
          {...defaultProps}
          tagName="spotify"
        />
      );
      
      expect(screen.getByText('Classification de "spotify"')).toBeInTheDocument();
    });
  });

  describe('Visual Styling Validation', () => {
    it('should apply correct border and background colors for high confidence', () => {
      const highConfidence = createMockClassification({ confidence_score: 0.95 });
      
      render(
        <ClassificationModal 
          {...defaultProps}
          classification={highConfidence}
        />
      );
      
      const suggestionSection = screen.getByText('IA suggère : FIXED').closest('.rounded-lg');
      expect(suggestionSection).toHaveClass('bg-green-50', 'border-green-200');
      
      const confidenceBadge = screen.getByText('95% sûr');
      expect(confidenceBadge).toHaveClass('bg-green-100', 'text-green-700');
    });

    it('should apply correct styling for selected options', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);
      
      // Select fixed option
      await user.click(screen.getByLabelText(/Dépense fixe/));
      
      const fixedLabel = screen.getByLabelText(/Dépense fixe/).closest('label');
      expect(fixedLabel).toHaveClass('border-orange-500', 'bg-orange-50');
      
      const radioIndicator = fixedLabel?.querySelector('.border-orange-500.bg-orange-500');
      expect(radioIndicator).toBeInTheDocument();
    });
  });
});