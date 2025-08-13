'use client';

import { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import Button from "../ui/Button";

export type ClassificationChoice = 'fixed' | 'variable' | 'ai_suggestion';

interface ExpenseTypeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (choice: ClassificationChoice, type?: 'fixed' | 'variable') => void;
  transactionLabel: string;
  suggestedType: 'fixed' | 'variable';
  confidence: number;
}

export function ExpenseTypeModal({
  isOpen,
  onClose,
  onConfirm,
  transactionLabel,
  suggestedType,
  confidence
}: ExpenseTypeModalProps) {
  const [selectedChoice, setSelectedChoice] = useState<ClassificationChoice>('ai_suggestion');

  useEffect(() => {
    // Par défaut, suivre la suggestion IA
    setSelectedChoice('ai_suggestion');
  }, [suggestedType]);

  const handleConfirm = () => {
    if (selectedChoice === 'ai_suggestion') {
      onConfirm('ai_suggestion', suggestedType);
    } else {
      onConfirm(selectedChoice, selectedChoice);
    }
    onClose();
  };

  const confidenceColor = confidence > 0.8 ? 'text-green-600' : confidence > 0.6 ? 'text-yellow-600' : 'text-gray-600';
  const confidenceText = confidence > 0.8 ? 'Très confiant' : confidence > 0.6 ? 'Confiant' : 'Incertain';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Type de dépense"
      size="md"
    >
      <div className="space-y-6">
        {/* Transaction info */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h4 className="font-medium text-gray-900 mb-2">Transaction analysée :</h4>
          <p className="text-gray-700 text-sm font-mono bg-white p-2 rounded border">
            {transactionLabel}
          </p>
        </div>

        {/* AI Suggestion */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-5 h-5 text-blue-600">🤖</div>
            <h4 className="font-medium text-blue-900">Suggestion intelligente</h4>
          </div>
          <p className="text-blue-800 text-sm">
            Auto-détecté: {transactionLabel.length > 20 ? transactionLabel.substring(0, 20) + '...' : transactionLabel} → 
            <span className="font-semibold"> {suggestedType === 'fixed' ? 'FIXE 🏠' : 'VARIABLE 📊'}</span>
            <span className="text-blue-600"> ({Math.round(confidence * 100)}%)</span>
          </p>
          <p className={`text-xs mt-1 ${confidenceColor}`}>
            Niveau de confiance : {confidenceText} ({Math.round(confidence * 100)}%)
          </p>
        </div>

        {/* Type selection */}
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900">Votre choix :</h4>
          
          <div className="space-y-3">
            {/* AI Suggestion option (recommended) */}
            <button
              onClick={() => setSelectedChoice('ai_suggestion')}
              className={`
                w-full p-4 rounded-lg border-2 transition-all text-left relative
                ${selectedChoice === 'ai_suggestion' 
                  ? 'border-blue-500 bg-blue-50 text-blue-900 shadow-md ring-2 ring-blue-200' 
                  : 'border-gray-200 hover:border-gray-300 text-gray-700 hover:shadow-sm'
                }
              `}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🤖</span>
                <span className="font-semibold">Suivre suggestion IA</span>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                  Recommandé
                </span>
              </div>
              <p className="text-xs opacity-80">
                Appliquer la classification automatique : <span className="font-medium">
                  {suggestedType === 'fixed' ? '🏠 Dépense fixe' : '📊 Dépense variable'}
                </span> ({Math.round(confidence * 100)}% de confiance)
              </p>
              {selectedChoice === 'ai_suggestion' && (
                <div className="absolute top-2 right-2 w-5 h-5 text-blue-600">
                  <svg fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            {/* Manual options */}
            <div className="grid grid-cols-2 gap-3">
              {/* Fixed option */}
              <button
                onClick={() => setSelectedChoice('fixed')}
                className={`
                  p-4 rounded-lg border-2 transition-all text-left relative
                  ${selectedChoice === 'fixed' 
                    ? 'border-orange-500 bg-orange-50 text-orange-900 shadow-md' 
                    : 'border-gray-200 hover:border-gray-300 text-gray-700 hover:shadow-sm'
                  }
                `}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">🏠</span>
                  <span className="font-semibold">Dépense fixe</span>
                </div>
                <p className="text-xs opacity-80">
                  Montant régulier et prévisible (loyer, abonnements, prêt...)
                </p>
                {selectedChoice === 'fixed' && (
                  <div className="absolute top-2 right-2 w-5 h-5 text-orange-600">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </button>

              {/* Variable option */}
              <button
                onClick={() => setSelectedChoice('variable')}
                className={`
                  p-4 rounded-lg border-2 transition-all text-left relative
                  ${selectedChoice === 'variable' 
                    ? 'border-blue-500 bg-blue-50 text-blue-900 shadow-md' 
                    : 'border-gray-200 hover:border-gray-300 text-gray-700 hover:shadow-sm'
                  }
                `}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">📊</span>
                  <span className="font-semibold">Dépense variable</span>
                </div>
                <p className="text-xs opacity-80">
                  Montant qui varie selon les besoins (courses, resto, shopping...)
                </p>
                {selectedChoice === 'variable' && (
                  <div className="absolute top-2 right-2 w-5 h-5 text-blue-600">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button
            variant="outline"
            onClick={onClose}
            className="px-4 py-2"
          >
            Annuler
          </Button>
          <Button
            onClick={handleConfirm}
            className={`px-6 py-2 ${
              selectedChoice === 'ai_suggestion' 
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : selectedChoice === 'fixed' 
                  ? 'bg-orange-600 hover:bg-orange-700 text-white' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {selectedChoice === 'ai_suggestion' ? (
              <>🤖 Suivre IA ({suggestedType === 'fixed' ? '🏠 Fixe' : '📊 Variable'})</>
            ) : selectedChoice === 'fixed' ? (
              <>🏠 Confirmer comme Fixe</>
            ) : (
              <>📊 Confirmer comme Variable</>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}