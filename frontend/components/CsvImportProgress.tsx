'use client'

import * as React from 'react'
import Card from './ui/Card'
import Button from './ui/Button'
import LoadingSpinner from './ui/LoadingSpinner'

export type CsvImportPhase = 'upload' | 'parse' | 'validate' | 'import'

type Props = {
  fileName?: string
  progress: number | null // null => indéterminé (équivalent spinner)
  phase?: CsvImportPhase
  cancellable?: boolean
  onCancel?: () => void
  hint?: string
  error?: string | null
  className?: string
  fileSize?: number // Taille du fichier en bytes
  estimatedLines?: number // Nombre de lignes estimé
}

function clamp(n: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(n)))
}

function phaseLabel(phase?: CsvImportPhase, estimatedLines?: number) {
  switch (phase) {
    case 'upload':
      return 'Téléversement en cours…'
    case 'parse':
      return 'Analyse du fichier…'
    case 'validate':
      return estimatedLines ? `Validation de ~${estimatedLines} lignes…` : 'Validation des lignes…'
    case 'import':
      return estimatedLines ? `Importation de ~${estimatedLines} transactions…` : 'Importation des données…'
    default:
      return 'Traitement en cours…'
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CsvImportProgress({
  fileName,
  progress,
  phase = 'upload',
  cancellable = false,
  onCancel,
  hint,
  error,
  className,
  fileSize,
  estimatedLines,
}: Props) {
  const pct = typeof progress === 'number' ? clamp(progress) : null

  return (
    <Card className={className} padding="lg">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100">
                <span className="text-lg">📊</span>
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-zinc-900">Import CSV</div>
                {fileName && (
                  <div className="space-y-1">
                    <div 
                      title={fileName}
                      className="text-sm text-zinc-600 truncate max-w-xs"
                    >
                      {fileName}
                    </div>
                    {(fileSize || estimatedLines) && (
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        {fileSize && <span>📁 {formatFileSize(fileSize)}</span>}
                        {estimatedLines && <span>📊 ~{estimatedLines} lignes</span>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {cancellable && onCancel && (
            <Button 
              variant="secondary" 
              size="sm"
              onClick={onCancel}
              className="shrink-0"
            >
              Annuler
            </Button>
          )}
        </div>

        <div className="space-y-3">
          {pct === null ? (
            <div
              role="status"
              aria-live="polite"
              className="flex items-center gap-3"
            >
              <LoadingSpinner size="sm" />
              <div className="text-sm text-zinc-700">{phaseLabel(phase, estimatedLines)}</div>
            </div>
          ) : (
            <div className="space-y-2">
              <div
                role="progressbar"
                aria-label={`Progression de l'import (${pct}%)`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct}
                className="relative"
              >
                <div className="h-2 w-full bg-zinc-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-700">{phaseLabel(phase, estimatedLines)}</span>
                <span className="font-mono text-blue-600 font-medium">{pct}%</span>
              </div>
            </div>
          )}
        </div>

        {hint && (
          <div className="text-xs text-zinc-600 bg-zinc-50 rounded-lg p-3">
            <span className="inline-block mr-2">💡</span>
            {hint}
          </div>
        )}

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
            <span className="inline-block mr-2">⚠️</span>
            {error}
          </div>
        )}
      </div>
    </Card>
  )
}