'use client';

import { useState, useEffect } from 'react';
import { Tx, expenseClassificationApi } from '../../lib/api';
import { ExpenseTypeBadge, PendingClassificationBadge } from './ExpenseTypeBadge';
import { ExpenseTypeModal, ClassificationChoice } from './ExpenseTypeModal';
import { ClassificationModal } from './ClassificationModal';
import { InfoButton } from './InfoButton';
import { CompactConfidenceBadge } from './ConfidenceBadge';
import { CompactToggleSwitch } from '../ui/ToggleSwitch';
import { WebResearchIndicator } from '../ui/WebResearchIndicator';
import { MerchantInfoDisplay } from '../ui/MerchantInfoDisplay';
import { useTagClassification } from '../../hooks/useTagClassification';

interface TransactionRowProps {
  row: Tx;
  importId: string | null;
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
  onExpenseTypeChange?: (id: number, expenseType: 'fixed' | 'variable') => void;
}

export function TransactionRow({ row, importId, onToggle, onSaveTags, onExpenseTypeChange }: TransactionRowProps) {
  const [isLegacyModalOpen, setIsLegacyModalOpen] = useState(false);
  const [isUpdatingExpenseType, setIsUpdatingExpenseType] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  
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

  // Sauvegarde des tags (comportement existant maintenu)
  const handleTagsSave = async (id: number, tagsCSV: string) => {
    // Sauvegarder les tags
    onSaveTags(id, tagsCSV);
    
    // Re-déclencher la classification avec les nouveaux tags si nécessaire
    if (isExpense && tagsCSV.trim() && tagsCSV !== (Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || ""))) {
      console.log(`🏷️ Tags updated for transaction ${id}, re-triggering AI classification...`);
      
      const success = await classificationActions.classifyAfterTagUpdate(row, tagsCSV);
      
      if (success) {
        onExpenseTypeChange?.(row.id, currentExpenseType === 'fixed' ? 'fixed' : 'variable');
      }
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
        onExpenseTypeChange?.(row.id, decision === 'ai_suggestion' 
          ? (classificationState.pendingClassification?.suggested_type || 'variable')
          : decision);
      }
    } catch (error) {
      console.error('Error handling classification decision:', error);
    }
  };

  // Legacy: Toggle manuel pour les cas simples
  const handleExpenseTypeToggle = async (newType: 'fixed' | 'variable') => {
    if (!isExpense || isUpdatingExpenseType) return;
    
    setIsUpdatingExpenseType(true);
    try {
      await expenseClassificationApi.updateTransactionType(row.id, newType, true);
      onExpenseTypeChange?.(row.id, newType);
    } catch (error) {
      console.error('Failed to update expense type:', error);
      // TODO: Show toast error
    } finally {
      setIsUpdatingExpenseType(false);
    }
  };

  // Legacy: Clic sur badge pour modal existante
  const handleBadgeClick = () => {
    if (isExpense && row.expense_type_auto_detected) {
      setIsLegacyModalOpen(true);
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

  // Déterminer la couleur de fond selon le type de dépense
  const getRowBackgroundClass = () => {
    if (isHighlighted) {
      return 'bg-green-50 border-green-200 shadow-sm';
    }
    
    if (isClassifying) {
      return 'bg-blue-50/50 border-blue-200/50 shadow-sm animate-pulse';
    }
    
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
            <input 
              className={`w-full px-2 py-1 border rounded text-sm transition-all duration-300 ${
                isClassifying 
                  ? 'border-blue-300 bg-blue-50/50 ring-1 ring-blue-200 shadow-sm' 
                  : 'border-zinc-200 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 hover:border-zinc-300'
              }`}
              defaultValue={Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "")} 
              onFocus={handleTagsFocus}
              onBlur={e => handleTagsSave(row.id, e.target.value)} 
              placeholder={isExpense ? "Cliquer pour analyser avec l'IA..." : "courses, resto, santé…"}
              disabled={isClassifying}
            />
            {/* Indicateur de classification en cours - protection hydratation */}
            {isMounted && isClassifying && (
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 animate-fade-in">
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
              {row.expense_type_auto_detected ? (
                <ExpenseTypeBadge
                  type={currentExpenseType}
                  size="sm"
                  interactive={true}
                  onClick={handleBadgeClick}
                  confidenceScore={row.expense_type_confidence}
                  autoDetected={true}
                />
              ) : (
                <CompactToggleSwitch
                  value={currentExpenseType}
                  onChange={handleExpenseTypeToggle}
                  disabled={isUpdatingExpenseType}
                />
              )}
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
                  <CompactToggleSwitch
                    value="variable"
                    onChange={handleExpenseTypeToggle}
                    disabled={isUpdatingExpenseType}
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
