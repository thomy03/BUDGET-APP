'use client';

import { useState, useEffect } from 'react';
import { useTagsManagement, TagInfo, TagEditData } from '../../hooks/useTagsManagement';
import { Modal, Button, Input, Alert } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';

interface TagEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  tag?: TagInfo | null;
  isCreating?: boolean;
}

const CATEGORIES = [
  'Alimentation',
  'Transport',
  'Logement',
  'Loisirs',
  'Santé',
  'Shopping',
  'Services',
  'Épargne',
  'Autre'
];

export function TagEditModal({ isOpen, onClose, tag, isCreating = false }: TagEditModalProps) {
  const { createTag, updateTag, addAssociatedLabel, removeAssociatedLabel, isUpdating } = useTagsManagement();
  
  const [formData, setFormData] = useState<TagEditData>({
    name: '',
    expense_type: 'variable',
    associated_labels: [],
    category: undefined
  });
  
  const [newLabelInput, setNewLabelInput] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  // Initialiser le formulaire avec les données du tag
  useEffect(() => {
    if (tag && !isCreating) {
      setFormData({
        name: tag.name,
        expense_type: tag.expense_type,
        associated_labels: [...tag.associated_labels],
        category: tag.category
      });
    } else {
      // Réinitialiser pour un nouveau tag
      setFormData({
        name: '',
        expense_type: 'variable',
        associated_labels: [],
        category: undefined
      });
    }
    setNewLabelInput('');
    setLocalError(null);
  }, [tag, isCreating, isOpen]);

  const handleSave = async () => {
    setLocalError(null);
    
    // Validation
    if (!formData.name.trim()) {
      setLocalError('Le nom du tag est obligatoire');
      return;
    }

    const success = isCreating 
      ? await createTag(formData)
      : await updateTag(tag!.name, formData);

    if (success) {
      onClose();
    }
  };

  const handleAddLabel = () => {
    const trimmedLabel = newLabelInput.trim().toLowerCase();
    if (trimmedLabel && !formData.associated_labels.includes(trimmedLabel)) {
      setFormData({
        ...formData,
        associated_labels: [...formData.associated_labels, trimmedLabel]
      });
      setNewLabelInput('');
    }
  };

  const handleRemoveLabel = (labelToRemove: string) => {
    setFormData({
      ...formData,
      associated_labels: formData.associated_labels.filter(label => label !== labelToRemove)
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddLabel();
    }
  };

  const title = isCreating ? '+ Nouveau tag' : `✏️ Modifier le tag "${tag?.name}"`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="lg"
    >
      <div className="space-y-6">
        {/* Messages d'erreur locaux */}
        {localError && (
          <Alert variant="error">
            {localError}
          </Alert>
        )}

        {/* Nom du tag */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Nom du tag *
          </label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Ex: restaurant, netflix, courses..."
            required
            disabled={isUpdating}
          />
        </div>

        {/* Type de dépense */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Type de dépense *
          </label>
          <div className="flex items-center gap-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="variable"
                checked={formData.expense_type === 'variable'}
                onChange={(e) => setFormData({ ...formData, expense_type: e.target.value as 'fixed' | 'variable' })}
                className="mr-2"
                disabled={isUpdating}
              />
              <ExpenseTypeBadge type="variable" size="sm" />
              <span className="ml-2 text-sm text-gray-600">Montant variable (courses, restaurants, loisirs...)</span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="fixed"
                checked={formData.expense_type === 'fixed'}
                onChange={(e) => setFormData({ ...formData, expense_type: e.target.value as 'fixed' | 'variable' })}
                className="mr-2"
                disabled={isUpdating}
              />
              <ExpenseTypeBadge type="fixed" size="sm" />
              <span className="ml-2 text-sm text-gray-600">Montant fixe (abonnements, loyer, assurances...)</span>
            </label>
          </div>
        </div>

        {/* Libellés associés */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Libellés associés
          </label>
          <p className="text-xs text-gray-500 mb-3">
            Ces libellés permettront de reconnaître automatiquement les transactions associées à ce tag
          </p>
          
          {/* Liste des libellés existants */}
          {formData.associated_labels.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.associated_labels.map((label, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                >
                  <span>{label}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveLabel(label)}
                    className="text-blue-500 hover:text-blue-800 font-bold"
                    disabled={isUpdating}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Ajout de nouveau libellé */}
          <div className="flex items-center gap-2">
            <Input
              value={newLabelInput}
              onChange={(e) => setNewLabelInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="CHEZ PAUL, LE PETIT BISTROT, NETFLIX..."
              disabled={isUpdating}
              className="flex-1"
            />
            <Button
              onClick={handleAddLabel}
              disabled={!newLabelInput.trim() || isUpdating}
              variant="outline"
              size="sm"
            >
              + Ajouter
            </Button>
          </div>
        </div>

        {/* Catégorie */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Catégorie (optionnelle)
          </label>
          <select
            value={formData.category || ''}
            onChange={(e) => setFormData({ ...formData, category: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            disabled={isUpdating}
          >
            <option value="">Choisir une catégorie...</option>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {/* Statistiques (si modification) */}
        {tag && !isCreating && (
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Statistiques actuelles</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Transactions:</span>
                <span className="ml-2 font-medium">{tag.transaction_count}</span>
              </div>
              <div>
                <span className="text-gray-500">Total:</span>
                <span className="ml-2 font-medium">
                  {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                  })}€
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isUpdating}
          >
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={!formData.name.trim() || isUpdating}
          >
            {isUpdating ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                {isCreating ? 'Création...' : 'Sauvegarde...'}
              </div>
            ) : (
              isCreating ? 'Créer le tag' : 'Sauvegarder'
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default TagEditModal;