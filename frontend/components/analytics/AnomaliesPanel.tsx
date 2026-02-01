'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Card } from '../ui';
import { predictionsApi, api, Anomaly, DuplicateGroup, AnomaliesOverview, MLStatus } from '../../lib/api';

interface AnomaliesPanelProps {
  month: string;
  className?: string;
  onTransactionClick?: (transactionId: string) => void;
}

type SeverityFilter = 'all' | 'high' | 'medium' | 'low';
type TabType = 'anomalies' | 'duplicates';

export function AnomaliesPanel({ month, className = '', onTransactionClick }: AnomaliesPanelProps) {
  const [data, setData] = useState<AnomaliesOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [mlStatus, setMlStatus] = useState<MLStatus | null>(null);
  const [error, setError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<TabType>('anomalies');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [dismissedAnomalies, setDismissedAnomalies] = useState<Set<string>>(new Set());
  const [dismissedDuplicates, setDismissedDuplicates] = useState<Set<number>>(new Set());
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const retryIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check ML status first
  const checkMlStatus = useCallback(async () => {
    try {
      const status = await predictionsApi.getStatus();
      setMlStatus(status);
      return status;
    } catch (err) {
      console.warn('Could not check ML status:', err);
      return null;
    }
  }, []);

  const loadAnomalies = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      // Check ML status first
      const status = await checkMlStatus();

      // If ML is training but not ready, just show status and wait
      if (status && status.training && !status.ready) {
        setLoading(false);
        // Set up auto-retry every 5 seconds while training
        if (!retryIntervalRef.current) {
          retryIntervalRef.current = setInterval(async () => {
            const newStatus = await checkMlStatus();
            if (newStatus && newStatus.ready) {
              // ML is now ready, clear interval and load data
              if (retryIntervalRef.current) {
                clearInterval(retryIntervalRef.current);
                retryIntervalRef.current = null;
              }
              loadAnomalies();
            }
          }, 5000);
        }
        return;
      }

      // Clear any existing retry interval
      if (retryIntervalRef.current) {
        clearInterval(retryIntervalRef.current);
        retryIntervalRef.current = null;
      }

      const result = await predictionsApi.detectAnomalies(month, 50);
      setData(result);

      // Check if response indicates ML is still training
      if (result.summary?.message?.includes('entrainement')) {
        // Backend returned training message, set up retry
        if (!retryIntervalRef.current) {
          retryIntervalRef.current = setInterval(loadAnomalies, 5000);
        }
      }
    } catch (err: any) {
      console.error('Erreur chargement anomalies:', err);
      setError(err.response?.data?.detail || err.message || 'Erreur lors du chargement des anomalies');
    } finally {
      setLoading(false);
    }
  }, [month, checkMlStatus]);

  useEffect(() => {
    if (month) {
      loadAnomalies();
    }

    // Cleanup interval on unmount
    return () => {
      if (retryIntervalRef.current) {
        clearInterval(retryIntervalRef.current);
        retryIntervalRef.current = null;
      }
    };
  }, [month, loadAnomalies]);

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR'
    }).format(Math.abs(value));
  };

  // Get severity level from score
  const getSeverityLevel = (severity: number): 'high' | 'medium' | 'low' => {
    if (severity >= 0.7) return 'high';
    if (severity >= 0.4) return 'medium';
    return 'low';
  };

  // Get severity color classes
  const getSeverityColor = (severity: number) => {
    const level = getSeverityLevel(severity);
    switch (level) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'low': return 'bg-amber-100 text-amber-800 border-amber-200';
    }
  };

  const getSeverityBadgeColor = (severity: number) => {
    const level = getSeverityLevel(severity);
    switch (level) {
      case 'high': return 'bg-red-500 text-white';
      case 'medium': return 'bg-orange-500 text-white';
      case 'low': return 'bg-amber-500 text-white';
    }
  };

  // Get anomaly type icon
  const getAnomalyIcon = (type: string) => {
    switch (type) {
      case 'amount': return '💰';
      case 'frequency': return '📊';
      case 'merchant': return '🏪';
      case 'duplicate': return '📋';
      case 'statistical': return '📈';
      default: return '⚠️';
    }
  };

  // Get anomaly type label
  const getAnomalyTypeLabel = (type: string) => {
    switch (type) {
      case 'amount': return 'Montant inhabituel';
      case 'frequency': return 'Fréquence anormale';
      case 'merchant': return 'Nouveau marchand';
      case 'duplicate': return 'Doublon potentiel';
      case 'statistical': return 'Statistiquement anormal';
      default: return 'Anomalie détectée';
    }
  };

  // Get duplicate type badge
  const getDuplicateTypeBadge = (type: string) => {
    switch (type) {
      case 'exact': return { label: 'Exact', color: 'bg-red-100 text-red-700' };
      case 'fuzzy': return { label: 'Similaire', color: 'bg-orange-100 text-orange-700' };
      case 'temporal': return { label: 'Temporel', color: 'bg-amber-100 text-amber-700' };
      default: return { label: type, color: 'bg-gray-100 text-gray-700' };
    }
  };

  // Filter anomalies by severity
  const filteredAnomalies = data?.anomalies.filter(a => {
    if (dismissedAnomalies.has(a.transaction_id)) return false;
    if (severityFilter === 'all') return true;
    return getSeverityLevel(a.severity) === severityFilter;
  }) || [];

  // Filter duplicates (not dismissed)
  const filteredDuplicates = data?.duplicate_groups.filter((_, idx) =>
    !dismissedDuplicates.has(idx)
  ) || [];

  // Dismiss anomaly
  const dismissAnomaly = (transactionId: string) => {
    setDismissedAnomalies(prev => new Set([...prev, transactionId]));
  };

  // Dismiss duplicate group
  const dismissDuplicate = (index: number) => {
    setDismissedDuplicates(prev => new Set([...prev, index]));
  };

  // Mark transaction as excluded (for duplicates)
  const excludeTransaction = async (transactionId: string) => {
    try {
      setProcessingAction(transactionId);
      await api.patch(`/transactions/${transactionId}`, { exclude: true });
      // Reload data
      await loadAnomalies();
    } catch (err: any) {
      console.error('Erreur exclusion transaction:', err);
    } finally {
      setProcessingAction(null);
    }
  };

  // ML Training state - show special UI when training is in progress
  if (!loading && mlStatus && mlStatus.training && !mlStatus.ready) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-purple-100">
            <svg className="w-8 h-8 text-purple-600 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            🤖 Entraînement ML en cours
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            {mlStatus.message || 'Les modèles d\'intelligence artificielle se préparent...'}
          </p>
          <p className="text-xs text-gray-500">
            Rechargement automatique toutes les 5 secondes
          </p>
        </div>
      </Card>
    );
  }

  // Loading state
  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="flex gap-2 mb-4">
            <div className="h-8 bg-gray-200 rounded w-24"></div>
            <div className="h-8 bg-gray-200 rounded w-24"></div>
          </div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className={`p-6 border-red-200 bg-red-50 ${className}`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">❌</span>
          <div>
            <h3 className="text-lg font-semibold text-red-900">Erreur de chargement</h3>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
        <button
          onClick={loadAnomalies}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          Réessayer
        </button>
      </Card>
    );
  }

  const anomalyCount = filteredAnomalies.length;
  const duplicateCount = filteredDuplicates.length;
  const highSeverityCount = data?.summary.high_severity_count || 0;

  return (
    <Card className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔍</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Détection d'Anomalies ML
            </h3>
            <p className="text-sm text-gray-500">
              {month} • Analyse intelligente des transactions
            </p>
          </div>
        </div>

        {/* Summary badges */}
        <div className="flex items-center gap-2">
          {highSeverityCount > 0 && (
            <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">
              {highSeverityCount} critique{highSeverityCount > 1 ? 's' : ''}
            </span>
          )}
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {data?.summary.total_transactions || 0} transactions analysées
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200 pb-2">
        <button
          onClick={() => setActiveTab('anomalies')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            activeTab === 'anomalies'
              ? 'bg-purple-100 text-purple-700 border-b-2 border-purple-500'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          Anomalies
          {anomalyCount > 0 && (
            <span className="ml-2 px-1.5 py-0.5 text-xs bg-purple-500 text-white rounded-full">
              {anomalyCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('duplicates')}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            activeTab === 'duplicates'
              ? 'bg-orange-100 text-orange-700 border-b-2 border-orange-500'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          Doublons
          {duplicateCount > 0 && (
            <span className="ml-2 px-1.5 py-0.5 text-xs bg-orange-500 text-white rounded-full">
              {duplicateCount}
            </span>
          )}
        </button>
      </div>

      {/* Anomalies Tab */}
      {activeTab === 'anomalies' && (
        <>
          {/* Severity Filter */}
          <div className="flex gap-2 mb-4">
            {(['all', 'high', 'medium', 'low'] as SeverityFilter[]).map((filter) => (
              <button
                key={filter}
                onClick={() => setSeverityFilter(filter)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                  severityFilter === filter
                    ? filter === 'all' ? 'bg-gray-800 text-white'
                      : filter === 'high' ? 'bg-red-500 text-white'
                      : filter === 'medium' ? 'bg-orange-500 text-white'
                      : 'bg-amber-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filter === 'all' ? 'Toutes' : filter === 'high' ? 'Critiques' : filter === 'medium' ? 'Moyennes' : 'Faibles'}
              </button>
            ))}
          </div>

          {/* Anomalies List */}
          {filteredAnomalies.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-5xl mb-3">✅</div>
              <h4 className="text-lg font-medium text-gray-700">Aucune anomalie détectée</h4>
              <p className="text-sm text-gray-500 mt-1">
                {severityFilter !== 'all'
                  ? `Aucune anomalie de sévérité "${severityFilter}" ce mois-ci.`
                  : 'Vos transactions semblent normales ce mois-ci.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
              {filteredAnomalies.map((anomaly, idx) => (
                <div
                  key={`${anomaly.transaction_id}-${idx}`}
                  className={`border rounded-lg p-4 transition-all hover:shadow-md ${getSeverityColor(anomaly.severity)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">{getAnomalyIcon(anomaly.anomaly_type)}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-gray-900">
                            {getAnomalyTypeLabel(anomaly.anomaly_type)}
                          </h4>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getSeverityBadgeColor(anomaly.severity)}`}>
                            {(anomaly.severity * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{anomaly.explanation}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <span>ID: #{anomaly.transaction_id}</span>
                          <span>Confiance: {(anomaly.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {onTransactionClick && (
                        <button
                          onClick={() => onTransactionClick(anomaly.transaction_id)}
                          className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Voir la transaction"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                      )}
                      <button
                        onClick={() => dismissAnomaly(anomaly.transaction_id)}
                        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Ignorer"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Duplicates Tab */}
      {activeTab === 'duplicates' && (
        <>
          {filteredDuplicates.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-5xl mb-3">📋</div>
              <h4 className="text-lg font-medium text-gray-700">Aucun doublon détecté</h4>
              <p className="text-sm text-gray-500 mt-1">
                Pas de transactions en double ce mois-ci.
              </p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
              {filteredDuplicates.map((group, idx) => {
                const typeBadge = getDuplicateTypeBadge(group.duplicate_type);
                return (
                  <div
                    key={idx}
                    className="border border-orange-200 bg-orange-50 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">📋</span>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${typeBadge.color}`}>
                          {typeBadge.label}
                        </span>
                        <span className="text-sm text-gray-600">
                          Similarité: {group.similarity_score.toFixed(0)}%
                        </span>
                      </div>
                      <button
                        onClick={() => dismissDuplicate(idx)}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                        title="Ignorer ce groupe"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>

                    <p className="text-sm text-gray-700 mb-3">{group.explanation}</p>

                    {/* Transaction IDs with actions */}
                    <div className="flex flex-wrap gap-2">
                      {group.transaction_ids.map((txId, txIdx) => (
                        <div
                          key={txId}
                          className="flex items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded text-sm"
                        >
                          <span className="text-gray-600">#{txId}</span>
                          {txIdx > 0 && (
                            <button
                              onClick={() => excludeTransaction(txId)}
                              disabled={processingAction === txId}
                              className="ml-1 p-0.5 text-red-500 hover:text-red-700 disabled:opacity-50"
                              title="Exclure cette transaction"
                            >
                              {processingAction === txId ? (
                                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                              ) : (
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              )}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <p className="text-xs text-gray-500 mt-2">
                      💡 Cliquez sur 🗑️ pour exclure les doublons (garde la première transaction)
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Summary Stats */}
      {data && (anomalyCount > 0 || duplicateCount > 0) && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-sm text-gray-600">Anomalies</div>
              <div className="text-2xl font-bold text-purple-600">{data.summary.anomalies_found}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Doublons</div>
              <div className="text-2xl font-bold text-orange-600">{data.summary.duplicates_found}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Critiques</div>
              <div className="text-2xl font-bold text-red-600">{highSeverityCount}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Analysées</div>
              <div className="text-2xl font-bold text-gray-600">{data.summary.total_transactions}</div>
            </div>
          </div>
        </div>
      )}

      {/* Refresh button */}
      <div className="mt-4 text-center">
        <button
          onClick={loadAnomalies}
          disabled={loading}
          className="text-sm text-purple-600 hover:text-purple-700 hover:underline disabled:opacity-50"
        >
          🔄 Actualiser l'analyse
        </button>
      </div>
    </Card>
  );
}

export default AnomaliesPanel;
