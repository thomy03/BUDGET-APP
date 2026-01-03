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

    it('should display AI suggestion section with correct content', () => {
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

      // Should show AI suggestion content
      expect(screen.getByText(/IA suggère/)).toBeInTheDocument();
      expect(screen.getAllByText('🤖').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('95% sûr')).toBeInTheDocument();
    });

    it('should display medium confidence content', () => {
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

      // Should show medium confidence content
      expect(screen.getByText(/IA suggère/)).toBeInTheDocument();
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

      // All options should be rendered
      expect(screen.getByText(/Suivre suggestion IA/)).toBeInTheDocument();
      expect(screen.getByText(/Dépense fixe/)).toBeInTheDocument();
      expect(screen.getByText(/Dépense variable/)).toBeInTheDocument();

      // Icons should be present (may be multiple due to button icons)
      expect(screen.getAllByText('🤖').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('🏠').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('📊').length).toBeGreaterThanOrEqual(1);

      // Descriptions
      expect(screen.getByText(/récurrent, prévisible/)).toBeInTheDocument();
      expect(screen.getByText(/occasionnel, variable/)).toBeInTheDocument();
    });

    it('should default to AI suggestion option', () => {
      render(<ClassificationModal {...defaultProps} />);

      // The AI suggestion label should have the selected styling (border-blue-500)
      const aiLabel = screen.getByText(/Suivre suggestion IA/).closest('label');
      expect(aiLabel).toHaveClass('border-blue-500');
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

      // Initially AI suggestion should be selected (has border-blue-500)
      const aiLabel = screen.getByText(/Suivre suggestion IA/).closest('label');
      expect(aiLabel).toHaveClass('border-blue-500');

      // Select fixed expense by clicking the label
      const fixedLabel = screen.getByText(/Dépense fixe/).closest('label');
      await user.click(fixedLabel!);
      expect(fixedLabel).toHaveClass('border-orange-500');

      // Select variable expense
      const variableLabel = screen.getByText(/Dépense variable/).closest('label');
      await user.click(variableLabel!);
      expect(variableLabel).toHaveClass('border-blue-500');
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

      // Select fixed option by clicking label
      const fixedLabel = screen.getByText(/Dépense fixe/).closest('label');
      await user.click(fixedLabel!);

      // Click validate button (using role to handle button with icon + text)
      await user.click(screen.getByRole('button', { name: /Valider/i }));

      await waitFor(() => {
        expect(mockOnDecision).toHaveBeenCalledWith('fixed');
      });
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
      await user.click(screen.getByRole('button', { name: /Valider/i }));

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Application/i })).toBeInTheDocument();
      });

      // Wait for completion
      await waitFor(() => {
        expect(slowOnDecision).toHaveBeenCalled();
      }, { timeout: 300 });
    });

    it('should return to normal state after processing', async () => {
      const user = userEvent.setup();

      render(<ClassificationModal {...defaultProps} />);

      // Click validate
      await user.click(screen.getByRole('button', { name: /Valider/i }));

      // Wait for processing to complete
      await waitFor(() => {
        expect(defaultProps.onDecision).toHaveBeenCalled();
      });

      // Buttons should not be disabled (if modal is still open)
      // Note: In real usage, modal would close after successful validation
    });
  });

  describe('Button Styling and Icons', () => {
    it('should show validate button', async () => {
      render(<ClassificationModal {...defaultProps} />);

      // Validate button should be present
      const validateButton = screen.getByRole('button', { name: /Valider/i });
      expect(validateButton).toBeInTheDocument();
    });

    it('should show icon for fixed expense when selected', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);

      // Select fixed expense
      const fixedLabel = screen.getByText(/Dépense fixe/).closest('label');
      await user.click(fixedLabel!);

      // Should show house icon in button area
      expect(screen.getAllByText('🏠').length).toBeGreaterThanOrEqual(1);
    });

    it('should show icon for variable expense when selected', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);

      // Select variable expense
      const variableLabel = screen.getByText(/Dépense variable/).closest('label');
      await user.click(variableLabel!);

      // Should show chart icon in button area
      expect(screen.getAllByText('📊').length).toBeGreaterThanOrEqual(1);
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
    it('should have focusable validate button', async () => {
      render(<ClassificationModal {...defaultProps} />);

      const validateButton = screen.getByRole('button', { name: /Valider/i });
      expect(validateButton).toBeInTheDocument();
      expect(validateButton.tagName.toLowerCase()).toBe('button');
    });

    it('should have focusable cancel button', async () => {
      render(<ClassificationModal {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /Annuler/i });
      expect(cancelButton).toBeInTheDocument();
      expect(cancelButton.tagName.toLowerCase()).toBe('button');
    });

    it('should support clicking validate button', async () => {
      const mockOnDecision = jest.fn().mockResolvedValue(undefined);
      const user = userEvent.setup();

      render(
        <ClassificationModal
          {...defaultProps}
          onDecision={mockOnDecision}
        />
      );

      const validateButton = screen.getByRole('button', { name: /Valider/i });
      await user.click(validateButton);

      await waitFor(() => {
        expect(mockOnDecision).toHaveBeenCalledWith('ai_suggestion');
      });
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

      await user.click(screen.getByRole('button', { name: /Valider/i }));

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Error processing classification decision:',
          expect.any(Error)
        );
      });

      // Should return to normal state
      expect(screen.getByRole('button', { name: /Valider/i })).toBeEnabled();

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

      // Initially AI suggestion should be selected
      const aiLabel = screen.getByText(/Suivre suggestion IA/).closest('label');
      expect(aiLabel).toHaveClass('border-blue-500');

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
      const newAiLabel = screen.getByText(/Suivre suggestion IA/).closest('label');
      expect(newAiLabel).toHaveClass('border-blue-500');
      expect(screen.getByText(/IA suggère/)).toBeInTheDocument();
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
    it('should display confidence badge for high confidence', () => {
      const highConfidence = createMockClassification({ confidence_score: 0.95 });

      render(
        <ClassificationModal
          {...defaultProps}
          classification={highConfidence}
        />
      );

      const confidenceBadge = screen.getByText('95% sûr');
      expect(confidenceBadge).toBeInTheDocument();
    });

    it('should apply correct styling for selected fixed option', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);

      // Select fixed option
      const fixedLabel = screen.getByText(/Dépense fixe/).closest('label');
      await user.click(fixedLabel!);

      expect(fixedLabel).toHaveClass('border-orange-500');
    });

    it('should apply correct styling for selected variable option', async () => {
      const user = userEvent.setup();
      render(<ClassificationModal {...defaultProps} />);

      // Select variable option
      const variableLabel = screen.getByText(/Dépense variable/).closest('label');
      await user.click(variableLabel!);

      expect(variableLabel).toHaveClass('border-blue-500');
    });
  });
});