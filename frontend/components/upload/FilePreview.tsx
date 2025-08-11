'use client';

import React, { useEffect, useState } from 'react';
import { Card, LoadingSpinner } from '../ui';

interface FilePreviewProps {
  file: File | null;
}

interface PreviewData {
  headers: string[];
  rows: string[][];
  totalRows: number;
  errors?: string[];
}

const FilePreview = React.memo<FilePreviewProps>(({ file }) => {
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreviewData(null);
      setError(null);
      return;
    }

    const parseFile = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const text = await file.text();
        
        // Simple parsing CSV (pour preview seulement)
        const lines = text.split('\n').filter(line => line.trim());
        
        if (lines.length === 0) {
          throw new Error('Le fichier est vide');
        }

        // Détecter le séparateur (virgule ou point-virgule)
        const firstLine = lines[0];
        const separator = firstLine.includes(';') ? ';' : ',';
        
        // Parser l'en-tête
        const headers = lines[0].split(separator).map(h => h.trim().replace(/['"]/g, ''));
        
        // Parser les premières lignes de données (max 5)
        const dataLines = lines.slice(1, Math.min(6, lines.length));
        const rows = dataLines.map(line => 
          line.split(separator).map(cell => cell.trim().replace(/['"]/g, ''))
        );

        // Validation basique avec mapping flexible des colonnes
        const errors: string[] = [];
        
        // Définition des colonnes requises avec leurs variantes acceptées
        const columnMappings = {
          date: ['date', 'datum', 'transaction_date', 'tran_date'],
          description: ['description', 'libelle', 'libellé', 'label', 'desc', 'details'],
          montant: ['montant', 'amount', 'somme', 'valeur', 'sum', 'total'],
          compte: ['compte', 'account', 'accountlabel', 'account_label', 'accountnum', 'account_num', 'bank_account']
        };
        
        const headerLower = headers.map(h => h.toLowerCase().replace(/[^a-z0-9]/g, ''));
        
        const missingColumns: string[] = [];
        
        // Vérifier chaque colonne requise
        Object.entries(columnMappings).forEach(([requiredCol, variants]) => {
          const found = variants.some(variant => 
            headerLower.some(header => 
              header.includes(variant.toLowerCase()) || 
              variant.toLowerCase().includes(header)
            )
          );
          
          if (!found) {
            missingColumns.push(requiredCol);
          }
        });
        
        if (missingColumns.length > 0) {
          errors.push(`Colonnes manquantes: ${missingColumns.join(', ')}. Colonnes détectées: ${headers.join(', ')}`);
        }

        setPreviewData({
          headers,
          rows,
          totalRows: lines.length - 1,
          errors: errors.length > 0 ? errors : undefined
        });

      } catch (err: any) {
        console.error('Preview parsing error:', err);
        setError(err.message || 'Erreur lors de la lecture du fichier');
      } finally {
        setLoading(false);
      }
    };

    // Delay pour éviter trop d'appels
    const timeoutId = setTimeout(parseFile, 300);
    return () => clearTimeout(timeoutId);
  }, [file]);

  if (!file) return null;

  return (
    <Card padding="lg">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          👀 Aperçu du fichier
          <span className="text-sm font-normal text-zinc-500">
            ({file.name})
          </span>
        </h3>

        {loading ? (
          <div className="flex items-center gap-3 py-4">
            <LoadingSpinner size="sm" />
            <span className="text-sm text-zinc-600">Analyse du fichier...</span>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-red-600">⚠️</span>
              <div>
                <div className="font-medium text-red-800">Erreur de lecture</div>
                <div className="text-sm text-red-700 mt-1">{error}</div>
              </div>
            </div>
          </div>
        ) : previewData ? (
          <div className="space-y-4">
            {/* Erreurs de validation */}
            {previewData.errors && previewData.errors.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <span className="text-amber-600">⚠️</span>
                  <div>
                    <div className="font-medium text-amber-800">Problèmes détectés</div>
                    <ul className="text-sm text-amber-700 mt-1 space-y-1">
                      {previewData.errors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Informations sur le fichier */}
            <div className="flex items-center gap-6 text-sm text-zinc-600">
              <span>📊 {previewData.totalRows} ligne{previewData.totalRows > 1 ? 's' : ''} de données</span>
              <span>📋 {previewData.headers.length} colonne{previewData.headers.length > 1 ? 's' : ''}</span>
            </div>

            {/* Tableau preview */}
            <div className="border border-zinc-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-50">
                    <tr>
                      {previewData.headers.map((header, index) => (
                        <th 
                          key={index}
                          className="px-3 py-2 text-left font-medium text-zinc-700 border-r border-zinc-200 last:border-r-0"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="border-t border-zinc-200">
                        {row.map((cell, cellIndex) => (
                          <td 
                            key={cellIndex}
                            className="px-3 py-2 text-zinc-600 border-r border-zinc-200 last:border-r-0 max-w-xs truncate"
                            title={cell}
                          >
                            {cell || <span className="text-zinc-400">—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {previewData.totalRows > 5 && (
                <div className="bg-zinc-50 px-3 py-2 text-xs text-zinc-500 text-center border-t border-zinc-200">
                  ... et {previewData.totalRows - 5} autres ligne{previewData.totalRows - 5 > 1 ? 's' : ''}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  );
});

FilePreview.displayName = 'FilePreview';

export default FilePreview;