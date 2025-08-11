'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, ImportResponse } from '../lib/api';
import { useGlobalMonth } from '../lib/month';
import { useToast } from '../components/ui';
import { 
  pickTargetMonth, 
  humanizeMonth, 
  generateImportSummary, 
  buildTransactionUrl 
} from '../lib/import-utils';
import { runPhase, ImportPhase, PhaseState } from './useFileUpload';

const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

export function useUploadApi() {
  const router = useRouter();
  const [month, setGlobalMonth] = useGlobalMonth();
  const { success, error, warning } = useToast();

  const performApiCall = useCallback(async (file: File): Promise<ImportResponse> => {
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
    } catch (apiError: any) {
      // Log détaillé de l'erreur pour le débogage
      console.error("❌ API Request failed:", {
        message: apiError.message,
        status: apiError.response?.status,
        statusText: apiError.response?.statusText,
        headers: apiError.response?.headers,
        data: apiError.response?.data,
        config: {
          url: apiError.config?.url,
          method: apiError.config?.method,
          headers: apiError.config?.headers
        },
        code: apiError.code,
        stack: apiError.stack
      });
      
      throw apiError;
    }
  }, []);

  const simulatePhases = useCallback(async (
    setPhase: (phase: ImportPhase, data: Partial<PhaseState>) => void
  ): Promise<void> => {
    console.log('📊 Phase 1: Upload');
    await runPhase('upload', () => sleep(0), setPhase);
    console.log('📊 Phase 2: Parse');
    await runPhase('parse', () => sleep(0), setPhase);
    console.log('📊 Phase 3: Validate');
    await runPhase('validate', () => sleep(0), setPhase);
    console.log('📊 Phase 4: Import');
    await runPhase('import', () => sleep(0), setPhase);
    console.log('✅ All phases completed');
  }, []);

  const handleUploadSuccess = useCallback((importData: ImportResponse) => {
    // Déterminer le mois cible
    console.log('🎯 Determining target month:', {
      months: importData.months_detected,
      currentMonth: month
    });
    
    const targetMonth = pickTargetMonth(importData.months_detected, null, month);
    
    console.log('🎯 Target month selected:', targetMonth);
    
    if (!targetMonth) {
      error("Import terminé, aucun mois détecté", {
        description: "Vérifiez la colonne des dates et le format du CSV.",
        duration: 0
      });
      return;
    }
    
    // Générer le résumé
    const { totalNew, monthsSummary } = generateImportSummary(importData.months_detected);
    
    // Afficher les avertissements si nécessaire
    if (importData.validation_errors.length > 0) {
      warning(`${totalNew} transactions importées avec ${importData.validation_errors.length} avertissement(s)`, {
        description: importData.validation_errors.slice(0, 2).join(" • "),
        duration: 8000
      });
    }
    
    // Construire l'URL de redirection
    const redirectUrl = buildTransactionUrl(targetMonth, importData.import_id);
    
    console.log('🔗 Redirect URL built:', redirectUrl, {
      targetMonth,
      importId: importData.import_id
    });
    
    // Toast de succès avec actions rapides
    const otherMonths = importData.months_detected.filter(m => 
      m.month !== targetMonth && m.transaction_count > 0
    );
    
    const toastActions = otherMonths.slice(0, 2).map(monthItem => ({
      label: humanizeMonth(monthItem.month),
      onClick: () => {
        const url = buildTransactionUrl(monthItem.month, importData.import_id);
        router.replace(url);
      }
    }));
    
    success(`Import réussi • ${totalNew} nouvelles transactions`, {
      description: importData.months_detected.length === 1 
        ? `Redirection vers ${humanizeMonth(targetMonth)}...`
        : `Mois: ${monthsSummary}`,
      actions: toastActions,
      ...(otherMonths.length > 2 && {
        secondaryAction: {
          label: `+${otherMonths.length - 2} autres`,
          onClick: () => {
            router.replace(redirectUrl);
          }
        }
      }),
      duration: 3000
    });
    
    // Mettre à jour le mois global avant la navigation
    console.log('🗓️  Updating global month before redirect:', targetMonth);
    setGlobalMonth(targetMonth);
    
    // Navigation après un délai court
    setTimeout(() => {
      console.log('🚀 Navigating to:', redirectUrl);
      router.replace(redirectUrl);
    }, 1200);
  }, [month, router, setGlobalMonth, success, error, warning]);

  const uploadFile = useCallback(async (
    file: File,
    setPhase: (phase: ImportPhase, data: Partial<PhaseState>) => void
  ) => {
    // Lancer l'API et la simulation en parallèle
    const [importData] = await Promise.all([
      performApiCall(file),
      simulatePhases(setPhase)
    ]);
    
    handleUploadSuccess(importData);
  }, [performApiCall, simulatePhases, handleUploadSuccess]);

  return {
    uploadFile
  };
}