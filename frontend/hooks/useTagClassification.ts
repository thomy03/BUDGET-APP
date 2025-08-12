'use client';

import { useState, useCallback } from 'react';
import { Tx, expenseClassificationApi, ExpenseClassificationResult } from '../lib/api';

export interface TagClassificationState {
  isLoading: boolean;
  error: string | null;
  pendingClassification: ExpenseClassificationResult | null;
  showModal: boolean;
  currentTransaction: Tx | null;
}

export interface TagClassificationActions {
  classifyAfterTagUpdate: (transaction: Tx, newTags: string) => Promise<boolean>;
  acceptSuggestion: (useAIsuggestion?: boolean) => Promise<boolean>;
  rejectSuggestion: () => void;
  forceClassification: (expenseType: 'fixed' | 'variable') => Promise<boolean>;
  clearState: () => void;
}

export interface UseTagClassificationReturn {
  state: TagClassificationState;
  actions: TagClassificationActions;
}

/**
 * Hook pour gérer la classification intelligente des dépenses après saisie de tags
 * 
 * Workflow:
 * 1. Après saisie d'un tag → Classification automatique IA
 * 2. Si confiance ≥ 70% → Application directe
 * 3. Si confiance < 70% → Modal de confirmation
 * 4. Possibilité de modifier manuellement après classification
 */
export function useTagClassification(): UseTagClassificationReturn {
  const [state, setState] = useState<TagClassificationState>({
    isLoading: false,
    error: null,
    pendingClassification: null,
    showModal: false,
    currentTransaction: null
  });

  // Configuration du seuil de confiance (selon spécifications)
  const CONFIDENCE_THRESHOLD = 0.7; // 70%

  /**
   * Déclenche la classification automatique après mise à jour des tags
   */
  const classifyAfterTagUpdate = useCallback(async (
    transaction: Tx, 
    newTags: string
  ): Promise<boolean> => {
    // Réinitialiser l'état
    setState(prev => ({
      ...prev,
      error: null,
      pendingClassification: null,
      showModal: false
    }));

    // Vérifier que la transaction est une dépense
    if (!transaction.is_expense || transaction.amount >= 0) {
      console.log('🔍 Classification skipped - not an expense transaction');
      return true; // Pas de classification nécessaire pour les revenus
    }

    // Si aucun tag ajouté, pas de classification
    if (!newTags || !newTags.trim()) {
      console.log('🔍 Classification skipped - no tags provided');
      return true;
    }

    try {
      setState(prev => ({ 
        ...prev, 
        isLoading: true,
        currentTransaction: transaction 
      }));

      console.log(`🤖 Starting AI classification for transaction ${transaction.id} with tags: "${newTags}"`);

      // Appeler l'API de classification IA
      const classificationResult = await expenseClassificationApi.classifyTransaction(transaction.id);

      console.log(`🎯 Classification result:`, {
        transactionId: transaction.id,
        suggestedType: classificationResult.suggested_type,
        confidence: classificationResult.confidence_score,
        reasoning: classificationResult.reasoning,
        threshold: CONFIDENCE_THRESHOLD
      });

      // Logique de décision selon le seuil de confiance
      if (classificationResult.confidence_score >= CONFIDENCE_THRESHOLD) {
        // Confiance ≥ 70% → Application automatique
        console.log(`✅ High confidence (${Math.round(classificationResult.confidence_score * 100)}%) - Applying directly`);
        
        await expenseClassificationApi.updateTransactionType(
          transaction.id,
          classificationResult.suggested_type,
          false // Pas un override manuel, c'est automatique
        );

        setState(prev => ({
          ...prev,
          isLoading: false,
          error: null
        }));

        return true;
      } else {
        // Confiance < 70% → Demander confirmation utilisateur
        console.log(`🤔 Low confidence (${Math.round(classificationResult.confidence_score * 100)}%) - Requesting user confirmation`);
        
        setState(prev => ({
          ...prev,
          isLoading: false,
          pendingClassification: classificationResult,
          showModal: true
        }));

        return false; // Indique qu'une action utilisateur est requise
      }

    } catch (error: any) {
      console.error('❌ Classification error:', error);
      
      const errorMessage = error?.response?.data?.detail || error?.message || 'Erreur lors de la classification automatique';
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
        showModal: false
      }));

      return false;
    }
  }, []);

  /**
   * Accepte la suggestion IA (avec ou sans confirmation explicite)
   */
  const acceptSuggestion = useCallback(async (useAIsuggestion: boolean = true): Promise<boolean> => {
    const { pendingClassification, currentTransaction } = state;
    
    if (!pendingClassification || !currentTransaction) {
      console.warn('🚫 No pending classification to accept');
      return false;
    }

    try {
      setState(prev => ({ ...prev, isLoading: true }));

      const suggestedType = useAIsuggestion 
        ? pendingClassification.suggested_type 
        : pendingClassification.suggested_type; // Pour le moment, même comportement

      console.log(`🎯 Accepting suggestion: ${suggestedType} for transaction ${currentTransaction.id}`);

      await expenseClassificationApi.updateTransactionType(
        currentTransaction.id,
        suggestedType,
        !useAIsuggestion // Si l'utilisateur choisit explicitement, c'est un override manuel
      );

      setState(prev => ({
        ...prev,
        isLoading: false,
        showModal: false,
        pendingClassification: null,
        currentTransaction: null,
        error: null
      }));

      return true;
    } catch (error: any) {
      console.error('❌ Error accepting suggestion:', error);
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error?.response?.data?.detail || 'Erreur lors de l\'application de la classification'
      }));

      return false;
    }
  }, [state]);

  /**
   * Rejette la suggestion IA (ferme la modal sans action)
   */
  const rejectSuggestion = useCallback(() => {
    console.log('❌ User rejected AI suggestion');
    
    setState(prev => ({
      ...prev,
      showModal: false,
      pendingClassification: null,
      currentTransaction: null,
      error: null
    }));
  }, []);

  /**
   * Force une classification manuelle (override utilisateur)
   */
  const forceClassification = useCallback(async (expenseType: 'fixed' | 'variable'): Promise<boolean> => {
    const { currentTransaction } = state;
    
    if (!currentTransaction) {
      console.warn('🚫 No current transaction to classify');
      return false;
    }

    try {
      setState(prev => ({ ...prev, isLoading: true }));

      console.log(`🔧 Force classification: ${expenseType} for transaction ${currentTransaction.id}`);

      await expenseClassificationApi.updateTransactionType(
        currentTransaction.id,
        expenseType,
        true // C'est un override manuel explicite
      );

      setState(prev => ({
        ...prev,
        isLoading: false,
        showModal: false,
        pendingClassification: null,
        currentTransaction: null,
        error: null
      }));

      return true;
    } catch (error: any) {
      console.error('❌ Error forcing classification:', error);
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error?.response?.data?.detail || 'Erreur lors de la classification forcée'
      }));

      return false;
    }
  }, [state]);

  /**
   * Réinitialise l'état du hook
   */
  const clearState = useCallback(() => {
    setState({
      isLoading: false,
      error: null,
      pendingClassification: null,
      showModal: false,
      currentTransaction: null
    });
  }, []);

  return {
    state,
    actions: {
      classifyAfterTagUpdate,
      acceptSuggestion,
      rejectSuggestion,
      forceClassification,
      clearState
    }
  };
}

export default useTagClassification;