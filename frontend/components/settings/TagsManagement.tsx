'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTagsManagement, TagInfo } from '../../hooks/useTagsManagement';
import { Card, Button, Alert } from '../ui';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { TagSourceBadge } from '../ui/TagSourceBadge';
import { TagEditModal } from './TagEditModal';
import { TagsStatsDashboard } from './TagsStatsDashboard';
import { TagRulesConfig } from './TagRulesConfig';
import { TagsImportExport } from './TagsImportExport';
import { TagMergeDialog } from './TagMergeDialog';

export function TagsManagement() {
  const router = useRouter();
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
  const [activeTab, setActiveTab] = useState<'overview' | 'tags' | 'rules' | 'import-export'>('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'fixed' | 'variable'>('all');
  const [sortBy, setSortBy] = useState<'name' | 'usage' | 'amount'>('usage');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showMergeDialog, setShowMergeDialog] = useState(false);

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
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Chargement des tags...</span>
      </div>
    );
  }

  // Calculate tag statistics
  const tagStats = {
    total: tags.length,
    fixed: tags.filter(t => t.expense_type === 'fixed').length,
    variable: tags.filter(t => t.expense_type === 'variable').length,
    totalTransactions: tags.reduce((sum, tag) => sum + tag.transaction_count, 0),
    totalAmount: tags.reduce((sum, tag) => sum + Math.abs(tag.total_amount), 0),
    averageTransactionsPerTag: tags.length > 0 ? Math.round(tags.reduce((sum, tag) => sum + tag.transaction_count, 0) / tags.length) : 0
  };

  // Filter and sort tags
  const filteredTags = tags
    .filter(tag => {
      const matchesSearch = tag.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === 'all' || tag.expense_type === filterType;
      return matchesSearch && matchesType;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'usage':
          return b.transaction_count - a.transaction_count;
        case 'amount':
          return Math.abs(b.total_amount) - Math.abs(a.total_amount);
        default:
          return 0;
      }
    });

  const handleBulkDelete = async () => {
    if (selectedTags.length === 0) return;
    
    const message = `Êtes-vous sûr de vouloir supprimer ${selectedTags.length} tag(s) sélectionné(s) ?`;
    if (window.confirm(message)) {
      for (const tagName of selectedTags) {
        await deleteTag(tagName);
      }
      setSelectedTags([]);
    }
  };

  const toggleTagSelection = (tagName: string) => {
    setSelectedTags(prev => 
      prev.includes(tagName)
        ? prev.filter(t => t !== tagName)
        : [...prev, tagName]
    );
  };

  const handleMergeTags = async (sourceTags: string[], targetTag: string) => {
    try {
      // TODO: Implement actual merge API call
      console.log('Merging tags:', sourceTags, 'into', targetTag);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Reload tags after merge
      await loadTags();
      
      return true;
    } catch (error) {
      console.error('Failed to merge tags:', error);
      return false;
    }
  };

  const handleViewTransactions = (tagName: string) => {
    // Navigate to transactions page with tag filter
    const searchParams = new URLSearchParams();
    searchParams.set('tag', tagName);
    router.push(`/transactions?${searchParams.toString()}`);
  };

  const tabsConfig = [
    { id: 'overview', label: 'Vue d\'ensemble', icon: '📊' },
    { id: 'tags', label: 'Mes Tags', icon: '🏷️', count: tags.length },
    { id: 'rules', label: 'Règles Auto', icon: '⚙️' },
    { id: 'import-export', label: 'Import/Export', icon: '📁' }
  ] as const;

  return (
    <>
      <div className="space-y-6">
        {/* Navigation Tabs */}
        <Card className="p-1">
          <div className="flex items-center gap-1">
            {tabsConfig.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-all
                  ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50'
                  }
                `}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`
                    text-xs px-2 py-1 rounded-full font-semibold
                    ${
                      activeTab === tab.id
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-700'
                    }
                  `}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </Card>
        {/* Tab Content */}
        {activeTab === 'overview' && (
          <TagsStatsDashboard />
        )}

        {activeTab === 'rules' && (
          <TagRulesConfig />
        )}

        {activeTab === 'import-export' && (
          <TagsImportExport />
        )}

        {activeTab === 'tags' && (
          <div className="space-y-6">
            {/* Tags Management Header */}
            <Card className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Gestion des Tags</h2>
                  <p className="text-gray-600">Organisez et suivez vos catégories de transactions</p>
                </div>
                <Button onClick={handleCreateTag} className="bg-blue-600 hover:bg-blue-700">
                  <span className="mr-2">+</span>
                  Nouveau tag
                </Button>
              </div>
              
              {/* Enhanced Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-white rounded-lg p-4 border border-blue-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Total Tags</span>
                  </div>
                  <div className="text-2xl font-bold text-blue-600">{tagStats.total}</div>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-orange-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-orange-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Dépenses Fixes</span>
                  </div>
                  <div className="text-2xl font-bold text-orange-600">{tagStats.fixed}</div>
                  {tagStats.total > 0 && (
                    <div className="text-xs text-gray-500 mt-1">
                      {Math.round((tagStats.fixed / tagStats.total) * 100)}%
                    </div>
                  )}
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Dépenses Variables</span>
                  </div>
                  <div className="text-2xl font-bold text-green-600">{tagStats.variable}</div>
                  {tagStats.total > 0 && (
                    <div className="text-xs text-gray-500 mt-1">
                      {Math.round((tagStats.variable / tagStats.total) * 100)}%
                    </div>
                  )}
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-purple-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-purple-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Transactions</span>
                  </div>
                  <div className="text-2xl font-bold text-purple-600">{tagStats.totalTransactions.toLocaleString()}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {tagStats.averageTransactionsPerTag} par tag
                  </div>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-emerald-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-emerald-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Montant Total</span>
                  </div>
                  <div className="text-xl font-bold text-emerald-600">
                    {tagStats.totalAmount.toLocaleString('fr-FR', {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0
                    })}€
                  </div>
                </div>
                
                <div className="bg-white rounded-lg p-4 border border-indigo-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="w-3 h-3 bg-indigo-500 rounded-full"></span>
                    <span className="text-sm font-medium text-gray-700">Filtres Actifs</span>
                  </div>
                  <div className="text-2xl font-bold text-indigo-600">{filteredTags.length}</div>
                  {filteredTags.length !== tagStats.total && (
                    <div className="text-xs text-gray-500 mt-1">
                      sur {tagStats.total}
                    </div>
                  )}
                </div>
              </div>
            </Card>

        {/* Error Messages */}
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

            {/* Search and Filters */}
            <Card className="p-4">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                {/* Search */}
                <div className="flex-1 w-full sm:w-auto">
                  <label htmlFor="tag-search" className="sr-only">
                    Rechercher dans les tags
                  </label>
                  <div className="relative">
                    <input
                      id="tag-search"
                      type="text"
                      placeholder="Rechercher un tag..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      aria-label="Rechercher dans les tags"
                    />
                    <span className="absolute left-3 top-2.5 text-gray-400" aria-hidden="true">🔍</span>
                  </div>
                </div>

                {/* Filters */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
                  <div>
                    <label htmlFor="filter-type" className="sr-only">
                      Filtrer par type de dépense
                    </label>
                    <select
                      id="filter-type"
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value as any)}
                      className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                      aria-label="Filtrer par type de dépense"
                    >
                      <option value="all">Tous les types</option>
                      <option value="fixed">Dépenses fixes</option>
                      <option value="variable">Dépenses variables</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="sort-by" className="sr-only">
                      Trier les tags par
                    </label>
                    <select
                      id="sort-by"
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                      aria-label="Trier les tags par"
                    >
                      <option value="usage">Par utilisation</option>
                      <option value="name">Par nom</option>
                      <option value="amount">Par montant</option>
                    </select>
                  </div>
                </div>

                {/* Bulk Actions */}
                {selectedTags.length > 0 && (
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
                    <Button 
                      onClick={() => setShowMergeDialog(true)}
                      variant="outline"
                      size="sm"
                      className="text-blue-600 border-blue-300 hover:bg-blue-50"
                      disabled={selectedTags.length < 2}
                      aria-label={`Fusionner ${selectedTags.length} tags sélectionnés`}
                    >
                      🔗 Fusionner ({selectedTags.length})
                    </Button>
                    <Button 
                      onClick={handleBulkDelete}
                      variant="outline"
                      size="sm"
                      className="text-red-600 border-red-300 hover:bg-red-50"
                      aria-label={`Supprimer ${selectedTags.length} tags sélectionnés`}
                    >
                      🗑️ Supprimer ({selectedTags.length})
                    </Button>
                    <Button 
                      onClick={() => setSelectedTags([])}
                      variant="outline"
                      size="sm"
                      aria-label="Annuler la sélection"
                    >
                      Annuler
                    </Button>
                  </div>
                )}
              </div>
            </Card>

            {/* Tags List */}
            <Card className="p-6">
              {filteredTags.length === 0 ? (
                searchTerm || filterType !== 'all' ? (
                  <div className="text-center py-8">
                    <div className="text-4xl mb-4">🔍</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Aucun tag trouvé
                    </h3>
                    <p className="text-gray-600 mb-4">
                      Aucun tag ne correspond à vos critères de recherche.
                    </p>
                    <Button 
                      onClick={() => {
                        setSearchTerm('');
                        setFilterType('all');
                      }}
                      variant="outline"
                    >
                      Réinitialiser les filtres
                    </Button>
                  </div>
                ) : (
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
                )
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Mes Tags ({filteredTags.length}{filteredTags.length !== tags.length ? ` sur ${tags.length}` : ''})
                    </h3>
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      {tags.length > 0 && (
                        <Button 
                          onClick={() => setSelectedTags(filteredTags.map(t => t.name))}
                          variant="outline" 
                          size="sm"
                          className="text-sm"
                          aria-label={`Sélectionner tous les ${filteredTags.length} tags affichés`}
                        >
                          Tout sélectionner
                        </Button>
                      )}
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={loadTags}
                        className="text-sm"
                        aria-label="Actualiser la liste des tags"
                      >
                        <span className="mr-1" aria-hidden="true">🔄</span>
                        Actualiser
                      </Button>
                    </div>
                  </div>


                  {/* Tags Grid */}
                  <div className="space-y-3" role="list" aria-label="Liste des tags">
                    {filteredTags.map((tag) => (
                      <div
                        key={tag.name}
                        className={`
                          flex flex-col sm:flex-row sm:items-center justify-between p-4 border border-gray-200 rounded-lg bg-white 
                          hover:shadow-sm transition-all cursor-pointer focus-within:ring-2 focus-within:ring-blue-500
                          ${
                            selectedTags.includes(tag.name)
                              ? 'ring-2 ring-blue-500 border-blue-300 bg-blue-50'
                              : ''
                          }
                        `}
                        onClick={() => toggleTagSelection(tag.name)}
                        role="listitem"
                        aria-label={`Tag ${tag.name}, ${tag.transaction_count} transactions, type ${tag.expense_type}`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-1">
                          {/* Mobile: First row - Checkbox, Name and Badges */}
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            {/* Checkbox */}
                            <input
                              type="checkbox"
                              checked={selectedTags.includes(tag.name)}
                              onChange={() => toggleTagSelection(tag.name)}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
                              onClick={(e) => e.stopPropagation()}
                              aria-label={`Sélectionner le tag ${tag.name}`}
                            />

                            {/* Tag Name & Badges */}
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <span className="font-medium text-gray-900 truncate">
                                {tag.name}
                              </span>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <ExpenseTypeBadge
                                  type={tag.expense_type}
                                  size="sm"
                                />
                                {/* Mock AI source badge - replace with actual data */}
                                <TagSourceBadge 
                                  source={tag.transaction_count > 50 ? 'ai_pattern' : 'manual'} 
                                  size="xs" 
                                  showLabel={false}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Mobile: Second row / Desktop: Same row - Stats */}
                          <div className="flex items-center justify-between sm:justify-end gap-4 text-sm text-gray-600 pl-7 sm:pl-0">
                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-1">
                                <span aria-hidden="true">📊</span>
                                <span className="font-medium">{tag.transaction_count}</span>
                                <span className="text-xs hidden sm:inline">uses</span>
                                <span className="text-xs sm:hidden">trans.</span>
                              </div>
                              {tag.total_amount !== 0 && (
                                <div className="flex items-center gap-1">
                                  <span aria-hidden="true">💰</span>
                                  <span className="font-medium">
                                    {Math.abs(tag.total_amount).toLocaleString('fr-FR', {
                                      minimumFractionDigits: 0,
                                      maximumFractionDigits: 0
                                    })}€
                                  </span>
                                </div>
                              )}
                              {/* Mock confidence indicator for AI tags */}
                              {tag.transaction_count > 50 && (
                                <div className="flex items-center gap-1" title="Confiance IA">
                                  <span className="text-xs text-green-600 font-medium">
                                    {Math.floor(Math.random() * 15) + 85}%
                                  </span>
                                  <span className="w-2 h-2 bg-green-500 rounded-full" aria-hidden="true"></span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 mt-3 sm:mt-0 sm:ml-4 pt-3 sm:pt-0 border-t sm:border-t-0 border-gray-200">
                          {/* Quick Type Toggle */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleType(tag.name, tag.expense_type);
                            }}
                            disabled={isUpdating}
                            className={`
                              px-3 py-2 text-xs rounded-lg transition-colors border text-white font-medium text-center
                              ${tag.expense_type === 'fixed' 
                                ? 'bg-orange-500 border-orange-500 hover:bg-orange-600' 
                                : 'bg-green-500 border-green-500 hover:bg-green-600'
                              }
                              ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                            title={`Changer vers ${tag.expense_type === 'fixed' ? 'Variable' : 'Fixe'}`}
                            aria-label={`Changer le type de ${tag.name} vers ${tag.expense_type === 'fixed' ? 'Variable' : 'Fixe'}`}
                          >
                            <span className="hidden sm:inline">
                              {tag.expense_type === 'fixed' ? 'Fixe → Var' : 'Var → Fixe'}
                            </span>
                            <span className="sm:hidden">
                              Changer en {tag.expense_type === 'fixed' ? 'Variable' : 'Fixe'}
                            </span>
                          </button>

                          <div className="flex items-center gap-2">
                            {/* View Transactions */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewTransactions(tag.name);
                              }}
                              className="flex-1 sm:flex-none p-2 text-gray-400 hover:text-blue-600 transition-colors border border-gray-300 rounded-lg hover:border-blue-300 disabled:opacity-50"
                              title="Voir les transactions"
                              disabled={tag.transaction_count === 0}
                              aria-label={`Voir les ${tag.transaction_count} transactions pour ${tag.name}`}
                            >
                              <span aria-hidden="true">👁️</span>
                              <span className="ml-1 text-xs sm:hidden">Voir</span>
                            </button>

                            {/* Edit */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditTag(tag);
                              }}
                              disabled={isUpdating}
                              className="flex-1 sm:flex-none p-2 text-gray-400 hover:text-blue-600 transition-colors border border-gray-300 rounded-lg hover:border-blue-300 disabled:opacity-50"
                              title="Modifier"
                              aria-label={`Modifier le tag ${tag.name}`}
                            >
                              <span aria-hidden="true">✏️</span>
                              <span className="ml-1 text-xs sm:hidden">Éditer</span>
                            </button>

                            {/* Delete */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteTag(tag.name, tag.transaction_count);
                              }}
                              disabled={isUpdating}
                              className="flex-1 sm:flex-none p-2 text-gray-400 hover:text-red-600 transition-colors border border-gray-300 rounded-lg hover:border-red-300 disabled:opacity-50"
                              title="Supprimer"
                              aria-label={`Supprimer le tag ${tag.name}`}
                            >
                              <span aria-hidden="true">🗑️</span>
                              <span className="ml-1 text-xs sm:hidden">Suppr.</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}

      {/* Edit Modal */}
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

      {/* Merge Dialog */}
      <TagMergeDialog
        isOpen={showMergeDialog}
        onClose={() => {
          setShowMergeDialog(false);
          setSelectedTags([]);
        }}
        availableTags={tags}
        onMerge={handleMergeTags}
      />
    </div>
    </>
  );
}

export default TagsManagement;