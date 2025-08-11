'use client';

import React, { useState } from 'react';
import { Button, Card } from '../ui';
import { api } from '../../lib/api';

interface ExportManagerProps {
  availableMonths: string[];
  className?: string;
}

export function ExportManager({ availableMonths, className = "" }: ExportManagerProps) {
  const [selectedMonths, setSelectedMonths] = useState<string[]>(availableMonths.slice(-3));
  const [exportFormat, setExportFormat] = useState<'csv' | 'pdf'>('csv');
  const [includeCharts, setIncludeCharts] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string>("");

  const handleExport = async () => {
    if (selectedMonths.length === 0) {
      setError("Veuillez sélectionner au moins un mois");
      return;
    }

    try {
      setExporting(true);
      setError("");

      const response = await api.post('/analytics/export', {
        months: selectedMonths,
        format: exportFormat,
        include_charts: includeCharts
      }, {
        responseType: exportFormat === 'csv' ? 'blob' : 'json'
      });

      if (exportFormat === 'csv') {
        // Téléchargement CSV
        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `analytics_${selectedMonths.join('_')}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } else {
        // Pour le PDF (pas encore implémenté côté backend)
        console.log('Export PDF:', response.data);
        setError("L'export PDF sera disponible prochainement");
      }
    } catch (err: any) {
      console.error('Erreur export:', err);
      setError(err.response?.data?.detail || "Erreur lors de l'export");
    } finally {
      setExporting(false);
    }
  };

  const toggleMonth = (month: string) => {
    setSelectedMonths(prev => 
      prev.includes(month) 
        ? prev.filter(m => m !== month)
        : [...prev, month].sort()
    );
  };

  const selectAllMonths = () => {
    setSelectedMonths([...availableMonths]);
  };

  const clearSelection = () => {
    setSelectedMonths([]);
  };

  const selectLastN = (n: number) => {
    setSelectedMonths(availableMonths.slice(-n));
  };

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          📥 Export des Données
        </h3>
        <p className="text-sm text-gray-600">
          Exportez vos analyses au format CSV ou PDF
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {/* Sélection des mois */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Sélection des mois à exporter
        </label>
        
        {/* Actions rapides */}
        <div className="flex flex-wrap gap-2 mb-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => selectLastN(3)}
            className="text-xs"
          >
            3 derniers mois
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => selectLastN(6)}
            className="text-xs"
          >
            6 derniers mois
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => selectLastN(12)}
            className="text-xs"
          >
            12 derniers mois
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={selectAllMonths}
            className="text-xs"
          >
            Tout sélectionner
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={clearSelection}
            className="text-xs"
          >
            Tout désélectionner
          </Button>
        </div>

        {/* Grille des mois */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50">
          {availableMonths.sort().reverse().map(month => (
            <label key={month} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedMonths.includes(month)}
                onChange={() => toggleMonth(month)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">{month}</span>
            </label>
          ))}
        </div>
        
        <p className="text-xs text-gray-500 mt-2">
          {selectedMonths.length} mois sélectionnés
        </p>
      </div>

      {/* Format d'export */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Format d'export
        </label>
        <div className="space-y-2">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              value="csv"
              checked={exportFormat === 'csv'}
              onChange={(e) => setExportFormat(e.target.value as 'csv')}
              className="text-blue-600 focus:ring-blue-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-700">CSV (Excel)</span>
              <p className="text-xs text-gray-500">Format compatible Excel avec toutes les données</p>
            </div>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer opacity-50">
            <input
              type="radio"
              value="pdf"
              checked={exportFormat === 'pdf'}
              onChange={(e) => setExportFormat(e.target.value as 'pdf')}
              className="text-blue-600 focus:ring-blue-500"
              disabled
            />
            <div>
              <span className="text-sm font-medium text-gray-700">PDF (Rapport)</span>
              <p className="text-xs text-gray-500">Rapport formaté avec graphiques (bientôt disponible)</p>
            </div>
          </label>
        </div>
      </div>

      {/* Options supplémentaires */}
      {exportFormat === 'pdf' && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Options PDF
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeCharts}
              onChange={(e) => setIncludeCharts(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Inclure les graphiques</span>
          </label>
        </div>
      )}

      {/* Aperçu de l'export */}
      <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h4 className="text-sm font-medium text-blue-800 mb-2">Aperçu de l'export</h4>
        <div className="text-xs text-blue-700 space-y-1">
          <p>• <strong>Période :</strong> {selectedMonths.length > 0 ? `${selectedMonths[0]} à ${selectedMonths[selectedMonths.length - 1]}` : 'Aucun mois sélectionné'}</p>
          <p>• <strong>Format :</strong> {exportFormat.toUpperCase()}</p>
          <p>• <strong>Données incluses :</strong> KPIs, tendances mensuelles, catégories, anomalies</p>
          {exportFormat === 'pdf' && (
            <p>• <strong>Graphiques :</strong> {includeCharts ? 'Inclus' : 'Non inclus'}</p>
          )}
        </div>
      </div>

      {/* Bouton d'export */}
      <Button
        onClick={handleExport}
        disabled={exporting || selectedMonths.length === 0}
        className="w-full"
      >
        {exporting ? (
          <div className="flex items-center space-x-2">
            <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
            <span>Export en cours...</span>
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            <span>📥</span>
            <span>Exporter {exportFormat.toUpperCase()}</span>
          </div>
        )}
      </Button>

      {/* Informations complémentaires */}
      <div className="mt-4 text-xs text-gray-500 space-y-1">
        <p>• Les données exportées respectent la période sélectionnée</p>
        <p>• L'export CSV est compatible avec Excel, Google Sheets, etc.</p>
        <p>• Les montants sont en euros avec 2 décimales</p>
      </div>
    </Card>
  );
}

export default ExportManager;