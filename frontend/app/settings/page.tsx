'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ConfigOut, FixedLine } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card, Button, Input, Alert } from "../../components/ui";

export default function Settings() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [cfg, setCfg] = useState<ConfigOut | null>(null);
  const [lines, setLines] = useState<FixedLine[]>([]);
  const [newLine, setNewLine] = useState<Partial<FixedLine>>({
    label: "",
    amount: 0,
    freq: "mensuelle",
    split_mode: "clé",
    split1: 0.5,
    split2: 0.5,
    active: true
  } as any);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
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
      
      const [configResponse, linesResponse] = await Promise.all([
        api.get<ConfigOut>("/config"),
        api.get<FixedLine[]>("/fixed-lines")
      ]);
      
      setCfg(configResponse.data);
      setLines(linesResponse.data);
    } catch (err: any) {
      setError("Erreur lors du chargement des paramètres");
      console.error("Erreur settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      load();
    }
  }, [isAuthenticated]);

  const saveCfg = async () => {
    if (!cfg) return;
    
    try {
      setSaving(true);
      setError("");
      
      const response = await api.post<ConfigOut>("/config", cfg);
      setCfg(response.data);
      setMessage("Paramètres enregistrés avec succès ✅");
      
      // Effacer le message après 3 secondes
      setTimeout(() => setMessage(""), 3000);
    } catch (err: any) {
      setError("Erreur lors de la sauvegarde");
      console.error("Erreur sauvegarde:", err);
    } finally {
      setSaving(false);
    }
  };

  const addLine = async () => {
    try {
      const payload = { ...newLine, amount: Number(newLine.amount || 0) };
      const response = await api.post<FixedLine>("/fixed-lines", payload);
      setLines(prev => [...prev, response.data]);
      setNewLine({
        label: "",
        amount: 0,
        freq: "mensuelle",
        split_mode: "clé",
        split1: 0.5,
        split2: 0.5,
        active: true
      } as any);
      setMessage("Ligne ajoutée ✅");
      setTimeout(() => setMessage(""), 2000);
    } catch (err: any) {
      setError("Erreur lors de l'ajout");
      console.error("Erreur addLine:", err);
    }
  };

  const updateLine = async (line: FixedLine) => {
    try {
      // Note: L'API actuelle n'a pas de PATCH, on utilise POST
      const response = await api.post<FixedLine>(`/fixed-lines`, line);
      setMessage("Ligne mise à jour ✅");
      setTimeout(() => setMessage(""), 2000);
    } catch (err: any) {
      setError("Erreur lors de la mise à jour");
      console.error("Erreur updateLine:", err);
    }
  };

  const deleteLine = async (id: number) => {
    try {
      await api.delete(`/fixed-lines/${id}`);
      setLines(prev => prev.filter(x => x.id !== id));
      setMessage("Ligne supprimée ✅");
      setTimeout(() => setMessage(""), 2000);
    } catch (err: any) {
      setError("Erreur lors de la suppression");
      console.error("Erreur deleteLine:", err);
    }
  };

  // Ne pas afficher si en cours d'authentification
  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return null; // Redirection en cours
  }

  if (loading) {
    return (
      <main className="container mx-auto px-4 py-6">
        <LoadingSpinner />
      </main>
    );
  }

  if (!cfg) {
    return (
      <main className="container mx-auto px-4 py-6">
        <div className="text-center text-gray-500">
          <p>Erreur de chargement des paramètres</p>
        </div>
      </main>
    );
  }

  return (
    <main className="container mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">⚙️ Paramètres</h1>
      </div>

      {message && <Alert variant="success">{message}</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      {/* Section Membres & Répartition */}
      <Card className="p-6">
        <div className="space-y-6">
          <div className="border-b border-gray-200 pb-4">
            <h2 className="text-xl font-semibold text-gray-900">Membres & Répartition</h2>
            <p className="text-sm text-gray-600 mt-1">
              Configurez les membres du foyer et leur mode de répartition des dépenses.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Membre 1
              </label>
              <Input
                value={cfg.member1}
                onChange={e => setCfg({ ...cfg, member1: e.target.value })}
                placeholder="Nom du membre 1"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Membre 2
              </label>
              <Input
                value={cfg.member2}
                onChange={e => setCfg({ ...cfg, member2: e.target.value })}
                placeholder="Nom du membre 2"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Revenu annuel - {cfg.member1} (€)
              </label>
              <Input
                type="number"
                value={cfg.rev1}
                onChange={e => setCfg({ ...cfg, rev1: parseFloat(e.target.value) || 0 })}
                placeholder="0"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Revenu annuel - {cfg.member2} (€)
              </label>
              <Input
                type="number"
                value={cfg.rev2}
                onChange={e => setCfg({ ...cfg, rev2: parseFloat(e.target.value) || 0 })}
                placeholder="0"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Mode de répartition
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                value={cfg.split_mode}
                onChange={e => setCfg({ ...cfg, split_mode: e.target.value as any })}
              >
                <option value="revenus">Proportion des revenus</option>
                <option value="manuel">Répartition manuelle</option>
              </select>
            </div>

            {cfg.split_mode === "manuel" && (
              <div className="space-y-4">
                <div className="text-sm font-medium text-gray-700">Répartition manuelle (%)</div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm text-gray-600">
                      Part {cfg.member1} (%)
                    </label>
                    <Input
                      type="number"
                      value={Math.round(cfg.split1 * 100)}
                      onChange={e => {
                        const value = parseFloat(e.target.value) || 0;
                        setCfg({ 
                          ...cfg, 
                          split1: value / 100,
                          split2: (100 - value) / 100
                        });
                      }}
                      min="0"
                      max="100"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-gray-600">
                      Part {cfg.member2} (%)
                    </label>
                    <Input
                      type="number"
                      value={Math.round(cfg.split2 * 100)}
                      onChange={e => {
                        const value = parseFloat(e.target.value) || 0;
                        setCfg({ 
                          ...cfg, 
                          split2: value / 100,
                          split1: (100 - value) / 100
                        });
                      }}
                      min="0"
                      max="100"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {cfg.split_mode === "revenus" && (cfg.rev1 + cfg.rev2) > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-blue-800 mb-2">Répartition automatique</h4>
              <div className="grid grid-cols-2 gap-4 text-sm text-blue-600">
                <div>
                  {cfg.member1}: {((cfg.rev1 / (cfg.rev1 + cfg.rev2)) * 100).toFixed(1)}%
                </div>
                <div>
                  {cfg.member2}: {((cfg.rev2 / (cfg.rev1 + cfg.rev2)) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end pt-4 border-t border-gray-200">
            <Button 
              onClick={saveCfg} 
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors"
            >
              {saving ? "Enregistrement..." : "Enregistrer les paramètres"}
            </Button>
          </div>
        </div>
      </Card>

      {/* Section Dépenses Fixes - Simplifiée pour les tests */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="border-b border-gray-200 pb-4">
            <h2 className="text-xl font-semibold text-gray-900">Dépenses Fixes</h2>
            <p className="text-sm text-gray-600 mt-1">
              Fonctionnalité avancée - sera implémentée dans une version future.
            </p>
          </div>
          
          <div className="text-center py-8 text-gray-500">
            <p className="text-lg">🚧 En construction</p>
            <p className="text-sm mt-2">Cette section sera disponible dans la v3.1</p>
          </div>
        </div>
      </Card>
    </main>
  );
}

function round100(v: number): number {
  return Math.round((v || 0) * 100);
}
