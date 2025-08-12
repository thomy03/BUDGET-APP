'use client';

import { useState, useRef } from 'react';
import { Card, Button, Alert, Modal, ErrorBoundary } from '../ui';
import { useTagsManagement, TagInfo, TagEditData } from '../../hooks/useTagsManagement';
import { ExpenseTypeBadge } from '../transactions/ExpenseTypeBadge';
import { safeArray, safeSlice, validateRequiredProps } from '../../types/defensive-programming';

interface TagsImportExportProps {
  tags: TagInfo[] | undefined;
  isLoading: boolean;
}

interface ImportPreview {
  valid: TagEditData[];
  invalid: Array<{ line: number; data: any; error: string }>;
  duplicates: string[];
}

const TEMPLATE_TAGS = [
  {
    name: "Alimentaire",
    expense_type: "variable" as const,
    associated_labels: ["supermarché", "boulangerie", "épicerie", "courses"],
    category: "Alimentation"
  },
  {
    name: "Transport",
    expense_type: "variable" as const,
    associated_labels: ["essence", "péage", "parking", "train"],
    category: "Transport"
  },
  {
    name: "Logement",
    expense_type: "fixed" as const,
    associated_labels: ["loyer", "charges", "électricité", "gaz"],
    category: "Logement"
  },
  {
    name: "Abonnements",
    expense_type: "fixed" as const,
    associated_labels: ["netflix", "spotify", "internet", "mobile"],
    category: "Services"
  },
  {
    name: "Restaurants",
    expense_type: "variable" as const,
    associated_labels: ["restaurant", "mcdonald", "pizza", "café"],
    category: "Alimentation"
  }
];

export function TagsImportExport({ tags, isLoading }: TagsImportExportProps) {
  // DEFENSIVE PROGRAMMING: Validate critical props
  if (!validateRequiredProps({ isLoading }, ['isLoading'], 'TagsImportExport')) {
    return null;
  }
  
  const { createTag } = useTagsManagement();
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExportTags = () => {
    try {
      // Vérifier que tags existe et n'est pas vide
      if (!tags || tags.length === 0) {
        setImportError('Aucun tag à exporter');
        return;
      }

      // Préparer les données pour l'export
      const exportData = tags.map(tag => ({
        name: tag.name,
        expense_type: tag.expense_type,
        associated_labels: tag.associated_labels || [],
        category: tag.category || '',
        transaction_count: tag.transaction_count || 0,
        total_amount: tag.total_amount || 0
      }));

      // Créer le fichier CSV
      const headers = 'Nom,Type,Libellés associés,Catégorie,Transactions,Montant total\n';
      const csvContent = exportData.map(tag => 
        `"${tag.name}","${tag.expense_type}","${tag.associated_labels.join(';')}","${tag.category}",${tag.transaction_count},${tag.total_amount}`
      ).join('\n');

      const fullCsv = headers + csvContent;

      // Télécharger le fichier
      const blob = new Blob([fullCsv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `tags_export_${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
    } catch (error) {
      setImportError('Erreur lors de l\'export des tags');
    }
  };

  const handleDownloadTemplate = () => {
    try {
      // Créer un template avec des exemples
      const headers = 'Nom,Type,Libellés associés,Catégorie\n';
      const csvContent = TEMPLATE_TAGS.map(tag => 
        `"${tag.name}","${tag.expense_type}","${tag.associated_labels.join(';')}","${tag.category}"`
      ).join('\n');

      const fullCsv = headers + csvContent;

      const blob = new Blob([fullCsv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'template_tags.csv';
      link.click();
    } catch (error) {
      setImportError('Erreur lors du téléchargement du template');
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const csv = e.target?.result as string;
        const preview = parseCSV(csv);
        setImportPreview(preview);
        setIsImportModalOpen(true);
        setImportError(null);
      } catch (error) {
        setImportError('Erreur lors de la lecture du fichier CSV');
      }
    };
    reader.readAsText(file, 'utf-8');

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const parseCSV = (csvContent: string): ImportPreview => {
    const lines = csvContent.split('\n').filter(line => line.trim());
    const headers = lines[0].toLowerCase();
    
    if (!headers.includes('nom') || !headers.includes('type')) {
      throw new Error('Le fichier doit contenir au minimum les colonnes "Nom" et "Type"');
    }

    const valid: TagEditData[] = [];
    const invalid: Array<{ line: number; data: any; error: string }> = [];
    const duplicates: string[] = [];
    const existingNames = new Set((tags || []).map(t => t.name.toLowerCase()));
    const newNames = new Set<string>();

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (!line.trim()) continue;

      try {
        // Parse CSV line (basic implementation)
        const values = line.split(',').map(v => v.replace(/^"|"$/g, '').trim());
        
        const name = values[0];
        const type = values[1];
        const labels = values[2] ? values[2].split(';').filter(l => l.trim()) : [];
        const category = values[3] || undefined;

        // Validation
        if (!name) {
          invalid.push({ line: i + 1, data: values, error: 'Nom manquant' });
          continue;
        }

        if (!['fixed', 'variable'].includes(type)) {
          invalid.push({ line: i + 1, data: values, error: 'Type invalide (doit être "fixed" ou "variable")' });
          continue;
        }

        // Vérifier les doublons
        const nameLower = name.toLowerCase();
        if (existingNames.has(nameLower) || newNames.has(nameLower)) {
          duplicates.push(name);
          continue;
        }

        newNames.add(nameLower);
        valid.push({
          name: name,
          expense_type: type as 'fixed' | 'variable',
          associated_labels: labels,
          category: category
        });
      } catch (error) {
        invalid.push({ line: i + 1, data: line, error: 'Ligne mal formatée' });
      }
    }

    return { valid, invalid, duplicates };
  };

  const handleConfirmImport = async () => {
    if (!importPreview) return;

    try {
      setIsImporting(true);
      setImportError(null);

      // Importer tous les tags valides
      for (const tagData of importPreview.valid) {
        await createTag(tagData);
      }

      setIsImportModalOpen(false);
      setImportPreview(null);
    } catch (error) {
      setImportError('Erreur lors de l\'import des tags');
    } finally {
      setIsImporting(false);
    }
  };

  if (isLoading) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Chargement...</span>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          📁 Import / Export des Tags
        </h3>

        {/* Messages d'erreur */}
        {importError && (
          <Alert variant="error" className="mb-4">
            <div className="flex items-center justify-between">
              <span>{importError}</span>
              <button onClick={() => setImportError(null)} className="text-red-800 hover:text-red-900">
                ×
              </button>
            </div>
          </Alert>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* Export */}
          <div className="space-y-4">
            <div className="border-l-4 border-green-400 pl-4">
              <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                📤 Exporter vos tags
              </h4>
              <p className="text-sm text-gray-600 mb-3">
                Sauvegardez vos {tags?.length || 0} tag(s) actuel(s) dans un fichier CSV.
              </p>
              <Button
                onClick={handleExportTags}
                disabled={!tags || tags.length === 0}
                className="flex items-center gap-2"
              >
                <span>📥</span>
                Exporter ({tags?.length || 0} tags)
              </Button>
            </div>

            {/* Aperçu des données à exporter */}
            {tags && tags.length > 0 && (
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-xs text-gray-500 mb-2">Aperçu de l'export :</div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {safeSlice(tags, 0, 5).map((tag) => (
                    <div key={tag.name} className="flex items-center gap-2 text-sm">
                      <span className="font-mono text-xs bg-white px-1 rounded">{tag.name}</span>
                      <ErrorBoundary componentName="ExpenseTypeBadge" fallback={<span className="text-red-500">❌</span>}>
                        <ExpenseTypeBadge type={tag.expense_type} size="sm" />
                      </ErrorBoundary>
                      <span className="text-gray-500 text-xs">
                        ({tag.associated_labels?.length || 0} libellés)
                      </span>
                    </div>
                  ))}
                  {(tags?.length || 0) > 5 && (
                    <div className="text-xs text-gray-500">... et {(tags?.length || 0) - 5} autres</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Import */}
          <div className="space-y-4">
            <div className="border-l-4 border-blue-400 pl-4">
              <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                📥 Importer des tags
              </h4>
              <p className="text-sm text-gray-600 mb-3">
                Ajoutez de nouveaux tags depuis un fichier CSV.
              </p>
              <div className="space-y-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  className="flex items-center gap-2 w-full"
                >
                  <span>📂</span>
                  Choisir un fichier CSV
                </Button>
                <Button
                  onClick={handleDownloadTemplate}
                  size="sm"
                  variant="outline"
                  className="w-full text-xs"
                >
                  📋 Télécharger un template
                </Button>
              </div>
            </div>

            {/* Format attendu */}
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-xs text-blue-700 font-medium mb-2">Format CSV attendu :</div>
              <div className="text-xs font-mono text-blue-600 bg-white p-2 rounded">
                Nom,Type,Libellés associés,Catégorie<br />
                Restaurant,variable,restaurant;pizza,Alimentation<br />
                Netflix,fixed,netflix;streaming,Services
              </div>
            </div>
          </div>
        </div>

        {/* Templates prédéfinis */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            🎯 Templates prédéfinis
          </h4>
          <div className="grid md:grid-cols-3 gap-3">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              👨‍👩‍👧‍👦 Famille
            </Button>
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              🏢 Entreprise
            </Button>
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              🎓 Étudiant
            </Button>
          </div>
        </div>
      </Card>

      {/* Modal de prévisualisation d'import */}
      <Modal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        title="📥 Prévisualisation de l'import"
        size="xl"
      >
        {importPreview && (
          <div className="space-y-4">
            {/* Résumé */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="text-xl font-bold text-green-600">{importPreview.valid.length}</div>
                <div className="text-sm text-gray-600">Tags valides</div>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <div className="text-xl font-bold text-red-600">{importPreview.invalid.length}</div>
                <div className="text-sm text-gray-600">Erreurs</div>
              </div>
              <div className="text-center p-3 bg-yellow-50 rounded-lg">
                <div className="text-xl font-bold text-yellow-600">{importPreview.duplicates.length}</div>
                <div className="text-sm text-gray-600">Doublons</div>
              </div>
            </div>

            {/* Tags valides */}
            {importPreview.valid.length > 0 && (
              <div>
                <h4 className="font-medium text-green-700 mb-2">✅ Tags à importer :</h4>
                <div className="max-h-40 overflow-y-auto space-y-2">
                  {importPreview.valid.map((tag, index) => (
                    <div key={index} className="flex items-center gap-2 p-2 bg-green-50 rounded">
                      <span className="font-medium">{tag.name}</span>
                      <ExpenseTypeBadge type={tag.expense_type} size="sm" />
                      <span className="text-xs text-gray-500">
                        ({tag.associated_labels.length} libellés)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Erreurs */}
            {importPreview.invalid.length > 0 && (
              <div>
                <h4 className="font-medium text-red-700 mb-2">❌ Erreurs :</h4>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {importPreview.invalid.map((error, index) => (
                    <div key={index} className="text-sm p-2 bg-red-50 rounded">
                      Ligne {error.line}: {error.error}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Doublons */}
            {importPreview.duplicates.length > 0 && (
              <div>
                <h4 className="font-medium text-yellow-700 mb-2">⚠️ Doublons ignorés :</h4>
                <div className="flex flex-wrap gap-1">
                  {importPreview.duplicates.map((name, index) => (
                    <span key={index} className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-sm">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setIsImportModalOpen(false)}
                disabled={isImporting}
              >
                Annuler
              </Button>
              <Button
                onClick={handleConfirmImport}
                disabled={importPreview.valid.length === 0 || isImporting}
              >
                {isImporting ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Import en cours...
                  </div>
                ) : (
                  `Importer ${importPreview.valid.length} tag(s)`
                )}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}