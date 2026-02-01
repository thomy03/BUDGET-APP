'use client';

import { useState, useEffect } from 'react';
import { Tx } from '../../lib/api';
import { CompactAITriggerButton } from './AITriggerButton';

interface AISuggestion {
  suggested_type: string;
  confidence_score: number;
  explanation: string;
  auto_apply_recommended: boolean;
  needs_user_input: boolean;
}

interface AISuggestionColumnProps {
  transaction: Tx;
  onTriggerAnalysis: (transactionId: number) => Promise<void>;
  onApplySuggestion?: (transactionId: number, suggestion: AISuggestion) => void;
  isAnalyzing?: boolean;
  existingSuggestion?: AISuggestion | null;
  autoShowSuggestions?: boolean;
}

export function AISuggestionColumn({
  transaction,
  onTriggerAnalysis,
  onApplySuggestion,
  isAnalyzing = false,
  existingSuggestion,
  autoShowSuggestions = false
}: AISuggestionColumnProps) {
  const [suggestion, setSuggestion] = useState<AISuggestion | null>(existingSuggestion || null);
  const [isHovering, setIsHovering] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  // Auto-load suggestions if enabled
  useEffect(() => {
    if (autoShowSuggestions && !suggestion && !isAnalyzing && transaction.amount < 0) {
      // Delay to avoid overwhelming the system
      const timer = setTimeout(() => {
        handleTriggerAnalysis();
      }, Math.random() * 2000 + 500); // Random delay between 500ms and 2.5s

      return () => clearTimeout(timer);
    }
  }, [autoShowSuggestions, suggestion, isAnalyzing, transaction]);

  const handleTriggerAnalysis = async () => {
    try {
      await onTriggerAnalysis(transaction.id);
      // Note: The suggestion would be set through props in a real implementation
    } catch (error) {
      console.error('Error triggering analysis:', error);
    }
  };

  const handleApplySuggestion = () => {
    if (suggestion && onApplySuggestion) {
      onApplySuggestion(transaction.id, suggestion);
    }
  };

  // Render different states
  const renderContent = () => {
    // Pour les revenus (montants positifs), ne pas afficher de suggestions
    if (transaction.amount >= 0) {
      return (
        <div className="text-xs text-gray-400 text-center py-2">
          Revenus
        </div>
      );
    }

    // État de chargement
    if (isAnalyzing) {
      return (
        <div className="flex items-center justify-center py-2">
          <div className="flex items-center gap-2 text-xs text-blue-600">
            <div className="w-3 h-3 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            Analyse...
          </div>
        </div>
      );
    }

    // Suggestion existante
    if (suggestion) {
      const confidenceText = suggestion.confidence_score >= 0.8 
        ? 'Haute' 
        : suggestion.confidence_score >= 0.6 
        ? 'Moyenne' 
        : 'Faible';
      
      const typeText = suggestion.suggested_type === 'FIXED' ? 'FIXE' : 'VARIABLE';
      const confidencePercentage = Math.round(suggestion.confidence_score * 100);
      
      return (
        <div 
          className="relative cursor-pointer group"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          {/* Badge de suggestion principal */}
          <div 
            className={`
              inline-flex flex-col items-center px-2 py-1 rounded-md text-xs font-medium border
              transition-all duration-200 hover:shadow-md
              ${suggestion.confidence_score >= 0.8
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                : suggestion.confidence_score >= 0.6
                ? 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
                : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100'
              }
            `}
            onClick={handleApplySuggestion}
          >
            <span className="font-semibold">{typeText}</span>
            <span className="text-[10px] opacity-75">{confidencePercentage}%</span>
          </div>

          {/* Indicateur de confiance visuel */}
          <div className="mt-1 w-full bg-gray-200 rounded-full h-1">
            <div
              className={`
                h-1 rounded-full transition-all duration-300
                ${suggestion.confidence_score >= 0.8
                  ? 'bg-emerald-400'
                  : suggestion.confidence_score >= 0.6
                  ? 'bg-amber-400'
                  : 'bg-red-400'
                }
              `}
              style={{ width: `${confidencePercentage}%` }}
            />
          </div>

          {/* Tooltip détaillé */}
          {showTooltip && (
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
              <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 max-w-xs">
                <div className="font-medium mb-1">
                  Suggestion IA: {typeText}
                </div>
                <div className="text-gray-300 mb-2">
                  Confiance: {confidenceText} ({confidencePercentage}%)
                </div>
                <div className="text-gray-400">
                  {suggestion.explanation}
                </div>
                {suggestion.auto_apply_recommended && (
                  <div className="text-green-400 mt-1 text-[10px]">
                    ✓ Application automatique recommandée
                  </div>
                )}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2">
                  <div className="border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    // Classification existante (déjà classifiée)
    if (transaction.expense_type && transaction.expense_type !== '') {
      const hasConfidence = transaction.expense_type_confidence && transaction.expense_type_confidence > 0;
      const isAutoDetected = transaction.expense_type_auto_detected;
      
      return (
        <div className="flex flex-col items-center gap-1">
          <div 
            className={`
              inline-flex items-center px-2 py-1 rounded-md text-xs font-medium
              ${transaction.expense_type === 'fixed' 
                ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' 
                : 'bg-orange-100 text-orange-700 border border-orange-200'
              }
            `}
          >
            {transaction.expense_type === 'fixed' ? 'FIXE' : 'VARIABLE'}
            {isAutoDetected && <span className="ml-1 text-[10px]">🤖</span>}
          </div>
          
          {hasConfidence && (
            <div className="text-[10px] text-gray-500">
              {Math.round((transaction.expense_type_confidence || 0) * 100)}%
            </div>
          )}
          
          {/* Bouton pour re-analyser */}
          <CompactAITriggerButton
            transaction={transaction}
            onTriggerAnalysis={handleTriggerAnalysis}
            isAnalyzing={isAnalyzing}
            hasExistingSuggestion={false}
            confidenceScore={transaction.expense_type_confidence}
          />
        </div>
      );
    }

    // Transaction non classifiée - bouton pour déclencher l'analyse
    return (
      <div className="flex flex-col items-center gap-1">
        <div className="text-xs text-gray-400 mb-1">
          À classifier
        </div>
        <CompactAITriggerButton
          transaction={transaction}
          onTriggerAnalysis={handleTriggerAnalysis}
          isAnalyzing={isAnalyzing}
          hasExistingSuggestion={false}
        />
      </div>
    );
  };

  return (
    <div 
      className="p-2 text-center min-h-[60px] flex items-center justify-center"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {renderContent()}
      
      {/* Hover effect pour ligne entière */}
      {isHovering && !isAnalyzing && !suggestion && transaction.amount < 0 && (
        <div className="absolute inset-0 bg-blue-50/20 pointer-events-none rounded-md border border-blue-200/30" />
      )}
    </div>
  );
}

// Hook pour gérer les suggestions en lot
export function useBulkAISuggestions() {
  const [suggestions, setSuggestions] = useState<Record<number, AISuggestion>>({});
  const [loading, setLoading] = useState<Record<number, boolean>>({});

  const loadSuggestionsForTransactions = async (transactionIds: number[]) => {
    // Mark all as loading
    setLoading(prev => {
      const newLoading = { ...prev };
      transactionIds.forEach(id => {
        newLoading[id] = true;
      });
      return newLoading;
    });

    try {
      // Call bulk suggestions API
      const response = await fetch('/api/expense-classification/bulk-suggestions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_ids: transactionIds,
          confidence_threshold: 0.1,
          include_explanations: true,
          use_cache: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to load bulk suggestions');
      }

      const data = await response.json();
      
      // Update suggestions
      setSuggestions(prev => ({ ...prev, ...data.suggestions }));
      
    } catch (error) {
      console.error('Error loading bulk suggestions:', error);
    } finally {
      // Clear loading states
      setLoading(prev => {
        const newLoading = { ...prev };
        transactionIds.forEach(id => {
          delete newLoading[id];
        });
        return newLoading;
      });
    }
  };

  const getSuggestion = (transactionId: number): AISuggestion | null => {
    return suggestions[transactionId] || null;
  };

  const isLoading = (transactionId: number): boolean => {
    return loading[transactionId] || false;
  };

  return {
    loadSuggestionsForTransactions,
    getSuggestion,
    isLoading,
    suggestions
  };
}