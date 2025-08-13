'use client';

import { useState, useEffect } from 'react';

interface WebResearchIndicatorProps {
  /** Indique si la recherche est en cours */
  isSearching: boolean;
  /** Le nom du marchand recherché */
  merchantName?: string;
  /** Callback appelé lorsque l'utilisateur clique sur Annuler */
  onCancel?: () => void;
  /** Niveau de confiance (0-1) */
  confidence?: number;
  /** Résultat de la recherche si disponible */
  result?: {
    name: string;
    category: string;
    type: 'fixed' | 'variable';
    source?: string;
  };
}

export function WebResearchIndicator({ 
  isSearching, 
  merchantName, 
  onCancel, 
  confidence,
  result 
}: WebResearchIndicatorProps) {
  const [dots, setDots] = useState('');

  // Animation des points de chargement
  useEffect(() => {
    if (!isSearching) {
      setDots('');
      return;
    }

    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isSearching]);

  if (!isSearching && !result) {
    return null;
  }

  return (
    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-blue-200 rounded-lg shadow-lg z-50 p-3">
      {isSearching ? (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
            <div>
              <div className="text-sm font-medium text-blue-700">
                Recherche web en cours{dots}
              </div>
              <div className="text-xs text-blue-600">
                Analyse de "{merchantName}"
              </div>
            </div>
          </div>
          {onCancel && (
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 text-xs px-2 py-1 hover:bg-gray-100 rounded"
            >
              Annuler
            </button>
          )}
        </div>
      ) : result ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium text-green-700">
                Informations trouvées
              </span>
              {confidence && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                  {Math.round(confidence * 100)}% confiance
                </span>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Nom:</span>
              <span className="ml-1 font-medium">{result.name}</span>
            </div>
            <div>
              <span className="text-gray-500">Catégorie:</span>
              <span className="ml-1 font-medium">{result.category}</span>
            </div>
            <div>
              <span className="text-gray-500">Type suggéré:</span>
              <span className={`ml-1 font-medium ${
                result.type === 'fixed' ? 'text-orange-600' : 'text-blue-600'
              }`}>
                {result.type === 'fixed' ? '🏠 Fixe' : '📊 Variable'}
              </span>
            </div>
            {result.source && (
              <div>
                <span className="text-gray-500">Source:</span>
                <span className="ml-1 font-medium text-blue-600">{result.source}</span>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-gray-100">
            <div className="text-xs text-gray-600 flex items-center gap-1">
              <span>💡</span>
              <span>Classification automatique basée sur les données web</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}