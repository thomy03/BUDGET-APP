'use client';

import { useEffect, useState } from 'react';

interface AutoTaggingStats {
  totalTransactions: number;
  processed: number;
  successfullyTagged: number;
  skippedLowConfidence: number;
  fixedClassifications: number;
  variableClassifications: number;
  newTagsCreated: string[];
  processingTimeMs: number;
  estimatedTimeRemainingMs?: number;
}

interface AutoTaggingProgressProps {
  isOpen: boolean;
  onClose: () => void;
  onCancel?: () => void;
  stats: AutoTaggingStats;
  progressPercentage: number;
  isCompleted: boolean;
  hasError?: boolean;
  errorMessage?: string;
}

export function AutoTaggingProgress({
  isOpen,
  onClose,
  onCancel,
  stats,
  progressPercentage,
  isCompleted,
  hasError = false,
  errorMessage
}: AutoTaggingProgressProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" />
      
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
          <h3 className="text-lg font-semibold mb-4">
            {hasError ? "❌ Erreur de traitement" : isCompleted ? "✅ Traitement terminé" : "🤖 Tagging automatique en cours..."}
          </h3>

          {hasError && errorMessage && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{errorMessage}</p>
            </div>
          )}

          {!hasError && !isCompleted && (
            <div className="mb-4">
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600">Progression</span>
                <span className="text-sm font-medium">{Math.round(progressPercentage)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
              <div className="mt-2 text-sm text-gray-500">
                {stats.processed} / {stats.totalTransactions} transactions traitées
              </div>
              {stats.estimatedTimeRemainingMs && (
                <div className="mt-1 text-xs text-gray-400">
                  Temps restant estimé: {Math.ceil(stats.estimatedTimeRemainingMs / 60000)} min
                </div>
              )}
            </div>
          )}

          {isCompleted && !hasError && (
            <div className="mb-4 space-y-2">
              <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-700">
                  ✅ {stats.successfullyTagged} transactions taguées avec succès
                </p>
                {stats.skippedLowConfidence > 0 && (
                  <p className="text-sm text-yellow-700">
                    ⚠️ {stats.skippedLowConfidence} transactions ignorées (confiance faible)
                  </p>
                )}
                {stats.newTagsCreated.length > 0 && (
                  <p className="text-sm text-blue-700">
                    🏷️ {stats.newTagsCreated.length} nouveaux tags créés
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-center gap-4">
            {isCompleted || hasError ? (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Fermer
              </button>
            ) : (
              onCancel && (
                <button
                  onClick={onCancel}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                >
                  Annuler
                </button>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}