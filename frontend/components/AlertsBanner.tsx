'use client';

import { useState, useEffect, useCallback } from 'react';
import { useGlobalMonth } from '../lib/month';
import { predictionsApi, BudgetAlert, BudgetPrediction, SmartRecommendation } from '../lib/api';

interface AlertsBannerProps {
  showPredictions?: boolean;
  showRecommendations?: boolean;
  maxAlerts?: number;
  refreshInterval?: number; // in seconds
}

export function AlertsBanner({
  showPredictions = false,
  showRecommendations = false,
  maxAlerts = 3,
  refreshInterval = 300 // 5 minutes default
}: AlertsBannerProps) {
  const [month] = useGlobalMonth();
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);
  const [predictions, setPredictions] = useState<BudgetPrediction[]>([]);
  const [recommendations, setRecommendations] = useState<SmartRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState(false);

  const loadAlerts = useCallback(async () => {
    if (!month) return;

    try {
      setLoading(true);
      setError('');
      const data = await predictionsApi.getOverview(month);
      setAlerts(data.alerts);
      if (showPredictions) setPredictions(data.predictions);
      if (showRecommendations) setRecommendations(data.recommendations);
    } catch (err: any) {
      console.error('Error loading alerts:', err);
      // Don't show error for 500 errors (ML not trained yet)
      if (err.response?.status !== 500) {
        setError('Erreur lors du chargement des alertes');
      }
    } finally {
      setLoading(false);
    }
  }, [month, showPredictions, showRecommendations]);

  useEffect(() => {
    loadAlerts();

    // Set up refresh interval
    if (refreshInterval > 0) {
      const interval = setInterval(loadAlerts, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [loadAlerts, refreshInterval]);

  const dismissAlert = (alertKey: string) => {
    setDismissed(prev => new Set([...prev, alertKey]));
  };

  const getAlertKey = (alert: BudgetAlert, index: number) =>
    `${alert.alert_type}-${alert.category}-${index}`;

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'high':
        return {
          bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
          icon: 'text-red-500',
          text: 'text-red-800 dark:text-red-200'
        };
      case 'medium':
        return {
          bg: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
          icon: 'text-orange-500',
          text: 'text-orange-800 dark:text-orange-200'
        };
      default:
        return {
          bg: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
          icon: 'text-yellow-500',
          text: 'text-yellow-800 dark:text-yellow-200'
        };
    }
  };

  const getAlertIcon = (alertType: string) => {
    switch (alertType) {
      case 'overspend_risk': return '⚠️';
      case 'unusual_spike': return '📈';
      case 'category_trend': return '📊';
      default: return '💡';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      default: return '➡️';
    }
  };

  // Filter out dismissed alerts
  const activeAlerts = alerts.filter(
    (alert, index) => !dismissed.has(getAlertKey(alert, index))
  );

  // If no alerts and not loading, don't render
  if (!loading && activeAlerts.length === 0 && predictions.length === 0 && recommendations.length === 0) {
    return null;
  }

  // Show loading state briefly
  if (loading && alerts.length === 0) {
    return null; // Don't show loading spinner for alerts banner
  }

  const displayedAlerts = expanded ? activeAlerts : activeAlerts.slice(0, maxAlerts);
  const hasMore = activeAlerts.length > maxAlerts;

  return (
    <div className="space-y-2 mb-4">
      {/* Alerts */}
      {displayedAlerts.map((alert, index) => {
        const styles = getSeverityStyles(alert.severity);
        const alertKey = getAlertKey(alert, index);

        return (
          <div
            key={alertKey}
            className={`${styles.bg} border rounded-lg p-3 flex items-start gap-3 transition-all`}
          >
            <span className={`text-xl ${styles.icon}`}>
              {getAlertIcon(alert.alert_type)}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`font-semibold ${styles.text} capitalize`}>
                  {alert.category}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  alert.severity === 'high' ? 'bg-red-200 text-red-800' :
                  alert.severity === 'medium' ? 'bg-orange-200 text-orange-800' :
                  'bg-yellow-200 text-yellow-800'
                }`}>
                  {alert.severity === 'high' ? 'Urgent' :
                   alert.severity === 'medium' ? 'Attention' : 'Info'}
                </span>
              </div>
              <p className={`text-sm ${styles.text} mt-0.5`}>
                {alert.message}
              </p>
              <div className="flex gap-4 mt-1 text-xs text-gray-500 dark:text-gray-400">
                <span>Actuel: {alert.current_amount.toFixed(0)}EUR</span>
                <span>Predit: {alert.predicted_amount.toFixed(0)}EUR</span>
                <span>{alert.days_remaining}j restants</span>
              </div>
            </div>
            <button
              onClick={() => dismissAlert(alertKey)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Ignorer"
            >
              ×
            </button>
          </div>
        );
      })}

      {/* Show more/less button */}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 py-1"
        >
          {expanded ? 'Voir moins' : `Voir ${activeAlerts.length - maxAlerts} alertes de plus`}
        </button>
      )}

      {/* Predictions summary (compact view) */}
      {showPredictions && predictions.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-500">🔮</span>
            <span className="font-semibold text-blue-800 dark:text-blue-200">
              Predictions du mois
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            {predictions.slice(0, 4).map((pred, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <span>{getTrendIcon(pred.trend_direction)}</span>
                <span className="capitalize truncate">{pred.category}</span>
                <span className="font-mono text-gray-600 dark:text-gray-400">
                  {pred.predicted_month_end.toFixed(0)}EUR
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations (compact view) */}
      {showRecommendations && recommendations.length > 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-green-500">💡</span>
            <span className="font-semibold text-green-800 dark:text-green-200">
              Recommandations
            </span>
          </div>
          <ul className="text-sm text-green-700 dark:text-green-300 space-y-1">
            {recommendations.slice(0, 2).map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span>-</span>
                <span>
                  <span className="capitalize">{rec.category}</span>: {rec.reasoning}
                  <span className="text-green-600 dark:text-green-400 ml-1">
                    ({rec.impact_estimate})
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-sm text-gray-600 dark:text-gray-400">
          {error}
        </div>
      )}
    </div>
  );
}

// Compact version for dashboard header
export function AlertsIndicator() {
  const [month] = useGlobalMonth();
  const [alertCount, setAlertCount] = useState(0);
  const [highSeverityCount, setHighSeverityCount] = useState(0);

  useEffect(() => {
    const loadCounts = async () => {
      if (!month) return;
      try {
        const data = await predictionsApi.getOverview(month);
        setAlertCount(data.alerts.length);
        setHighSeverityCount(data.alerts.filter(a => a.severity === 'high').length);
      } catch {
        // Ignore errors for indicator
      }
    };
    loadCounts();
  }, [month]);

  if (alertCount === 0) return null;

  return (
    <div className="relative inline-flex items-center">
      <span className="text-lg">🔔</span>
      {alertCount > 0 && (
        <span className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] flex items-center justify-center text-xs font-bold rounded-full ${
          highSeverityCount > 0
            ? 'bg-red-500 text-white'
            : 'bg-orange-400 text-white'
        }`}>
          {alertCount}
        </span>
      )}
    </div>
  );
}
