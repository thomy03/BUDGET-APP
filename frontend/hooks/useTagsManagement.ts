'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

export type TagInfo = {
  name: string;
  expense_type: 'fixed' | 'variable';
  transaction_count: number;
  total_amount: number;
  associated_labels: string[];
  category?: string;
  created_at?: string;
  updated_at?: string;
};

export type TagEditData = {
  name: string;
  expense_type: 'fixed' | 'variable';
  associated_labels: string[];
  category?: string;
};

export function useTagsManagement() {
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  // Charger tous les tags avec leurs statistiques
  const loadTags = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fallback gracieux : essayer plusieurs endpoints
      let tags: TagInfo[] = [];
      
      try {
        // Tentative avec l'endpoint préféré
        const response = await api.get<{
          tags: TagInfo[]
        }>('/tags/stats');
        tags = response.data.tags || [];
      } catch (statsError: any) {
        console.warn('Tags stats endpoint unavailable:', statsError);
        
        try {
          // Fallback sur l'endpoint tags-summary
          const summaryResponse = await api.get('/tags-summary');
          const summaryData = summaryResponse.data;
          
          // Convertir en format TagInfo
          if (summaryData.tags && typeof summaryData.tags === 'object') {
            tags = Object.entries(summaryData.tags).map(([name, count]) => ({
              name,
              expense_type: 'variable' as const,
              transaction_count: Number(count) || 0,
              total_amount: 0,
              associated_labels: [name.toLowerCase()]
            }));
          }
        } catch (summaryError: any) {
          console.warn('Tags summary endpoint unavailable:', summaryError);
          
          try {
            // Fallback ultime : liste simple des tags
            const basicResponse = await api.get<string[]>('/tags');
            tags = basicResponse.data.map((name: string) => ({
              name,
              expense_type: 'variable' as const,
              transaction_count: 0,
              total_amount: 0,
              associated_labels: [name.toLowerCase()]
            }));
          } catch (basicError: any) {
            // Si tout échoue, utiliser des données par défaut
            console.warn('All tags endpoints unavailable, using defaults');
            tags = [
              {
                name: 'Alimentaire',
                expense_type: 'variable' as const,
                transaction_count: 0,
                total_amount: 0,
                associated_labels: ['alimentaire', 'courses', 'supermarché']
              },
              {
                name: 'Transport',
                expense_type: 'variable' as const,
                transaction_count: 0,
                total_amount: 0,
                associated_labels: ['transport', 'essence', 'bus']
              },
              {
                name: 'Logement',
                expense_type: 'fixed' as const,
                transaction_count: 0,
                total_amount: 0,
                associated_labels: ['loyer', 'charges', 'électricité']
              }
            ];
            setError('API indisponible - Données par défaut affichées');
          }
        }
      }
      
      setTags(tags);
    } catch (err: any) {
      console.error('Critical error loading tags:', err);
      setError('Erreur critique lors du chargement des tags');
      
      // Toujours afficher quelque chose à l'utilisateur
      setTags([{
        name: 'Données indisponibles',
        expense_type: 'variable' as const,
        transaction_count: 0,
        total_amount: 0,
        associated_labels: []
      }]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Mettre à jour un tag
  const updateTag = useCallback(async (originalName: string, tagData: TagEditData) => {
    try {
      setIsUpdating(true);
      setError(null);

      await api.put(`/tags/${encodeURIComponent(originalName)}`, tagData);
      
      // Recharger les tags après mise à jour
      await loadTags();
      
      return true;
    } catch (err: any) {
      console.error('Failed to update tag:', err);
      setError(err.response?.data?.detail || 'Erreur lors de la mise à jour du tag');
      return false;
    } finally {
      setIsUpdating(false);
    }
  }, [loadTags]);

  // Supprimer un tag
  const deleteTag = useCallback(async (tagName: string) => {
    try {
      setIsUpdating(true);
      setError(null);

      await api.delete(`/tags/${encodeURIComponent(tagName)}`);
      
      // Recharger les tags après suppression
      await loadTags();
      
      return true;
    } catch (err: any) {
      console.error('Failed to delete tag:', err);
      setError(err.response?.data?.detail || 'Erreur lors de la suppression du tag');
      return false;
    } finally {
      setIsUpdating(false);
    }
  }, [loadTags]);

  // Créer un nouveau tag
  const createTag = useCallback(async (tagData: TagEditData) => {
    try {
      setIsUpdating(true);
      setError(null);

      await api.post('/tags', tagData);
      
      // Recharger les tags après création
      await loadTags();
      
      return true;
    } catch (err: any) {
      console.error('Failed to create tag:', err);
      setError(err.response?.data?.detail || 'Erreur lors de la création du tag');
      return false;
    } finally {
      setIsUpdating(false);
    }
  }, [loadTags]);

  // Basculer le type d'un tag (fixe ↔ variable)
  const toggleExpenseType = useCallback(async (tagName: string, currentType: 'fixed' | 'variable') => {
    const tag = tags.find(t => t.name === tagName);
    if (!tag) return false;

    return await updateTag(tagName, {
      name: tagName,
      expense_type: currentType === 'fixed' ? 'variable' : 'fixed',
      associated_labels: tag.associated_labels,
      category: tag.category
    });
  }, [tags, updateTag]);

  // Ajouter un libellé associé à un tag
  const addAssociatedLabel = useCallback(async (tagName: string, label: string) => {
    const tag = tags.find(t => t.name === tagName);
    if (!tag) return false;

    const newLabels = [...tag.associated_labels];
    if (!newLabels.includes(label.toLowerCase())) {
      newLabels.push(label.toLowerCase());
    }

    return await updateTag(tagName, {
      name: tagName,
      expense_type: tag.expense_type,
      associated_labels: newLabels,
      category: tag.category
    });
  }, [tags, updateTag]);

  // Supprimer un libellé associé d'un tag
  const removeAssociatedLabel = useCallback(async (tagName: string, labelToRemove: string) => {
    const tag = tags.find(t => t.name === tagName);
    if (!tag) return false;

    const newLabels = tag.associated_labels.filter(label => 
      label.toLowerCase() !== labelToRemove.toLowerCase()
    );

    return await updateTag(tagName, {
      name: tagName,
      expense_type: tag.expense_type,
      associated_labels: newLabels,
      category: tag.category
    });
  }, [tags, updateTag]);

  // Charger les tags au montage
  useEffect(() => {
    loadTags();
  }, [loadTags]);

  return {
    tags,
    isLoading,
    error,
    isUpdating,
    loadTags,
    updateTag,
    deleteTag,
    createTag,
    toggleExpenseType,
    addAssociatedLabel,
    removeAssociatedLabel,
    clearError: () => setError(null)
  };
}