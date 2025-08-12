'use client';

import { useState } from 'react';
import { Tx } from '../../lib/api';

interface InfoButtonProps {
  /** Transaction associée */
  transaction: Tx;
  /** Indique si une classification IA est en cours */
  isClassifying?: boolean;
  /** Callback pour déclencher une classification manuelle */
  onTriggerClassification: () => void;
  /** Indique si la transaction a une suggestion IA en attente */
  hasPendingClassification?: boolean;
  /** Score de confiance si classification existante */
  confidenceScore?: number;
  /** Indique si la transaction a été classifiée automatiquement */
  isAutoDetected?: boolean;
}

/**
 * Bouton d'information IA pour chaque transaction
 * Affiche l'état de la classification et permet de déclencher l'IA
 */
export function InfoButton({
  transaction,
  isClassifying = false,
  onTriggerClassification,
  hasPendingClassification = false,
  confidenceScore,
  isAutoDetected = false
}: InfoButtonProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  
  const isExpense = transaction.amount < 0;
  const hasClassification = transaction.expense_type && isExpense;
  const hasAIIndicators = isAutoDetected || hasPendingClassification;
  
  // Ne rien afficher pour les revenus (non-dépenses)
  if (!isExpense) {
    return null;
  }

  // Déterminer l'état du bouton et ses couleurs
  let buttonState: 'unclassified' | 'pending' | 'classified' | 'processing' = 'unclassified';
  let buttonColor = 'text-gray-400 hover:text-gray-600';
  let bgColor = 'hover:bg-gray-100';
  let icon = '🛈';
  
  if (isClassifying) {
    buttonState = 'processing';
    buttonColor = 'text-blue-600';
    bgColor = 'bg-blue-50';
    icon = '⏳';
  } else if (hasPendingClassification) {
    buttonState = 'pending';
    buttonColor = 'text-orange-600 hover:text-orange-700';
    bgColor = 'hover:bg-orange-50';
    icon = '⚠️';
  } else if (hasClassification) {
    buttonState = 'classified';
    if (isAutoDetected) {
      buttonColor = 'text-green-600 hover:text-green-700';
      bgColor = 'hover:bg-green-50';
      icon = '🤖';
    } else {
      buttonColor = 'text-blue-600 hover:text-blue-700';
      bgColor = 'hover:bg-blue-50';
      icon = '✓';
    }
  }

  // Texte du tooltip selon l'état
  const getTooltipText = () => {
    switch (buttonState) {
      case 'processing':
        return 'Classification IA en cours...';
      case 'pending':
        return 'Suggestion IA en attente de validation';
      case 'classified':
        if (isAutoDetected && confidenceScore) {
          return `Classification IA: ${transaction.expense_type} (${Math.round(confidenceScore * 100)}% confiance)`;
        }
        return hasClassification 
          ? `Classification: ${transaction.expense_type}${isAutoDetected ? ' (Auto-détecté)' : ''}`
          : 'Cliquer pour analyser avec l\'IA';
      default:
        return 'Cliquer pour analyser cette dépense avec l\'IA';
    }
  };

  const handleClick = () => {
    if (isClassifying) return; // Ne pas permettre de clic pendant le processing
    onTriggerClassification();
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={handleClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        disabled={isClassifying}
        className={`
          relative inline-flex items-center justify-center w-6 h-6 
          rounded-full transition-all duration-200 text-sm
          ${buttonColor} ${bgColor}
          ${isClassifying ? 'cursor-not-allowed' : 'cursor-pointer'}
          focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
          ${hasAIIndicators ? 'ring-1 ring-current ring-opacity-30' : ''}
        `}
        title={getTooltipText()}
      >
        {isClassifying ? (
          <div className="w-3 h-3 animate-spin rounded-full border border-current border-t-transparent"></div>
        ) : (
          <span className="text-xs">{icon}</span>
        )}
        
        {/* Indicateur visuel pour les états importants */}
        {hasPendingClassification && !isClassifying && (
          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
        )}
        
        {hasClassification && isAutoDetected && !hasPendingClassification && (
          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full"></div>
        )}
      </button>

      {/* Tooltip détaillé */}
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-20">
          <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
            <div className="font-medium">{getTooltipText()}</div>
            
            {/* Informations additionnelles selon l'état */}
            {buttonState === 'classified' && isAutoDetected && confidenceScore && (
              <div className="text-gray-300 text-xs mt-1">
                Score: {Math.round(confidenceScore * 100)}% • {
                  confidenceScore >= 0.8 ? 'Haute confiance' :
                  confidenceScore >= 0.6 ? 'Confiance moyenne' : 'Faible confiance'
                }
              </div>
            )}
            
            {buttonState === 'pending' && (
              <div className="text-orange-200 text-xs mt-1">
                Cliquer pour valider ou modifier
              </div>
            )}
            
            {buttonState === 'unclassified' && (
              <div className="text-gray-300 text-xs mt-1">
                IA va analyser les patterns et suggérer FIXE/VARIABLE
              </div>
            )}
            
            {/* Flèche du tooltip */}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2">
              <div className="border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InfoButton;