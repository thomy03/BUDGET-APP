import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";

// Configuration de l'API
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || "http://host.docker.internal:8000";

// Types de données de l'application
export type ConfigOut = {
  id: number;
  member1: string;
  member2: string;
  rev1: number;
  rev2: number;
  tax_rate1: number;
  tax_rate2: number;
  split_mode: "revenus" | "manuel";
  split1: number;
  split2: number;
  other_split_mode?: string;
  var_percent?: number;
  max_var?: number;
  min_fixed?: number;
  created_at?: string;
  updated_at?: string;
  // Champs obsolètes - remplacés par le système de dépenses fixes personnalisables
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  loan_equal: boolean;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  loan_amount: number;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  other_fixed_simple: boolean;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  other_fixed_monthly: number;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  taxe_fonciere_ann: number;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  copro_montant: number;
  /** @deprecated Utiliser le système de dépenses fixes personnalisables */
  copro_freq: "mensuelle" | "trimestrielle";
  /** @deprecated Utiliser le système de provisions personnalisables */
  vac_percent: number;
  /** @deprecated Utiliser le système de provisions personnalisables */
  vac_base: "2" | "1" | "2nd";
};

export type Tx = {
  id: number;
  date_op: string; // Date format backend
  date_valeur?: string; // Date de valeur (optional - sent by backend)
  label: string; // Libellé
  category: string; // Catégorie
  subcategory?: string; // Sous-catégorie (sent by backend as subcategory)
  amount: number; // Montant  
  tags: string[]; // Tags as array
  month: string;
  is_expense: boolean;
  exclude?: boolean; // Optionnel
  // New fields for expense type classification
  expense_type?: 'fixed' | 'variable'; // Type de dépense
  expense_type_confidence?: number; // Score de confiance IA (0-1)
  confidence_score?: number; // Score de confiance IA (0-1) - backend field
  expense_type_auto_detected?: boolean; // Si détecté automatiquement par IA
  expense_type_manual_override?: boolean; // Si modifié manuellement par l'utilisateur
  // Optional fields for backward compatibility
  category_parent?: string; // Legacy field - mapped from subcategory
  account_label?: string; // Legacy field - not used in current backend
  row_id?: string; // Legacy field - not used in current backend
  import_id?: string; // Legacy field - not used in current backend
};

export type Summary = {
  month: string;
  var_total: number;
  r1: number;
  r2: number;
  member1: string;
  member2: string;
  total_p1: number;
  total_p2: number;
  detail: Record<string, Record<string, number>>;
  // Champs obsolètes - conservés pour compatibilité backend mais non utilisés dans l'interface
  /** @deprecated Données maintenant calculées via le système de dépenses fixes personnalisables */
  loan_amount: number;
  /** @deprecated Données maintenant calculées via le système de dépenses fixes personnalisables */
  taxe_m: number;
  /** @deprecated Données maintenant calculées via le système de dépenses fixes personnalisables */
  copro_m: number;
  /** @deprecated Données maintenant calculées via le système de dépenses fixes personnalisables */
  other_fixed_total: number;
  /** @deprecated Données maintenant calculées via le système de provisions personnalisables */
  vac_monthly_total: number;
};

export type FixedLine = {
  id: number;
  label: string;
  amount: number;
  freq: "mensuelle" | "trimestrielle" | "annuelle";
  split_mode: "clé" | "50/50" | "m1" | "m2" | "manuel";
  split1: number;
  split2: number;
  category: "logement" | "transport" | "services" | "loisirs" | "santé" | "autres";
  active: boolean;
  // Computed properties for UI compatibility
  name?: string; // Alias for label
  is_active?: boolean; // Alias for active
};

export type FixedLineCreate = {
  label: string;
  amount: number;
  freq: "mensuelle" | "trimestrielle" | "annuelle";
  split_mode: "clé" | "50/50" | "m1" | "m2" | "manuel";
  split1: number;
  split2: number;
  category?: "logement" | "transport" | "services" | "loisirs" | "santé" | "autres";
  active?: boolean;
};

export type FixedLineUpdate = Partial<FixedLineCreate>;

// Types pour le nouveau système d'import optimisé
export type ImportMonth = {
  month: string; // Format YYYY-MM
  transaction_count: number; // Nombre de transactions créées
  date_range: {
    start?: string;
    end?: string;
  }; // Plage de dates du mois
  total_amount: number; // Montant total des transactions
  categories: string[]; // Catégories détectées
};

export type ImportResponse = {
  import_id: string; // UUID unique de l'import
  status: string; // État de l'import
  filename: string; // Nom du fichier original
  rows_processed: number; // Nombre de lignes traitées
  months_detected: ImportMonth[]; // Mois détectés avec métadonnées
  duplicates_info: { // Information sur les doublons
    duplicates_count?: number;
  };
  validation_errors: string[]; // Erreurs de validation
  message: string; // Message de réponse
};

// =============================================================================
// PAGINATION - Types pour les réponses paginées (Phase 3 Performance)
// =============================================================================

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
};

export type PaginationParams = {
  page?: number;
  limit?: number;
};

// =============================================================================
// IMPORT PREVIEW - Prévisualisation avant import (Phase 4 Fonctionnel)
// =============================================================================

export type ImportPreviewTransaction = {
  row_number: number;
  date: string | null;
  label: string | null;
  amount: number | null;
  month: string | null;
  is_valid: boolean;
  validation_errors: string[];
};

export type ImportPreviewResponse = {
  success: boolean;
  filename: string;
  file_type: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  months_detected: string[];
  months_summary: Record<string, number>;
  sample_transactions: ImportPreviewTransaction[];
  potential_duplicates: Array<{
    month: string;
    existing_transactions: number;
    new_transactions: number;
    warning: string;
  }>;
  validation_warnings: string[];
  columns_detected: string[];
  ready_to_import: boolean;
};

// =============================================================================
// MERGE TAGS - Fusion de tags (Phase 4 Fonctionnel)
// =============================================================================

export type MergeTagsRequest = {
  source_tags: string[];
  target_tag: string;
  delete_source_tags?: boolean;
};

export type MergeTagsResponse = {
  success: boolean;
  message: string;
  source_tags: string[];
  target_tag: string;
  transactions_updated: number;
  patterns_merged: number;
  fixed_line_mappings_updated: number;
  stats: {
    source_tags_stats: Record<string, { transaction_count: number; updated: number }>;
    target_tag_final_stats: {
      transaction_count: number;
      total_amount: number;
    };
  };
};

// =============================================================================
// ML TRAINING - Entraînement ML asynchrone (Phase 3 Performance)
// =============================================================================

export type MLTrainingJobStatus = {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  progress: number;
  duration_seconds: number | null;
};

export type MLTrainingSubmitResponse = {
  status: 'submitted';
  message: string;
  job_id: string;
  check_status_url: string;
};

// Types pour les provisions personnalisables
export type CustomProvision = {
  id: number;
  name: string;
  description?: string;
  percentage: number;
  base_calculation: "total" | "member1" | "member2" | "fixed";
  fixed_amount?: number;
  split_mode: "key" | "50/50" | "custom" | "100/0" | "0/100";
  split_member1: number;
  split_member2: number;
  icon: string;
  color: string;
  display_order: number;
  is_active: boolean;
  is_temporary: boolean;
  start_date?: string;
  end_date?: string;
  target_amount?: number;
  current_amount: number;
  created_at: string;
  updated_at?: string;
  created_by?: string;
  category: "savings" | "investment" | "project" | "custom";
  monthly_amount?: number;
  progress_percentage?: number;
};

export type CustomProvisionCreate = {
  name: string;
  description?: string;
  percentage: number;
  base_calculation: "total" | "member1" | "member2" | "fixed";
  fixed_amount?: number;
  split_mode: "key" | "50/50" | "custom" | "100/0" | "0/100";
  split_member1: number;
  split_member2: number;
  icon: string;
  color: string;
  display_order?: number;
  is_active: boolean;
  is_temporary: boolean;
  start_date?: string;
  end_date?: string;
  target_amount?: number;
  category: "savings" | "investment" | "project" | "custom";
};

export type CustomProvisionUpdate = Partial<CustomProvisionCreate>;

export type CustomProvisionSummary = {
  total_provisions: number;
  active_provisions: number;
  total_monthly_amount: number;
  total_monthly_member1: number;
  total_monthly_member2: number;
  provisions_by_category: Record<string, number>;
  provisions_details: CustomProvision[];
};

// Types pour le système de classification automatique des dépenses
export type ExpenseClassificationRule = {
  id: number;
  name: string;
  description?: string;
  keywords: string[]; // Mots-clés à rechercher dans les libellés
  expense_type: 'fixed' | 'variable';
  confidence_threshold: number; // Seuil de confiance minimum (0-1)
  is_active: boolean;
  priority: number; // Ordre de priorité d'application
  created_at: string;
  updated_at?: string;
  match_type: 'exact' | 'partial' | 'regex'; // Type de correspondance
  case_sensitive: boolean;
};

export type ExpenseClassificationRuleCreate = {
  name: string;
  description?: string;
  keywords: string[];
  expense_type: 'fixed' | 'variable';
  confidence_threshold: number;
  is_active: boolean;
  priority?: number;
  match_type?: 'exact' | 'partial' | 'regex';
  case_sensitive?: boolean;
};

export type ExpenseClassificationRuleUpdate = Partial<ExpenseClassificationRuleCreate>;

export type ExpenseClassificationResult = {
  transaction_id: number;
  suggested_type: 'fixed' | 'variable';
  confidence_score: number;
  matched_rules: {
    rule_id: number;
    rule_name: string;
    matched_keywords: string[];
  }[];
  reasoning: string; // Explication textuelle du choix
};

// Types pour la gestion du solde de compte
export type AccountBalance = {
  id: number;
  month: string;
  account_balance: number;
  budget_target?: number;
  savings_goal?: number;
  notes?: string;
  is_closed?: boolean;
  created_at: string;
  updated_at?: string;
  created_by: string;
};

export type AccountBalanceUpdate = {
  account_balance: number;
  notes?: string;
};

export type BalanceTransferCalculation = {
  month: string;
  total_expenses: number;
  total_member1: number;
  total_member2: number;
  current_balance: number;
  suggested_transfer_member1: number;
  suggested_transfer_member2: number;
  final_balance_after_transfers: number;
  balance_status: 'sufficient' | 'tight' | 'deficit' | 'surplus';
};

// Types pour les erreurs API
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: Record<string, unknown>;
}

// Types pour le scanner de tickets (OCR)
export type ReceiptScanResult = {
  success: boolean;
  merchant: string | null;
  amount: number | null;
  date: string | null;
  suggested_tag: string | null;
  confidence: number;
  all_amounts: number[];
  raw_text: string;
  message: string;
};

export type ReceiptCreateRequest = {
  merchant: string;
  amount: number;
  date: string;
  tag?: string | null;
  notes?: string | null;
};

export type ReceiptCreateResponse = {
  success: boolean;
  transaction_id: number | null;
  message: string;
};

export type OCRStatusResponse = {
  available: boolean;
  message: string;
};

// Déclaration pour étendre le type de config axios
declare module "axios" {
  interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}

// Créer l'instance axios
export const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000, // 15 secondes timeout
  headers: {
    "Content-Type": "application/json",
  },
});

// Intercepteur de requête
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Ajouter timestamp pour éviter le cache
    config.metadata = { startTime: new Date() };
    
    // Assurer que le token d'authentification est présent sur chaque requête
    if (typeof window !== "undefined" && !config.headers.Authorization) {
      const token = localStorage.getItem("auth_token");
      const tokenType = localStorage.getItem("token_type") || "Bearer";
      
      if (token) {
        config.headers.Authorization = `${tokenType} ${token}`;
        
        // Logs spécifiques pour les requêtes critiques
        if (process.env.NODE_ENV === "development" && (config.url?.includes("/import") || config.url?.includes("/provision"))) {
          console.log(`🔑 Auth header added to ${config.url}:`, {
            authHeader: config.headers.Authorization?.substring(0, 20) + "...",
            tokenType,
            hasToken: !!token
          });
        }
      } else if (process.env.NODE_ENV === "development") {
        console.warn(`⚠️ No auth token found for ${config.url}`);
      }
    }
    
    // Logs de développement pour les provisions
    if (process.env.NODE_ENV === "development" && config.url?.includes("provision")) {
      console.log(`🚀 Provisions API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        baseURL: config.baseURL,
        fullURL: `${config.baseURL}${config.url}`,
        hasAuth: !!config.headers.Authorization,
        contentType: config.headers["Content-Type"],
        authType: String(config.headers.Authorization || '').split(' ')[0]
      });
    } else if (process.env.NODE_ENV === "development") {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        hasAuth: !!config.headers.Authorization,
        contentType: config.headers["Content-Type"]
      });
    }
    
    return config;
  },
  (error: AxiosError) => {
    console.error("❌ Request error:", error);
    return Promise.reject(error);
  }
);

// Intercepteur de réponse
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Logs de développement
    if (process.env.NODE_ENV === "development") {
      const duration = new Date().getTime() - (response.config.metadata?.startTime?.getTime() || 0);
      console.log(`✅ API Response: ${response.status} ${response.config.url} (${duration}ms)`);
    }
    
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Logs d'erreur détaillés
    if (process.env.NODE_ENV === "development") {
      const isImportRequest = originalRequest?.url?.includes("/import");
      const isProvisionRequest = originalRequest?.url?.includes("/provision");
      
      if (isImportRequest || isProvisionRequest) {
        // Logs spécialement détaillés pour les requêtes critiques
        const requestType = isImportRequest ? "Import" : "Provision";
        console.error(`❌ ${requestType} API Error: ${error.response?.status} ${originalRequest?.url}`, {
          status: error.response?.status,
          statusText: error.response?.statusText,
          headers: error.response?.headers,
          data: error.response?.data,
          config: {
            url: originalRequest?.url,
            method: originalRequest?.method,
            baseURL: originalRequest?.baseURL,
            fullURL: `${originalRequest?.baseURL}${originalRequest?.url}`,
            headers: {
              'Content-Type': originalRequest?.headers?.['Content-Type'],
              'Authorization': originalRequest?.headers?.['Authorization'] ? 
                `${String(originalRequest?.headers?.['Authorization'] || '').split(' ')[0]} [TOKEN]` : 'None'
            }
          },
          networkError: error.code === 'ERR_NETWORK',
          timeout: error.code === 'ECONNABORTED',
          message: error.message
        });
      } else {
        console.error(`❌ API Error: ${error.response?.status} ${originalRequest?.url}`, error.response?.data);
      }
    }

    // Gestion des erreurs d'authentification
    if (error.response?.status === 401) {
      // Éviter les boucles infinies
      if (originalRequest?.url?.includes("/token")) {
        return Promise.reject(createApiError(error, "Identifiants incorrects"));
      }

      // Nettoyer les données d'authentification
      localStorage.removeItem("auth_token");
      localStorage.removeItem("token_type");
      localStorage.removeItem("username");
      delete api.defaults.headers.common["Authorization"];
      
      // Rediriger vers login seulement si on n'y est pas déjà
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
      
      return Promise.reject(createApiError(error, "Session expirée. Veuillez vous reconnecter."));
    }

    // Autres erreurs HTTP
    return Promise.reject(createApiError(error));
  }
);

// Fonction utilitaire pour créer des erreurs API structurées
function createApiError(axiosError: AxiosError, customMessage?: string): ApiError {
  const status = axiosError.response?.status;
  const data = axiosError.response?.data as Record<string, unknown> | undefined;
  
  let message = customMessage || "Une erreur est survenue";
  
  if (!customMessage) {
    if (status === 400) {
      message = "Données invalides";
      
      // Pour les erreurs 400 spécifiquement, essayer d'extraire plus d'informations
      if (axiosError.config?.url?.includes("/import")) {
        message = "Fichier CSV invalide";
        
        // Log détaillé pour les erreurs d'import 400
        if (process.env.NODE_ENV === "development") {
          console.error("🔍 Detailed 400 error analysis:", {
            url: axiosError.config.url,
            responseData: data,
            responseType: typeof data,
            responseKeys: data && typeof data === 'object' ? Object.keys(data) : [],
            statusText: axiosError.response?.statusText
          });
        }
      }
    } else if (status === 403) {
      message = "Accès refusé";
    } else if (status === 404) {
      message = "Ressource introuvable";
    } else if (status === 422) {
      message = "Données de validation incorrectes";
    } else if (status && status >= 500) {
      message = "Erreur serveur - Veuillez réessayer plus tard";
    } else if (axiosError.code === "ECONNABORTED") {
      message = "Délai de connexion dépassé";
    } else if (axiosError.code === "ERR_NETWORK") {
      message = "Erreur réseau - Vérifiez votre connexion";
    }
    
    // Utiliser le message du serveur si disponible
    if (data?.detail && typeof data.detail === 'string') {
      message = data.detail;
    } else if (data?.message && typeof data.message === 'string') {
      message = data.message;
    } else if (data?.error && typeof data.error === 'string') {
      message = data.error;
    }
  }
  
  return {
    message,
    status,
    code: axiosError.code,
    details: data,
  };
}

// Fonctions utilitaires pour les appels API
export const apiUtils = {
  // Vérifier si l'API est accessible
  async checkHealth(): Promise<boolean> {
    try {
      await api.get("/health", { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  },

  // Configurer l'authentification
  setAuthToken(token: string, tokenType: string = "Bearer") {
    const authHeader = `${tokenType} ${token}`;
    api.defaults.headers.common["Authorization"] = authHeader;
    
    // Logs de débogage en développement
    if (process.env.NODE_ENV === "development") {
      console.log("🔑 Auth token set globally:", authHeader.substring(0, 20) + "...");
    }
  },

  // Supprimer l'authentification
  clearAuthToken() {
    delete api.defaults.headers.common["Authorization"];
    
    // Logs de débogage en développement
    if (process.env.NODE_ENV === "development") {
      console.log("🔑 Auth token cleared");
    }
  },

  // Vérifier si le token d'authentification est configuré
  hasAuthToken(): boolean {
    return !!api.defaults.headers.common["Authorization"];
  },

  // Obtenir le token actuel (pour débogage)
  getCurrentAuthHeader(): string | undefined {
    return api.defaults.headers.common["Authorization"] as string | undefined;
  },

  // Retry d'une requête avec backoff exponentiel
  async retryRequest<T>(requestFn: () => Promise<T>, maxRetries: number = 3): Promise<T> {
    let lastError: any;
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        
        // Ne pas retry sur les erreurs d'auth ou de validation
        if (error instanceof AxiosError && error.response) {
          const status = error.response.status;
          if (status === 401 || status === 403 || status === 422) {
            throw error;
          }
        }
        
        // Attendre avant de retry (backoff exponentiel)
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
        }
      }
    }
    
    throw lastError;
  },
};

// =============================================================================
// FONCTIONS API POUR PROVISIONS PERSONNALISABLES
// =============================================================================

export const provisionsApi = {
  // Récupérer toutes les provisions
  async getAll(): Promise<CustomProvision[]> {
    const response = await api.get<CustomProvision[]>('/custom-provisions');
    return response.data || [];
  },

  // Créer une nouvelle provision
  async create(provision: CustomProvisionCreate): Promise<CustomProvision> {
    const response = await api.post<CustomProvision>('/custom-provisions', provision);
    return response.data;
  },

  // Mettre à jour une provision existante
  async update(id: number, provision: CustomProvisionUpdate): Promise<CustomProvision> {
    const response = await api.put<CustomProvision>(`/custom-provisions/${id}`, provision);
    return response.data;
  },

  // Mettre à jour partiellement une provision (ex: statut actif/inactif)
  async patch(id: number, updates: Partial<CustomProvision>): Promise<CustomProvision> {
    const response = await api.patch<CustomProvision>(`/custom-provisions/${id}`, updates);
    return response.data;
  },

  // Supprimer une provision
  async delete(id: number): Promise<void> {
    await api.delete(`/custom-provisions/${id}`);
  },

  // Récupérer le résumé des provisions
  async getSummary(): Promise<CustomProvisionSummary> {
    const response = await api.get<CustomProvisionSummary>('/custom-provisions/summary');
    return response.data;
  }
};

// =============================================================================
// FONCTIONS API POUR DÉPENSES FIXES
// =============================================================================

export const fixedExpensesApi = {
  // Récupérer toutes les dépenses fixes
  async getAll(): Promise<FixedLine[]> {
    const response = await api.get<FixedLine[]>('/fixed-lines');
    return response.data || [];
  },

  // Créer une nouvelle dépense fixe
  async create(expense: FixedLineCreate): Promise<FixedLine> {
    const response = await api.post<FixedLine>('/fixed-lines', expense);
    return response.data;
  },

  // Mettre à jour une dépense fixe existante
  async update(id: number, expense: FixedLineUpdate): Promise<FixedLine> {
    const response = await api.put<FixedLine>(`/fixed-lines/${id}`, expense);
    return response.data;
  },

  // Mettre à jour partiellement une dépense fixe (ex: statut actif/inactif)
  async patch(id: number, updates: Partial<FixedLine>): Promise<FixedLine> {
    const response = await api.patch<FixedLine>(`/fixed-lines/${id}`, updates);
    return response.data;
  },

  // Supprimer une dépense fixe
  async delete(id: number): Promise<void> {
    await api.delete(`/fixed-lines/${id}`);
  }
};

// =============================================================================
// FONCTIONS API POUR CLASSIFICATION AUTOMATIQUE DES DÉPENSES
// =============================================================================

export const expenseClassificationApi = {
  // Récupérer toutes les règles de classification avec fallback gracieux
  async getRules(): Promise<ExpenseClassificationRule[]> {
    try {
      const response = await api.get<ExpenseClassificationRule[]>('/expense-classification/rules');
      return response.data || [];
    } catch (error: any) {
      console.warn('Expense classification rules endpoint unavailable:', error);
      
      // Fallback : règles de classification par défaut
      const defaultRules: ExpenseClassificationRule[] = [
        {
          id: 1,
          name: 'Abonnements et Services',
          description: 'Détecte les abonnements récurrents (Netflix, Spotify, etc.)',
          keywords: ['netflix', 'spotify', 'abonnement', 'mensuel', 'subscription'],
          expense_type: 'fixed',
          confidence_threshold: 0.8,
          is_active: true,
          priority: 1,
          match_type: 'partial',
          case_sensitive: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 2,
          name: 'Courses et Alimentaire',
          description: 'Détecte les dépenses alimentaires variables',
          keywords: ['carrefour', 'leclerc', 'auchan', 'courses', 'supermarché', 'alimentaire'],
          expense_type: 'variable',
          confidence_threshold: 0.7,
          is_active: true,
          priority: 2,
          match_type: 'partial',
          case_sensitive: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 3,
          name: 'Loyer et Charges',
          description: 'Détecte les charges fixes de logement',
          keywords: ['loyer', 'charges', 'syndic', 'électricité', 'gaz', 'eau'],
          expense_type: 'fixed',
          confidence_threshold: 0.9,
          is_active: true,
          priority: 3,
          match_type: 'partial',
          case_sensitive: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 4,
          name: 'Transport Variable',
          description: 'Détecte les dépenses de transport variables (essence, parking)',
          keywords: ['essence', 'station', 'parking', 'péage', 'carburant'],
          expense_type: 'variable',
          confidence_threshold: 0.8,
          is_active: true,
          priority: 4,
          match_type: 'partial',
          case_sensitive: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 5,
          name: 'Assurances',
          description: 'Détecte les paiements d\'assurance fixes',
          keywords: ['assurance', 'mutuelle', 'maaf', 'axa', 'generali'],
          expense_type: 'fixed',
          confidence_threshold: 0.9,
          is_active: true,
          priority: 5,
          match_type: 'partial',
          case_sensitive: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ];
      
      // Ajouter une indication que ce sont des données par défaut
      console.info('Using default classification rules due to API unavailability');
      return defaultRules;
    }
  },

  // Créer une nouvelle règle de classification
  async createRule(rule: ExpenseClassificationRuleCreate): Promise<ExpenseClassificationRule> {
    const response = await api.post<ExpenseClassificationRule>('/expense-classification/rules', rule);
    return response.data;
  },

  // Mettre à jour une règle de classification
  async updateRule(id: number, rule: ExpenseClassificationRuleUpdate): Promise<ExpenseClassificationRule> {
    const response = await api.put<ExpenseClassificationRule>(`/expense-classification/rules/${id}`, rule);
    return response.data;
  },

  // Supprimer une règle de classification
  async deleteRule(id: number): Promise<void> {
    await api.delete(`/expense-classification/rules/${id}`);
  },

  // Classifier une transaction spécifique
  async classifyTransaction(transactionId: number): Promise<ExpenseClassificationResult> {
    const response = await api.post<ExpenseClassificationResult>(`/expense-classification/classify/${transactionId}`);
    return response.data;
  },

  // Classifier toutes les transactions d'un mois
  async classifyMonth(month: string): Promise<ExpenseClassificationResult[]> {
    const response = await api.post<ExpenseClassificationResult[]>(`/expense-classification/classify-month`, { month });
    return response.data || [];
  },

  // Mettre à jour le type de dépense d'une transaction
  async updateTransactionType(transactionId: number, expenseType: 'fixed' | 'variable', manualOverride: boolean = true): Promise<Tx> {
    const response = await api.patch<Tx>(`/transactions/${transactionId}/expense-type`, {
      expense_type: expenseType.toUpperCase()
    });
    return response.data;
  }
};

// =============================================================================
// FONCTIONS API POUR ML FEEDBACK
// =============================================================================

export const mlFeedbackApi = {
  // Envoyer un feedback pour un changement de tag
  async sendTagFeedback(transactionId: number, oldTags: string, newTags: string): Promise<void> {
    try {
      await api.post('/api/ml-feedback', {
        transaction_id: transactionId,
        feedback_type: 'tag_change',
        old_value: oldTags,
        new_value: newTags,
        timestamp: new Date().toISOString()
      });
      console.log(`📝 ML Feedback sent: Tag change for transaction ${transactionId}`);
    } catch (error) {
      console.warn('Failed to send ML feedback for tag change:', error);
      // Non-blocking error - don't throw
    }
  },

  // Envoyer un feedback pour un changement de type de dépense
  async sendExpenseTypeFeedback(transactionId: number, oldType: string | null, newType: 'fixed' | 'variable'): Promise<void> {
    try {
      await api.post('/api/ml-feedback', {
        transaction_id: transactionId,
        feedback_type: 'expense_type_change',
        old_value: oldType,
        new_value: newType,
        timestamp: new Date().toISOString()
      });
      console.log(`📝 ML Feedback sent: Expense type change for transaction ${transactionId}`);
    } catch (error) {
      console.warn('Failed to send ML feedback for expense type change:', error);
      // Non-blocking error - don't throw
    }
  },

  // Envoyer un feedback pour une classification acceptée/rejetée
  async sendClassificationFeedback(transactionId: number, suggestedType: string, userAction: 'accept' | 'reject', finalType?: 'fixed' | 'variable'): Promise<void> {
    try {
      await api.post('/api/ml-feedback', {
        transaction_id: transactionId,
        feedback_type: 'classification_feedback',
        suggested_value: suggestedType,
        user_action: userAction,
        final_value: finalType,
        timestamp: new Date().toISOString()
      });
      console.log(`📝 ML Feedback sent: Classification ${userAction} for transaction ${transactionId}`);
    } catch (error) {
      console.warn('Failed to send ML feedback for classification:', error);
      // Non-blocking error - don't throw
    }
  }
};

// =============================================================================
// FONCTIONS API POUR LA GESTION DU SOLDE DE COMPTE
// =============================================================================

// =============================================================================
// FONCTIONS API POUR AUTO-TAGGING INTELLIGENT
// =============================================================================

export type AutoTagSuggestion = {
  transaction_id: number;
  label: string;
  suggested_tag: string;
  confidence: number;
  match_type: 'exact' | 'pattern' | 'merchant' | 'similar';
  source_label?: string;
};

export type AutoTagResult = {
  month: string;
  total_untagged: number;
  suggestions: AutoTagSuggestion[];
  applied_count?: number;
  skipped_count?: number;
};

export const autoTagApi = {
  // Prévisualiser les suggestions d'auto-tagging pour un mois
  async preview(month: string, minConfidence: number = 0.5): Promise<AutoTagResult> {
    const response = await api.get<AutoTagResult>('/transactions/auto-tag-preview', {
      params: { month, min_confidence: minConfidence }
    });
    return response.data;
  },

  // Appliquer l'auto-tagging sur un mois
  async apply(month: string, minConfidence: number = 0.7, dryRun: boolean = false): Promise<AutoTagResult> {
    const response = await api.post<AutoTagResult>('/transactions/auto-tag-month', {
      month,
      min_confidence: minConfidence,
      dry_run: dryRun
    });
    return response.data;
  },

  // Appliquer un tag suggéré à une transaction spécifique
  async applyTag(transactionId: number, tag: string): Promise<void> {
    await api.patch(`/transactions/${transactionId}`, { tags: tag });
  }
};

export const balanceApi = {
  // Récupérer le solde d'un mois
  async get(month: string): Promise<AccountBalance> {
    const response = await api.get<AccountBalance>(`/api/balance/${month}`);
    return response.data;
  },

  // Mettre à jour le solde d'un mois
  async update(month: string, balanceData: AccountBalanceUpdate): Promise<AccountBalance> {
    const response = await api.put<AccountBalance>(`/api/balance/${month}`, balanceData);
    return response.data;
  },

  // Récupérer le calcul des virements avec le solde
  async getTransferCalculation(month: string): Promise<BalanceTransferCalculation> {
    const response = await api.get<BalanceTransferCalculation>(`/api/balance/${month}/transfer-calculation`);
    return response.data;
  },

  // Lister tous les mois avec leurs soldes
  async list(limit: number = 12, offset: number = 0): Promise<AccountBalance[]> {
    const response = await api.get<AccountBalance[]>('/api/balance', {
      params: { limit, offset }
    });
    return response.data || [];
  }
};

// ============================================================================
// ANALYTICS API
// ============================================================================

export interface TrendData {
  month: string;
  revenues: number;
  expenses: number;
  savings: number;
  balance: number;
}

export const analyticsApi = {
  // Récupérer les tendances sur plusieurs mois
  async getTrends(period: string = 'last6'): Promise<TrendData[]> {
    try {
      const response = await api.get<TrendData[]>('/api/analytics/trends', {
        params: { months: period }
      });
      return response.data || [];
    } catch (error) {
      console.error('Error fetching trends:', error);
      // Retourner des données vides en cas d'erreur
      return [];
    }
  },

  // Récupérer le résumé analytics d'un mois
  async getSummary(month: string): Promise<any> {
    try {
      const response = await api.get(`/api/analytics/summary`, {
        params: { month }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching analytics summary:', error);
      return null;
    }
  },

  // Récupérer les dépenses par catégorie
  async getExpensesByCategory(month: string): Promise<any[]> {
    try {
      const response = await api.get('/api/analytics/expenses-by-category', {
        params: { month }
      });
      return response.data || [];
    } catch (error) {
      console.error('Error fetching expenses by category:', error);
      return [];
    }
  }
};

// ============================================================================
// TAG-CATEGORY MAPPINGS API
// ============================================================================

export type TagCategoryMappingBulkOut = {
  created: number;
  updated: number;
  total: number;
  mappings: Record<string, string>;
};

export const tagCategoryApi = {
  // Récupérer tous les mappings tag->catégorie
  async getAll(): Promise<Record<string, string>> {
    try {
      const response = await api.get<Record<string, string>>('/tag-categories/');
      return response.data || {};
    } catch (error) {
      console.error('Error fetching tag-category mappings:', error);
      return {};
    }
  },

  // Créer ou mettre à jour un mapping unique
  async setMapping(tagName: string, categoryId: string): Promise<void> {
    await api.post('/tag-categories/', { tag_name: tagName, category_id: categoryId });
  },

  // Synchroniser tous les mappings (bulk)
  async syncAll(mappings: Record<string, string>): Promise<TagCategoryMappingBulkOut> {
    const response = await api.post<TagCategoryMappingBulkOut>('/tag-categories/bulk', { mappings });
    return response.data;
  },

  // Supprimer un mapping
  async deleteMapping(tagName: string): Promise<void> {
    await api.delete(`/tag-categories/${encodeURIComponent(tagName)}`);
  },

  // Récupérer les statistiques
  async getStats(): Promise<{ total_mappings: number; categories_breakdown: Record<string, number> }> {
    const response = await api.get('/tag-categories/stats');
    return response.data;
  }
};

// =============================================================================
// CUSTOM CATEGORIES API (User-defined categories persistence)
// =============================================================================

export type CustomCategory = {
  id: string;
  name: string;
  icon?: string;
  color?: string;
  user_id?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type CustomCategoryCreate = {
  id: string;
  name: string;
  icon?: string;
  color?: string;
};

export type CustomCategoryBulkOut = {
  created: number;
  updated: number;
  total: number;
  categories: CustomCategory[];
};

export const customCategoriesApi = {
  // Récupérer toutes les catégories personnalisées
  async getAll(): Promise<CustomCategory[]> {
    try {
      const response = await api.get<CustomCategory[]>('/custom-categories/');
      return response.data || [];
    } catch (error) {
      console.error('Error fetching custom categories:', error);
      return [];
    }
  },

  // Créer ou mettre à jour une catégorie
  async save(category: CustomCategoryCreate): Promise<CustomCategory> {
    const response = await api.post<CustomCategory>('/custom-categories/', category);
    return response.data;
  },

  // Synchroniser toutes les catégories (bulk)
  async syncAll(categories: CustomCategoryCreate[]): Promise<CustomCategoryBulkOut> {
    const response = await api.post<CustomCategoryBulkOut>('/custom-categories/bulk', { categories });
    return response.data;
  },

  // Supprimer une catégorie
  async delete(categoryId: string): Promise<void> {
    await api.delete(`/custom-categories/${encodeURIComponent(categoryId)}`);
  }
};

// =============================================================================
// CATEGORY BUDGETS API (v4.0)
// =============================================================================

export type CategoryBudget = {
  id: number;
  category: string;
  tag_name?: string;
  month?: string;  // YYYY-MM or null for default
  budget_amount: number;
  alert_threshold: number;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at?: string;
  created_by?: string;
};

export type CategoryBudgetCreate = {
  category: string;
  tag_name?: string;
  month?: string;
  budget_amount: number;
  alert_threshold?: number;
  notes?: string;
};

export type CategoryBudgetUpdate = Partial<CategoryBudgetCreate> & {
  is_active?: boolean;
};

export type CategoryBudgetSuggestion = {
  category: string;
  suggested_amount: number;
  average_3_months: number;
  average_6_months: number;
  min_amount: number;
  max_amount: number;
  months_with_data: number;
  trend: 'increasing' | 'decreasing' | 'stable';
};

export type BudgetSuggestionsResponse = {
  suggestions: CategoryBudgetSuggestion[];
  total_suggested_budget: number;
  analysis_period_start: string;
  analysis_period_end: string;
};

export const categoryBudgetsApi = {
  // Lister tous les budgets par catégorie
  async list(month?: string, activeOnly: boolean = true): Promise<CategoryBudget[]> {
    const params: Record<string, any> = { active_only: activeOnly };
    if (month) params.month = month;

    const response = await api.get<CategoryBudget[]>('/budgets/categories', { params });
    return response.data || [];
  },

  // Alias pour compatibilité avec les composants
  async getAll(month?: string, activeOnly: boolean = true): Promise<CategoryBudget[]> {
    return this.list(month, activeOnly);
  },

  // Créer un nouveau budget par catégorie
  async create(budget: CategoryBudgetCreate): Promise<CategoryBudget> {
    const response = await api.post<CategoryBudget>('/budgets/categories', budget);
    return response.data;
  },

  // Récupérer un budget spécifique
  async get(id: number): Promise<CategoryBudget> {
    const response = await api.get<CategoryBudget>(`/budgets/categories/${id}`);
    return response.data;
  },

  // Mettre à jour un budget
  async update(id: number, updates: CategoryBudgetUpdate): Promise<CategoryBudget> {
    const response = await api.put<CategoryBudget>(`/budgets/categories/${id}`, updates);
    return response.data;
  },

  // Supprimer un budget
  async delete(id: number): Promise<void> {
    await api.delete(`/budgets/categories/${id}`);
  },

  // Obtenir des suggestions basées sur l'historique
  async getSuggestions(monthsHistory: number = 6): Promise<BudgetSuggestionsResponse> {
    const response = await api.get<BudgetSuggestionsResponse>('/budgets/suggestions', {
      params: { months_history: monthsHistory }
    });
    return response.data;
  },

  // Créer plusieurs budgets en une fois
  async bulkCreate(budgets: CategoryBudgetCreate[]): Promise<CategoryBudget[]> {
    const response = await api.post<CategoryBudget[]>('/budgets/bulk-create', budgets);
    return response.data || [];
  },

  // Appliquer automatiquement les suggestions pour un mois
  async applySuggestions(month: string, minAmount: number = 50): Promise<CategoryBudget[]> {
    const response = await api.post<CategoryBudget[]>('/budgets/apply-suggestions', null, {
      params: { month, min_amount: minAmount }
    });
    return response.data || [];
  }
};

// =============================================================================
// VARIANCE ANALYSIS API (v4.0)
// =============================================================================

export type CategoryVariance = {
  category: string;
  budgeted: number;
  actual: number;
  variance: number;
  variance_pct: number;
  status: 'under_budget' | 'on_track' | 'warning' | 'over_budget' | 'no_budget';
  top_transactions: Array<{
    id?: number;
    label: string;
    amount: number;
    date?: string;
  }>;
  vs_last_month?: string;
  transaction_count: number;
};

export type GlobalVariance = {
  budgeted: number;
  actual: number;
  variance: number;
  variance_pct: number;
  status: 'under_budget' | 'on_track' | 'warning' | 'over_budget' | 'no_budget';
};

export type VarianceAlert = {
  type: string;
  category: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
};

export type VarianceAnalysisResponse = {
  month: string;
  global_variance: GlobalVariance;
  by_category: CategoryVariance[];
  categories_over_budget: number;
  categories_on_track: number;
  alerts: VarianceAlert[];
};

export const varianceApi = {
  // Obtenir l'analyse de variance pour un mois
  async analyze(month: string): Promise<VarianceAnalysisResponse> {
    const response = await api.get<VarianceAnalysisResponse>('/analytics/variance', {
      params: { month }
    });
    return response.data;
  }
};

// =============================================================================
// AI ANALYSIS API (v4.0 - OpenRouter Integration)
// =============================================================================

export type AIStatus = {
  configured: boolean;
  model: string;
  language: string;
  max_tokens: number;
};

export type AIExplanationResponse = {
  explanation: string;
  model_used: string;
  language: string;
};

export type AISavingsResponse = {
  category: string;
  suggestions: string;
  average_spending: number;
  model_used: string;
};

export type AIMonthlySummaryResponse = {
  month: string;
  summary: string;
  income: number;
  expenses: number;
  savings: number;
  model_used: string;
};

export type AIQuestionResponse = {
  question: string;
  answer: string;
  model_used: string;
};

export const aiApi = {
  // Vérifier le statut du service IA
  async getStatus(): Promise<AIStatus> {
    const response = await api.get<AIStatus>('/ai/status');
    return response.data;
  },

  // Obtenir une explication IA des écarts budgétaires
  async explainVariance(month: string): Promise<AIExplanationResponse> {
    const response = await api.post<AIExplanationResponse>('/ai/explain-variance', { month }, {
      timeout: 60000, // 60 seconds for LLM processing
    });
    return response.data;
  },

  // Obtenir des suggestions d'économie pour une catégorie
  async suggestSavings(category: string, monthsHistory: number = 6): Promise<AISavingsResponse> {
    const response = await api.post<AISavingsResponse>('/ai/suggest-savings', {
      category,
      months_history: monthsHistory
    }, {
      timeout: 60000, // 60 seconds for LLM processing
    });
    return response.data;
  },

  // Générer un résumé mensuel intelligent
  async getMonthlySummary(month: string): Promise<AIMonthlySummaryResponse> {
    const response = await api.post<AIMonthlySummaryResponse>('/ai/monthly-summary', { month }, {
      timeout: 60000, // 60 seconds for LLM processing
    });
    return response.data;
  },

  // Poser une question libre sur le budget
  async askQuestion(question: string, month?: string): Promise<AIQuestionResponse> {
    const response = await api.post<AIQuestionResponse>('/ai/chat', {
      question,
      month
    }, {
      timeout: 60000, // 60 seconds for LLM processing
    });
    return response.data;
  },

  // Alias pour monthlySummary
  async monthlySummary(month: string): Promise<AIMonthlySummaryResponse> {
    return this.getMonthlySummary(month);
  },

  // Alias pour chat
  async chat(question: string, month?: string): Promise<AIQuestionResponse> {
    return this.askQuestion(question, month);
  },

  // Streaming chat (v4.1) - returns an async generator for SSE consumption
  async *streamChat(
    question: string,
    month?: string,
    onChunk?: (chunk: string) => void
  ): AsyncGenerator<string, void, unknown> {
    const token = localStorage.getItem("auth_token");
    const tokenType = localStorage.getItem("token_type") || "Bearer";

    const response = await fetch(`${API_BASE}/ai/chat-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `${tokenType} ${token}`
      },
      body: JSON.stringify({ question, month })
    });

    if (!response.ok) {
      throw new Error(`Streaming error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No readable stream available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              return;
            }

            if (data.startsWith('[ERROR:')) {
              throw new Error(data.slice(7, -1));
            }

            if (data) {
              if (onChunk) onChunk(data);
              yield data;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  // =============================================================================
  // SESSION-BASED CHAT (v4.1) - Multi-turn conversation memory
  // =============================================================================

  // Create a new chat session
  async createSession(month?: string): Promise<ChatSession> {
    const response = await api.post<ChatSession>('/ai/sessions', { month });
    return response.data;
  },

  // List all user sessions
  async listSessions(): Promise<ChatSession[]> {
    const response = await api.get<ChatSession[]>('/ai/sessions');
    return response.data;
  },

  // Get active session
  async getActiveSession(): Promise<ChatSession | null> {
    const response = await api.get<ChatSession | null>('/ai/sessions/active');
    return response.data;
  },

  // Get chat history for a session
  async getSessionHistory(sessionId: string): Promise<ChatHistoryResponse> {
    const response = await api.get<ChatHistoryResponse>(`/ai/sessions/${sessionId}`);
    return response.data;
  },

  // Delete a session
  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/ai/sessions/${sessionId}`);
  },

  // Clear all sessions
  async clearAllSessions(): Promise<{ sessions_deleted: number }> {
    const response = await api.delete<{ sessions_deleted: number }>('/ai/sessions');
    return response.data;
  },

  // Chat within a session (non-streaming)
  async sessionChat(sessionId: string, question: string, month?: string): Promise<SessionChatResponse> {
    const response = await api.post<SessionChatResponse>(`/ai/sessions/${sessionId}/chat`, {
      question,
      month
    });
    return response.data;
  },

  // Streaming chat within a session
  async *sessionStreamChat(
    sessionId: string,
    question: string,
    month?: string,
    onChunk?: (chunk: string) => void
  ): AsyncGenerator<string, void, unknown> {
    const token = localStorage.getItem("auth_token");
    const tokenType = localStorage.getItem("token_type") || "Bearer";

    const response = await fetch(`${API_BASE}/ai/sessions/${sessionId}/chat-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `${tokenType} ${token}`
      },
      body: JSON.stringify({ question, month })
    });

    if (!response.ok) {
      throw new Error(`Streaming error: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No readable stream available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              return;
            }

            if (data.startsWith('[ERROR:')) {
              throw new Error(data.slice(7, -1));
            }

            if (data) {
              if (onChunk) onChunk(data);
              yield data;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
};

// Session-based chat types
export type ChatSession = {
  session_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  has_context: boolean;
};

export type ChatHistoryMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  message_id: string;
};

export type ChatHistoryResponse = {
  session_id: string;
  messages: ChatHistoryMessage[];
  message_count: number;
};

export type SessionChatResponse = {
  session_id: string;
  question: string;
  answer: string;
  message_count: number;
  model_used: string;
};

// =============================================================================
// ML PREDICTIONS & ALERTS API (v4.0 - Budget Intelligence)
// =============================================================================

export type BudgetPrediction = {
  category: string;
  current_spent: number;
  predicted_month_end: number;
  monthly_average: number;
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'unknown';
  confidence: number;
  recommendation: string;
  // Prophet confidence intervals (v4.1)
  confidence_lower: number;  // 5th percentile
  confidence_upper: number;  // 95th percentile
  seasonality_detected: boolean;
  seasonal_component: number;  // Seasonal adjustment factor
  prediction_method: 'prophet' | 'linear' | 'simple';  // Which predictor was used
  mae_score: number;  // Mean Absolute Error
};

export type BudgetAlert = {
  alert_type: 'overspend_risk' | 'unusual_spike' | 'category_trend';
  category: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  current_amount: number;
  predicted_amount: number;
  threshold: number;
  days_remaining: number;
};

export type SmartRecommendation = {
  recommendation_type: 'budget_increase' | 'savings_opportunity' | 'spending_optimization';
  category: string;
  current_budget: number;
  suggested_budget: number;
  reasoning: string;
  impact_estimate: string;
  confidence: number;
};

export type Anomaly = {
  transaction_id: string;
  anomaly_type: 'amount' | 'frequency' | 'merchant' | 'duplicate' | 'statistical';
  severity: number;
  explanation: string;
  confidence: number;
};

export type DuplicateGroup = {
  transaction_ids: string[];
  similarity_score: number;
  duplicate_type: 'exact' | 'fuzzy' | 'temporal';
  explanation: string;
};

export type PredictionsOverview = {
  predictions: BudgetPrediction[];
  alerts: BudgetAlert[];
  recommendations: SmartRecommendation[];
  summary: {
    total_categories: number;
    total_spending?: number;
    at_risk_count: number;
    alerts_count?: number;
    month: string;
    message?: string;
    // Prophet-specific fields (v4.1)
    prediction_method?: 'prophet' | 'linear' | 'none';
    prophet_categories?: number;  // Number of categories using Prophet
  };
};

export type AnomaliesOverview = {
  anomalies: Anomaly[];
  duplicate_groups: DuplicateGroup[];
  summary: {
    total_transactions: number;
    anomalies_found: number;
    duplicates_found: number;
    high_severity_count?: number;
    message?: string;  // Added for ML training status messages
  };
};

// ML Status type
export type MLStatus = {
  ready: boolean;
  training: boolean;
  message: string;
};

export const predictionsApi = {
  // Check ML status (quick endpoint - no timeout needed)
  async getStatus(): Promise<MLStatus> {
    const response = await api.get<MLStatus>('/predictions/status', {
      timeout: 5000, // 5 seconds max for status check
    });
    return response.data;
  },

  // Get comprehensive predictions overview
  async getOverview(month: string): Promise<PredictionsOverview> {
    const response = await api.get<PredictionsOverview>('/predictions/overview', {
      params: { month },
      timeout: 60000, // 60 seconds for ML processing
    });
    return response.data;
  },

  // Get budget alerts only
  async getAlerts(month: string, severity?: 'low' | 'medium' | 'high'): Promise<BudgetAlert[]> {
    const response = await api.get<BudgetAlert[]>('/predictions/alerts', {
      params: { month, severity },
      timeout: 60000, // 60 seconds for ML processing
    });
    return response.data;
  },

  // Detect anomalies in transactions
  async detectAnomalies(month: string, limit: number = 20): Promise<AnomaliesOverview> {
    const response = await api.get<AnomaliesOverview>('/predictions/anomalies', {
      params: { month, limit },
      timeout: 60000, // 60 seconds for ML processing
    });
    return response.data;
  },

  // Force ML systems retraining (async mode by default)
  async retrain(asyncMode: boolean = true): Promise<MLTrainingSubmitResponse | { status: string; message: string }> {
    const response = await api.post('/predictions/retrain', null, {
      params: { async_mode: asyncMode }
    });
    return response.data;
  },

  // Get ML training job status
  async getTrainingStatus(jobId: string): Promise<MLTrainingJobStatus> {
    const response = await api.get<MLTrainingJobStatus>(`/predictions/retrain/status/${jobId}`);
    return response.data;
  },

  // List recent ML training jobs
  async listTrainingJobs(limit: number = 20): Promise<{ jobs: MLTrainingJobStatus[]; total: number }> {
    const response = await api.get('/predictions/retrain/jobs', {
      params: { limit }
    });
    return response.data;
  }
};

// =============================================================================
// TAGS API (v4.2 - Tag Management with Merge)
// =============================================================================

export type TagOut = {
  id: number;
  name: string;
  expense_type: 'FIXED' | 'VARIABLE' | 'PROVISION';
  transaction_count: number;
  total_amount: number;
  patterns: string[];
  category: string | null;
  created_at: string;
  last_used: string | null;
};

export type TagsListResponse = {
  tags: TagOut[];
  total_count: number;
  stats: {
    most_used_tags: string[];
    total_transactions_tagged: number;
    expense_type_distribution: Record<string, number>;
    average_transactions_per_tag: number;
    tags_with_patterns: number;
  };
};

export const tagsApi = {
  // List all tags with statistics
  async list(params?: {
    expense_type?: string;
    category?: string;
    min_usage?: number;
    sort_by?: 'usage' | 'amount' | 'name' | 'last_used';
    limit?: number;
  }): Promise<TagsListResponse> {
    const response = await api.get<TagsListResponse>('/tags', { params });
    return response.data;
  },

  // Search tags by name
  async search(query: string, limit: number = 10): Promise<{ query: string; results: TagOut[]; total_found: number }> {
    const response = await api.get('/tags/search', {
      params: { query, limit }
    });
    return response.data;
  },

  // Get global tags statistics
  async getStats(): Promise<Record<string, unknown>> {
    const response = await api.get('/tags/stats');
    return response.data;
  },

  // Merge multiple tags into one
  async merge(request: MergeTagsRequest): Promise<MergeTagsResponse> {
    const response = await api.post<MergeTagsResponse>('/tags/merge', request);
    return response.data;
  },

  // Update a tag
  async update(tagId: number, data: { name?: string; expense_type?: string; patterns?: string[] }): Promise<Record<string, unknown>> {
    const response = await api.put(`/tags/${tagId}`, data);
    return response.data;
  },

  // Delete a tag
  async delete(tagId: number, cascade: boolean = false): Promise<Record<string, unknown>> {
    const response = await api.delete(`/tags/${tagId}`, {
      params: { cascade }
    });
    return response.data;
  },

  // Toggle expense type (FIXED/VARIABLE)
  async toggleExpenseType(tagId: number): Promise<Record<string, unknown>> {
    const response = await api.post(`/tags/${tagId}/toggle-type`);
    return response.data;
  },

  // Get transactions for a tag
  async getTransactions(tagId: number, params?: { limit?: number; offset?: number; month?: string }): Promise<Record<string, unknown>> {
    const response = await api.get(`/tags/${tagId}/transactions`, { params });
    return response.data;
  }
};

// =============================================================================
// IMPORT PREVIEW API (v4.2 - Preview before import)
// =============================================================================

export const importPreviewApi = {
  // Preview a file before import
  async preview(file: File, sampleSize: number = 10): Promise<ImportPreviewResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<ImportPreviewResponse>('/import/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { sample_size: sampleSize }
    });
    return response.data;
  },

  // Import a file (existing endpoint)
  async import(file: File): Promise<ImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<ImportResponse>('/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }
};

// =============================================================================
// TRANSACTIONS API (v4.2 - Paginated)
// =============================================================================

export const transactionsApi = {
  // List transactions with pagination
  async list(month: string, params?: PaginationParams & { tag?: string; expense_type?: string; sort_by?: string; sort_order?: string }): Promise<PaginatedResponse<Tx>> {
    const response = await api.get<PaginatedResponse<Tx>>('/transactions', {
      params: { month, ...params }
    });
    return response.data;
  },

  // List all transactions without pagination (legacy/backward compatibility)
  async listAll(month: string, params?: { tag?: string; expense_type?: string }): Promise<Tx[]> {
    const response = await api.get<Tx[]>('/transactions/all', {
      params: { month, ...params }
    });
    return response.data;
  },

  // Get single transaction
  async get(id: number): Promise<Tx> {
    const response = await api.get<Tx>(`/transactions/${id}`);
    return response.data;
  },

  // Update transaction
  async update(id: number, data: Partial<Tx>): Promise<Tx> {
    const response = await api.patch<Tx>(`/transactions/${id}`, data);
    return response.data;
  },

  // Update transaction tags
  async updateTags(id: number, tags: string[]): Promise<Tx> {
    const response = await api.patch<Tx>(`/transactions/${id}/tags`, { tags });
    return response.data;
  },

  // Update expense type
  async updateExpenseType(id: number, expenseType: string): Promise<Tx> {
    const response = await api.patch<Tx>(`/transactions/${id}/expense-type`, { expense_type: expenseType });
    return response.data;
  },

  // Exclude/include transaction
  async setExclude(id: number, exclude: boolean): Promise<Tx> {
    const response = await api.patch<Tx>(`/transactions/${id}/exclude`, { exclude });
    return response.data;
  }
};

// =============================================================================
// IMPORT ADVISOR API (v4.1 - Post-import AI Analysis)
// =============================================================================

export type ImportAnomalyItem = {
  type: 'unusual_amount' | 'duplicate_suspect' | 'category_spike';
  description: string;
  amount?: number;
  transaction_id?: number;
  severity: 'low' | 'medium' | 'high';
};

export type MonthComparison = {
  current_month: string;
  previous_month?: string;
  current_total: number;
  previous_total?: number;
  variance?: number;
  variance_pct?: number;
  categories_increased: string[];
  categories_decreased: string[];
};

export type ImportInsight = {
  status: 'ready' | 'processing' | 'error';
  import_id: string;
  month: string;
  narrative?: string;
  anomalies: ImportAnomalyItem[];
  recommendations: string[];
  comparison?: MonthComparison;
  summary?: {
    total_expenses: number;
    total_income: number;
    transaction_count: number;
    top_categories: Record<string, number>;
  };
};

export const importAdvisorApi = {
  // Trigger post-import AI analysis
  async analyze(importId: string, month: string): Promise<{ status: string; import_id: string; cached?: boolean }> {
    const response = await api.post('/import-advisor/analyze', {
      import_id: importId,
      month
    });
    return response.data;
  },

  // Get import insights (poll until ready)
  async getInsights(importId: string, month?: string): Promise<ImportInsight> {
    const response = await api.get<ImportInsight>(`/import-advisor/insights/${importId}`, {
      params: month ? { month } : undefined
    });
    return response.data;
  },

  // Invalidate cached insights
  async invalidate(importId: string): Promise<{ invalidated: number; import_id: string }> {
    const response = await api.delete(`/import-advisor/insights/${importId}`);
    return response.data;
  }
};

// =============================================================================
// COACH API (v4.1 - AI Budget Coaching)
// =============================================================================

export type CoachTip = {
  id: string;
  message: string;
  category: 'insight' | 'warning' | 'tip' | 'motivation';
  icon: string;
  priority: number;
};

export type QuickAction = {
  id: string;
  label: string;
  action_type: 'navigate' | 'trigger';
  target: string;
  icon: string;
};

export type DailyInsight = {
  message: string;
  emoji: string;
  data_point?: string;
};

export type DashboardTipsResponse = {
  tips: CoachTip[];
  refresh_at: string;
};

export type DailyInsightResponse = {
  insight: DailyInsight;
  valid_until: string;
};

export type QuickActionsResponse = {
  actions: QuickAction[];
};

export const coachApi = {
  // Get rotating dashboard tips
  async getDashboardTips(month: string, limit: number = 3): Promise<DashboardTipsResponse> {
    const response = await api.get<DashboardTipsResponse>('/coach/dashboard-tips', {
      params: { month, limit }
    });
    return response.data;
  },

  // Get personalized daily insight
  async getDailyInsight(): Promise<DailyInsightResponse> {
    const response = await api.get<DailyInsightResponse>('/coach/daily-insight');
    return response.data;
  },

  // Get contextual quick actions
  async getQuickActions(month: string): Promise<QuickActionsResponse> {
    const response = await api.get<QuickActionsResponse>('/coach/quick-actions', {
      params: { month }
    });
    return response.data;
  },

  // Force refresh tips cache
  async refreshTips(month: string): Promise<{ invalidated: number; message: string }> {
    const response = await api.post('/coach/refresh-tips', null, {
      params: { month }
    });
    return response.data;
  }
};

// =============================================================================
// GAMIFICATION API (v4.1)
// =============================================================================

export type Achievement = {
  id: number;
  code: string;
  name: string;
  description: string;
  icon: string;
  category: 'budget' | 'savings' | 'import' | 'engagement';
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  points: number;
  is_hidden: boolean;
  progress: number;
  is_earned: boolean;
  earned_at: string | null;
};

export type Challenge = {
  id: number;
  code: string;
  name: string;
  description: string;
  icon: string;
  challenge_type: 'weekly' | 'monthly' | 'special';
  start_date: string;
  end_date: string;
  goal_type: string;
  goal_value: number;
  goal_category: string | null;
  reward_points: number;
  is_joined: boolean;
  progress: number;
  progress_percent: number;
  is_completed: boolean;
};

export type UserStats = {
  total_points: number;
  level: number;
  level_progress: number;
  achievements_earned: number;
  total_achievements: number;
  challenges_completed: number;
  current_streak: number;
  longest_streak: number;
};

export type UserStreak = {
  streak_type: string;
  current_streak: number;
  longest_streak: number;
  last_activity: string | null;
};

export type LeaderboardEntry = {
  rank: number;
  username: string;
  total_points: number;
  level: number;
  achievements_count: number;
};

export const gamificationApi = {
  // Get user's gamification stats
  async getStats(): Promise<UserStats> {
    const response = await api.get<UserStats>('/gamification/stats');
    return response.data;
  },

  // Get all achievements with user progress
  async getAchievements(category?: string): Promise<Achievement[]> {
    const response = await api.get<Achievement[]>('/gamification/achievements', {
      params: { category }
    });
    return response.data;
  },

  // Get recently earned achievements
  async getRecentAchievements(limit: number = 5): Promise<Achievement[]> {
    const response = await api.get<Achievement[]>('/gamification/achievements/recent', {
      params: { limit }
    });
    return response.data;
  },

  // Get active challenges
  async getActiveChallenges(): Promise<Challenge[]> {
    const response = await api.get<Challenge[]>('/gamification/challenges');
    return response.data;
  },

  // Join a challenge
  async joinChallenge(challengeId: number): Promise<{ status: string; challenge_name?: string }> {
    const response = await api.post(`/gamification/challenges/${challengeId}/join`);
    return response.data;
  },

  // Get user streaks
  async getStreaks(): Promise<UserStreak[]> {
    const response = await api.get<UserStreak[]>('/gamification/streaks');
    return response.data;
  },

  // Track an activity
  async trackActivity(activityType: string): Promise<{ current_streak: number; longest_streak: number }> {
    const response = await api.post('/gamification/track-activity', null, {
      params: { activity_type: activityType }
    });
    return response.data;
  },

  // Get leaderboard
  async getLeaderboard(limit: number = 10): Promise<LeaderboardEntry[]> {
    const response = await api.get<LeaderboardEntry[]>('/gamification/leaderboard', {
      params: { limit }
    });
    return response.data;
  },

  // Initialize achievements (admin)
  async initAchievements(): Promise<{ created: number; updated: number }> {
    const response = await api.post('/gamification/init-achievements');
    return response.data;
  },

  // Check and award any earned achievements
  async checkAchievements(): Promise<{ awarded: string[]; count: number }> {
    const response = await api.post('/gamification/check-achievements');
    return response.data;
  }
};

// ============================================================
// RECEIPTS API - OCR Receipt Scanning
// ============================================================
export const receiptsApi = {
  // Check if OCR service is available
  async getStatus(): Promise<OCRStatusResponse> {
    const response = await api.get<OCRStatusResponse>('/receipts/status');
    return response.data;
  },

  // Scan a receipt image
  async scan(file: File): Promise<ReceiptScanResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<ReceiptScanResult>('/receipts/scan', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds for OCR processing
    });
    return response.data;
  },

  // Create a transaction from scanned receipt data
  async createTransaction(data: ReceiptCreateRequest): Promise<ReceiptCreateResponse> {
    const response = await api.post<ReceiptCreateResponse>('/receipts/create', data);
    return response.data;
  },

  // Scan and optionally create transaction in one step
  async scanAndCreate(file: File, tag?: string, autoCreate: boolean = false): Promise<ReceiptCreateResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (tag) formData.append('tag', tag);
    formData.append('auto_create', autoCreate.toString());

    const response = await api.post<ReceiptCreateResponse>('/receipts/scan-and-create', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds for OCR processing
    });
    return response.data;
  }
};

// ============================================================
// PDF EXPORT API - Monthly Report Generation
// ============================================================
export interface PDFPreviewData {
  month: string;
  summary: Record<string, any>;
  tags_summary: Record<string, any>;
  top_transactions: Array<{ date: string; label: string; amount: number }>;
  pdf_ready: boolean;
}

export const pdfExportApi = {
  // Get preview data for PDF report
  async preview(month: string): Promise<PDFPreviewData> {
    const response = await api.get<PDFPreviewData>(`/export/pdf/preview/${month}`);
    return response.data;
  },

  // Download monthly PDF report
  async downloadMonthly(month: string): Promise<Blob> {
    const token = localStorage.getItem("auth_token");
    const tokenType = localStorage.getItem("token_type") || "Bearer";

    const response = await fetch(`${API_BASE}/export/pdf/monthly/${month}`, {
      method: 'GET',
      headers: {
        'Authorization': `${tokenType} ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erreur lors du téléchargement' }));
      throw new Error(error.detail || 'Erreur lors du téléchargement du PDF');
    }

    return response.blob();
  },

  // Helper to trigger download in browser
  async downloadAndSave(month: string): Promise<void> {
    const blob = await this.downloadMonthly(month);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `budget_famille_${month}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
};