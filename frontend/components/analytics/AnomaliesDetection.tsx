'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '../ui';
import { api } from '../../lib/api';

interface Anomaly {
  transaction_id: number;
  date: string;
  amount: number;
  category: string;
  label: string;
  anomaly_type: string;
  score: number;
}

interface AnomaliesDetectionProps {
  month: string;
  className?: string;
}

export function AnomaliesDetection({ month, className = "" }: AnomaliesDetectionProps) {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const loadAnomalies = async () => {
      try {
        setLoading(true);
        setError("");
        
        const response = await api.get(`/analytics/anomalies?month=${month}`);
        setAnomalies(response.data);
      } catch (err: any) {
        console.error('Erreur chargement anomalies:', err);
        setError(err.response?.data?.detail || "Erreur lors du chargement des anomalies");
      } finally {
        setLoading(false);
      }
    };

    if (month) {
      loadAnomalies();
    }
  }, [month]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR' 
    }).format(Math.abs(value));
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const getAnomalyTypeIcon = (type: string) => {
    switch (type) {
      case 'high_amount': return '💰';
      case 'unusual_category': return '🔍';
      case 'frequency_spike': return '📊';
      default: return '⚠️';
    }
  };

  const getAnomalyTypeLabel = (type: string) => {
    switch (type) {
      case 'high_amount': return 'Montant élevé';
      case 'unusual_category': return 'Catégorie inhabituelle';
      case 'frequency_spike': return 'Pic de fréquence';
      default: return 'Anomalie détectée';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'bg-red-100 text-red-800';
    if (score >= 0.6) return 'bg-orange-100 text-orange-800';
    if (score >= 0.4) return 'bg-amber-100 text-amber-800';
    return 'bg-blue-100 text-blue-800';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.8) return 'Critique';
    if (score >= 0.6) return 'Élevée';
    if (score >= 0.4) return 'Modérée';
    return 'Faible';
  };

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 border-red-200 bg-red-50 ${className}`}>
        <h3 className="text-lg font-semibold text-red-900 mb-2">Erreur</h3>
        <p className="text-red-600">{error}</p>
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          🔍 Détection d'Anomalies
          {anomalies.length > 0 && (
            <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
              {anomalies.length}
            </span>
          )}
        </h3>
        <p className="text-sm text-gray-600">
          {month} • Analyse des transactions inhabituelles
        </p>
      </div>

      {!anomalies.length ? (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">✅</div>
          <p className="text-lg font-medium text-gray-700">Aucune anomalie détectée</p>
          <p className="text-sm">Vos dépenses semblent normales ce mois-ci.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {anomalies.map((anomaly, index) => (
            <div
              key={`${anomaly.transaction_id}-${index}`}
              className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">
                    {getAnomalyTypeIcon(anomaly.anomaly_type)}
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {getAnomalyTypeLabel(anomaly.anomaly_type)}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {formatDate(anomaly.date)} • {anomaly.category}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getScoreColor(anomaly.score)}`}>
                    {getScoreLabel(anomaly.score)}
                  </span>
                  <span className="text-lg font-bold text-red-600">
                    {formatCurrency(anomaly.amount)}
                  </span>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-800 font-medium mb-1">
                  Transaction: {anomaly.label}
                </p>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">
                    Score d'anomalie: {(anomaly.score * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-gray-500">
                    ID: #{anomaly.transaction_id}
                  </span>
                </div>
              </div>

              {/* Suggestions basées sur le type d'anomalie */}
              <div className="mt-3 p-2 bg-blue-50 rounded border-l-4 border-blue-400">
                <div className="text-xs text-blue-800">
                  💡 <strong>Conseil:</strong>
                  {anomaly.anomaly_type === 'high_amount' && 
                    " Vérifiez si cette dépense importante était prévue dans votre budget."
                  }
                  {anomaly.anomaly_type === 'unusual_category' && 
                    " Cette catégorie de dépense est inhabituelle pour vos habitudes."
                  }
                  {anomaly.anomaly_type === 'frequency_spike' && 
                    " Fréquence de transactions élevée dans cette catégorie ce mois-ci."
                  }
                </div>
              </div>
            </div>
          ))}

          {/* Résumé des anomalies */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-sm text-gray-600">Total Anomalies</div>
                <div className="text-2xl font-bold text-red-600">{anomalies.length}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Score Moyen</div>
                <div className="text-2xl font-bold text-orange-600">
                  {(anomalies.reduce((sum, a) => sum + a.score, 0) / anomalies.length * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Montant Total</div>
                <div className="text-2xl font-bold text-purple-600">
                  {formatCurrency(anomalies.reduce((sum, a) => sum + Math.abs(a.amount), 0))}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Plus Critique</div>
                <div className="text-2xl font-bold text-gray-600">
                  {getScoreLabel(Math.max(...anomalies.map(a => a.score)))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

export default AnomaliesDetection;