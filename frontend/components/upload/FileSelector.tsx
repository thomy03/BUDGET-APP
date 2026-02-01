'use client';

import React, { useRef } from 'react';
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
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFileChange(e.target.files?.[0] || null);
  };

  const clearFile = () => {
    onFileChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <Card padding="lg">
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold mb-2 text-zinc-900">Sélectionner un fichier</h3>
          <p className="text-sm text-zinc-600 mb-4">
            Importez vos transactions bancaires (CSV, Excel ou PDF de relevé bancaire).
            Le système détecte automatiquement le format et les colonnes.
          </p>

          <div className="space-y-4">
            <div className="flex items-center gap-4">
              {/* Input caché */}
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileChange}
                accept=".csv,.xlsx,.xls,.pdf"
                className="hidden"
              />
              {/* Bouton personnalisé */}
              <button
                type="button"
                onClick={handleButtonClick}
                className="py-2 px-4 rounded-full border-0 text-sm font-semibold bg-zinc-50 text-zinc-700 hover:bg-zinc-100 transition-colors"
              >
                Choisir un fichier
              </button>
              {/* Texte d'état personnalisé */}
              <span className={"text-sm " + (file ? "text-teal-600 font-medium" : "text-zinc-500")}>
                {file ? file.name : "Aucun fichier sélectionné"}
              </span>
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
