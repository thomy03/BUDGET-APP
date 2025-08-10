'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Summary, ConfigOut } from "../lib/api";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner, Card, Button } from "../components/ui";

export default function Page() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [cfg, setCfg] = useState<ConfigOut | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  const load = async () => {
    if (!isAuthenticated) return;
    
    console.log('📊 Dashboard - Loading data for month:', month);
    try {
      setLoading(true);
      setError("");
      
      const [configResponse, summaryResponse] = await Promise.all([
        api.get<ConfigOut>("/config"),
        api.get<Summary>("/summary", { params: { month } })
      ]);
      
      console.log('✅ Dashboard - Data loaded for month:', month);
      setCfg(configResponse.data);
      setSummary(summaryResponse.data);
    } catch (err: any) {
      setError("Erreur lors du chargement des données");
      console.error("❌ Dashboard - Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🔄 Dashboard useEffect - Month:', month, 'Auth:', isAuthenticated);
    if (isAuthenticated) {
      load();
    }
  }, [month, isAuthenticated]);

  const saveCfg = async () => {
    if (!cfg) return;
    
    try {
      setLoading(true);
      const configResponse = await api.post<ConfigOut>("/config", cfg);
      setCfg(configResponse.data);
      
      const summaryResponse = await api.get<Summary>("/summary", { params: { month } });
      setSummary(summaryResponse.data);
      setDirty(false);
    } catch (err) {
      setError("Erreur lors de la sauvegarde");
    } finally {
      setLoading(false);
    }
  };

  const setField = (patch: Partial<ConfigOut>) => {
    setCfg(prev => prev ? { ...prev, ...patch } : prev);
    setDirty(true);
  };

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié (redirection en cours)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">Tableau de bord</h1>
        <Button 
          variant="primary" 
          onClick={saveCfg} 
          disabled={!dirty}
          loading={loading}
        >
          Enregistrer
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      {summary && cfg ? (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric title="Variables incluses" value={summary.var_total} />
            <Metric 
              title="Charges fixes (total)" 
              value={summary.loan_amount + summary.other_fixed_total + summary.vac_monthly_total} 
            />
            <Metric title={`Part ${summary.member1}`} value={summary.total_p1} />
            <Metric title={`Part ${summary.member2}`} value={summary.total_p2} />
          </div>

          <section className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <Card padding="lg">
                <h2 className="h2 mb-4">Détail par poste — {month}</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr>
                        <th className="text-left p-2 font-medium">Poste</th>
                        <th className="text-right p-2 font-medium">{summary.member1}</th>
                        <th className="text-right p-2 font-medium">{summary.member2}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(summary.detail).map(([poste, byMember]) => (
                        <tr key={poste} className="border-t border-zinc-100">
                          <td className="p-2">{poste}</td>
                          <td className="p-2 text-right font-mono">
                            {(byMember as any)[cfg.member1]?.toFixed(2)} €
                          </td>
                          <td className="p-2 text-right font-mono">
                            {(byMember as any)[cfg.member2]?.toFixed(2)} €
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            <div>
              <Card padding="lg">
                <h2 className="h2 mb-4">Réglages rapides</h2>
                <div className="space-y-6">
                  <fieldset className="space-y-3">
                    <label className="block text-sm font-medium text-zinc-700">
                      Crédit immo + voiture (€/mois)
                    </label>
                    <input 
                      type="number" 
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                      value={cfg.loan_amount} 
                      onChange={e => setField({ loan_amount: parseFloat(e.target.value) || 0 })} 
                    />
                    <label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={cfg.loan_equal} 
                        onChange={e => setField({ loan_equal: e.target.checked })} 
                      />
                      <span>Répartition 50/50</span>
                    </label>
                  </fieldset>

                  <fieldset className="space-y-3">
                    <label className="block text-sm font-medium text-zinc-700">
                      Autres charges fixes — mode
                    </label>
                    <select 
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                      value={cfg.other_fixed_simple ? "simple" : "avance"} 
                      onChange={e => setField({ other_fixed_simple: e.target.value === "simple" })}
                    >
                      <option value="simple">Mensuel simple</option>
                      <option value="avance">Détaillé (taxe/copro)</option>
                    </select>
                    
                    {cfg.other_fixed_simple ? (
                      <>
                        <label className="block text-sm font-medium text-zinc-700">
                          Montant mensuel (ex: 360)
                        </label>
                        <input 
                          type="number" 
                          className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                          value={cfg.other_fixed_monthly} 
                          onChange={e => setField({ other_fixed_monthly: parseFloat(e.target.value) || 0 })} 
                        />
                      </>
                    ) : (
                      <>
                        <label className="block text-sm font-medium text-zinc-700">
                          Taxe foncière N-1 (annuelle)
                        </label>
                        <input 
                          type="number" 
                          className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                          value={cfg.taxe_fonciere_ann} 
                          onChange={e => setField({ taxe_fonciere_ann: parseFloat(e.target.value) || 0 })} 
                        />
                        <label className="block text-sm font-medium text-zinc-700">
                          Provision de copro
                        </label>
                        <input 
                          type="number" 
                          className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                          value={cfg.copro_montant} 
                          onChange={e => setField({ copro_montant: parseFloat(e.target.value) || 0 })} 
                        />
                        <label className="block text-sm font-medium text-zinc-700">
                          Fréquence de copro
                        </label>
                        <select 
                          className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                          value={cfg.copro_freq} 
                          onChange={e => setField({ copro_freq: e.target.value as any })}
                        >
                          <option value="mensuelle">mensuelle</option>
                          <option value="trimestrielle">trimestrielle</option>
                        </select>
                      </>
                    )}
                    
                    <label className="block text-sm font-medium text-zinc-700">
                      Répartition des autres fixes
                    </label>
                    <select 
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                      value={cfg.other_split_mode} 
                      onChange={e => setField({ other_split_mode: e.target.value as any })}
                    >
                      <option value="clé">Clé générale</option>
                      <option value="50/50">50/50</option>
                    </select>
                  </fieldset>

                  <fieldset className="space-y-3">
                    <label className="block text-sm font-medium text-zinc-700">
                      Provision vacances/bébé/plaisir
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <input 
                        type="number" 
                        className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                        value={cfg.vac_percent} 
                        onChange={e => setField({ vac_percent: parseFloat(e.target.value) || 0 })} 
                      />
                      <select 
                        className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-transparent" 
                        value={cfg.vac_base} 
                        onChange={e => setField({ vac_base: e.target.value as any })}
                      >
                        <option value="2">2 membres</option>
                        <option value="1">{cfg.member1}</option>
                        <option value="2nd">{cfg.member2}</option>
                      </select>
                    </div>
                  </fieldset>
                </div>
              </Card>
            </div>
          </section>
        </>
      ) : (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" text="Chargement des données..." />
        </div>
      )}
    </main>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card padding="lg">
      <div className="text-sm text-zinc-500 mb-1">{title}</div>
      <div className="text-2xl font-bold text-zinc-900">{value.toFixed(2)} €</div>
    </Card>
  );
}
