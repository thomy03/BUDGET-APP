'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Tx } from '../../lib/api';

interface AutoClassificationResult {
  total_analyzed: number;
  auto_applied: number;
  pending_review: number;
  high_confidence_applied: number;
  medium_confidence_pending: number;
  classifications: Array<{
    transaction_id: number;
    suggested_type: string;
    confidence_score: number;
    explanation: string;
    auto_applied: boolean;
    needs_review: boolean;
  }>;
  processing_time_ms: number;
  month_analyzed?: string;
}

interface AutoAIProcessorProps {
  transactions: Tx[];
  enabled?: boolean;
  autoApplyThreshold?: number;
  maxConcurrent?: number;
  backgroundMode?: boolean;
  onProgress?: (progress: { processed: number; total: number; autoApplied: number }) => void;
  onComplete?: (result: AutoClassificationResult) => void;
  onTransactionUpdate?: (transactionId: number, classification: any) => void;
}

export function AutoAIProcessor({
  transactions,
  enabled = false,
  autoApplyThreshold = 0.7,
  maxConcurrent = 10,
  backgroundMode = true,
  onProgress,
  onComplete,
  onTransactionUpdate
}: AutoAIProcessorProps) {
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({ processed: 0, total: 0, autoApplied: 0 });
  const [results, setResults] = useState<AutoClassificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filtrer les transactions qui nécessitent une classification
  const transactionsToProcess = useMemo(() => {
    return transactions.filter(tx => 
      tx.amount < 0 && // Seulement les dépenses
      (!tx.expense_type || tx.expense_type === '' || tx.expense_type === 'variable') && // Non classifiées ou par défaut
      (tx.tags && tx.tags.length > 0) // Ont des tags pour l'analyse
    );
  }, [transactions]);

  // Traitement par lots pour éviter la surcharge
  const processInBatches = useCallback(async (transactionIds: number[], batchSize: number = maxConcurrent) => {
    const batches = [];
    for (let i = 0; i < transactionIds.length; i += batchSize) {
      batches.push(transactionIds.slice(i, i + batchSize));
    }

    let allResults: AutoClassificationResult['classifications'] = [];
    let totalAutoApplied = 0;

    for (const [index, batch] of batches.entries()) {
      try {
        const response = await fetch('/api/expense-classification/bulk-suggestions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            transaction_ids: batch,
            confidence_threshold: 0.1,
            include_explanations: true,
            use_cache: true,
            max_processing_time_ms: 5000
          })
        });

        if (!response.ok) {
          throw new Error(`Batch ${index + 1} failed: ${response.statusText}`);
        }

        const data = await response.json();
        
        // Traiter les résultats du lot
        const batchResults = Object.entries(data.suggestions).map(([txId, suggestion]: [string, any]) => {
          const autoApplied = suggestion.confidence_score >= autoApplyThreshold;
          
          if (autoApplied) {
            totalAutoApplied++;
            // Notifier la mise à jour de la transaction
            onTransactionUpdate?.(parseInt(txId), {
              expense_type: suggestion.suggested_type.toLowerCase(),
              expense_type_confidence: suggestion.confidence_score,
              expense_type_auto_detected: true
            });
          }

          return {
            transaction_id: parseInt(txId),
            suggested_type: suggestion.suggested_type,
            confidence_score: suggestion.confidence_score,
            explanation: suggestion.explanation,
            auto_applied: autoApplied,
            needs_review: !autoApplied && suggestion.confidence_score >= 0.4
          };
        });

        allResults = allResults.concat(batchResults);

        // Mettre à jour le progrès
        const newProgress = {
          processed: (index + 1) * batchSize,
          total: transactionIds.length,
          autoApplied: totalAutoApplied
        };
        setProgress(newProgress);
        onProgress?.(newProgress);

        // Pause entre les lots pour éviter la surcharge
        if (index < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, backgroundMode ? 1000 : 200));
        }

      } catch (error) {
        console.error(`Error processing batch ${index + 1}:`, error);
        // Continuer avec les autres lots même si un échoue
      }
    }

    return allResults;
  }, [maxConcurrent, autoApplyThreshold, backgroundMode, onTransactionUpdate, onProgress]);

  // Fonction principale de traitement
  const startProcessing = useCallback(async () => {
    if (processing || transactionsToProcess.length === 0) return;

    setProcessing(true);
    setError(null);
    setProgress({ processed: 0, total: transactionsToProcess.length, autoApplied: 0 });

    try {
      const startTime = performance.now();
      
      // Extraire les IDs des transactions à traiter
      const transactionIds = transactionsToProcess.map(tx => tx.id);
      
      // Traiter par lots
      const classifications = await processInBatches(transactionIds);
      
      const endTime = performance.now();
      
      // Calculer les résultats finaux
      const result: AutoClassificationResult = {
        total_analyzed: classifications.length,
        auto_applied: classifications.filter(c => c.auto_applied).length,
        pending_review: classifications.filter(c => c.needs_review).length,
        high_confidence_applied: classifications.filter(c => c.auto_applied && c.confidence_score >= 0.8).length,
        medium_confidence_pending: classifications.filter(c => c.needs_review && c.confidence_score >= 0.6).length,
        classifications,
        processing_time_ms: endTime - startTime
      };

      setResults(result);
      onComplete?.(result);

    } catch (error) {
      console.error('Auto AI processing failed:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setProcessing(false);
    }
  }, [processing, transactionsToProcess, processInBatches, onComplete]);

  // Démarrer automatiquement si activé
  useEffect(() => {
    if (enabled && transactionsToProcess.length > 0 && !processing && !results) {
      // Délai initial pour éviter de surcharger au chargement
      const timer = setTimeout(() => {
        startProcessing();
      }, backgroundMode ? 2000 : 500);

      return () => clearTimeout(timer);
    }
  }, [enabled, transactionsToProcess.length, processing, results, startProcessing, backgroundMode]);

  // Interface utilisateur (optionnelle)
  if (!processing && !results && !error) {
    return null; // Mode invisible par défaut
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {processing && (
        <div className="bg-white rounded-lg shadow-lg border p-4 min-w-[300px]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <div>
              <div className="font-medium text-sm">Classification IA automatique</div>
              <div className="text-xs text-gray-500">Traitement en arrière-plan...</div>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span>Progrès</span>
              <span>{progress.processed}/{progress.total}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(progress.processed / progress.total) * 100}%` }}
              />
            </div>
            <div className="text-xs text-gray-600">
              {progress.autoApplied} classifications appliquées automatiquement
            </div>
          </div>
        </div>
      )}

      {results && (
        <div className="bg-green-50 rounded-lg shadow-lg border border-green-200 p-4 min-w-[300px]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <div className="font-medium text-sm text-green-800">Classification terminée</div>
              <div className="text-xs text-green-600">
                {results.processing_time_ms < 1000 
                  ? `${Math.round(results.processing_time_ms)}ms`
                  : `${(results.processing_time_ms / 1000).toFixed(1)}s`
                }
              </div>
            </div>
          </div>
          
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600">Analysées:</span>
              <span className="font-medium">{results.total_analyzed}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-600">Auto-appliquées:</span>
              <span className="font-medium text-green-700">{results.auto_applied}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-amber-700">À réviser:</span>
              <span className="font-medium text-amber-700">{results.pending_review}</span>
            </div>
          </div>
          
          <button
            onClick={() => setResults(null)}
            className="mt-3 w-full text-xs bg-green-100 hover:bg-green-200 text-green-800 px-2 py-1 rounded transition-colors"
          >
            Fermer
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 rounded-lg shadow-lg border border-red-200 p-4 min-w-[300px]">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <div className="font-medium text-sm text-red-800">Erreur de traitement</div>
            </div>
          </div>
          
          <div className="text-xs text-red-600 mb-3">
            {error}
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={startProcessing}
              className="flex-1 text-xs bg-red-100 hover:bg-red-200 text-red-800 px-2 py-1 rounded transition-colors"
            >
              Réessayer
            </button>
            <button
              onClick={() => setError(null)}
              className="flex-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-800 px-2 py-1 rounded transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Hook pour utiliser le processeur auto IA
export function useAutoAIProcessor() {
  const [enabled, setEnabled] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [lastResult, setLastResult] = useState<AutoClassificationResult | null>(null);

  const startAutoProcessing = useCallback((transactions: Tx[]) => {
    setEnabled(true);
    setProcessing(true);
  }, []);

  const stopAutoProcessing = useCallback(() => {
    setEnabled(false);
    setProcessing(false);
  }, []);

  return {
    enabled,
    processing,
    lastResult,
    startAutoProcessing,
    stopAutoProcessing,
    setLastResult
  };
}