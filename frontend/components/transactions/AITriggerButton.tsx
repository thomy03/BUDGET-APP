'use client';

import { useState } from 'react';
import { Tx } from '../../lib/api';

interface AITriggerButtonProps {
  transaction: Tx;
  onTriggerAnalysis: (transactionId: number) => Promise<void>;
  isAnalyzing: boolean;
  hasExistingSuggestion?: boolean;
  confidenceScore?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'ghost';
  disabled?: boolean;
}

export function AITriggerButton({
  transaction,
  onTriggerAnalysis,
  isAnalyzing,
  hasExistingSuggestion = false,
  confidenceScore,
  size = 'sm',
  variant = 'ghost',
  disabled = false
}: AITriggerButtonProps) {
  const [isHovering, setIsHovering] = useState(false);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled || isAnalyzing) return;
    
    try {
      await onTriggerAnalysis(transaction.id);
    } catch (error) {
      console.error('Error triggering AI analysis:', error);
    }
  };

  // Déterminer l'état du bouton
  const getButtonState = () => {
    if (isAnalyzing) return 'analyzing';
    if (hasExistingSuggestion) return 'suggestion';
    if (confidenceScore && confidenceScore >= 0.8) return 'confident';
    if (confidenceScore && confidenceScore >= 0.6) return 'medium';
    return 'default';
  };

  const buttonState = getButtonState();

  // Classes CSS selon la taille
  const getSizeClasses = () => {
    switch (size) {
      case 'lg':
        return 'px-4 py-2 text-base';
      case 'md':
        return 'px-3 py-1.5 text-sm';
      case 'sm':
      default:
        return 'px-2 py-1 text-xs';
    }
  };

  // Classes CSS selon la variante et l'état
  const getVariantClasses = () => {
    const base = getSizeClasses();
    
    switch (variant) {
      case 'primary':
        if (buttonState === 'analyzing') {
          return `${base} bg-blue-500 text-white border border-blue-500 animate-pulse`;
        }
        if (buttonState === 'suggestion') {
          return `${base} bg-green-500 text-white border border-green-500 hover:bg-green-600`;
        }
        return `${base} bg-blue-500 text-white border border-blue-500 hover:bg-blue-600`;
      
      case 'secondary':
        if (buttonState === 'analyzing') {
          return `${base} bg-blue-50 text-blue-700 border border-blue-300 animate-pulse`;
        }
        if (buttonState === 'suggestion') {
          return `${base} bg-green-50 text-green-700 border border-green-300 hover:bg-green-100`;
        }
        return `${base} bg-gray-50 text-gray-700 border border-gray-300 hover:bg-gray-100`;
      
      case 'ghost':
      default:
        if (buttonState === 'analyzing') {
          return `${base} bg-blue-50/50 text-blue-600 border border-blue-200 animate-pulse`;
        }
        if (buttonState === 'suggestion') {
          return `${base} bg-green-50/50 text-green-600 border border-green-200 hover:bg-green-100`;
        }
        if (buttonState === 'confident') {
          return `${base} bg-emerald-50/50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100`;
        }
        if (buttonState === 'medium') {
          return `${base} bg-yellow-50/50 text-yellow-600 border border-yellow-200 hover:bg-yellow-100`;
        }
        return `${base} bg-gray-50/50 text-gray-600 border border-gray-200 hover:bg-gray-100 hover:text-gray-700`;
    }
  };

  // Icônes et texte selon l'état
  const getButtonContent = () => {
    switch (buttonState) {
      case 'analyzing':
        return (
          <>
            <div className="w-3 h-3 animate-spin rounded-full border-2 border-current border-t-transparent mr-1" />
            Analyse...
          </>
        );
      
      case 'suggestion':
        return (
          <>
            <span className="text-green-500 mr-1">🤖</span>
            Suggestion IA
          </>
        );
      
      case 'confident':
        return (
          <>
            <span className="text-emerald-500 mr-1">✨</span>
            IA ({Math.round((confidenceScore || 0) * 100)}%)
          </>
        );
      
      case 'medium':
        return (
          <>
            <span className="text-yellow-500 mr-1">🤔</span>
            IA ({Math.round((confidenceScore || 0) * 100)}%)
          </>
        );
      
      default:
        return (
          <>
            <span className="text-gray-400 mr-1">🤖</span>
            Analyser
          </>
        );
    }
  };

  // Tooltip selon l'état
  const getTooltip = () => {
    switch (buttonState) {
      case 'analyzing':
        return 'Analyse IA en cours...';
      case 'suggestion':
        return 'Suggestion IA disponible - cliquer pour voir';
      case 'confident':
        return `Classification IA très fiable (${Math.round((confidenceScore || 0) * 100)}%)`;
      case 'medium':
        return `Classification IA moyenne (${Math.round((confidenceScore || 0) * 100)}%) - vérifier`;
      default:
        return 'Cliquer pour analyser avec l\'IA';
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
        disabled={disabled || isAnalyzing}
        className={`
          ${getVariantClasses()}
          rounded-md font-medium transition-all duration-200 ease-in-out
          flex items-center justify-center min-w-0
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
          disabled:opacity-50 disabled:cursor-not-allowed
          transform hover:scale-105 active:scale-95
          shadow-sm hover:shadow-md
        `}
        title={getTooltip()}
      >
        {getButtonContent()}
      </button>

      {/* Tooltip au survol */}
      {isHovering && !isAnalyzing && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
          <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
            {getTooltip()}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2">
              <div className="border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>
      )}

      {/* Indicateur de score de confiance */}
      {confidenceScore && confidenceScore > 0 && !isAnalyzing && (
        <div className="absolute -top-1 -right-1">
          <div
            className={`w-2 h-2 rounded-full ${
              confidenceScore >= 0.8
                ? 'bg-green-400'
                : confidenceScore >= 0.6
                ? 'bg-yellow-400'
                : 'bg-red-400'
            }`}
            title={`Confiance: ${Math.round(confidenceScore * 100)}%`}
          />
        </div>
      )}
    </div>
  );
}

// Composant spécialisé pour utilisation dans le tableau
export function CompactAITriggerButton({
  transaction,
  onTriggerAnalysis,
  isAnalyzing,
  hasExistingSuggestion,
  confidenceScore
}: Omit<AITriggerButtonProps, 'size' | 'variant'>) {
  return (
    <AITriggerButton
      transaction={transaction}
      onTriggerAnalysis={onTriggerAnalysis}
      isAnalyzing={isAnalyzing}
      hasExistingSuggestion={hasExistingSuggestion}
      confidenceScore={confidenceScore}
      size="sm"
      variant="ghost"
    />
  );
}

// Composant pour bouton principal d'action
export function PrimaryAITriggerButton({
  transaction,
  onTriggerAnalysis,
  isAnalyzing,
  hasExistingSuggestion,
  confidenceScore
}: Omit<AITriggerButtonProps, 'size' | 'variant'>) {
  return (
    <AITriggerButton
      transaction={transaction}
      onTriggerAnalysis={onTriggerAnalysis}
      isAnalyzing={isAnalyzing}
      hasExistingSuggestion={hasExistingSuggestion}
      confidenceScore={confidenceScore}
      size="md"
      variant="primary"
    />
  );
}