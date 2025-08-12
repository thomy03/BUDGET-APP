'use client';

import { useState } from 'react';
import { useTagsManagement, TagInfo } from '../../hooks/useTagsManagement';
import { Card, Button, Modal, Alert } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { TagEditModal } from './TagEditModal';

export function TagsManagement() {
  const {
    tags,
    isLoading,
    error,
    isUpdating,
    toggleExpenseType,
    deleteTag,
    clearError,
    loadTags
  } = useTagsManagement();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingTag, setEditingTag] = useState<TagInfo | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const handleEditTag = (tag: TagInfo) => {
    setEditingTag(tag);
    setIsCreating(false);
    setIsEditModalOpen(true);
  };

  const handleCreateTag = () => {
    setEditingTag(null);
    setIsCreating(true);
    setIsEditModalOpen(true);
  };

  const handleDeleteTag = async (tagName: string, transactionCount: number) => {
    const message = transactionCount > 0 
      ? `Êtes-vous sûr de vouloir supprimer le tag "${tagName}" ? Cette action affectera ${transactionCount} transaction(s).`
      : `Êtes-vous sûr de vouloir supprimer le tag "${tagName}" ?`;

    if (window.confirm(message)) {
      await deleteTag(tagName);
    }
  };

  const handleToggleType = async (tagName: string, currentType: 'fixed' | 'variable') => {
    await toggleExpenseType(tagName, currentType);
  };

  if (isLoading) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Chargement des tags...</span>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              🏷️ Gestion des Tags
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Gérez vos tags et leur classification automatique (Fixe/Variable)
            </p>
          </div>
          <Button onClick={handleCreateTag} className="flex items-center gap-2">
            <span>+</span>
            Nouveau tag
          </Button>
        </div>

        {/* Messages d'erreur et d'état */}
        {error && (
          <Alert variant={error.includes('par défaut') ? 'warning' : 'error'} className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {error.includes('API indisponible') && (
                  <span className="text-amber-600">⚠️</span>
                )}
                <span>{error}</span>
                {error.includes('par défaut') && (
                  <button
                    onClick={loadTags}
                    className="ml-3 px-2 py-1 text-xs bg-amber-100 text-amber-700 rounded hover:bg-amber-200 transition-colors"
                  >
                    Réessayer
                  </button>
                )}
              </div>
              <button
                onClick={clearError}
                className={error.includes('par défaut') ? 'text-amber-800 hover:text-amber-900' : 'text-red-800 hover:text-red-900'}
              >
                ×
              </button>
            </div>
          </Alert>
        )}

        {tags.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🏷️</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucun tag trouvé
            </h3>
            <p className="text-gray-600 mb-4">
              Créez votre premier tag pour organiser vos transactions.
            </p>
            <Button onClick={handleCreateTag}>
              Créer le premier tag
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-sm text-gray-600 mb-4">
              Tags actifs ({tags.length})
            </div>

            {tags.map((tag) => (
              <div
                key={tag.name}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg bg-white hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-4 flex-1">
                  {/* Nom du tag */}
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {tag.name}
                    </span>
                    <ExpenseTypeBadge
                      type={tag.expense_type}
                      size="sm"
                    />
                  </div>

                  {/* Statistiques */}
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span>{tag.transaction_count} transaction{tag.transaction_count > 1 ? 's' : ''}</span>
                    {tag.total_amount !== 0 && (
                      <span>
                        {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        })}€
                      </span>
                    )}
                  </div>

                  {/* Libellés associés (preview) */}
                  {tag.associated_labels.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Libellés:</span>
                      <div className="flex gap-1">
                        {tag.associated_labels.slice(0, 2).map((label, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs"
                          >
                            {label}
                          </span>
                        ))}
                        {tag.associated_labels.length > 2 && (
                          <span className="text-xs text-gray-500">
                            +{tag.associated_labels.length - 2}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {/* Toggle Type */}
                  <button
                    onClick={() => handleToggleType(tag.name, tag.expense_type)}
                    disabled={isUpdating}
                    className={`
                      px-3 py-1 text-xs rounded-full transition-colors border
                      ${tag.expense_type === 'fixed' 
                        ? 'border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100' 
                        : 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100'
                      }
                      ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                    title={`Basculer vers ${tag.expense_type === 'fixed' ? 'Variable' : 'Fixe'}`}
                  >
                    → {tag.expense_type === 'fixed' ? 'Var' : 'Fix'}
                  </button>

                  {/* Edit */}
                  <button
                    onClick={() => handleEditTag(tag)}
                    disabled={isUpdating}
                    className="p-2 text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50"
                    title="Modifier"
                  >
                    ✏️
                  </button>

                  {/* Delete */}
                  <button
                    onClick={() => handleDeleteTag(tag.name, tag.transaction_count)}
                    disabled={isUpdating}
                    className="p-2 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                    title="Supprimer"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Modal d'édition */}
      <TagEditModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingTag(null);
          setIsCreating(false);
        }}
        tag={editingTag}
        isCreating={isCreating}
      />
    </>
  );
}

export default TagsManagement;