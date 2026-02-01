'use client';

import { useState, useCallback, useRef } from 'react';
import { Tx } from '../../lib/api';

interface HoverPreview {
  preview_text: string;
  confidence_indicator: 'high' | 'medium' | 'low' | 'error' | 'unknown';
  suggested_type: string;
  confidence_score?: number;
  main_reason?: string;
}

interface HoverAIPreviewProps {
  transaction: Tx;
  onRowClick?: (transaction: Tx) => void;
  onTriggerFullAnalysis?: (transactionId: number) => void;
  className?: string;
  children: React.ReactNode;
}

export function HoverAIPreview({
  transaction,
  onRowClick,
  onTriggerFullAnalysis,
  className = '',
  children
}: HoverAIPreviewProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [preview, setPreview] = useState<HoverPreview | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [showClickHint, setShowClickHint] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previewTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const loadHoverPreview = useCallback(async () => {
    if (transaction.amount >= 0) return; // Skip pour les revenus
    if (isLoadingPreview) return;

    setIsLoadingPreview(true);
    
    try {
      const response = await fetch('/api/expense-classification/transactions/hover-preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_ids: [transaction.id],
          preview_only: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to load preview');
      }

      const data = await response.json();
      const previewData = data.previews[transaction.id];
      
      if (previewData) {
        setPreview(previewData);
      }
    } catch (error) {
      console.error('Error loading hover preview:', error);
      setPreview({
        preview_text: 'Erreur de chargement',
        confidence_indicator: 'error',
        suggested_type: 'unknown'
      });
    } finally {
      setIsLoadingPreview(false);
    }
  }, [transaction.id, transaction.amount, isLoadingPreview]);

  const handleMouseEnter = useCallback(() => {
    setIsHovering(true);
    
    // Délai avant de charger la prévisualisation pour éviter les appels excessifs
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    
    hoverTimeoutRef.current = setTimeout(() => {
      loadHoverPreview();
      
      // Afficher l'indication de clic après un délai supplémentaire
      previewTimeoutRef.current = setTimeout(() => {
        setShowClickHint(true);
      }, 1500);
    }, 300);
  }, [loadHoverPreview]);

  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    setShowClickHint(false);
    
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    
    if (previewTimeoutRef.current) {
      clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }

    // Garder la prévisualisation un moment après avoir quitté le hover
    setTimeout(() => {
      if (!isHovering) {
        setPreview(null);
      }
    }, 500);
  }, [isHovering]);

  const handleRowClick = useCallback(() => {
    if (onRowClick) {
      onRowClick(transaction);
    } else if (onTriggerFullAnalysis) {
      onTriggerFullAnalysis(transaction.id);
    }
  }, [onRowClick, onTriggerFullAnalysis, transaction]);

  const getConfidenceColor = (indicator: HoverPreview['confidence_indicator']) => {
    switch (indicator) {
      case 'high':
        return 'border-green-400 bg-green-50';
      case 'medium':
        return 'border-amber-400 bg-amber-50';
      case 'low':
        return 'border-red-400 bg-red-50';
      case 'error':
        return 'border-red-500 bg-red-100';
      default:
        return 'border-gray-400 bg-gray-50';
    }
  };

  const getHoverStyles = () => {
    if (!isHovering || transaction.amount >= 0) return '';
    
    const baseStyle = 'transform transition-all duration-200 cursor-pointer';
    
    if (preview) {
      return `${baseStyle} scale-[1.01] ${getConfidenceColor(preview.confidence_indicator)} border-2 shadow-lg`;
    }
    
    return `${baseStyle} scale-[1.005] bg-blue-50/30 border-blue-200 border shadow-md`;
  };

  return (
    <div
      className={`relative ${className} ${getHoverStyles()}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleRowClick}
      style={{ borderRadius: '6px' }}
    >
      {children}
      
      {/* Indicateur de hover pour les dépenses non analysées */}
      {isHovering && transaction.amount < 0 && !preview && !isLoadingPreview && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-blue-600 text-white text-xs px-2 py-1 rounded-md shadow-md animate-fade-in">
            Survoler pour analyser
          </div>
        </div>
      )}

      {/* Loader pendant le chargement de la prévisualisation */}
      {isLoadingPreview && (
        <div className="absolute top-2 right-2 z-10">
          <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent bg-white rounded-full shadow-sm" />
        </div>
      )}

      {/* Prévisualisation de l'IA au hover */}
      {preview && isHovering && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1">
          <div className="bg-white rounded-lg shadow-xl border-2 border-gray-200 p-3 mx-2">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div 
                  className={`w-3 h-3 rounded-full ${
                    preview.confidence_indicator === 'high' ? 'bg-green-400' :
                    preview.confidence_indicator === 'medium' ? 'bg-amber-400' :
                    preview.confidence_indicator === 'low' ? 'bg-red-400' :
                    'bg-gray-400'
                  }`}
                />
                <span className="text-sm font-medium text-gray-800">
                  Suggestion IA: {preview.preview_text}
                </span>
              </div>
              
              {preview.confidence_score && (
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  {Math.round(preview.confidence_score * 100)}%
                </span>
              )}
            </div>
            
            {preview.main_reason && (
              <div className="text-xs text-gray-600 mb-2">
                {preview.main_reason}
              </div>
            )}
            
            {/* Indication de clic */}
            {showClickHint && (
              <div className="flex items-center gap-2 text-xs text-blue-600 animate-pulse">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
                </svg>
                Cliquer pour une analyse complète
              </div>
            )}
            
            {/* Petite flèche pointant vers la ligne */}
            <div className="absolute -top-2 left-4 w-4 h-4 bg-white border-t-2 border-l-2 border-gray-200 transform rotate-45" />
          </div>
        </div>
      )}
    </div>
  );
}

// Hook pour gérer les prévisualisations en lot
export function useHoverPreviewBatch() {
  const [previews, setPreviews] = useState<Record<number, HoverPreview>>({});
  const [loading, setLoading] = useState<Set<number>>(new Set());

  const loadPreviewsForTransactions = useCallback(async (transactionIds: number[]) => {
    // Filtrer ceux qui ne sont pas déjà en cours de chargement
    const toLoad = transactionIds.filter(id => !loading.has(id) && !previews[id]);
    if (toLoad.length === 0) return;

    // Marquer comme en cours de chargement
    setLoading(prev => {
      const newLoading = new Set(prev);
      toLoad.forEach(id => newLoading.add(id));
      return newLoading;
    });

    try {
      const response = await fetch('/api/expense-classification/transactions/hover-preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_ids: toLoad,
          preview_only: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to load batch previews');
      }

      const data = await response.json();
      
      // Mettre à jour les prévisualisations
      setPreviews(prev => ({ ...prev, ...data.previews }));
      
    } catch (error) {
      console.error('Error loading batch previews:', error);
      
      // Ajouter des prévisualisations d'erreur
      const errorPreviews: Record<number, HoverPreview> = {};
      toLoad.forEach(id => {
        errorPreviews[id] = {
          preview_text: 'Erreur de chargement',
          confidence_indicator: 'error',
          suggested_type: 'unknown'
        };
      });
      setPreviews(prev => ({ ...prev, ...errorPreviews }));
      
    } finally {
      // Retirer du chargement
      setLoading(prev => {
        const newLoading = new Set(prev);
        toLoad.forEach(id => newLoading.delete(id));
        return newLoading;
      });
    }
  }, [loading, previews]);

  const getPreview = useCallback((transactionId: number): HoverPreview | null => {
    return previews[transactionId] || null;
  }, [previews]);

  const isLoadingPreview = useCallback((transactionId: number): boolean => {
    return loading.has(transactionId);
  }, [loading]);

  const clearPreviews = useCallback(() => {
    setPreviews({});
    setLoading(new Set());
  }, []);

  return {
    loadPreviewsForTransactions,
    getPreview,
    isLoadingPreview,
    clearPreviews
  };
}