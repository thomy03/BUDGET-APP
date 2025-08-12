'use client';

import { useState, useEffect } from 'react';
import { Tx, expenseClassificationApi } from '../../lib/api';
import { ExpenseTypeBadge } from './ExpenseTypeBadge';
import { ExpenseTypeModal, ClassificationChoice } from './ExpenseTypeModal';
import { ClassificationModal } from './ClassificationModal';
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
  
  // Nouveau workflow : classification intelligente après saisie de tags
  const handleTagsSave = async (id: number, tagsCSV: string) => {
    // D'abord, sauvegarder les tags (comportement existant)
    onSaveTags(id, tagsCSV);
    
    // Ensuite, déclencher la classification intelligente si c'est une dépense
    if (isExpense && tagsCSV.trim()) {
      console.log(`🏷️ Tags saved for transaction ${id}, triggering AI classification...`);
      
      const success = await classificationActions.classifyAfterTagUpdate(row, tagsCSV);
      
      if (!success && classificationState.showModal) {
        console.log('🤔 Low confidence classification, showing modal for user decision');
      }
      
      // Notifier le parent du changement si la classification a réussi
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
  
  return (
    <>
      <tr 
        className={`border-t border-zinc-100 hover:bg-zinc-50 transition-colors ${
          isHighlighted ? 'bg-green-50 border-green-200' : ''
        }`}
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
              className="w-full px-2 py-1 border border-zinc-200 rounded text-sm focus:ring-1 focus:ring-zinc-900 focus:border-transparent" 
              defaultValue={Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "")} 
              onBlur={e => handleTagsSave(row.id, e.target.value)} 
              placeholder="courses, resto, santé…" 
            />
            {/* Indicateur de classification en cours - protection hydratation */}
            {isMounted && classificationState.isLoading && classificationState.currentTransaction?.id === row.id && (
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                <div className="w-3 h-3 animate-spin rounded-full border border-blue-600 border-t-transparent"></div>
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
                  name: classificationState.pendingClassification.merchant_name || row.label,
                  category: classificationState.pendingClassification.merchant_category || 'Non défini',
                  type: classificationState.pendingClassification.suggested_type,
                  source: classificationState.pendingClassification.reasoning ? 'Recherche web' : undefined
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
            </div>
          ) : isExpense ? (
            <CompactToggleSwitch
              value="variable"
              onChange={handleExpenseTypeToggle}
              disabled={isUpdatingExpenseType}
            />
          ) : (
            <span className="text-xs text-gray-400">Revenus</span>
          )}
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
