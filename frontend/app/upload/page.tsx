'use client';

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, ImportResponse } from "../../lib/api";
import { useGlobalMonth } from "../../lib/month";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner, Card, Button, useToast } from "../../components/ui";
import { CsvImportProgress } from "../../components/CsvImportProgress";
import { pickTargetMonth, humanizeMonth, generateImportSummary, buildTransactionUrl } from "../../lib/import-utils";

type ImportPhase = 'upload' | 'parse' | 'validate' | 'import';

type PhaseState = {
  status: 'pending' | 'active' | 'done' | 'error';
  progress: number;
};

// Configuration des durées pour chaque phase (augmentées pour être bien visibles)
const PHASE_DURATIONS: Record<ImportPhase, number> = {
  upload: 800,
  parse: 900,
  validate: 1000,
  import: 1100
};

// Utilitaire pour analyser un fichier en détail pour le débogage
const analyzeFileForDebug = async (file: File): Promise<void> => {
  try {
    console.log("🔬 File Analysis:", {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: new Date(file.lastModified).toISOString(),
      sizeInMB: (file.size / 1024 / 1024).toFixed(2)
    });

    // Lire les premiers caractères du fichier pour détecter l'encodage/format
    if (file.size > 0 && file.size < 10 * 1024 * 1024) { // Moins de 10MB
      const slice = file.slice(0, Math.min(1000, file.size));
      const text = await slice.text();
      
      console.log("📝 File Content Sample:", {
        firstChars: text.substring(0, 200),
        hasUTF8BOM: text.charCodeAt(0) === 0xFEFF,
        lineCount: text.split('\n').length,
        delimiter: text.includes(';') ? ';' : (text.includes(',') ? ',' : 'unknown'),
        encoding: 'UTF-8' // Par défaut, le navigateur lit en UTF-8
      });
    }
  } catch (error) {
    console.warn("⚠️ Could not analyze file:", error);
  }
};

// Utilitaires pour l'animation
const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

const jitter = (ms: number, ratio = 0.15) => 
  Math.round(ms * (1 - ratio + Math.random() * ratio * 2));

async function withMinDuration<T>(promise: Promise<T>, minMs: number): Promise<T> {
  const [result] = await Promise.all([promise, sleep(minMs)]);
  return result;
}

function useImportPhases() {
  const [phases, setPhases] = useState<Record<ImportPhase, PhaseState>>({
    upload: { status: 'pending', progress: 0 },
    parse: { status: 'pending', progress: 0 },
    validate: { status: 'pending', progress: 0 },
    import: { status: 'pending', progress: 0 }
  });
  
  const [currentPhase, setCurrentPhase] = useState<ImportPhase>('upload');
  const rafRef = useRef<number | undefined>(undefined);
  
  const setPhase = useCallback((phase: ImportPhase, data: Partial<PhaseState>) => {
    setPhases(prev => ({ 
      ...prev, 
      [phase]: { ...prev[phase], ...data } 
    }));
    if (data.status === 'active') {
      setCurrentPhase(phase);
    }
  }, []);
  
  const reset = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }
    setPhases({
      upload: { status: 'pending', progress: 0 },
      parse: { status: 'pending', progress: 0 },
      validate: { status: 'pending', progress: 0 },
      import: { status: 'pending', progress: 0 }
    });
    setCurrentPhase('upload');
  }, []);
  
  return { phases, currentPhase, setPhase, reset };
}

function smoothProgress(
  updateFn: (progress: number) => void,
  durationMs: number,
  cap = 93
) {
  let rafId = 0;
  let lastProgress = 0;
  const startTime = performance.now();
  
  const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
  
  const tick = (now: number) => {
    const elapsed = now - startTime;
    const t = Math.min(1, elapsed / durationMs);
    lastProgress = Math.min(cap, Math.round(easeOutCubic(t) * cap));
    updateFn(lastProgress);
    
    if (t < 1) {
      rafId = requestAnimationFrame(tick);
    }
  };
  
  rafId = requestAnimationFrame(tick);
  
  return (finishMs = 250) => {
    cancelAnimationFrame(rafId);
    const from = lastProgress;
    const startFinish = performance.now();
    
    const finish = (now: number) => {
      const t = Math.min(1, (now - startFinish) / finishMs);
      const progress = Math.round(from + t * (100 - from));
      updateFn(progress);
      
      if (t < 1) {
        requestAnimationFrame(finish);
      }
    };
    
    requestAnimationFrame(finish);
  };
}

async function runPhase<T>(
  phase: ImportPhase,
  task: () => Promise<T> | T,
  setPhase: (phase: ImportPhase, data: Partial<PhaseState>) => void,
  baseMs = PHASE_DURATIONS[phase]
): Promise<T> {
  const minMs = jitter(baseMs);
  
  setPhase(phase, { status: 'active', progress: 0 });
  
  const stopProgress = smoothProgress(
    (progress) => setPhase(phase, { status: 'active', progress }),
    Math.max(minMs - 200, 200)
  );
  
  try {
    const result = await withMinDuration(Promise.resolve(task()), minMs);
    stopProgress(250);
    setPhase(phase, { status: 'done', progress: 100 });
    return result;
  } catch (error) {
    stopProgress(150);
    setPhase(phase, { status: 'error', progress: 100 });
    throw error;
  }
}

export default function UploadPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month, setGlobalMonth] = useGlobalMonth();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const { phases, currentPhase, setPhase, reset } = useImportPhases();
  const { success, error, warning } = useToast();

  // Fonction de débogage globale disponible dans la console
  React.useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      (window as any).debugCSVImport = {
        getCurrentState: () => ({
          file: file ? {
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: new Date(file.lastModified).toISOString()
          } : null,
          loading,
          phases,
          currentPhase,
          isAuthenticated,
          authToken: localStorage.getItem("auth_token")?.substring(0, 10) + "...",
          tokenType: localStorage.getItem("token_type"),
          currentUrl: window.location.href
        }),
        testAuthHeaders: () => {
          const token = localStorage.getItem("auth_token");
          const tokenType = localStorage.getItem("token_type");
          console.log("🔑 Current auth state:", {
            hasToken: !!token,
            tokenLength: token?.length,
            tokenType,
            tokenPreview: token?.substring(0, 10) + "...",
            isAuthenticated,
            apiDefaults: (window as any).api?.defaults?.headers?.common
          });
        },
        analyzeCurrentFile: file ? () => analyzeFileForDebug(file) : () => console.log("No file selected")
      };
      
      console.log("🛠️ Debug tools available: window.debugCSVImport");
    }
  }, [file, loading, phases, currentPhase, isAuthenticated]);

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  const onUpload = async () => {
    if (!file) return;
    
    console.log('🚀 Starting upload with animation...');
    
    // Analyser le fichier pour le débogage en mode développement
    if (process.env.NODE_ENV === "development") {
      await analyzeFileForDebug(file);
    }
    
    try {
      setLoading(true);
      reset();
      console.log('✅ Loading state set to true');
      
      // Fonction pour effectuer l'appel API réel
      const performApiCall = async (): Promise<ImportResponse> => {
        const form = new FormData();
        form.append("file", file as Blob);
        
        // Récupérer explicitement le token pour s'assurer qu'il est présent
        const token = localStorage.getItem("auth_token");
        const tokenType = localStorage.getItem("token_type");
        
        if (!token || !tokenType) {
          throw new Error("Token d'authentification manquant");
        }
        
        console.log("🔑 Making import request with auth token:", tokenType, token.substring(0, 10) + "...");
        
        // Log détaillé de la requête pour le débogage
        console.log("📤 Request details:", {
          url: "/import",
          method: "POST",
          fileName: file.name,
          fileSize: file.size,
          fileType: file.type,
          headers: {
            "Content-Type": "multipart/form-data",
            "Authorization": `${tokenType} ${token.substring(0, 10)}...`
          }
        });
        
        try {
          const response = await api.post<ImportResponse>("/import", form, {
            headers: { 
              "Content-Type": "multipart/form-data",
              "Authorization": `${tokenType} ${token}`
            }
          });
          
          console.log("📥 Response received:", {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers,
            dataKeys: Object.keys(response.data || {}),
            data: response.data
          });
          
          return response.data;
        } catch (error: any) {
          // Log détaillé de l'erreur pour le débogage
          console.error("❌ API Request failed:", {
            message: error.message,
            status: error.response?.status,
            statusText: error.response?.statusText,
            headers: error.response?.headers,
            data: error.response?.data,
            config: {
              url: error.config?.url,
              method: error.config?.method,
              headers: error.config?.headers
            },
            code: error.code,
            stack: error.stack
          });
          
          // Re-throw l'erreur pour la gestion dans le catch principal
          throw error;
        }
      };
      
      // Simuler les phases avec animation fluide
      const simulatePhases = async (): Promise<void> => {
        console.log('📊 Phase 1: Upload');
        await runPhase('upload', () => sleep(0), setPhase);
        console.log('📊 Phase 2: Parse');
        await runPhase('parse', () => sleep(0), setPhase);
        console.log('📊 Phase 3: Validate');
        await runPhase('validate', () => sleep(0), setPhase);
        console.log('📊 Phase 4: Import');
        await runPhase('import', () => sleep(0), setPhase);
        console.log('✅ All phases completed');
      };
      
      // Lancer l'API et la simulation en parallèle
      const [importData] = await Promise.all([
        performApiCall(),
        simulatePhases()
      ]);
      
      // Déterminer le mois cible
      console.log('🎯 Determining target month:', {
        months: importData.months,
        suggestedMonth: importData.suggestedMonth,
        currentMonth: month
      });
      
      const targetMonth = pickTargetMonth(importData.months, importData.suggestedMonth, month);
      
      console.log('🎯 Target month selected:', targetMonth);
      
      if (!targetMonth) {
        error("Import terminé, aucun mois détecté", {
          description: "Vérifiez la colonne des dates et le format du CSV.",
          duration: 0
        });
        return;
      }
      
      // Générer le résumé
      const { totalNew, monthsSummary } = generateImportSummary(importData.months);
      
      // Afficher les avertissements si nécessaire
      if (importData.warnings.length > 0) {
        warning(`${totalNew} transactions importées avec ${importData.warnings.length} avertissement(s)`, {
          description: importData.warnings.slice(0, 2).join(" • "),
          duration: 8000
        });
      }
      
      // Afficher les erreurs si nécessaire  
      if (importData.errors.length > 0) {
        warning(`Import partiellement réussi`, {
          description: `${importData.errors.length} ligne(s) ignorée(s). ${totalNew} transactions créées.`,
          duration: 10000
        });
      }
      
      // Construire l'URL de redirection
      const redirectUrl = buildTransactionUrl(targetMonth, importData.importId);
      
      console.log('🔗 Redirect URL built:', redirectUrl, {
        targetMonth,
        importId: importData.importId
      });
      
      // Toast de succès avec actions rapides
      const otherMonths = importData.months.filter(m => 
        m.month !== targetMonth && m.newCount > 0
      );
      
      const toastActions = otherMonths.slice(0, 2).map(monthItem => ({
        label: humanizeMonth(monthItem.month),
        onClick: () => {
          const url = buildTransactionUrl(monthItem.month, importData.importId);
          router.replace(url);
        }
      }));
      
      success(`Import réussi • ${totalNew} nouvelles transactions`, {
        description: importData.months.length === 1 
          ? `Redirection vers ${humanizeMonth(targetMonth)}...`
          : `Mois: ${monthsSummary}`,
        actions: toastActions,
        ...(otherMonths.length > 2 && {
          secondaryAction: {
            label: `+${otherMonths.length - 2} autres`,
            onClick: () => {
              // La navigation se fera et le bandeau montrera tous les mois
              router.replace(redirectUrl);
            }
          }
        }),
        duration: 3000
      });
      
      // Mettre à jour le mois global avant la navigation pour éviter les conflits de state
      console.log('🗓️  Updating global month before redirect:', targetMonth);
      setGlobalMonth(targetMonth);
      
      // Navigation après un délai court pour laisser le temps de voir le toast
      setTimeout(() => {
        console.log('🚀 Navigating to:', redirectUrl);
        router.replace(redirectUrl);
      }, 1200);
      
    } catch (err: any) {
      console.error("❌ Import error occurred:", err);
      
      let errorMessage = "Erreur lors de l'import du fichier";
      let errorDescription = "Réessayez plus tard.";
      
      // Log l'erreur complète pour le débogage
      console.error("🔍 Full error analysis:", {
        errorType: typeof err,
        message: err?.message,
        response: {
          status: err?.response?.status,
          statusText: err?.response?.statusText,
          data: err?.response?.data,
          headers: err?.response?.headers
        },
        request: {
          method: err?.config?.method,
          url: err?.config?.url,
          headers: err?.config?.headers
        },
        code: err?.code,
        name: err?.name
      });
      
      // Gestion spécifique des erreurs d'authentification
      if (err?.response?.status === 401) {
        errorMessage = "Authentification requise";
        errorDescription = "Votre session a expiré. Veuillez vous reconnecter.";
        
        // Forcer la reconnexion
        setTimeout(() => {
          router.push("/login");
        }, 2000);
      } else if (err?.message === "Token d'authentification manquant") {
        errorMessage = "Authentification manquante";
        errorDescription = "Veuillez vous reconnecter pour continuer.";
        
        // Forcer la reconnexion
        setTimeout(() => {
          router.push("/login");
        }, 2000);
      } else if (err?.response?.status === 400) {
        // Gestion spécifique des erreurs 400 Bad Request
        errorMessage = "Fichier CSV invalide";
        
        const responseData = err?.response?.data;
        console.error("🔍 400 Bad Request details:", responseData);
        
        if (responseData?.detail) {
          // Si le backend envoie un message d'erreur détaillé
          errorDescription = `Erreur de validation: ${responseData.detail}`;
        } else if (responseData?.message) {
          errorDescription = `Erreur: ${responseData.message}`;
        } else if (responseData?.error) {
          errorDescription = `Erreur: ${responseData.error}`;
        } else if (typeof responseData === 'string') {
          errorDescription = `Détail de l'erreur: ${responseData}`;
        } else {
          // Message par défaut avec plus d'informations
          errorDescription = "Le format du fichier CSV est invalide. Vérifiez que le fichier contient les colonnes requises: Date, Description, Montant, Compte.";
          
          // Ajouter des détails techniques pour le débogage
          if (responseData) {
            errorDescription += ` (Données reçues: ${JSON.stringify(responseData).substring(0, 200)}...)`;
          }
        }
        
        // Ajouter des suggestions spécifiques pour les erreurs 400
        if (file) {
          errorDescription += ` Fichier: "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)}MB)`;
        }
        
      } else if (err?.response?.status === 422) {
        // Erreurs de validation Pydantic
        errorMessage = "Erreur de validation des données";
        const validationErrors = err?.response?.data?.detail;
        
        if (Array.isArray(validationErrors)) {
          const errorMessages = validationErrors.map((e: any) => 
            `${e.loc?.join(' → ') || 'Champ'}: ${e.msg}`
          ).join(', ');
          errorDescription = `Validation échouée: ${errorMessages}`;
        } else if (typeof validationErrors === 'string') {
          errorDescription = validationErrors;
        } else {
          errorDescription = "Les données du fichier ne respectent pas le format attendu.";
        }
      } else if (err?.response?.status === 413) {
        // Fichier trop volumineux
        errorMessage = "Fichier trop volumineux";
        errorDescription = "La taille du fichier dépasse la limite autorisée (10MB maximum).";
      } else if (err?.response?.status === 415) {
        // Type de fichier non supporté
        errorMessage = "Type de fichier non supporté";
        errorDescription = "Seuls les fichiers CSV, XLSX et XLS sont acceptés.";
      } else if (err?.response?.data?.detail) {
        // Autres erreurs avec détail du backend
        errorMessage = "Import échoué";
        errorDescription = err.response.data.detail;
      } else if (err?.code === 'ECONNABORTED') {
        // Timeout de la requête
        errorMessage = "Délai d'attente dépassé";
        errorDescription = "L'import a pris trop de temps. Essayez avec un fichier plus petit.";
      } else if (err?.code === 'ERR_NETWORK') {
        // Erreur réseau
        errorMessage = "Erreur de connexion";
        errorDescription = "Impossible de joindre le serveur. Vérifiez votre connexion internet.";
      } else if (err?.response?.status >= 500) {
        // Erreurs serveur
        errorMessage = "Erreur serveur";
        errorDescription = `Le serveur a rencontré une erreur (${err?.response?.status}). Réessayez dans quelques minutes.`;
      }
      
      // Ajouter des informations de débogage en mode développement
      if (process.env.NODE_ENV === "development") {
        errorDescription += ` [Debug: Status ${err?.response?.status}, Code: ${err?.code || 'N/A'}]`;
      }
      
      error(errorMessage, {
        description: errorDescription,
        duration: 0
      });
    } finally {
      setLoading(false);
      reset();
      setFile(null); // Reset le fichier après upload (succès ou échec)
    }
  };

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">📥 Import de fichier</h1>
        <div className="text-sm text-zinc-500">
          <span className="mr-4">Formats acceptés: CSV, XLSX, XLS</span>
          <span>Max: 10MB</span>
        </div>
      </div>

      {loading ? (
        <>
          {console.log('🎬 Rendering CsvImportProgress:', { 
            currentPhase, 
            progress: phases[currentPhase].progress,
            fileName: file?.name 
          })}
          <CsvImportProgress
            fileName={file?.name}
            progress={phases[currentPhase].progress}
            phase={currentPhase}
            cancellable={false}
            hint="L'analyse du fichier commencera après le téléversement. Veuillez patienter."
          />
        </>
      ) : (
        <Card padding="lg">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-2">Sélectionner un fichier</h3>
            <p className="text-sm text-zinc-600 mb-4">
              Importez vos transactions bancaires. Le fichier doit contenir les colonnes : 
              Date, Description, Montant, Compte.
            </p>
            
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <input 
                  type="file" 
                  onChange={e => setFile(e.target.files?.[0] || null)}
                  accept=".csv,.xlsx,.xls"
                  className="flex-1 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-zinc-50 file:text-zinc-700 hover:file:bg-zinc-100"
                />
              </div>
              
              {file && (
                <div className="flex items-center gap-2 text-sm text-zinc-600">
                  <span>📄 {file.name}</span>
                  <span>•</span>
                  <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 pt-4 border-t">
            <Button 
              variant="primary" 
              onClick={onUpload}
              disabled={!file || loading}
              loading={loading}
              className="min-w-[120px]"
            >
              {loading ? 'Import en cours...' : 'Importer'}
            </Button>
            
            {file && !loading && (
              <Button 
                variant="secondary" 
                onClick={() => setFile(null)}
              >
                Annuler
              </Button>
            )}
          </div>
        </div>
      </Card>
      )}

      <Card padding="lg">
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Informations importantes</h3>
          <div className="space-y-3 text-sm text-zinc-600">
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Les doublons sont automatiquement détectés et ignorés</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Vous serez redirigé automatiquement vers le mois le plus pertinent</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-green-600">✓</span>
              <span>Les nouvelles transactions seront mises en évidence</span>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-blue-600">ℹ</span>
              <span>Formats de date supportés : YYYY-MM-DD ou DD/MM/YYYY</span>
            </div>
          </div>
        </div>
      </Card>
    </main>
  );
}
