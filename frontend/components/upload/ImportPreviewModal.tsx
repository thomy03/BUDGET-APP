'use client';

import { useState, useCallback, useEffect } from 'react';
import { importPreviewApi, ImportPreviewResponse } from '../../lib/api';
import { Button } from '../ui';
import {
  XMarkIcon,
  DocumentArrowUpIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentDuplicateIcon,
  CalendarIcon,
  CurrencyEuroIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

interface ImportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  file: File | null;
  onConfirmImport: () => void;
}

export function ImportPreviewModal({ isOpen, onClose, file, onConfirmImport }: ImportPreviewModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);

  const loadPreview = useCallback(async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const result = await importPreviewApi.preview(file, 10);
      setPreview(result);
    } catch (err: any) {
      console.error('Preview error:', err);
      setError(err.response?.data?.detail || err.message || 'Erreur lors de la prévisualisation');
    } finally {
      setLoading(false);
    }
  }, [file]);

  // Charger la preview quand le modal s'ouvre avec un fichier
  useEffect(() => {
    if (isOpen && file && !preview && !loading) {
      loadPreview();
    }
  }, [isOpen, file]);

  const handleClose = () => {
    setPreview(null);
    setError(null);
    onClose();
  };

  const handleConfirm = () => {
    onConfirmImport();
    handleClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-emerald-600 to-teal-600">
          <div className="flex items-center gap-3">
            <DocumentArrowUpIcon className="w-6 h-6 text-white" />
            <div>
              <h2 className="text-lg font-bold text-white">Prévisualisation de l'import</h2>
              <p className="text-sm text-emerald-100">
                {file?.name || 'Aucun fichier'}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mb-4"></div>
              <p className="text-gray-600 dark:text-gray-300">Analyse du fichier en cours...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <ExclamationTriangleIcon className="w-6 h-6 text-red-600 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-red-800 dark:text-red-200">Erreur d'analyse</h3>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
                </div>
              </div>
              <Button onClick={loadPreview} variant="outline" className="mt-4">
                Réessayer
              </Button>
            </div>
          ) : preview ? (
            <div className="space-y-6">
              {/* Résumé */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-600">{preview.total_rows}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Lignes totales</p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-green-600">{preview.valid_rows}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Valides</p>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-red-600">{preview.invalid_rows}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Invalides</p>
                </div>
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-blue-600">{preview.months_detected.length}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Mois détectés</p>
                </div>
              </div>

              {/* Statut global */}
              <div className={`rounded-lg p-4 flex items-center gap-3 ${
                preview.ready_to_import
                  ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                  : 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
              }`}>
                {preview.ready_to_import ? (
                  <>
                    <CheckCircleIcon className="w-6 h-6 text-green-600" />
                    <span className="text-green-800 dark:text-green-200 font-medium">
                      Fichier valide et prêt pour l'import
                    </span>
                  </>
                ) : (
                  <>
                    <ExclamationTriangleIcon className="w-6 h-6 text-yellow-600" />
                    <span className="text-yellow-800 dark:text-yellow-200 font-medium">
                      Attention : vérifiez les avertissements avant d'importer
                    </span>
                  </>
                )}
              </div>

              {/* Mois détectés */}
              {preview.months_detected.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <CalendarIcon className="w-4 h-4" />
                    Mois détectés
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {preview.months_detected.map(month => (
                      <span
                        key={month}
                        className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded-full text-sm"
                      >
                        {month} ({preview.months_summary[month] || 0} transactions)
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Avertissements */}
              {preview.validation_warnings && preview.validation_warnings.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
                  <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-200 mb-2 flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-4 h-4" />
                    Avertissements ({preview.validation_warnings.length})
                  </h3>
                  <ul className="space-y-1">
                    {preview.validation_warnings.map((warning, idx) => (
                      <li key={idx} className="text-sm text-yellow-700 dark:text-yellow-300">
                        {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Doublons potentiels */}
              {preview.potential_duplicates && preview.potential_duplicates.length > 0 && (
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4 border border-orange-200 dark:border-orange-800">
                  <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-2 flex items-center gap-2">
                    <DocumentDuplicateIcon className="w-4 h-4" />
                    Doublons potentiels ({preview.potential_duplicates.length})
                  </h3>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {preview.potential_duplicates.slice(0, 5).map((dup, idx) => (
                      <div key={idx} className="text-sm bg-white dark:bg-gray-700 rounded p-2">
                        <span className="font-medium">{dup.label || dup.date_op}</span>
                        {dup.amount && (
                          <span className="ml-2 text-gray-500">
                            {Number(dup.amount).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                          </span>
                        )}
                      </div>
                    ))}
                    {preview.potential_duplicates.length > 5 && (
                      <p className="text-xs text-orange-600 dark:text-orange-400">
                        + {preview.potential_duplicates.length - 5} autres doublons potentiels
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Aperçu des transactions */}
              {preview.sample_transactions && preview.sample_transactions.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <CurrencyEuroIcon className="w-4 h-4" />
                    Aperçu des transactions ({preview.sample_transactions.length} premières)
                  </h3>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-100 dark:bg-gray-600">
                          <tr>
                            <th className="px-3 py-2 text-left text-gray-600 dark:text-gray-300">Date</th>
                            <th className="px-3 py-2 text-left text-gray-600 dark:text-gray-300">Libellé</th>
                            <th className="px-3 py-2 text-right text-gray-600 dark:text-gray-300">Montant</th>
                            <th className="px-3 py-2 text-center text-gray-600 dark:text-gray-300">Statut</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-600">
                          {preview.sample_transactions.map((tx, idx) => (
                            <tr key={idx} className="hover:bg-gray-100 dark:hover:bg-gray-600/50">
                              <td className="px-3 py-2 whitespace-nowrap text-gray-900 dark:text-gray-100">
                                {tx.date_op}
                              </td>
                              <td className="px-3 py-2 text-gray-700 dark:text-gray-300 max-w-xs truncate">
                                {tx.label}
                              </td>
                              <td className={`px-3 py-2 text-right whitespace-nowrap font-medium ${
                                tx.amount < 0 ? 'text-red-600' : 'text-green-600'
                              }`}>
                                {tx.amount.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                              </td>
                              <td className="px-3 py-2 text-center">
                                {tx.is_valid ? (
                                  <CheckCircleIcon className="w-5 h-5 text-green-500 mx-auto" />
                                ) : (
                                  <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500 mx-auto" />
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Colonnes détectées */}
              {preview.columns_detected && preview.columns_detected.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <InformationCircleIcon className="w-4 h-4" />
                    Colonnes détectées
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {preview.columns_detected.map(col => (
                      <span
                        key={col}
                        className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs"
                      >
                        {col}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <DocumentArrowUpIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Sélectionnez un fichier pour voir l'aperçu</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {preview && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {preview.file_type?.toUpperCase()} - {preview.total_rows} lignes
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={handleClose}>
                Annuler
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={!preview.ready_to_import && preview.valid_rows === 0}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                <DocumentArrowUpIcon className="w-4 h-4 mr-2" />
                Importer {preview.valid_rows} transactions
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ImportPreviewModal;
