'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Button } from '../ui';

export interface Category {
  id: string;
  name: string;
  color: string;
  icon: string;
  tagCount?: number;
}

// Couleurs disponibles
const CATEGORY_COLORS = [
  { value: '#3B82F6', name: 'Bleu' },
  { value: '#10B981', name: 'Vert' },
  { value: '#F59E0B', name: 'Orange' },
  { value: '#EF4444', name: 'Rouge' },
  { value: '#8B5CF6', name: 'Violet' },
  { value: '#EC4899', name: 'Rose' },
  { value: '#06B6D4', name: 'Cyan' },
  { value: '#84CC16', name: 'Lime' },
  { value: '#F97316', name: 'Orange vif' },
  { value: '#6366F1', name: 'Indigo' },
  { value: '#14B8A6', name: 'Teal' },
  { value: '#A855F7', name: 'Pourpre' },
];

// Icônes disponibles
const CATEGORY_ICONS = [
  '🛒', '🍔', '🚗', '🏠', '💡', '📱', '💳', '🎮', '🎬', '✈️',
  '🏥', '👕', '📚', '🎁', '💰', '🏦', '🔧', '🎨', '🏋️', '🌿',
  '☕', '🍕', '🚌', '⛽', '💊', '🐕', '👶', '🎓', '💼', '🏪'
];

// Catégories par défaut
const DEFAULT_CATEGORIES: Category[] = [
  { id: 'alimentation', name: 'Alimentation', color: '#10B981', icon: '🛒' },
  { id: 'transport', name: 'Transport', color: '#3B82F6', icon: '🚗' },
  { id: 'logement', name: 'Logement', color: '#F59E0B', icon: '🏠' },
  { id: 'loisirs', name: 'Loisirs', color: '#8B5CF6', icon: '🎮' },
  { id: 'sante', name: 'Santé', color: '#EF4444', icon: '🏥' },
  { id: 'shopping', name: 'Shopping', color: '#EC4899', icon: '👕' },
  { id: 'abonnements', name: 'Abonnements', color: '#06B6D4', icon: '📱' },
  { id: 'services', name: 'Services', color: '#6366F1', icon: '💳' },
  { id: 'autres', name: 'Autres', color: '#9CA3AF', icon: '📦' },
];

const STORAGE_KEY = 'budget_app_categories';
const TAG_CATEGORY_MAPPING_KEY = 'budget_app_tag_category_mappings';

// Type pour les associations tag-catégorie
export type TagCategoryMapping = {
  [tagName: string]: string; // tagName -> categoryId
};

// Hook pour gérer les catégories
export function useCategories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [tagMappings, setTagMappings] = useState<TagCategoryMapping>({});
  const [isLoading, setIsLoading] = useState(true);

  // Charger les catégories et mappings au démarrage
  useEffect(() => {
    loadCategories();
    loadTagMappings();
  }, []);

  const loadCategories = useCallback(() => {
    setIsLoading(true);
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setCategories(JSON.parse(stored));
      } else {
        // Utiliser les catégories par défaut
        setCategories(DEFAULT_CATEGORIES);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_CATEGORIES));
      }
    } catch (err) {
      console.error('Error loading categories:', err);
      setCategories(DEFAULT_CATEGORIES);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadTagMappings = useCallback(() => {
    try {
      const stored = localStorage.getItem(TAG_CATEGORY_MAPPING_KEY);
      if (stored) {
        setTagMappings(JSON.parse(stored));
      }
    } catch (err) {
      console.error('Error loading tag mappings:', err);
    }
  }, []);

  const saveCategories = useCallback((newCategories: Category[]) => {
    setCategories(newCategories);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newCategories));
  }, []);

  const createCategory = useCallback((name: string, color: string, icon: string) => {
    const newCategory: Category = {
      id: `custom_${Date.now()}`,
      name,
      color,
      icon,
      tagCount: 0
    };
    const updated = [...categories, newCategory];
    saveCategories(updated);
    return newCategory;
  }, [categories, saveCategories]);

  const updateCategory = useCallback((id: string, updates: Partial<Category>) => {
    const updated = categories.map(cat =>
      cat.id === id ? { ...cat, ...updates } : cat
    );
    saveCategories(updated);
  }, [categories, saveCategories]);

  const deleteCategory = useCallback((id: string) => {
    // Ne pas permettre la suppression des catégories par défaut
    if (!id.startsWith('custom_')) {
      console.warn('Cannot delete default category');
      return false;
    }
    const updated = categories.filter(cat => cat.id !== id);
    saveCategories(updated);
    return true;
  }, [categories, saveCategories]);

  const resetToDefaults = useCallback(() => {
    saveCategories(DEFAULT_CATEGORIES);
  }, [saveCategories]);

  // Assigner un tag à une catégorie
  const assignTagToCategory = useCallback((tagName: string, categoryId: string | null) => {
    const newMappings = { ...tagMappings };
    if (categoryId) {
      newMappings[tagName] = categoryId;
    } else {
      delete newMappings[tagName];
    }
    setTagMappings(newMappings);
    localStorage.setItem(TAG_CATEGORY_MAPPING_KEY, JSON.stringify(newMappings));
  }, [tagMappings]);

  // Obtenir la catégorie d'un tag
  const getTagCategory = useCallback((tagName: string): Category | undefined => {
    const categoryId = tagMappings[tagName];
    if (!categoryId) return undefined;
    return categories.find(c => c.id === categoryId);
  }, [tagMappings, categories]);

  // Obtenir tous les tags d'une catégorie
  const getTagsForCategory = useCallback((categoryId: string): string[] => {
    return Object.entries(tagMappings)
      .filter(([_, catId]) => catId === categoryId)
      .map(([tagName]) => tagName);
  }, [tagMappings]);

  // Obtenir les catégories avec le compte de tags
  const getCategoriesWithCount = useCallback((): Category[] => {
    return categories.map(cat => ({
      ...cat,
      tagCount: getTagsForCategory(cat.id).length
    }));
  }, [categories, getTagsForCategory]);

  return {
    categories,
    tagMappings,
    isLoading,
    createCategory,
    updateCategory,
    deleteCategory,
    resetToDefaults,
    assignTagToCategory,
    getTagCategory,
    getTagsForCategory,
    getCategoriesWithCount,
    refresh: loadCategories
  };
}

interface CategoryManagerProps {
  className?: string;
  onCategorySelect?: (category: Category) => void;
}

export function CategoryManager({ className = '', onCategorySelect }: CategoryManagerProps) {
  const {
    categories,
    isLoading,
    createCategory,
    updateCategory,
    deleteCategory,
    resetToDefaults,
    getTagsForCategory,
    getCategoriesWithCount
  } = useCategories();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    color: CATEGORY_COLORS[0]?.value || '#3B82F6',
    icon: CATEGORY_ICONS[0] || '🏷️'
  });

  // Get categories with their tag counts
  const categoriesWithCounts = getCategoriesWithCount();

  const handleSubmit = () => {
    if (!formData.name.trim()) return;

    if (editingCategory) {
      updateCategory(editingCategory.id, formData);
      setEditingCategory(null);
    } else {
      createCategory(formData.name.trim(), formData.color, formData.icon);
    }

    setFormData({
      name: '',
      color: CATEGORY_COLORS[0]?.value || '#3B82F6',
      icon: CATEGORY_ICONS[0] || '🏷️'
    });
    setShowCreateForm(false);
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      color: category.color,
      icon: category.icon
    });
    setShowCreateForm(true);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Supprimer cette catégorie ?')) {
      deleteCategory(id);
    }
  };

  const handleCancel = () => {
    setShowCreateForm(false);
    setEditingCategory(null);
    setFormData({
      name: '',
      color: CATEGORY_COLORS[0]?.value || '#3B82F6',
      icon: CATEGORY_ICONS[0] || '🏷️'
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Catégories</h3>
          <p className="text-sm text-gray-500">{categories.length} catégories</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={resetToDefaults}
            title="Réinitialiser aux valeurs par défaut"
          >
            🔄
          </Button>
          <Button
            size="sm"
            onClick={() => setShowCreateForm(true)}
            className="bg-purple-600 hover:bg-purple-700"
          >
            + Nouvelle
          </Button>
        </div>
      </div>

      {/* Create/Edit Form */}
      {showCreateForm && (
        <Card className="p-4 border-2 border-purple-200 bg-purple-50">
          <h4 className="font-medium text-gray-900 mb-3">
            {editingCategory ? 'Modifier la catégorie' : 'Nouvelle catégorie'}
          </h4>

          <div className="space-y-4">
            {/* Nom */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nom</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Ex: Restaurants"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* Couleur */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Couleur</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORY_COLORS.map(color => (
                  <button
                    key={color.value}
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, color: color.value }))}
                    className={`w-8 h-8 rounded-lg transition-all ${
                      formData.color === color.value
                        ? 'ring-2 ring-offset-2 ring-gray-900 scale-110'
                        : 'hover:scale-105'
                    }`}
                    style={{ backgroundColor: color.value }}
                    title={color.name}
                  />
                ))}
              </div>
            </div>

            {/* Icône */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Icône</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORY_ICONS.map(icon => (
                  <button
                    key={icon}
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, icon }))}
                    className={`w-10 h-10 text-xl flex items-center justify-center rounded-lg border-2 transition-all ${
                      formData.icon === icon
                        ? 'border-purple-600 bg-purple-100'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>

            {/* Preview */}
            <div className="pt-2 border-t">
              <label className="block text-sm font-medium text-gray-700 mb-2">Aperçu</label>
              <div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-white font-medium"
                style={{ backgroundColor: formData.color }}
              >
                <span>{formData.icon}</span>
                <span>{formData.name || 'Nom de la catégorie'}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-2">
              <Button onClick={handleSubmit} disabled={!formData.name.trim()}>
                {editingCategory ? 'Enregistrer' : 'Créer'}
              </Button>
              <Button variant="outline" onClick={handleCancel}>
                Annuler
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Categories List - Accordion style */}
      <div className="space-y-2">
        {categoriesWithCounts.map(category => {
          const isExpanded = expandedCategory === category.id;
          const categoryTags = getTagsForCategory(category.id);

          return (
            <div
              key={category.id}
              className="rounded-xl border-2 transition-all overflow-hidden"
              style={{ borderColor: category.color + '40' }}
            >
              {/* Category Header */}
              <div
                onClick={() => setExpandedCategory(isExpanded ? null : category.id)}
                className="group p-4 cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
                      style={{ backgroundColor: category.color + '20' }}
                    >
                      {category.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900">{category.name}</div>
                      <div className="text-sm text-gray-500">
                        {category.tagCount || 0} tag{(category.tagCount || 0) > 1 ? 's' : ''} associé{(category.tagCount || 0) > 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Actions */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEdit(category);
                        }}
                        className="w-7 h-7 flex items-center justify-center rounded-lg bg-white border border-gray-200 hover:bg-gray-50 text-sm"
                        title="Modifier"
                      >
                        ✏️
                      </button>
                      {category.id.startsWith('custom_') && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(category.id);
                          }}
                          className="w-7 h-7 flex items-center justify-center rounded-lg bg-white border border-red-200 hover:bg-red-50 text-sm"
                          title="Supprimer"
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                    {/* Expand icon */}
                    <span className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                      ▶
                    </span>
                  </div>
                </div>
              </div>

              {/* Expanded Content - Tags in this category */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-2 border-t" style={{ borderColor: category.color + '20' }}>
                  {categoryTags.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {categoryTags.map(tagName => (
                        <span
                          key={tagName}
                          className="px-3 py-1.5 rounded-full text-sm font-medium text-white"
                          style={{ backgroundColor: category.color }}
                        >
                          {tagName}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 italic py-2">
                      Aucun tag dans cette catégorie. Assignez des tags depuis la liste &quot;Tags les plus utilisés&quot;.
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
