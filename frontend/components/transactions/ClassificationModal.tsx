'use client';

import { useState, useEffect } from "react";
import { Modal } from "../ui/Modal";
import Button from "../ui/Button";
import { ExpenseClassificationResult } from "../../lib/api";

export type ClassificationDecision = 'fixed' | 'variable' | 'ai_suggestion';

interface ClassificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDecision: (decision: ClassificationDecision) => Promise<void>;
  tagName: string;
  classification: ExpenseClassificationResult;
}

/**
 * Modal de classification selon les spécifications exactes de l'utilisateur
 * 
 * Design:
 * ┌─────────────────────────────────────┐
 * │ Classification de "netflix"         │
 * ├─────────────────────────────────────┤
 * │ 🤖 IA suggère : FIXE (95% sûr)     │
 * │ 💡 Raison : Abonnement récurrent   │
 * ├─────────────────────────────────────┤
 * │ Votre choix :                       │
 * │ ● 🏠 Dépense fixe                  │
 * │ ○ 📊 Dépense variable              │
 * │ ○ 🤖 Suivre suggestion IA          │
 * ├─────────────────────────────────────┤
 * │ [Annuler]  [Valider]              │
 * └─────────────────────────────────────┘
 */
export function ClassificationModal({
  isOpen,
  onClose,
  onDecision,
  tagName,
  classification
}: ClassificationModalProps) {
  const [selectedDecision, setSelectedDecision] = useState<ClassificationDecision>('ai_suggestion');
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // Par défaut, suivre la suggestion IA
    setSelectedDecision('ai_suggestion');
  }, [classification]);

  const handleValidate = async () => {
    try {
      setIsProcessing(true);
      await onDecision(selectedDecision);
    } catch (error) {
      console.error('Error processing classification decision:', error);
      // L'erreur sera gérée par le composant parent
    } finally {
      setIsProcessing(false);
    }
  };

  const confidencePercentage = Math.round(classification.confidence_score * 100);
  const isHighConfidence = classification.confidence_score >= 0.8;
  
  // Icônes de confiance selon le niveau
  const getConfidenceStars = (confidence: number) => {
    if (confidence >= 0.9) return '⭐⭐⭐';
    if (confidence >= 0.7) return '⭐⭐';
    return '⭐';
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Classification de "${tagName}"`}
      size="md"
    >
      <div className="space-y-6">
        {/* Suggestion IA */}
        <div className={`
          rounded-lg border p-4 
          ${isHighConfidence 
            ? 'bg-green-50 border-green-200' 
            : 'bg-yellow-50 border-yellow-200'
          }
        `}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🤖</span>
            <span className="font-semibold text-gray-900">
              IA suggère : {classification.suggested_type.toUpperCase()}
            </span>
            <span className={`
              text-sm font-medium px-2 py-1 rounded-full
              ${isHighConfidence 
                ? 'bg-green-100 text-green-700' 
                : 'bg-yellow-100 text-yellow-700'
              }
            `}>
              {confidencePercentage}% sûr
            </span>
            <span className="text-sm" title={`Confiance: ${confidencePercentage}%`}>
              {getConfidenceStars(classification.confidence_score)}
            </span>
          </div>

          <div className="flex items-start gap-2">
            <span className="text-lg">💡</span>
            <div>
              <span className="font-medium text-gray-700">Raison : </span>
              <span className="text-gray-600">
                {classification.reasoning || 'Classification automatique basée sur les patterns détectés'}
              </span>
              {classification.matched_rules && classification.matched_rules.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-gray-500">
                    Règles correspondantes: {classification.matched_rules.map(r => r.rule_name).join(', ')}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Choix utilisateur */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Votre choix :</h4>
          
          <div className="space-y-3">
            {/* Option suivre IA (recommandée si haute confiance) */}
            <label className={`
              flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all
              ${selectedDecision === 'ai_suggestion'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
              }
            `}>
              <input
                type="radio"
                name="classification"
                value="ai_suggestion"
                checked={selectedDecision === 'ai_suggestion'}
                onChange={(e) => setSelectedDecision(e.target.value as ClassificationDecision)}
                className="sr-only"
              />
              <div className={`
                w-4 h-4 rounded-full border-2 mr-3 flex items-center justify-center
                ${selectedDecision === 'ai_suggestion' 
                  ? 'border-blue-500 bg-blue-500' 
                  : 'border-gray-300'
                }
              `}>
                {selectedDecision === 'ai_suggestion' && (
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🤖</span>
                <span className="font-medium">Suivre suggestion IA</span>
                {isHighConfidence && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                    Recommandé
                  </span>
                )}
              </div>
            </label>

            {/* Option dépense fixe */}
            <label className={`
              flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all
              ${selectedDecision === 'fixed'
                ? 'border-orange-500 bg-orange-50'
                : 'border-gray-200 hover:border-gray-300'
              }
            `}>
              <input
                type="radio"
                name="classification"
                value="fixed"
                checked={selectedDecision === 'fixed'}
                onChange={(e) => setSelectedDecision(e.target.value as ClassificationDecision)}
                className="sr-only"
              />
              <div className={`
                w-4 h-4 rounded-full border-2 mr-3 flex items-center justify-center
                ${selectedDecision === 'fixed' 
                  ? 'border-orange-500 bg-orange-500' 
                  : 'border-gray-300'
                }
              `}>
                {selectedDecision === 'fixed' && (
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🏠</span>
                <span className="font-medium">Dépense fixe</span>
                <span className="text-xs text-gray-500">
                  (récurrent, prévisible)
                </span>
              </div>
            </label>

            {/* Option dépense variable */}
            <label className={`
              flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all
              ${selectedDecision === 'variable'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
              }
            `}>
              <input
                type="radio"
                name="classification"
                value="variable"
                checked={selectedDecision === 'variable'}
                onChange={(e) => setSelectedDecision(e.target.value as ClassificationDecision)}
                className="sr-only"
              />
              <div className={`
                w-4 h-4 rounded-full border-2 mr-3 flex items-center justify-center
                ${selectedDecision === 'variable' 
                  ? 'border-blue-500 bg-blue-500' 
                  : 'border-gray-300'
                }
              `}>
                {selectedDecision === 'variable' && (
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">📊</span>
                <span className="font-medium">Dépense variable</span>
                <span className="text-xs text-gray-500">
                  (occasionnel, variable)
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isProcessing}
          >
            Annuler
          </Button>
          <Button
            onClick={handleValidate}
            disabled={isProcessing}
            className={`
              flex items-center gap-2
              ${selectedDecision === 'fixed'
                ? 'bg-orange-600 hover:bg-orange-700'
                : 'bg-blue-600 hover:bg-blue-700'
              }
              text-white
            `}
          >
            {isProcessing ? (
              <>
                <div className="w-4 h-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                Application...
              </>
            ) : (
              <>
                {selectedDecision === 'ai_suggestion' ? '🤖' : 
                 selectedDecision === 'fixed' ? '🏠' : '📊'}
                Valider
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default ClassificationModal;