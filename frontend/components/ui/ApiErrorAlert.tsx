'use client';

import React from 'react';
import Alert from './Alert';
import Button from './Button';

interface ApiErrorAlertProps {
  error?: string | null;
  isOfflineMode?: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  showRetryButton?: boolean;
}

export function ApiErrorAlert({
  error,
  isOfflineMode = false,
  onRetry,
  onDismiss,
  className = "",
  showRetryButton = true
}: ApiErrorAlertProps) {
  if (!error) return null;

  const isDefaultDataMode = error.includes('par défaut') || error.includes('indisponible');
  const variant = isDefaultDataMode ? 'warning' : 'error';
  
  return (
    <Alert 
      variant={variant} 
      className={`${className} mb-4`}
      onClose={onDismiss}
    >
      <div className="flex items-center justify-between w-full">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="font-medium">
              {isDefaultDataMode ? 'Mode hors ligne' : 'Erreur API'}
            </span>
            <span className="text-sm mt-1">
              {error}
            </span>
            {isOfflineMode && (
              <span className="text-xs mt-2 opacity-80">
                Les modifications seront limitées jusqu'à la reconnexion.
              </span>
            )}
          </div>
        </div>
        
        {showRetryButton && onRetry && (
          <div className="flex-shrink-0 ml-4">
            <Button
              onClick={onRetry}
              variant="outline"
              size="sm"
              className={`
                ${isDefaultDataMode 
                  ? 'border-amber-300 text-amber-700 hover:bg-amber-100' 
                  : 'border-red-300 text-red-700 hover:bg-red-100'
                }
              `}
            >
              🔄 Réessayer
            </Button>
          </div>
        )}
      </div>
    </Alert>
  );
}

export default ApiErrorAlert;