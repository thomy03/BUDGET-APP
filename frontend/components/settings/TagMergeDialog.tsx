'use client';

import { useState } from 'react';
import { Card, Button, Alert } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { TagSourceBadge } from '../ui/TagSourceBadge';

interface TagInfo {
  name: string;
  expense_type: 'fixed' | 'variable';
  transaction_count: number;
  total_amount: number;
  associated_labels: string[];
}

interface TagMergeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  availableTags: TagInfo[];
  onMerge: (sourceTags: string[], targetTag: string) => Promise<boolean>;
}

export function TagMergeDialog({
  isOpen,
  onClose,
  availableTags,
  onMerge
}: TagMergeDialogProps) {
  const [selectedSourceTags, setSelectedSourceTags] = useState<string[]>([]);
  const [targetTag, setTargetTag] = useState<string>('');
  const [newTargetTag, setNewTargetTag] = useState<string>('');
  const [useNewTarget, setUseNewTarget] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>('');

  if (!isOpen) return null;

  const handleMerge = async () => {
    if (selectedSourceTags.length === 0) {
      setError('Veuillez sélectionner au moins un tag source');
      return;
    }

    const finalTargetTag = useNewTarget ? newTargetTag : targetTag;
    if (!finalTargetTag.trim()) {
      setError('Veuillez spécifier un tag de destination');
      return;
    }

    if (selectedSourceTags.includes(finalTargetTag)) {
      setError('Le tag de destination ne peut pas être dans la liste des tags sources');
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      const success = await onMerge(selectedSourceTags, finalTargetTag);
      if (success) {
        handleClose();
      } else {
        setError('Erreur lors de la fusion des tags');
      }
    } catch (err) {
      setError('Erreur lors de la fusion des tags');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClose = () => {
    setSelectedSourceTags([]);
    setTargetTag('');
    setNewTargetTag('');
    setUseNewTarget(false);
    setError('');
    onClose();
  };

  const toggleSourceTag = (tagName: string) => {
    setSelectedSourceTags(prev => 
      prev.includes(tagName)
        ? prev.filter(t => t !== tagName)
        : [...prev, tagName]
    );
  };

  const getEstimatedResult = () => {
    const sourceTags = availableTags.filter(tag => 
      selectedSourceTags.includes(tag.name)
    );
    
    const totalTransactions = sourceTags.reduce((sum, tag) => 
      sum + tag.transaction_count, 0
    );
    
    const totalAmount = sourceTags.reduce((sum, tag) => 
      sum + tag.total_amount, 0
    );

    return {
      totalTransactions,
      totalAmount,
      affectedTags: sourceTags.length
    };
  };

  const estimate = getEstimatedResult();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              Fusionner des Tags
            </h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 text-xl"
            >
              ×
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Combinez plusieurs tags en un seul. Toutes les transactions seront redistribuées.
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <Alert variant="error">
              {error}
            </Alert>
          )}

          {/* Source Tags Selection */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              1. Sélectionnez les tags à fusionner
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto border rounded-lg p-4">
              {availableTags.map((tag) => (
                <div
                  key={tag.name}
                  className={`
                    flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all
                    ${
                      selectedSourceTags.includes(tag.name)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                  onClick={() => toggleSourceTag(tag.name)}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selectedSourceTags.includes(tag.name)}
                      onChange={() => toggleSourceTag(tag.name)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{tag.name}</span>
                        <ExpenseTypeBadge type={tag.expense_type} size="sm" />
                      </div>
                      <div className="text-sm text-gray-600">
                        {tag.transaction_count} transaction(s)
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Target Tag Selection */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              2. Choisissez le tag de destination
            </h3>
            
            <div className="space-y-3">
              {/* Use existing tag */}
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  id="existing"
                  checked={!useNewTarget}
                  onChange={() => setUseNewTarget(false)}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="existing" className="text-sm font-medium text-gray-700">
                  Fusionner vers un tag existant
                </label>
              </div>

              {!useNewTarget && (
                <select
                  value={targetTag}
                  onChange={(e) => setTargetTag(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  disabled={useNewTarget}
                >
                  <option value="">Sélectionnez un tag de destination...</option>
                  {availableTags
                    .filter(tag => !selectedSourceTags.includes(tag.name))
                    .map((tag) => (
                      <option key={tag.name} value={tag.name}>
                        {tag.name} ({tag.transaction_count} transactions)
                      </option>
                    ))
                  }
                </select>
              )}

              {/* Create new tag */}
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  id="new"
                  checked={useNewTarget}
                  onChange={() => setUseNewTarget(true)}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="new" className="text-sm font-medium text-gray-700">
                  Créer un nouveau tag
                </label>
              </div>

              {useNewTarget && (
                <input
                  type="text"
                  value={newTargetTag}
                  onChange={(e) => setNewTargetTag(e.target.value)}
                  placeholder="Nom du nouveau tag..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  disabled={!useNewTarget}
                />
              )}
            </div>
          </div>

          {/* Preview */}
          {selectedSourceTags.length > 0 && (
            <Card className="p-4 bg-blue-50 border-blue-200">
              <h4 className="font-semibold text-gray-900 mb-2">Aperçu de la fusion</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Tags affectés:</span>
                  <div className="font-semibold text-gray-900">{estimate.affectedTags}</div>
                </div>
                <div>
                  <span className="text-gray-600">Transactions:</span>
                  <div className="font-semibold text-gray-900">{estimate.totalTransactions}</div>
                </div>
                <div>
                  <span className="text-gray-600">Montant total:</span>
                  <div className="font-semibold text-gray-900">
                    {Math.abs(estimate.totalAmount).toLocaleString('fr-FR', {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0
                    })}€
                  </div>
                </div>
              </div>
              
              <div className="mt-3 text-xs text-gray-600">
                ⚠️ Cette action est irréversible. Les tags sources seront supprimés après la fusion.
              </div>
            </Card>
          )}
        </div>

        {/* Actions */}
        <div className="p-6 border-t border-gray-200 flex items-center justify-end gap-3">
          <Button
            onClick={handleClose}
            variant="outline"
            disabled={isProcessing}
          >
            Annuler
          </Button>
          <Button
            onClick={handleMerge}
            disabled={
              isProcessing ||
              selectedSourceTags.length === 0 ||
              (!useNewTarget && !targetTag) ||
              (useNewTarget && !newTargetTag.trim())
            }
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isProcessing ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Fusion en cours...</span>
              </div>
            ) : (
              `Fusionner ${selectedSourceTags.length} tag(s)`
            )}
          </Button>
        </div>
      </Card>
    </div>
  );
}