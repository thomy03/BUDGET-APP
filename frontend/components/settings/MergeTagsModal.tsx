'use client';

import { useState, useMemo } from 'react';
import { tagsApi, MergeTagsRequest, MergeTagsResponse, TagOut } from '../../lib/api';
import { Button } from '../ui';
import { XMarkIcon, ArrowsRightLeftIcon, CheckIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface MergeTagsModalProps {
  isOpen: boolean;
  onClose: () => void;
  tags: TagOut[];
  onMergeComplete: () => void;
}

export function MergeTagsModal({ isOpen, onClose, tags, onMergeComplete }: MergeTagsModalProps) {
  const [selectedSourceTags, setSelectedSourceTags] = useState<Set<string>>(new Set());
  const [targetTag, setTargetTag] = useState<string>('');
  const [createNewTag, setCreateNewTag] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [deleteSourceTags, setDeleteSourceTags] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MergeTagsResponse | null>(null);

  // Tags triés par nombre de transactions (plus utilisés en premier)
  const sortedTags = useMemo(() => {
    return [...tags].sort((a, b) => b.transaction_count - a.transaction_count);
  }, [tags]);

  // Calcul du nombre de transactions qui seront affectées
  const affectedTransactions = useMemo(() => {
    let count = 0;
    selectedSourceTags.forEach(tagName => {
      const tag = tags.find(t => t.name === tagName);
      if (tag) count += tag.transaction_count;
    });
    return count;
  }, [selectedSourceTags, tags]);

  const toggleSourceTag = (tagName: string) => {
    const newSet = new Set(selectedSourceTags);
    if (newSet.has(tagName)) {
      newSet.delete(tagName);
    } else {
      newSet.add(tagName);
    }
    setSelectedSourceTags(newSet);
    // Si on sélectionne un tag qui était la cible, le retirer de la cible
    if (targetTag === tagName) {
      setTargetTag('');
    }
  };

  const handleMerge = async () => {
    const finalTargetTag = createNewTag ? newTagName.trim() : targetTag;

    if (selectedSourceTags.size === 0) {
      setError('Sélectionnez au moins un tag source');
      return;
    }
    if (!finalTargetTag) {
      setError('Sélectionnez ou créez un tag cible');
      return;
    }
    if (selectedSourceTags.has(finalTargetTag)) {
      setError('Le tag cible ne peut pas être dans les tags sources');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: MergeTagsRequest = {
        source_tags: Array.from(selectedSourceTags),
        target_tag: finalTargetTag,
        delete_source_tags: deleteSourceTags
      };

      const response = await tagsApi.merge(request);
      setResult(response);

      // Notifier le parent pour rafraîchir
      setTimeout(() => {
        onMergeComplete();
        handleClose();
      }, 2000);
    } catch (err: any) {
      console.error('Merge error:', err);
      setError(err.response?.data?.detail || err.message || 'Erreur lors de la fusion');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSelectedSourceTags(new Set());
    setTargetTag('');
    setCreateNewTag(false);
    setNewTagName('');
    setDeleteSourceTags(true);
    setError(null);
    setResult(null);
    onClose();
  };

  if (!isOpen) return null;

  // Vue de succès
  if (result) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full p-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckIcon className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              Fusion réussie
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              {result.transactions_updated} transactions mises à jour
            </p>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 text-left">
              <p className="text-sm text-gray-600 dark:text-gray-300">
                <span className="font-medium">Tags fusionnés :</span>{' '}
                {result.merged_tags.join(', ')}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                <span className="font-medium">Vers :</span>{' '}
                <span className="text-blue-600 dark:text-blue-400">{result.target_tag}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-600 to-purple-600">
          <div className="flex items-center gap-3">
            <ArrowsRightLeftIcon className="w-6 h-6 text-white" />
            <div>
              <h2 className="text-lg font-bold text-white">Fusionner des Tags</h2>
              <p className="text-sm text-indigo-100">Combiner plusieurs tags en un seul</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 flex items-start gap-2">
              <ExclamationTriangleIcon className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {/* Section 1: Sélection des tags sources */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              1. Sélectionnez les tags à fusionner
            </h3>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 max-h-48 overflow-y-auto">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {sortedTags.map(tag => (
                  <button
                    key={tag.name}
                    onClick={() => toggleSourceTag(tag.name)}
                    disabled={targetTag === tag.name}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedSourceTags.has(tag.name)
                        ? 'bg-indigo-100 dark:bg-indigo-900/30 border-2 border-indigo-500 text-indigo-800 dark:text-indigo-200'
                        : targetTag === tag.name
                        ? 'bg-gray-200 dark:bg-gray-600 text-gray-400 cursor-not-allowed'
                        : 'bg-white dark:bg-gray-600 border border-gray-200 dark:border-gray-500 hover:border-indigo-300 text-gray-700 dark:text-gray-200'
                    }`}
                  >
                    <span className="truncate">{tag.name}</span>
                    <span className="text-xs text-gray-400 ml-1">({tag.transaction_count})</span>
                  </button>
                ))}
              </div>
            </div>
            {selectedSourceTags.size > 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                {selectedSourceTags.size} tag(s) sélectionné(s) - {affectedTransactions} transactions
              </p>
            )}
          </div>

          {/* Section 2: Choix du tag cible */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              2. Choisissez le tag de destination
            </h3>

            <div className="space-y-3">
              {/* Option: Tag existant */}
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  id="existing-tag"
                  checked={!createNewTag}
                  onChange={() => setCreateNewTag(false)}
                  className="w-4 h-4 text-indigo-600"
                />
                <label htmlFor="existing-tag" className="text-sm text-gray-700 dark:text-gray-300">
                  Fusionner vers un tag existant
                </label>
              </div>

              {!createNewTag && (
                <select
                  value={targetTag}
                  onChange={(e) => setTargetTag(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Sélectionner un tag --</option>
                  {sortedTags
                    .filter(t => !selectedSourceTags.has(t.name))
                    .map(tag => (
                      <option key={tag.name} value={tag.name}>
                        {tag.name} ({tag.transaction_count} transactions)
                      </option>
                    ))}
                </select>
              )}

              {/* Option: Nouveau tag */}
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  id="new-tag"
                  checked={createNewTag}
                  onChange={() => setCreateNewTag(true)}
                  className="w-4 h-4 text-indigo-600"
                />
                <label htmlFor="new-tag" className="text-sm text-gray-700 dark:text-gray-300">
                  Créer un nouveau tag
                </label>
              </div>

              {createNewTag && (
                <input
                  type="text"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  placeholder="Nom du nouveau tag..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
                />
              )}
            </div>
          </div>

          {/* Section 3: Options */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              3. Options
            </h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={deleteSourceTags}
                onChange={(e) => setDeleteSourceTags(e.target.checked)}
                className="w-4 h-4 text-indigo-600 rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Supprimer les tags sources après la fusion
              </span>
            </label>
          </div>

          {/* Preview */}
          {selectedSourceTags.size > 0 && (createNewTag ? newTagName.trim() : targetTag) && (
            <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4 border border-indigo-200 dark:border-indigo-800">
              <h4 className="text-sm font-semibold text-indigo-800 dark:text-indigo-200 mb-2">
                Aperçu de la fusion
              </h4>
              <div className="flex items-center gap-2 flex-wrap text-sm">
                {Array.from(selectedSourceTags).map((tag, index) => (
                  <span key={tag}>
                    <span className="px-2 py-1 bg-gray-200 dark:bg-gray-600 rounded text-gray-700 dark:text-gray-300">
                      {tag}
                    </span>
                    {index < selectedSourceTags.size - 1 && <span className="mx-1">+</span>}
                  </span>
                ))}
                <span className="mx-2">=</span>
                <span className="px-2 py-1 bg-indigo-200 dark:bg-indigo-800 rounded text-indigo-800 dark:text-indigo-200 font-medium">
                  {createNewTag ? newTagName.trim() : targetTag}
                </span>
              </div>
              <p className="text-xs text-indigo-600 dark:text-indigo-300 mt-2">
                {affectedTransactions} transactions seront mises à jour
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Annuler
          </Button>
          <Button
            onClick={handleMerge}
            disabled={loading || selectedSourceTags.size === 0 || !(createNewTag ? newTagName.trim() : targetTag)}
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            {loading ? (
              <>
                <span className="animate-spin mr-2">...</span>
                Fusion en cours...
              </>
            ) : (
              <>
                <ArrowsRightLeftIcon className="w-4 h-4 mr-2" />
                Fusionner {selectedSourceTags.size} tag(s)
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default MergeTagsModal;
