'use client';

import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api, Tx } from "../../lib/api";
import { useGlobalMonthWithUrl } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card, Alert } from "../../components/ui";
import ImportSuccessBanner from "../../components/ImportSuccessBanner";

export default function TransactionsPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const [month, setMonth] = useGlobalMonthWithUrl();
  const [rows, setRows] = useState<Tx[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Paramètres d'URL
  const importId = searchParams.get('importId');

  // Calculs des totaux
  const calculations = React.useMemo(() => {
    const includedTransactions = rows.filter(tx => !tx.exclude);
    const excludedCount = rows.filter(tx => tx.exclude).length;
    
    const totalExpenses = includedTransactions
      .filter(tx => tx.amount < 0)
      .reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
    
    const totalIncome = includedTransactions
      .filter(tx => tx.amount > 0)
      .reduce((sum, tx) => sum + tx.amount, 0);
    
    const netBalance = totalIncome - totalExpenses;
    const totalAmount = includedTransactions.reduce((sum, tx) => sum + tx.amount, 0);
    
    return {
      totalExpenses,
      totalIncome,
      netBalance,
      totalAmount,
      includedCount: includedTransactions.length,
      excludedCount,
      totalCount: rows.length
    };
  }, [rows]);
  
  console.log('📊 Transactions page - Current month:', month, 'ImportId:', importId);

  const refresh = useCallback(async () => {
    if (!isAuthenticated || !month) {
      console.log('🚫 Refresh skipped - Auth:', isAuthenticated, 'Month:', month);
      return;
    }
    
    console.log('🔄 Starting refresh for month:', month);
    try {
      setLoading(true);
      setError(""); // Clear any previous errors
      const response = await api.get<Tx[]>("/transactions", { params: { month } });
      console.log('✅ Refresh successful - loaded', response.data.length, 'transactions');
      setRows(response.data);
    } catch (err) {
      console.error('❌ Refresh error:', err);
      setError("Erreur lors du chargement des transactions");
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, month]);

  const toggle = async (id: number, exclude: boolean) => {
    try {
      const response = await api.patch(`/transactions/${id}`, { exclude });
      setRows(prev => prev.map(x => x.id === id ? response.data : x));
    } catch (err: any) {
      console.error("Erreur toggle:", err);
      
      let errorMessage = "Erreur lors de la modification";
      
      if (err?.response?.status === 404) {
        errorMessage = `Transaction #${id} introuvable. Veuillez rafraîchir la page.`;
      } else if (err?.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      setError(errorMessage);
    }
  };

  const saveTags = async (id: number, tagsCSV: string) => {
    try {
      const transaction = rows.find(row => row.id === id);
      if (!transaction) {
        setError(`Transaction #${id} introuvable dans la liste actuelle. Veuillez rafraîchir la page.`);
        return;
      }

      const tags = tagsCSV.split(",").map(s => s.trim()).filter(Boolean);
      const response = await api.patch(`/transactions/${id}/tags`, { tags });
      setRows(prev => prev.map(x => x.id === id ? response.data : x));
    } catch (err: any) {
      console.error("Erreur tags:", err);
      
      let errorMessage = "Erreur lors de la sauvegarde des tags";
      
      if (err?.response?.status === 404) {
        errorMessage = `Transaction #${id} introuvable. Veuillez rafraîchir la page.`;
        setTimeout(() => refresh(), 1000);
      } else if (err?.response?.status === 401) {
        errorMessage = "Session expirée. Veuillez vous reconnecter.";
      } else if (err?.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      } else if (err?.message) {
        errorMessage = `Erreur: ${err.message}`;
      }
      
      setError(errorMessage);
    }
  };

  useEffect(() => {
    console.log('🔄 Transactions page useEffect - Month:', month, 'Auth:', isAuthenticated);
    refresh();
  }, [refresh]);

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié (le layout gère la redirection)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">📊 Transactions</h1>
        <div className="text-sm text-zinc-500">{month}</div>
      </div>

      {error && (
        <Alert variant="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Rappel des totaux du mois */}
      {!loading && rows.length > 0 && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Résumé du mois - {month}
              </h2>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-gray-900">
                    {calculations.totalAmount >= 0 ? '+' : ''}{calculations.totalAmount.toFixed(2)} €
                  </span>
                  <span className="text-sm text-gray-600">Total du mois</span>
                </div>
                <div className="text-sm text-gray-600">
                  {calculations.includedCount} transaction{calculations.includedCount > 1 ? 's' : ''} incluse{calculations.includedCount > 1 ? 's' : ''}
                  {calculations.excludedCount > 0 && (
                    <span className="ml-1">({calculations.excludedCount} exclue{calculations.excludedCount > 1 ? 's' : ''})</span>
                  )}
                </div>
              </div>
            </div>
            <div className="text-right space-y-1">
              <div className="text-sm">
                <span className="text-green-600 font-medium">
                  +{calculations.totalIncome.toFixed(2)} € revenus
                </span>
              </div>
              <div className="text-sm">
                <span className="text-red-600 font-medium">
                  -{calculations.totalExpenses.toFixed(2)} € dépenses
                </span>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Bandeau d'import success si importId présent */}
      {importId && (
        <ImportSuccessBanner
          importId={importId}
          currentMonth={month}
          onMonthChange={setMonth}
          onRefresh={refresh}
        />
      )}

      <Card padding="lg">
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner text="Chargement des transactions..." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200">
                  <th className="text-left p-3 font-medium">Date</th>
                  <th className="text-left p-3 font-medium">Libellé</th>
                  <th className="text-left p-3 font-medium">Compte</th>
                  <th className="text-right p-3 font-medium">Montant</th>
                  <th className="text-center p-3 font-medium">Exclure</th>
                  <th className="text-left p-3 font-medium">Tags</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => {
                  const isHighlighted = importId && row.import_id === importId;
                  return (
                    <tr 
                      key={row.id} 
                      className={`border-t border-zinc-100 hover:bg-zinc-50 ${
                        isHighlighted ? 'bg-green-50 border-green-200' : ''
                      }`}
                    >
                      <td className="p-3">{row.date_op}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {row.label}
                          {isHighlighted && (
                            <span className="px-2 py-1 text-xs bg-green-200 text-green-800 rounded-full">
                              Nouveau
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        <span className="text-xs bg-zinc-100 px-2 py-1 rounded-full">
                          {row.account_label}
                        </span>
                      </td>
                      <td className="p-3 text-right font-mono">
                        <span className={row.amount < 0 ? "text-red-600" : "text-green-600"}>
                          {row.amount < 0 ? "-" : "+"}{Math.abs(row.amount).toFixed(2)} €
                        </span>
                      </td>
                      <td className="p-3 text-center">
                        <input 
                          type="checkbox" 
                          checked={row.exclude} 
                          onChange={e => toggle(row.id, e.target.checked)}
                          className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                        />
                      </td>
                      <td className="p-3">
                        <input 
                          className="w-full px-2 py-1 border border-zinc-200 rounded text-sm focus:ring-1 focus:ring-zinc-900 focus:border-transparent" 
                          defaultValue={row.tags.join(", ") || ""} 
                          onBlur={e => saveTags(row.id, e.target.value)} 
                          placeholder="courses, resto, santé…" 
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {/* Ligne de totaux */}
              {rows.length > 0 && (
                <tfoot>
                  <tr className="border-t-2 border-gray-300 bg-gray-50">
                    <td className="p-3 font-medium text-gray-700" colSpan={3}>
                      <div className="flex items-center justify-between">
                        <span>TOTAUX DU MOIS</span>
                        <span className="text-sm text-gray-600">
                          {calculations.includedCount}/{calculations.totalCount} transactions
                          {calculations.excludedCount > 0 && (
                            <span className="ml-2 text-red-600">
                              ({calculations.excludedCount} exclue{calculations.excludedCount > 1 ? 's' : ''})
                            </span>
                          )}
                        </span>
                      </div>
                    </td>
                    <td className="p-3 text-right font-mono">
                      <div className="space-y-1">
                        <div className="text-red-600 font-medium">
                          -{calculations.totalExpenses.toFixed(2)} €
                        </div>
                        <div className="text-green-600 font-medium">
                          +{calculations.totalIncome.toFixed(2)} €
                        </div>
                        <div className="border-t border-gray-400 pt-1">
                          <span className={`font-bold text-lg ${
                            calculations.netBalance >= 0 ? 'text-green-700' : 'text-red-700'
                          }`}>
                            {calculations.netBalance >= 0 ? '+' : ''}{calculations.netBalance.toFixed(2)} €
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="p-3" colSpan={2}>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>Dépenses: {rows.filter(tx => !tx.exclude && tx.amount < 0).length} transactions</div>
                        <div>Revenus: {rows.filter(tx => !tx.exclude && tx.amount > 0).length} transactions</div>
                        <div className="font-medium">
                          Solde net: <span className={calculations.netBalance >= 0 ? 'text-green-700' : 'text-red-700'}>
                            {calculations.netBalance >= 0 ? '+' : ''}{calculations.netBalance.toFixed(2)} €
                          </span>
                        </div>
                      </div>
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
            
            {rows.length === 0 && !loading && (
              <div className="text-center py-12 text-zinc-500">
                <p>Aucune transaction pour ce mois</p>
                <p className="text-sm mt-1">Importez un fichier pour commencer</p>
              </div>
            )}
          </div>
        )}
      </Card>
    </main>
  );
}