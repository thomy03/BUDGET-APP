'use client';

import { useState } from 'react';

interface MerchantInfo {
  name: string;
  category: string;
  type: 'fixed' | 'variable';
  confidence: number;
  description?: string;
  website?: string;
  address?: string;
  phone?: string;
  sources: string[];
  lastUpdated?: string;
}

interface MerchantInfoDisplayProps {
  merchantInfo: MerchantInfo;
  /** Mode d'affichage */
  mode?: 'compact' | 'detailed';
  /** Afficher les actions */
  showActions?: boolean;
  /** Callback pour accepter la suggestion */
  onAccept?: (type: 'fixed' | 'variable') => void;
  /** Callback pour rejeter la suggestion */
  onReject?: () => void;
  /** Callback pour signaler une erreur */
  onReportError?: () => void;
}

export function MerchantInfoDisplay({
  merchantInfo,
  mode = 'compact',
  showActions = false,
  onAccept,
  onReject,
  onReportError
}: MerchantInfoDisplayProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600 bg-green-100';
    if (confidence >= 0.7) return 'text-blue-600 bg-blue-100';
    if (confidence >= 0.5) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };

  const getTypeIcon = (type: 'fixed' | 'variable') => {
    return type === 'fixed' ? '🏠' : '📊';
  };

  const getTypeLabel = (type: 'fixed' | 'variable') => {
    return type === 'fixed' ? 'Fixe' : 'Variable';
  };

  if (mode === 'compact') {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="font-medium text-blue-900">{merchantInfo.name}</span>
            <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(merchantInfo.confidence)}`}>
              {Math.round(merchantInfo.confidence * 100)}%
            </span>
          </div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-blue-600 hover:text-blue-800 text-xs"
          >
            {showDetails ? 'Masquer' : 'Détails'}
          </button>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div>
            <span className="text-gray-600">{merchantInfo.category}</span>
          </div>
          <div className="flex items-center gap-1">
            <span>{getTypeIcon(merchantInfo.type)}</span>
            <span className={`font-medium ${
              merchantInfo.type === 'fixed' ? 'text-orange-600' : 'text-blue-600'
            }`}>
              {getTypeLabel(merchantInfo.type)}
            </span>
          </div>
        </div>

        {showDetails && (
          <div className="pt-2 border-t border-blue-200 space-y-2">
            {merchantInfo.description && (
              <p className="text-xs text-gray-700">{merchantInfo.description}</p>
            )}
            
            {(merchantInfo.website || merchantInfo.address || merchantInfo.phone) && (
              <div className="grid grid-cols-1 gap-1 text-xs">
                {merchantInfo.website && (
                  <div>
                    <span className="text-gray-500">Site:</span>
                    <a 
                      href={merchantInfo.website} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="ml-1 text-blue-600 hover:underline"
                    >
                      {merchantInfo.website.replace(/^https?:\/\//, '')}
                    </a>
                  </div>
                )}
                {merchantInfo.address && (
                  <div>
                    <span className="text-gray-500">Adresse:</span>
                    <span className="ml-1">{merchantInfo.address}</span>
                  </div>
                )}
                {merchantInfo.phone && (
                  <div>
                    <span className="text-gray-500">Téléphone:</span>
                    <span className="ml-1">{merchantInfo.phone}</span>
                  </div>
                )}
              </div>
            )}

            <div className="text-xs text-gray-500">
              <div>Sources: {merchantInfo.sources.join(', ')}</div>
              {merchantInfo.lastUpdated && (
                <div>Mis à jour: {new Date(merchantInfo.lastUpdated).toLocaleDateString('fr-FR')}</div>
              )}
            </div>
          </div>
        )}

        {showActions && (
          <div className="flex items-center justify-between pt-2 border-t border-blue-200">
            <div className="flex gap-2">
              <button
                onClick={() => onAccept?.(merchantInfo.type)}
                className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
              >
                Accepter
              </button>
              <button
                onClick={onReject}
                className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300 transition-colors"
              >
                Ignorer
              </button>
            </div>
            <button
              onClick={onReportError}
              className="text-red-600 hover:text-red-800 text-xs"
            >
              Signaler erreur
            </button>
          </div>
        )}
      </div>
    );
  }

  // Mode detailed
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-lg text-gray-900">{merchantInfo.name}</h3>
          <p className="text-sm text-gray-600">{merchantInfo.category}</p>
        </div>
        <div className="text-right">
          <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm ${getConfidenceColor(merchantInfo.confidence)}`}>
            <span>Confiance: {Math.round(merchantInfo.confidence * 100)}%</span>
          </div>
          <div className="mt-1 flex items-center gap-1 justify-end">
            <span>{getTypeIcon(merchantInfo.type)}</span>
            <span className={`text-sm font-medium ${
              merchantInfo.type === 'fixed' ? 'text-orange-600' : 'text-blue-600'
            }`}>
              Dépense {getTypeLabel(merchantInfo.type)}
            </span>
          </div>
        </div>
      </div>

      {merchantInfo.description && (
        <div className="bg-gray-50 rounded p-3">
          <p className="text-sm text-gray-700">{merchantInfo.description}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {merchantInfo.website && (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Site web</label>
            <a 
              href={merchantInfo.website} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-sm"
            >
              {merchantInfo.website}
            </a>
          </div>
        )}
        
        {merchantInfo.address && (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Adresse</label>
            <p className="text-sm text-gray-700">{merchantInfo.address}</p>
          </div>
        )}
        
        {merchantInfo.phone && (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Téléphone</label>
            <p className="text-sm text-gray-700">{merchantInfo.phone}</p>
          </div>
        )}
      </div>

      <div className="border-t pt-3">
        <label className="block text-xs font-medium text-gray-500 mb-2">Sources de données</label>
        <div className="flex flex-wrap gap-2">
          {merchantInfo.sources.map((source, index) => (
            <span 
              key={index}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full"
            >
              {source}
            </span>
          ))}
        </div>
        {merchantInfo.lastUpdated && (
          <p className="text-xs text-gray-500 mt-2">
            Dernière mise à jour: {new Date(merchantInfo.lastUpdated).toLocaleDateString('fr-FR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </p>
        )}
      </div>

      {showActions && (
        <div className="flex items-center justify-between pt-3 border-t">
          <div className="flex gap-3">
            <button
              onClick={() => onAccept?.(merchantInfo.type)}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              Accepter la classification
            </button>
            <button
              onClick={onReject}
              className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
            >
              Ignorer
            </button>
          </div>
          <button
            onClick={onReportError}
            className="text-red-600 hover:text-red-800 text-sm flex items-center gap-1"
          >
            <span>⚠️</span>
            <span>Signaler une erreur</span>
          </button>
        </div>
      )}
    </div>
  );
}