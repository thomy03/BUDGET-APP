'use client';

import React from 'react';
import { Card, Button } from '../ui';

interface FileSelectorProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  loading: boolean;
  onUpload: () => void;
}

const FileSelector = React.memo<FileSelectorProps>(({ 
  file, 
  onFileChange, 
  loading, 
  onUpload 
}) => {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFileChange(e.target.files?.[0] || null);
  };

  const clearFile = () => onFileChange(null);

  return (
    <Card padding="lg">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-2">Sélectionner un fichier</h3>
          <p className="text-sm text-zinc-600 mb-4">
            Importez vos transactions bancaires. Le fichier doit contenir les colonnes : 
            Date, Description, Montant, Compte.
          </p>
          
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <input 
                type="file" 
                onChange={handleFileChange}
                accept=".csv,.xlsx,.xls"
                className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-zinc-50 file:text-zinc-700 hover:file:bg-zinc-100"
              />
            </div>
            
            {file && (
              <div className="flex items-center gap-2 text-sm text-zinc-600">
                <span>📄 {file.name}</span>
                <span>•</span>
                <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 pt-4 border-t">
          <Button 
            variant="primary" 
            onClick={onUpload}
            disabled={!file || loading}
            loading={loading}
            className="min-w-[120px]"
          >
            {loading ? 'Import en cours...' : 'Importer'}
          </Button>
          
          {file && !loading && (
            <Button 
              variant="secondary" 
              onClick={clearFile}
            >
              Annuler
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
});

FileSelector.displayName = 'FileSelector';

export default FileSelector;