'use client';

import { useState } from 'react';
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
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Gestion des Tags</h2>
                  <div className="flex items-center gap-6 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                      <span>{tags.length} tags au total</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>{tags.reduce((sum, tag) => sum + tag.transaction_count, 0)} transactions</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                      <span>{tags.filter(t => t.expense_type === 'fixed').length} fixes</span>
                    </div>
                  </div>
                </div>
                <Button onClick={handleCreateTag} className="bg-blue-600 hover:bg-blue-700">
                  <span className="mr-2">+</span>
                  Nouveau tag
                </Button>
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
                <div className="flex-1">
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Rechercher un tag..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <span className="absolute left-3 top-2.5 text-gray-400">🔍</span>
                  </div>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-3">
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value as any)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">Tous les types</option>
                    <option value="fixed">Dépenses fixes</option>
                    <option value="variable">Dépenses variables</option>
                  </select>

                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="usage">Par utilisation</option>
                    <option value="name">Par nom</option>
                    <option value="amount">Par montant</option>
                  </select>
                </div>

                {/* Bulk Actions */}
                {selectedTags.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Button 
                      onClick={() => setShowMergeDialog(true)}
                      variant="outline"
                      size="sm"
                      className="text-blue-600 border-blue-300 hover:bg-blue-50"
                      disabled={selectedTags.length < 2}
                    >
                      🔗 Fusionner ({selectedTags.length})
                    </Button>
                    <Button 
                      onClick={handleBulkDelete}
                      variant="outline"
                      size="sm"
                      className="text-red-600 border-red-300 hover:bg-red-50"
                    >
                      🗑️ Supprimer ({selectedTags.length})
                    </Button>
                    <Button 
                      onClick={() => setSelectedTags([])}
                      variant="outline"
                      size="sm"
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
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Mes Tags ({filteredTags.length}{filteredTags.length !== tags.length ? ` sur ${tags.length}` : ''})
                    </h3>
                    <div className="flex items-center gap-2">
                      {tags.length > 0 && (
                        <Button 
                          onClick={() => setSelectedTags(filteredTags.map(t => t.name))}
                          variant="outline" 
                          size="sm"
                          className="text-sm"
                        >
                          Tout sélectionner
                        </Button>
                      )}
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={loadTags}
                        className="text-sm"
                      >
                        <span className="mr-1">🔄</span>
                        Actualiser
                      </Button>
                    </div>
                  </div>


                  {/* Tags Grid */}
                  <div className="space-y-3">
                    {filteredTags.map((tag) => (
                      <div
                        key={tag.name}
                        className={`
                          flex items-center justify-between p-4 border border-gray-200 rounded-lg bg-white 
                          hover:shadow-sm transition-all cursor-pointer
                          ${
                            selectedTags.includes(tag.name)
                              ? 'ring-2 ring-blue-500 border-blue-300 bg-blue-50'
                              : ''
                          }
                        `}
                        onClick={() => toggleTagSelection(tag.name)}
                      >
                        <div className="flex items-center gap-4 flex-1">
                          {/* Checkbox */}
                          <input
                            type="checkbox"
                            checked={selectedTags.includes(tag.name)}
                            onChange={() => toggleTagSelection(tag.name)}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            onClick={(e) => e.stopPropagation()}
                          />

                          {/* Tag Name & Badges */}
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <span className="font-medium text-gray-900 truncate">
                              {tag.name}
                            </span>
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

                          {/* Stats */}
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <span>📊</span>
                              <span className="font-medium">{tag.transaction_count}</span>
                              <span className="text-xs">uses</span>
                            </div>
                            {tag.total_amount !== 0 && (
                              <div className="flex items-center gap-1">
                                <span>💰</span>
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
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-green-600 font-medium">
                                  {Math.floor(Math.random() * 15) + 85}%
                                </span>
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2 ml-4">
                          {/* Quick Type Toggle */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleToggleType(tag.name, tag.expense_type);
                            }}
                            disabled={isUpdating}
                            className={`
                              px-3 py-1 text-xs rounded-full transition-colors border text-white font-medium
                              ${tag.expense_type === 'fixed' 
                                ? 'bg-orange-500 border-orange-500 hover:bg-orange-600' 
                                : 'bg-green-500 border-green-500 hover:bg-green-600'
                              }
                              ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                            title={`Changer vers ${tag.expense_type === 'fixed' ? 'Variable' : 'Fixe'}`}
                          >
                            {tag.expense_type === 'fixed' ? 'Fixe → Var' : 'Var → Fixe'}
                          </button>

                          {/* View Transactions */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // TODO: Navigate to transactions filtered by tag
                              console.log('View transactions for', tag.name);
                            }}
                            className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                            title="Voir les transactions"
                          >
                            👁️
                          </button>

                          {/* Edit */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditTag(tag);
                            }}
                            disabled={isUpdating}
                            className="p-2 text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50"
                            title="Modifier"
                          >
                            ✏️
                          </button>

                          {/* Delete */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteTag(tag.name, tag.transaction_count);
                            }}
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