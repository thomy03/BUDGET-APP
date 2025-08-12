'use client';

import { useState } from 'react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';

interface AutoTaggingResult {
  id: number;
  label: string;
  amount: number;
  previousTags: string[];
  newTags: string[];
  classification: 'fixed' | 'variable';
  confidence: number;
  isNewClassification: boolean;
}

interface AutoTaggingResultsProps {
  /** Whether the results modal is open */
  isOpen: boolean;
  /** Results from the auto-tagging process */
  results: AutoTaggingResult[];
  /** Summary statistics */
  summary: {
    totalProcessed: number;
    successfullyTagged: number;
    newTagsCreated: number;
    fixedClassifications: number;
    variableClassifications: number;
    processingTimeMs: number;
  };
  /** List of newly created tags */
  newTags: string[];
  /** Whether user can review and modify results before applying */
  allowReview?: boolean;
  /** Callback when user confirms results */
  onConfirm: (approvedResults: AutoTaggingResult[]) => void;
  /** Callback when user cancels/rejects results */
  onCancel: () => void;
  /** Callback when modal is closed */
  onClose: () => void;
}

export function AutoTaggingResults({
  isOpen,
  results,
  summary,
  newTags,
  allowReview = true,
  onConfirm,
  onCancel,
  onClose
}: AutoTaggingResultsProps) {
  const [selectedResults, setSelectedResults] = useState<Set<number>>(
    new Set(results.map(r => r.id))
  );
  const [viewMode, setViewMode] = useState<'summary' | 'details'>('summary');

  // Toggle selection of a specific result
  const toggleResult = (resultId: number) => {
    const newSelection = new Set(selectedResults);
    if (newSelection.has(resultId)) {
      newSelection.delete(resultId);
    } else {
      newSelection.add(resultId);
    }
    setSelectedResults(newSelection);
  };

  // Select/deselect all results
  const toggleAllResults = () => {
    if (selectedResults.size === results.length) {
      setSelectedResults(new Set());
    } else {
      setSelectedResults(new Set(results.map(r => r.id)));
    }
  };

  // Get approved results for confirmation
  const getApprovedResults = () => {
    return results.filter(result => selectedResults.has(result.id));
  };

  // Format processing time
  const formatProcessingTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.round(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Résultats de la classification automatique"
      maxWidth="2xl"
    >
      <div className="space-y-6">
        {/* Summary header */}
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 border border-green-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Classification terminée avec succès
                </h3>
                <p className="text-sm text-gray-600">
                  Traitement complété en {formatProcessingTime(summary.processingTimeMs)}
                </p>
              </div>
            </div>
            <Badge variant="success" size="lg">
              {summary.successfullyTagged} classifiées
            </Badge>
          </div>

          {/* Statistics grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{summary.totalProcessed}</div>
              <div className="text-sm text-gray-600">Transactions traitées</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.fixedClassifications}</div>
              <div className="text-sm text-gray-600">Dépenses fixes</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{summary.variableClassifications}</div>
              <div className="text-sm text-gray-600">Dépenses variables</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{summary.newTagsCreated}</div>
              <div className="text-sm text-gray-600">Nouveaux tags</div>
            </div>
          </div>
        </div>

        {/* New tags created */}
        {newTags.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900 flex items-center gap-2">
              <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" />
              </svg>
              Nouveaux tags créés ({newTags.length})
            </h4>
            <div className="flex flex-wrap gap-2">
              {newTags.map((tag, index) => (
                <Badge key={index} variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* View mode selector */}
        <div className="flex items-center justify-between">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('summary')}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'summary'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Résumé
            </button>
            <button
              onClick={() => setViewMode('details')}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                viewMode === 'details'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Détails ({results.length})
            </button>
          </div>

          {allowReview && viewMode === 'details' && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">
                {selectedResults.size} sur {results.length} sélectionnées
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={toggleAllResults}
              >
                {selectedResults.size === results.length ? 'Tout désélectionner' : 'Tout sélectionner'}
              </Button>
            </div>
          )}
        </div>

        {/* Results content */}
        {viewMode === 'details' && (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {results.map((result) => (
              <div
                key={result.id}
                className={`border rounded-lg p-4 transition-all ${
                  selectedResults.has(result.id)
                    ? 'border-blue-200 bg-blue-50'
                    : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    {/* Transaction info */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {allowReview && (
                          <input
                            type="checkbox"
                            checked={selectedResults.has(result.id)}
                            onChange={() => toggleResult(result.id)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                        )}
                        <div>
                          <div className="font-medium text-gray-900">{result.label}</div>
                          <div className="text-sm text-gray-600">
                            {Math.abs(result.amount).toFixed(2)} €
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={result.classification === 'fixed' ? 'info' : 'warning'}
                          size="sm"
                        >
                          {result.classification === 'fixed' ? 'Fixe' : 'Variable'}
                        </Badge>
                        <div className="text-xs text-gray-500">
                          {Math.round(result.confidence * 100)}% confiance
                        </div>
                      </div>
                    </div>

                    {/* Tags comparison */}
                    <div className="space-y-1">
                      {result.previousTags.length > 0 && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">Ancien:</span>
                          <div className="flex gap-1">
                            {result.previousTags.map((tag, index) => (
                              <Badge key={index} variant="outline" size="xs" className="text-gray-600">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">Nouveau:</span>
                        <div className="flex gap-1">
                          {result.newTags.map((tag, index) => (
                            <Badge 
                              key={index} 
                              variant="outline" 
                              size="xs" 
                              className="bg-green-50 text-green-700 border-green-200"
                            >
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex justify-between items-center pt-4 border-t border-gray-200">
          <Button
            variant="secondary"
            onClick={onCancel}
          >
            Annuler
          </Button>

          <div className="flex gap-3">
            {allowReview ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => onConfirm([])}
                >
                  Ignorer les modifications
                </Button>
                <Button
                  variant="primary"
                  onClick={() => onConfirm(getApprovedResults())}
                  disabled={selectedResults.size === 0}
                >
                  Appliquer {selectedResults.size} modification{selectedResults.size > 1 ? 's' : ''}
                </Button>
              </>
            ) : (
              <Button
                variant="primary"
                onClick={() => onConfirm(results)}
              >
                Continuer
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}