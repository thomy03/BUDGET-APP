'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '../components/ui';

export function useUploadErrorHandler() {
  const router = useRouter();
  const { error } = useToast();

  const handleUploadError = useCallback((err: any, file?: File | null) => {
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
      
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } else if (err?.message === "Token d'authentification manquant") {
      errorMessage = "Authentification manquante";
      errorDescription = "Veuillez vous reconnecter pour continuer.";
      
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } else if (err?.response?.status === 400) {
      // Gestion spécifique des erreurs 400 Bad Request
      errorMessage = "Fichier CSV invalide";
      
      const responseData = err?.response?.data;
      console.error("🔍 400 Bad Request details:", responseData);
      
      let errorDetail = "";
      if (responseData?.detail) {
        errorDetail = responseData.detail;
      } else if (responseData?.message) {
        errorDetail = responseData.message;
      } else if (responseData?.error) {
        errorDetail = responseData.error;
      } else if (typeof responseData === 'string') {
        errorDetail = responseData;
      }
      
      // Amélioration pédagogique des messages d'erreur
      if (errorDetail.toLowerCase().includes('date') || errorDetail.toLowerCase().includes('parsing')) {
        errorMessage = "Format de date incorrect";
        errorDescription = "Les dates doivent être au format DD/MM/YYYY (ex: 15/03/2024) ou YYYY-MM-DD (ex: 2024-03-15). Vérifiez que votre fichier utilise un de ces formats.";
        if (errorDetail) {
          errorDescription += ` Détail technique: ${errorDetail}`;
        }
      } else if (errorDetail.toLowerCase().includes('montant') || errorDetail.toLowerCase().includes('amount')) {
        errorMessage = "Format de montant incorrect";
        errorDescription = "Les montants doivent être des nombres (positifs ou négatifs) avec virgule ou point comme séparateur décimal. Exemples valides: 123,45 ou -67.89";
        if (errorDetail) {
          errorDescription += ` Détail technique: ${errorDetail}`;
        }
      } else if (errorDetail.toLowerCase().includes('column') || errorDetail.toLowerCase().includes('colonne')) {
        errorMessage = "Colonnes manquantes";
        errorDescription = "Votre fichier doit contenir les colonnes suivantes (sous différentes variantes acceptées): Date (date, datum), Description (description, libellé, label), Montant (montant, amount), Compte (compte, account, accountLabel). Vérifiez la présence et l'orthographe des colonnes.";
        if (errorDetail) {
          errorDescription += ` Détail technique: ${errorDetail}`;
        }
      } else if (errorDetail) {
        errorDescription = `Erreur de validation: ${errorDetail}`;
      } else {
        errorDescription = "Le format du fichier CSV est invalide. Vérifiez que le fichier contient les colonnes requises avec leurs variantes acceptées: Date (date, datum), Description (description, libellé, label), Montant (montant, amount), Compte (compte, account, accountLabel).";
        
        if (responseData) {
          errorDescription += ` (Données reçues: ${JSON.stringify(responseData).substring(0, 200)}...)`;
        }
      }
      
      if (file) {
        errorDescription += ` • Fichier: "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)}MB)`;
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
      errorMessage = "Fichier trop volumineux";
      errorDescription = "La taille du fichier dépasse la limite autorisée (10MB maximum).";
    } else if (err?.response?.status === 415) {
      errorMessage = "Type de fichier non supporté";
      errorDescription = "Seuls les fichiers CSV, XLSX et XLS sont acceptés.";
    } else if (err?.response?.data?.detail) {
      errorMessage = "Import échoué";
      errorDescription = err.response.data.detail;
    } else if (err?.code === 'ECONNABORTED') {
      errorMessage = "Délai d'attente dépassé";
      errorDescription = "L'import a pris trop de temps. Essayez avec un fichier plus petit.";
    } else if (err?.code === 'ERR_NETWORK') {
      errorMessage = "Erreur de connexion";
      errorDescription = "Impossible de joindre le serveur. Vérifiez votre connexion internet.";
    } else if (err?.response?.status >= 500) {
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
  }, [router, error]);

  return { handleUploadError };
}