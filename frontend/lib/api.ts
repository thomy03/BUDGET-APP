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