'use client';

import { useState, useEffect } from 'react';
import { Tx, expenseClassificationApi, mlFeedbackApi } from '../../lib/api';
import { ExpenseTypeBadge, PendingClassificationBadge } from './ExpenseTypeBadge';
import { ExpenseTypeModal, ClassificationChoice } from './ExpenseTypeModal';
import { ClassificationModal } from './ClassificationModal';
import { InfoButton } from './InfoButton';
import { CompactConfidenceBadge } from './ConfidenceBadge';
import { CompactToggleSwitch } from '../ui/ToggleSwitch';
import { WebResearchIndicator } from '../ui/WebResearchIndicator';
import { MerchantInfoDisplay } from '../ui/MerchantInfoDisplay';
import { useTagClassification } from '../../hooks/useTagClassification';
import { Select, useToast, TagsInput } from '../ui';

interface TransactionRowProps {
  row: Tx;
  importId: string | null;
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
  onExpenseTypeChange?: (id: number, expenseType: 'fixed' | 'variable') => void;
  /** Whether this transaction was recently auto-tagged */
  isAutoTagged?: boolean;
  /** Whether this transaction is part of the current auto-tagging batch */
  isBeingAutoTagged?: boolean;
}

export function TransactionRow({ row, importId, onToggle, onSaveTags, onExpenseTypeChange, isAutoTagged = false, isBeingAutoTagged = false }: TransactionRowProps) {
  const [isLegacyModalOpen, setIsLegacyModalOpen] = useState(false);
  const [isUpdatingExpenseType, setIsUpdatingExpenseType] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [tagsValue, setTagsValue] = useState(Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || ""));
  const { addToast } = useToast();
  
  // Intégration du hook de classification intelligente
  const { state: classificationState, actions: classificationActions } = useTagClassification();

  // Protection contre l'hydratation - s'assurer que le composant est monté côté client
  useEffect(() => {
    setIsMounted(true);
  }, []);
  
  const isHighlighted = importId && row.import_id === importId;
  const isExpense = row.amount < 0; // Les dépenses sont négatives
  const currentExpenseType = row.expense_type || (isExpense ? 'variable' : null);
  
  // Nouveau workflow : classification intelligente immédiate au focus
  const handleTagsFocus = async () => {
    if (!isExpense) return;
    
    // Si déjà en cours de classification pour cette transaction, ne pas relancer
    if (classificationState.isLoading && classificationState.currentTransaction?.id === row.id) {
      return;
    }
    
    // Si la transaction a déjà une classification IA en attente, ouvrir directement la modal
    if (classificationState.pendingClassification && classificationState.currentTransaction?.id === row.id) {
      console.log('📋 Opening existing classification modal immediately');
      return;
    }
    
    console.log(`🚀 Auto-triggering AI classification on focus for transaction ${row.id}`);
    
    // Utiliser les tags existants, ou le label comme fallback
    const currentTags = Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "");
    const tagsForClassification = currentTags.trim() || row.label;
    
    const success = await classificationActions.classifyAfterTagUpdate(row, tagsForClassification);
    
    if (!success && classificationState.showModal) {
      console.log('🤔 Auto-classification needs user input, modal opened');
    }
  };

  // Sauvegarde des tags avec feedback API et optimistic update
  const handleTagsSave = async (id: number, tagsCSV: string) => {
    const oldTags = Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "");
    
    // Optimistic update
    setTagsValue(tagsCSV);
    
    try {
      // Sauvegarder les tags
      onSaveTags(id, tagsCSV);
      
      // Envoyer feedback ML si les tags ont changé
      if (tagsCSV.trim() !== oldTags.trim()) {
        await mlFeedbackApi.sendTagFeedback(id, oldTags, tagsCSV);
        
        addToast({
          message: "Tags mis à jour avec succès",
          type: "success",
          duration: 2000
        });
      }
      
      // Re-déclencher la classification avec les nouveaux tags si nécessaire
      if (isExpense && tagsCSV.trim() && tagsCSV !== oldTags) {
        console.log(`🏷️ Tags updated for transaction ${id}, re-triggering AI classification...`);
        
        const success = await classificationActions.classifyAfterTagUpdate(row, tagsCSV);
        
        if (success) {
          onExpenseTypeChange?.(row.id, currentExpenseType === 'fixed' ? 'fixed' : 'variable');
        }
      }
    } catch (error) {
      // Rollback optimistic update
      setTagsValue(oldTags);
      addToast({
        message: "Erreur lors de la mise à jour des tags",
        type: "error",
        duration: 3000
      });
      console.error('Failed to update tags:', error);
    }
  };

  // Gestion des décisions de classification
  const handleClassificationDecision = async (decision: 'fixed' | 'variable' | 'ai_suggestion') => {
    try {
      let success = false;
      
      if (decision === 'ai_suggestion') {
        success = await classificationActions.acceptSuggestion(true);
      } else {
        success = await classificationActions.forceClassification(decision);
      }
      
      if (success) {
        const normalizedType = decision === 'ai_suggestion' 
          ? (classificationState.pendingClassification?.suggested_type?.toLowerCase() === 'fixed' ? 'fixed' : 'variable')
          : (decision?.toLowerCase() === 'fixed' ? 'fixed' : 'variable');
        
        onExpenseTypeChange?.(row.id, normalizedType);
      }
    } catch (error) {
      console.error('Error handling classification decision:', error);
    }
  };

  // Toggle manuel pour les cas simples avec feedback API
  const handleExpenseTypeToggle = async (newType: 'fixed' | 'variable') => {
    if (!isExpense || isUpdatingExpenseType) return;
    
    const oldType = currentExpenseType;
    setIsUpdatingExpenseType(true);
    
    try {
      await expenseClassificationApi.updateTransactionType(row.id, newType, true);
      
      // Envoyer feedback ML pour le changement de type
      await mlFeedbackApi.sendExpenseTypeFeedback(row.id, oldType, newType);
      
      onExpenseTypeChange?.(row.id, newType);
      
      addToast({
        message: `Type de dépense changé en ${newType === 'fixed' ? 'FIXE' : 'VARIABLE'}`,
        type: "success",
        duration: 2000
      });
    } catch (error) {
      console.error('Failed to update expense type:', error);
      addToast({
        message: "Erreur lors de la mise à jour du type de dépense",
        type: "error",
        duration: 3000
      });
    } finally {
      setIsUpdatingExpenseType(false);
    }
  };

  // Legacy: Clic sur badge pour modal existante ou toggle direct
  const handleBadgeClick = async () => {
    if (isExpense) {
      if (row.expense_type_auto_detected) {
        // Si auto-détecté, ouvrir la modal de confirmation
        setIsLegacyModalOpen(true);
      } else {
        // Sinon, toggle direct entre fixed/variable
        const newType = currentExpenseType === 'fixed' ? 'variable' : 'fixed';
        await handleExpenseTypeToggle(newType);
      }
    }
  };

  // Legacy: Confirmation modal existante
  const handleLegacyModalConfirm = (choice: ClassificationChoice, type?: 'fixed' | 'variable') => {
    if (choice === 'ai_suggestion' && type) {
      handleExpenseTypeToggle(type);
    } else if (choice !== 'ai_suggestion') {
      handleExpenseTypeToggle(choice);
    }
  };

  // Nouveau: Classification à la demande via le bouton d'information
  const handleTriggerClassification = async () => {
    if (!isExpense) return;
    
    console.log(`🔍 Manual AI classification triggered for transaction ${row.id}`);
    
    // Si la transaction a déjà une classification IA en attente, ouvrir directement la modal
    if (classificationState.pendingClassification && classificationState.currentTransaction?.id === row.id) {
      console.log('📋 Opening existing classification modal');
      classificationActions.clearState();
      // Recréer l'état pour forcer l'ouverture de la modal
      setTimeout(() => {
        // Cette logique sera gérée par l'état existant
      }, 100);
      return;
    }
    
    // Déclencher une nouvelle classification pour cette transaction
    const currentTags = Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "");
    
    if (!currentTags.trim()) {
      console.log('⚠️ No tags available for classification, using label as fallback');
      // Utiliser le label comme tag temporaire pour la classification
      const success = await classificationActions.classifyAfterTagUpdate(row, row.label);
      
      if (!success && classificationState.showModal) {
        console.log('🤔 Manual classification needs user input');
      }
    } else {
      // Refaire la classification avec les tags existants
      const success = await classificationActions.classifyAfterTagUpdate(row, currentTags);
      
      if (!success && classificationState.showModal) {
        console.log('🤔 Re-classification needs user input');
      }
    }
  };
  
  // État de classification en cours pour animations
  const isClassifying = classificationState.isLoading && classificationState.currentTransaction?.id === row.id;

  // Déterminer la couleur de fond selon le type de dépense et l'état d'auto-tagging
  const getRowBackgroundClass = () => {
    // Priorité 1: Transaction en cours de traitement par auto-tagging
    if (isBeingAutoTagged) {
      return 'bg-indigo-50/60 border-indigo-200/60 shadow-sm animate-pulse ring-1 ring-indigo-200/50';
    }
    
    // Priorité 2: Transaction récemment auto-tagged
    if (isAutoTagged) {
      return 'bg-gradient-to-r from-purple-50/80 to-indigo-50/80 border-purple-200/60 shadow-md ring-1 ring-purple-200/50 hover:shadow-lg transition-all duration-300';
    }
    
    // Priorité 3: Transaction highlighted (import récent)
    if (isHighlighted) {
      return 'bg-green-50 border-green-200 shadow-sm';
    }
    
    // Priorité 4: Classification en cours (IA individuelle)
    if (isClassifying) {
      return 'bg-blue-50/50 border-blue-200/50 shadow-sm animate-pulse';
    }
    
    // Priorité 5: Classification par type de dépense
    if (isExpense && currentExpenseType) {
      if (currentExpenseType === 'fixed') {
        return 'bg-emerald-50/30 hover:bg-emerald-50 border-emerald-200/50 hover:shadow-sm';
      } else {
        return 'bg-orange-50/30 hover:bg-orange-50 border-orange-200/50 hover:shadow-sm';
      }
    }
    
    return 'hover:bg-zinc-50';
  };

  return (
    <>
      <tr 
        className={`border-t border-zinc-100 transition-all duration-300 ease-in-out ${getRowBackgroundClass()}`}
      >
        <td className="p-3">{row.date_op}</td>
        <td className="p-3">
          <div className="flex items-center gap-2">
            {row.label}
            {isHighlighted && (
              <span className="px-2 py-1 text-xs bg-green-200 text-green-800 rounded-full">
                Nouveau
              </span>
            )}
          </div>
        </td>
        <td className="p-3">
          <span className="text-xs bg-zinc-100 px-2 py-1 rounded-full">
            {row.category}
          </span>
        </td>
        <td className="p-3 text-right font-mono">
          <span className={row.amount < 0 ? "text-red-600" : "text-green-600"}>
            {row.amount < 0 ? "-" : "+"}{Math.abs(row.amount).toFixed(2)} €
          </span>
        </td>
        <td className="p-3 text-center">
          <input 
            type="checkbox" 
            checked={row.exclude} 
            onChange={e => onToggle(row.id, e.target.checked)}
            className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
          />
        </td>
        <td className="p-3">
          <div className="relative">
            <TagsInput
              value={tagsValue}
              onChange={setTagsValue}
              onFocus={handleTagsFocus}
              onBlur={(value) => handleTagsSave(row.id, value)}
              placeholder={isExpense ? "Cliquer pour analyser avec l'IA..." : "courses, resto, santé…"}
              disabled={isClassifying}
              isClassifying={isClassifying}
            />
            
            {/* Indicateur de classification en cours - protection hydratation */}
            {isMounted && isClassifying && (
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 animate-fade-in z-10">
                <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent shadow-sm"></div>
              </div>
            )}
            
            {/* Indicateur de recherche web - protection hydratation */}
            {isMounted && (
              <WebResearchIndicator
                isSearching={classificationState.isLoading && classificationState.currentTransaction?.id === row.id}
                merchantName={row.label}
                onCancel={() => classificationActions.clearState()}
                confidence={classificationState.pendingClassification?.confidence_score}
                result={classificationState.pendingClassification ? {
                  name: row.label, // Utiliser le label de la transaction
                  category: row.category, // Utiliser la catégorie de la transaction
                  type: classificationState.pendingClassification.suggested_type,
                  source: classificationState.pendingClassification.reasoning ? 'Classification IA' : undefined
                } : undefined}
              />
            )}
          </div>
        </td>
        <td className="p-3">
          {isExpense && currentExpenseType ? (
            <div className="flex items-center gap-2">
              <Select
                options={[
                  { value: 'variable', label: 'VARIABLE' },
                  { value: 'fixed', label: 'FIXE' }
                ]}
                value={currentExpenseType}
                onChange={(value) => handleExpenseTypeToggle(value as 'fixed' | 'variable')}
                variant="compact"
                size="sm"
                disabled={isUpdatingExpenseType}
                className="min-w-[90px] text-xs font-medium"
              />
              {isUpdatingExpenseType && (
                <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
              )}
              {/* Bouton d'information IA - protection hydratation */}
              {isMounted && (
                <InfoButton
                  transaction={row}
                  isClassifying={classificationState.isLoading && classificationState.currentTransaction?.id === row.id}
                  onTriggerClassification={handleTriggerClassification}
                  hasPendingClassification={
                    classificationState.showModal && 
                    classificationState.pendingClassification !== null &&
                    classificationState.currentTransaction?.id === row.id
                  }
                  confidenceScore={row.expense_type_confidence}
                  isAutoDetected={row.expense_type_auto_detected || false}
                />
              )}
            </div>
          ) : isExpense ? (
            <div className="flex items-center gap-2">
              {/* Afficher badge "À classifier" ou "Suggestion IA" pour les dépenses non classifiées */}
              {isMounted && classificationState.showModal && 
               classificationState.pendingClassification &&
               classificationState.currentTransaction?.id === row.id ? (
                <PendingClassificationBadge
                  size="sm"
                  interactive={true}
                  onClick={handleTriggerClassification}
                  hasAISuggestion={true}
                />
              ) : (
                <>
                  <Select
                    options={[
                      { value: 'variable', label: 'VARIABLE' },
                      { value: 'fixed', label: 'FIXE' }
                    ]}
                    value="variable"
                    onChange={(value) => handleExpenseTypeToggle(value as 'fixed' | 'variable')}
                    variant="compact"
                    size="sm"
                    disabled={isUpdatingExpenseType}
                    className="min-w-[90px] text-xs font-medium"
                    placeholder="Choisir..."
                  />
                  <PendingClassificationBadge
                    size="sm"
                    interactive={true}
                    onClick={handleTriggerClassification}
                    hasAISuggestion={false}
                  />
                </>
              )}
              
              {/* Bouton d'information IA pour transactions non classifiées - protection hydratation */}
              {isMounted && (
                <InfoButton
                  transaction={row}
                  isClassifying={classificationState.isLoading && classificationState.currentTransaction?.id === row.id}
                  onTriggerClassification={handleTriggerClassification}
                  hasPendingClassification={
                    classificationState.showModal && 
                    classificationState.pendingClassification !== null &&
                    classificationState.currentTransaction?.id === row.id
                  }
                />
              )}
            </div>
          ) : (
            <span className="text-xs text-gray-400">Revenus</span>
          )}
        </td>
        <td className="p-3 text-center">
          <CompactConfidenceBadge
            confidence={row.expense_type_confidence}
            isAutoDetected={row.expense_type_auto_detected}
            isLoading={classificationState.isLoading && classificationState.currentTransaction?.id === row.id}
            showProgressBar={true}
          />
        </td>
      </tr>

      {/* Modal intelligente de classification (nouveau workflow) - protection hydratation */}
      {isMounted && 
       classificationState.showModal && 
       classificationState.pendingClassification && 
       classificationState.currentTransaction?.id === row.id && (
        <ClassificationModal
          isOpen={classificationState.showModal}
          onClose={() => classificationActions.rejectSuggestion()}
          onDecision={handleClassificationDecision}
          tagName={Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "nouveau tag")}
          classification={classificationState.pendingClassification}
        />
      )}

      {/* Modal legacy pour les cas de classification déjà faite - protection hydratation */}
      {isMounted && isLegacyModalOpen && row.expense_type_auto_detected && (
        <ExpenseTypeModal
          isOpen={isLegacyModalOpen}
          onClose={() => setIsLegacyModalOpen(false)}
          onConfirm={handleLegacyModalConfirm}
          transactionLabel={row.label}
          suggestedType={currentExpenseType || 'variable'}
          confidence={row.expense_type_confidence || 0.5}
        />
      )}
      
      {/* Affichage des erreurs de classification - protection hydratation */}
      {isMounted && classificationState.error && classificationState.currentTransaction?.id === row.id && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded max-w-sm z-50">
          <div className="flex items-center">
            <span className="text-sm">⚠️ {classificationState.error}</span>
            <button 
              onClick={() => classificationActions.clearState()}
              className="ml-2 text-red-600 hover:text-red-800"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </>
  );
}
