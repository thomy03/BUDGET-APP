'use client';

import React, { useState, useEffect } from 'react';
import { Modal, LoadingSpinner, Button } from '../ui';
import { api } from '../../lib/api';
import { useRouter } from 'next/navigation';

interface Transaction {
  id: number;
  month: string;
  date_op: string;
  date_valeur: string;
  amount: number;
  label: string;
  category: string;
  subcategory: string;
  is_expense: boolean;
  exclude: boolean;
  expense_type: 'FIXED' | 'VARIABLE' | 'PROVISION';
  tags: string[];
}

interface CategoryLevel {
  name: string;
  level: 'category' | 'subcategory' | 'tag' | 'transaction';
  value: string;
  count: number;
  amount: number;
  parent?: string;
}

interface HierarchicalNavigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  month: string;
  initialCategory?: string;
  initialFilters?: {
    expense_type?: 'FIXED' | 'VARIABLE' | 'PROVISION';
    tag?: string;
  };
}

export function HierarchicalNavigationModal({
  isOpen,
  onClose,
  title,
  month,
  initialCategory,
  initialFilters
}: HierarchicalNavigationModalProps) {
  const [currentLevel, setCurrentLevel] = useState<'category' | 'subcategory' | 'tag' | 'transaction'>('category');
  const [navigationPath, setNavigationPath] = useState<CategoryLevel[]>([]);
  const [currentData, setCurrentData] = useState<CategoryLevel[] | Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [showReassignModal, setShowReassignModal] = useState(false);
  const router = useRouter();

  // Available categories and tags for reassignment
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);

  const formatAmount = (amount: number) => {
    return `${Math.abs(amount).toFixed(2)} €`;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR');
  };

  // Load available categories and tags for reassignment
  const loadReassignmentOptions = async () => {
    try {
      const [categoriesRes, tagsRes] = await Promise.all([
        api.get('/transactions/categories'),
        api.get('/transactions/tags')
      ]);
      
      setAvailableCategories(categoriesRes.data || []);
      setAvailableTags(tagsRes.data || []);
    } catch (error) {
      console.error('Error loading reassignment options:', error);
    }
  };

  // Load data based on current navigation level
  const loadCurrentLevel = async () => {
    if (!isOpen || !month) return;
    
    setLoading(true);
    setError('');
    
    try {
      let params: any = { month };
      
      // Apply initial filters
      if (initialFilters?.expense_type) {
        params.expense_type = initialFilters.expense_type;
      }
      if (initialFilters?.tag) {
        params.tag = initialFilters.tag;
      }
      
      // Apply navigation path filters
      navigationPath.forEach(level => {
        if (level.level === 'category') {
          params.category = level.value;
        } else if (level.level === 'subcategory') {
          params.subcategory = level.value;
        } else if (level.level === 'tag') {
          params.tag = level.value;
        }
      });
      
      console.log('🔍 Loading level data with params:', params);
      
      if (currentLevel === 'transaction') {
        // Load individual transactions
        const response = await api.get<Transaction[]>('/transactions', { params });
        const transactions = response.data.filter(t => !t.exclude && t.is_expense);
        setCurrentData(transactions);
      } else {
        // Load hierarchical data
        const updatedParams = { ...params, level: currentLevel };
        const response = await api.get('/transactions/hierarchy', { params: updatedParams });
        const hierarchyData: CategoryLevel[] = response.data || [];
        setCurrentData(hierarchyData);
      }
      
    } catch (err: any) {
      setError('Erreur lors du chargement des données');
      console.error('Error loading hierarchy data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Navigate to next level
  const navigateToLevel = (item: CategoryLevel) => {
    const newPath = [...navigationPath, item];
    setNavigationPath(newPath);
    
    // Determine next level
    if (currentLevel === 'category') {
      setCurrentLevel('subcategory');
    } else if (currentLevel === 'subcategory') {
      setCurrentLevel('tag');
    } else if (currentLevel === 'tag') {
      setCurrentLevel('transaction');
    }
  };

  // Navigate back to previous level
  const navigateBack = () => {
    if (navigationPath.length === 0) return;
    
    const newPath = navigationPath.slice(0, -1);
    setNavigationPath(newPath);
    
    // Determine previous level
    if (currentLevel === 'transaction') {
      setCurrentLevel('tag');
    } else if (currentLevel === 'tag') {
      setCurrentLevel('subcategory');
    } else if (currentLevel === 'subcategory') {
      setCurrentLevel('category');
    }
  };

  // Reset to initial state
  const resetNavigation = () => {
    setNavigationPath([]);
    setCurrentLevel('category');
    setSelectedTransaction(null);
  };

  // Handle transaction selection for reassignment
  const handleTransactionSelect = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    setShowReassignModal(true);
  };

  // Handle transaction reassignment
  const handleReassignTransaction = async (newCategory: string, newSubcategory: string, newTags: string[]) => {
    if (!selectedTransaction) return;
    
    try {
      setLoading(true);
      
      const queryParams = new URLSearchParams({
        category: newCategory,
        ...(newSubcategory && { subcategory: newSubcategory }),
        ...(newTags.length > 0 && { tags: newTags.join(',') })
      });
      
      await api.put(`/transactions/${selectedTransaction.id}/reassign?${queryParams}`);
      
      // Reload current level data
      await loadCurrentLevel();
      
      setShowReassignModal(false);
      setSelectedTransaction(null);
      
    } catch (error) {
      console.error('Error reassigning transaction:', error);
      setError('Erreur lors de la réassignation de la transaction');
    } finally {
      setLoading(false);
    }
  };

  // Create new category/tag
  const handleCreateNew = async (type: 'category' | 'tag', name: string) => {
    try {
      if (type === 'category') {
        await api.post('/transactions/categories', { name });
        setAvailableCategories([...availableCategories, name]);
      } else {
        await api.post('/transactions/tags', { name });
        setAvailableTags([...availableTags, name]);
      }
    } catch (error) {
      console.error(`Error creating new ${type}:`, error);
      setError(`Erreur lors de la création du ${type === 'category' ? 'catégorie' : 'tag'}`);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadReassignmentOptions();
      resetNavigation();
    }
  }, [isOpen]);

  useEffect(() => {
    loadCurrentLevel();
  }, [currentLevel, navigationPath, isOpen, month]);

  const breadcrumbs = [
    { name: 'Racine', level: 'category' as const },
    ...navigationPath
  ];

  return (
    <>
      <Modal 
        isOpen={isOpen} 
        onClose={onClose} 
        title={
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🗂️</span>
            <div>
              <h2 className="text-xl font-bold">{title}</h2>
              <p className="text-sm text-gray-600">Navigation hiérarchique complète</p>
            </div>
          </div>
        }
        size="xl"
      >
        <div className="space-y-6">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center space-x-2 p-4 bg-gray-50 rounded-lg">
            <span className="text-sm font-medium text-gray-600">Chemin :</span>
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && <span className="text-gray-400">›</span>}
                <button
                  onClick={() => {
                    if (index === 0) {
                      resetNavigation();
                    } else {
                      const targetPath = navigationPath.slice(0, index);
                      setNavigationPath(targetPath);
                      setCurrentLevel(targetPath.length === 0 ? 'category' : 
                        targetPath.length === 1 ? 'subcategory' : 
                        targetPath.length === 2 ? 'tag' : 'transaction');
                    }
                  }}
                  className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
            <span className="text-gray-400">›</span>
            <span className="text-sm font-medium text-gray-900 capitalize">{currentLevel}</span>
          </div>

          {/* Back Button */}
          {navigationPath.length > 0 && (
            <button
              onClick={navigateBack}
              className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 font-medium"
            >
              <span>←</span>
              <span>Retour au niveau précédent</span>
            </button>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="md" text="Chargement..." />
            </div>
          ) : currentLevel === 'transaction' ? (
            // Transaction List
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Transactions Individuelles</h3>
                <span className="text-sm text-gray-600">
                  {(currentData as Transaction[]).length} transaction(s)
                </span>
              </div>
              
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {(currentData as Transaction[]).map(transaction => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 mb-1">{transaction.label}</div>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>📅 {formatDate(transaction.date_op)}</span>
                        <span>🏷️ {transaction.category}</span>
                        {transaction.subcategory && <span>› {transaction.subcategory}</span>}
                        <span className={`px-2 py-1 rounded-full ${
                          transaction.expense_type === 'FIXED' ? 'bg-blue-100 text-blue-800' :
                          transaction.expense_type === 'VARIABLE' ? 'bg-orange-100 text-orange-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {transaction.expense_type === 'FIXED' ? 'Fixe' :
                           transaction.expense_type === 'VARIABLE' ? 'Variable' : 'Provision'}
                        </span>
                      </div>
                      {transaction.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {transaction.tags.map((tag, idx) => (
                            <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right space-y-2">
                      <div className="text-lg font-bold text-red-600">
                        -{formatAmount(transaction.amount)}
                      </div>
                      <button
                        onClick={() => handleTransactionSelect(transaction)}
                        className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs hover:bg-blue-200 transition-colors"
                      >
                        🔄 Réassigner
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // Hierarchical Level List
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold capitalize">
                  Niveau : {currentLevel === 'category' ? 'Catégories' :
                           currentLevel === 'subcategory' ? 'Sous-catégories' :
                           'Tags'}
                </h3>
                <span className="text-sm text-gray-600">
                  {(currentData as CategoryLevel[]).length} élément(s)
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(currentData as CategoryLevel[]).map((item, index) => (
                  <div
                    key={index}
                    onClick={() => navigateToLevel(item)}
                    className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md hover:border-blue-300 cursor-pointer transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 mb-1">{item.name}</h4>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span>📊 {item.count} transaction(s)</span>
                          <span>💰 {formatAmount(item.amount)}</span>
                        </div>
                      </div>
                      <div className="text-blue-600">
                        <span className="text-lg">→</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between items-center pt-4 border-t">
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  onClose();
                  router.push(`/transactions?month=${month}`);
                }}
                className="px-4 py-2 bg-blue-100 text-blue-800 rounded-lg hover:bg-blue-200 transition-colors"
              >
                🔍 Voir toutes les transactions
              </button>
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </Modal>

      {/* Transaction Reassignment Modal */}
      <TransactionReassignmentModal
        isOpen={showReassignModal}
        onClose={() => {
          setShowReassignModal(false);
          setSelectedTransaction(null);
        }}
        transaction={selectedTransaction}
        availableCategories={availableCategories}
        availableTags={availableTags}
        onReassign={handleReassignTransaction}
        onCreateNew={handleCreateNew}
      />
    </>
  );
}

// Transaction Reassignment Modal Component
interface TransactionReassignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: Transaction | null;
  availableCategories: string[];
  availableTags: string[];
  onReassign: (category: string, subcategory: string, tags: string[]) => void;
  onCreateNew: (type: 'category' | 'tag', name: string) => void;
}

function TransactionReassignmentModal({
  isOpen,
  onClose,
  transaction,
  availableCategories,
  availableTags,
  onReassign,
  onCreateNew
}: TransactionReassignmentModalProps) {
  const [newCategory, setNewCategory] = useState('');
  const [newSubcategory, setNewSubcategory] = useState('');
  const [newTags, setNewTags] = useState<string[]>([]);
  const [customCategory, setCustomCategory] = useState('');
  const [customTag, setCustomTag] = useState('');

  useEffect(() => {
    if (transaction) {
      setNewCategory(transaction.category);
      setNewSubcategory(transaction.subcategory);
      setNewTags(transaction.tags);
    }
  }, [transaction]);

  const handleSubmit = () => {
    const finalCategory = customCategory || newCategory;
    if (!finalCategory) return;
    
    const finalTags = [...newTags];
    if (customTag && !finalTags.includes(customTag)) {
      finalTags.push(customTag);
    }
    
    onReassign(finalCategory, newSubcategory, finalTags);
  };

  const addTag = (tag: string) => {
    if (!newTags.includes(tag)) {
      setNewTags([...newTags, tag]);
    }
  };

  const removeTag = (tag: string) => {
    setNewTags(newTags.filter(t => t !== tag));
  };

  if (!transaction) return null;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title="🔄 Réassigner la Transaction"
      size="lg"
    >
      <div className="space-y-6">
        {/* Transaction Info */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="font-medium text-gray-900 mb-2">{transaction.label}</div>
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span>📅 {new Date(transaction.date_op).toLocaleDateString('fr-FR')}</span>
            <span>💰 -{Math.abs(transaction.amount).toFixed(2)} €</span>
          </div>
        </div>

        {/* Category Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Catégorie *
          </label>
          <select
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Sélectionner une catégorie...</option>
            {availableCategories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          
          {/* Custom Category */}
          <div className="mt-2">
            <input
              type="text"
              placeholder="Ou créer une nouvelle catégorie..."
              value={customCategory}
              onChange={(e) => setCustomCategory(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Subcategory */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sous-catégorie
          </label>
          <input
            type="text"
            value={newSubcategory}
            onChange={(e) => setNewSubcategory(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Sous-catégorie (optionnel)"
          />
        </div>

        {/* Tags Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tags
          </label>
          
          {/* Current Tags */}
          <div className="flex flex-wrap gap-2 mb-3">
            {newTags.map(tag => (
              <span
                key={tag}
                className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {tag}
                <button
                  onClick={() => removeTag(tag)}
                  className="ml-2 text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          
          {/* Available Tags */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            {availableTags
              .filter(tag => !newTags.includes(tag))
              .map(tag => (
                <button
                  key={tag}
                  onClick={() => addTag(tag)}
                  className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm hover:bg-gray-200 transition-colors"
                >
                  + {tag}
                </button>
              ))}
          </div>
          
          {/* Custom Tag */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nouveau tag..."
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && customTag) {
                  addTag(customTag);
                  setCustomTag('');
                }
              }}
            />
            <button
              onClick={() => {
                if (customTag) {
                  addTag(customTag);
                  setCustomTag('');
                }
              }}
              className="px-4 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200 transition-colors"
            >
              + Ajouter
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={!newCategory && !customCategory}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Réassigner
          </button>
        </div>
      </div>
    </Modal>
  );
}