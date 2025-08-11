'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import { useGlobalMonth } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card } from "../../components/ui";

type Row = {
  tag: string;
  total: number;
  count: number;
};

export default function Analytics() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  const load = async () => {
    if (!isAuthenticated) return;
    
    try {
      setLoading(true);
      setError("");
      
      const response = await api.get("/tags-summary", { params: { month } });
      
      // La réponse contient un objet avec { month, tags, total_tagged_transactions }
      // Nous devons extraire l'objet "tags" et l'adapter
      const summaryData = response.data.tags || {};
      const rowsArray = Object.entries(summaryData).map(([tag, data]: [string, any]) => ({
        tag,
        total: Math.abs(data.total_amount || 0), // Le backend retourne total_amount, pas total
        count: data.count || 0
      }));
      
      // Trier par montant décroissant
      rowsArray.sort((a, b) => b.total - a.total);
      
      setRows(rowsArray);
    } catch (err: any) {
      setError("Erreur lors du chargement des analyses");
      console.error("Erreur analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      load();
    }
  }, [month, isAuthenticated]);

  // Ne pas afficher si en cours d'authentification
  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return null; // Redirection en cours
  }

  const total = rows.reduce((s, x) => s + x.total, 0);

  return (
    <main className="container mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          📊 Analyses par catégories — {month}
        </h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-6">
          {/* Résumé global */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-6 bg-gradient-to-r from-blue-50 to-blue-100 border-blue-200">
              <h3 className="text-sm font-medium text-blue-600 mb-1">Total dépenses</h3>
              <p className="text-2xl font-bold text-blue-900">{total.toFixed(2)} €</p>
            </Card>
            
            <Card className="p-6 bg-gradient-to-r from-green-50 to-green-100 border-green-200">
              <h3 className="text-sm font-medium text-green-600 mb-1">Catégories</h3>
              <p className="text-2xl font-bold text-green-900">{rows.length}</p>
            </Card>
            
            <Card className="p-6 bg-gradient-to-r from-purple-50 to-purple-100 border-purple-200">
              <h3 className="text-sm font-medium text-purple-600 mb-1">Transactions</h3>
              <p className="text-2xl font-bold text-purple-900">{rows.reduce((s, r) => s + r.count, 0)}</p>
            </Card>
          </div>

          {/* Tableau détaillé */}
          <Card className="overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-900">Répartition par catégorie</h3>
            </div>
            
            {rows.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p className="text-lg mb-2">Aucune donnée disponible</p>
                <p className="text-sm">Importez des transactions pour voir les analyses.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-4 font-medium text-gray-600">Catégorie</th>
                      <th className="text-right p-4 font-medium text-gray-600">Transactions</th>
                      <th className="text-right p-4 font-medium text-gray-600">Montant</th>
                      <th className="text-right p-4 font-medium text-gray-600">%</th>
                      <th className="w-32 p-4 font-medium text-gray-600">Répartition</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, index) => {
                      const percentage = total > 0 ? (row.total / total) * 100 : 0;
                      const isExpense = row.total > 0;
                      
                      return (
                        <tr key={row.tag} className="border-t border-gray-100 hover:bg-gray-50">
                          <td className="p-4">
                            <div className="flex items-center space-x-2">
                              <span className={`w-3 h-3 rounded-full ${
                                index % 6 === 0 ? 'bg-blue-500' :
                                index % 6 === 1 ? 'bg-green-500' :
                                index % 6 === 2 ? 'bg-yellow-500' :
                                index % 6 === 3 ? 'bg-red-500' :
                                index % 6 === 4 ? 'bg-purple-500' : 'bg-gray-500'
                              }`}></span>
                              <span className="font-medium text-gray-900">{row.tag}</span>
                            </div>
                          </td>
                          <td className="p-4 text-right text-gray-600">{row.count}</td>
                          <td className="p-4 text-right font-mono">
                            <span className={`${isExpense ? 'text-red-600' : 'text-green-600'} font-semibold`}>
                              {isExpense ? '-' : '+'}{row.total.toFixed(2)} €
                            </span>
                          </td>
                          <td className="p-4 text-right text-gray-600">
                            {percentage.toFixed(1)}%
                          </td>
                          <td className="p-4">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className={`h-2 rounded-full ${
                                  index % 6 === 0 ? 'bg-blue-500' :
                                  index % 6 === 1 ? 'bg-green-500' :
                                  index % 6 === 2 ? 'bg-yellow-500' :
                                  index % 6 === 3 ? 'bg-red-500' :
                                  index % 6 === 4 ? 'bg-purple-500' : 'bg-gray-500'
                                }`}
                                style={{ width: `${Math.min(percentage, 100)}%` }}
                              ></div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    
                    {total > 0 && (
                      <tr className="border-t-2 border-gray-200 bg-gray-50 font-semibold">
                        <td className="p-4 text-gray-900">Total</td>
                        <td className="p-4 text-right text-gray-900">{rows.reduce((s, r) => s + r.count, 0)}</td>
                        <td className="p-4 text-right font-mono text-gray-900">{total.toFixed(2)} €</td>
                        <td className="p-4 text-right text-gray-900">100%</td>
                        <td className="p-4">
                          <div className="w-full bg-gray-400 rounded-full h-2"></div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </main>
  );
}
