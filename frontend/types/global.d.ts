// Types globaux pour l'application Budget Famille

declare global {
  // Variables d'environnement
  namespace NodeJS {
    interface ProcessEnv {
      NEXT_PUBLIC_API_BASE: string;
      NODE_ENV: "development" | "production" | "test";
    }
  }

  // Étendre Window pour les données personnalisées
  interface Window {
    // Pour des analytiques ou debugging
    __BUDGET_APP_DEBUG__?: boolean;
  }

  // Types utilitaires personnalisés
  type Prettify<T> = {
    [K in keyof T]: T[K];
  } & {};

  // Pour les identifiants de ressources
  type ResourceId = number | string;

  // Types de statut communs
  type Status = "idle" | "loading" | "success" | "error";

  // Pour les réponses d'API génériques
  interface ApiResponse<T = any> {
    data: T;
    message?: string;
    status?: number;
  }

  // Pour les erreurs d'API
  interface ApiErrorResponse {
    detail: string;
    status_code: number;
    type?: string;
  }

  // Types de pagination
  interface PaginationParams {
    page?: number;
    limit?: number;
    offset?: number;
  }

  interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    limit: number;
    pages: number;
  }

  // Types de dates au format string
  type DateString = string; // ISO 8601 format
  type MonthString = string; // Format "YYYY-MM"

  // Types de validation
  interface ValidationError {
    field: string;
    message: string;
    code?: string;
  }

  // Types de formulaires
  interface FormState<T = any> {
    data: T;
    errors: Record<string, string>;
    isSubmitting: boolean;
    isValid: boolean;
  }
}

export {};