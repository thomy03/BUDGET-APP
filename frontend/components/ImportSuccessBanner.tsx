'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api, ImportMonth } from '../lib/api';
import { humanizeMonth, generateImportSummary } from '../lib/import-utils';
import { Card, Button } from './ui';

interface ImportSuccessBannerProps {
  importId: string;
  currentMonth: string;
  onMonthChange: (month: string) => void;
  onRefresh: () => void;
}

export default function ImportSuccessBanner({
  importId,
  currentMonth,
  onMonthChange,
  onRefresh,
}: ImportSuccessBannerProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [importData, setImportData] = useState<{
    months: ImportMonth[];
    fileName?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [showOtherMonths, setShowOtherMonths] = useState(false);

  useEffect(() => {
    const fetchImportDetails = async () => {
      try {
        const response = await api.get(`/imports/${importId}`);
        // Simulons la structure - dans un vrai cas, l'API devrait retourner les détails complets
        setImportData({
          months: response.data.months || [],
          fileName: response.data.fileName || 'fichier.csv'
        });
      } catch (error) {
        console.error('Erreur lors du chargement des détails d\'import:', error);
        // Si l'API ne supporte pas encore ce endpoint, on peut le masquer gracieusement
        setImportData({ months: [], fileName: 'fichier.csv' });
      } finally {
        setLoading(false);
      }
    };

    fetchImportDetails();
  }, [importId]);

  const handleMonthSwitch = (month: string) => {
    console.log('🔄 Import banner month switch:', month);
    // Appeler onMonthChange qui utilisera le hook avec URL sync
    onMonthChange(month);
    // Pas besoin de router.replace car le hook useGlobalMonthWithUrl s'en charge
  };

  const handleDismiss = () => {
    const newParams = new URLSearchParams(searchParams.toString());
    newParams.delete('importId');
    
    const newUrl = newParams.toString() 
      ? `/transactions?${newParams.toString()}`
      : '/transactions';
    
    router.replace(newUrl);
  };

  if (loading) {
    return (
      <Card padding="lg">
        <div className="flex items-center gap-3">
          <div className="animate-spin w-5 h-5 border-2 border-green-500 border-t-transparent rounded-full"></div>
          <span className="text-sm text-zinc-600">Chargement des détails d'import...</span>
        </div>
      </Card>
    );
  }

  if (!importData || importData.months.length === 0) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-green-600">✅</span>
            <div>
              <div className="font-medium text-green-800">Import réussi</div>
              <div className="text-sm text-green-600">Nouvelles transactions importées</div>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={handleDismiss}>
            Masquer
          </Button>
        </div>
      </Card>
    );
  }

  const { totalNew, monthsSummary } = generateImportSummary(importData.months);
  const otherMonths = importData.months.filter(m => 
    m.month !== currentMonth && m.newCount > 0
  );

  return (
    <Card padding="lg">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <span className="text-green-600 text-lg">✅</span>
            <div>
              <div className="font-medium text-green-800">
                Import réussi • {totalNew} nouvelles transactions
              </div>
              <div className="text-sm text-green-600 mt-1">
                {importData.months.length === 1 
                  ? `Vous consultez ${humanizeMonth(currentMonth)}`
                  : `Mois détectés: ${monthsSummary}`
                }
              </div>
            </div>
          </div>
          
          <div className="flex gap-2">
            {otherMonths.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowOtherMonths(!showOtherMonths)}
              >
                {showOtherMonths ? 'Masquer' : `${otherMonths.length} autre${otherMonths.length > 1 ? 's' : ''} mois`}
              </Button>
            )}
            <Button variant="secondary" size="sm" onClick={handleDismiss}>
              Masquer
            </Button>
          </div>
        </div>

        {showOtherMonths && otherMonths.length > 0 && (
          <div className="pt-3 border-t border-green-200">
            <div className="text-sm text-green-700 mb-2">Basculer vers un autre mois :</div>
            <div className="flex flex-wrap gap-2">
              {otherMonths.map((month) => (
                <Button
                  key={month.month}
                  variant="secondary"
                  size="sm"
                  onClick={() => handleMonthSwitch(month.month)}
                  className="text-xs"
                >
                  📅 {humanizeMonth(month.month)} ({month.newCount})
                </Button>
              ))}
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-green-200">
          <div className="flex gap-3 text-sm">
            <button
              onClick={() => {
                // TODO: Implémenter le filtre "nouvelles uniquement"
                console.log('Filter to new transactions only');
              }}
              className="text-green-700 hover:text-green-800 font-medium"
            >
              📋 Afficher uniquement les nouvelles
            </button>
            <button
              onClick={onRefresh}
              className="text-green-700 hover:text-green-800"
            >
              🔄 Actualiser
            </button>
          </div>
        </div>
      </div>
    </Card>
  );
}