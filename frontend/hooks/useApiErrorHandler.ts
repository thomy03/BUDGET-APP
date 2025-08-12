'use client';

import { useState, useCallback } from 'react';

export interface ApiErrorState {
  error: string | null;
  isOfflineMode: boolean;
  isUsingDefaults: boolean;
  retryCount: number;
}

export function useApiErrorHandler() {
  const [errorState, setErrorState] = useState<ApiErrorState>({
    error: null,
    isOfflineMode: false,
    isUsingDefaults: false,
    retryCount: 0
  });

  const setError = useCallback((
    error: string | null, 
    options?: {
      isOfflineMode?: boolean;
      isUsingDefaults?: boolean;
    }
  ) => {
    setErrorState(prev => ({
      ...prev,
      error,
      isOfflineMode: options?.isOfflineMode ?? false,
      isUsingDefaults: options?.isUsingDefaults ?? false
    }));
  }, []);

  const clearError = useCallback(() => {
    setErrorState(prev => ({
      ...prev,
      error: null,
      isOfflineMode: false,
      isUsingDefaults: false
    }));
  }, []);

  const handleApiError = useCallback((
    error: any,
    fallbackMessage: string = 'Une erreur est survenue'
  ): boolean => {
    console.error('API Error:', error);
    
    const isNetworkError = !error.response;
    const is404 = error.response?.status === 404;
    const is405 = error.response?.status === 405;
    const is503 = error.response?.status === 503;
    
    if (isNetworkError || is503) {
      setError('Service temporairement indisponible - Données par défaut utilisées', {
        isOfflineMode: true,
        isUsingDefaults: true
      });
      return true; // Utiliser les données par défaut
    }
    
    if (is404 || is405) {
      setError('API non disponible - Mode par défaut activé', {
        isOfflineMode: true,
        isUsingDefaults: true
      });
      return true; // Utiliser les données par défaut
    }
    
    // Autres erreurs
    const errorMessage = error.response?.data?.detail || error.message || fallbackMessage;
    setError(`Erreur API : ${errorMessage}`, {
      isOfflineMode: false,
      isUsingDefaults: false
    });
    
    return false; // Ne pas utiliser les données par défaut
  }, [setError]);

  const incrementRetryCount = useCallback(() => {
    setErrorState(prev => ({
      ...prev,
      retryCount: prev.retryCount + 1
    }));
  }, []);

  const resetRetryCount = useCallback(() => {
    setErrorState(prev => ({
      ...prev,
      retryCount: 0
    }));
  }, []);

  return {
    errorState,
    setError,
    clearError,
    handleApiError,
    incrementRetryCount,
    resetRetryCount
  };
}

export default useApiErrorHandler;