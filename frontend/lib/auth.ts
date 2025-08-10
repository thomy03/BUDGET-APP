import { api } from "./api";
import { useEffect, useState } from "react";

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: string | null;
  loading: boolean;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

class AuthService {
  private static instance: AuthService;
  private authState: AuthState = {
    isAuthenticated: false,
    token: null,
    user: null,
    loading: true,
  };
  private listeners: Set<() => void> = new Set();
  
  private constructor() {
    this.initializeAuth();
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener());
  }

  public subscribe(listener: () => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private updateAuthState(updates: Partial<AuthState>) {
    this.authState = { ...this.authState, ...updates };
    this.notifyListeners();
  }

  private initializeAuth() {
    // Restaurer l'authentification depuis localStorage au démarrage
    if (typeof window !== "undefined") {
      try {
        const token = localStorage.getItem("auth_token");
        const tokenType = localStorage.getItem("token_type");
        const user = localStorage.getItem("username");
        
        if (token && tokenType && user) {
          // Vérifier si le token n'est pas expiré
          if (!this.isTokenExpired(token)) {
            // S'assurer que l'en-tête d'autorisation est défini
            const authHeader = `${tokenType} ${token}`;
            api.defaults.headers.common["Authorization"] = authHeader;
            
            // Vérification supplémentaire en mode développement
            if (process.env.NODE_ENV === "development") {
              console.log("🔑 Auth initialized with token:", authHeader.substring(0, 20) + "...");
              console.log("🔑 API auth header set:", !!api.defaults.headers.common["Authorization"]);
            }
            
            this.updateAuthState({
              isAuthenticated: true,
              token,
              user,
              loading: false,
            });
          } else {
            // Token expiré, nettoyer
            console.log("🔑 Token expired on initialization");
            this.clearAuthData();
          }
        } else {
          this.updateAuthState({ loading: false });
        }
      } catch (error) {
        console.error("Erreur initialisation auth:", error);
        this.clearAuthData();
      }
    }
  }

  private clearAuthData() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("token_type");
    localStorage.removeItem("username");
    delete api.defaults.headers.common["Authorization"];
    this.updateAuthState({
      isAuthenticated: false,
      token: null,
      user: null,
      loading: false,
    });
  }

  public getAuthState(): AuthState {
    return { ...this.authState };
  }

  public async login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    this.updateAuthState({ loading: true });
    
    try {
      const response = await api.post<LoginResponse>("/token", 
        new URLSearchParams({
          username,
          password,
        }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          timeout: 10000, // 10 secondes timeout
        }
      );

      const { access_token, token_type } = response.data;
      
      // Validation du token reçu
      if (!access_token || !token_type) {
        throw new Error("Token invalide reçu du serveur");
      }
      
      // Stocker les informations d'authentification
      localStorage.setItem("auth_token", access_token);
      localStorage.setItem("token_type", token_type);
      localStorage.setItem("username", username);
      
      // Configurer axios avec vérification
      const authHeader = `${token_type} ${access_token}`;
      api.defaults.headers.common["Authorization"] = authHeader;
      
      // Vérification en mode développement
      if (process.env.NODE_ENV === "development") {
        console.log("🔑 Login successful, auth header set:", authHeader.substring(0, 20) + "...");
        console.log("🔑 API instance has auth:", !!api.defaults.headers.common["Authorization"]);
      }
      
      this.updateAuthState({
        isAuthenticated: true,
        token: access_token,
        user: username,
        loading: false,
      });
      
      return { success: true };
    } catch (error: any) {
      console.error("Erreur authentification:", error);
      
      this.clearAuthData();
      
      let errorMessage = "Erreur de connexion inconnue";
      
      if (error.code === 'ECONNABORTED') {
        errorMessage = "Délai de connexion dépassé - Vérifiez votre réseau";
      } else if (error.response?.status === 401) {
        errorMessage = "Nom d'utilisateur ou mot de passe incorrect";
      } else if (error.response?.status === 422) {
        errorMessage = "Format des données invalide";
      } else if (error.response?.status >= 500) {
        errorMessage = "Erreur serveur - Veuillez réessayer plus tard";
      } else if (!navigator.onLine) {
        errorMessage = "Pas de connexion internet";
      }
      
      return { success: false, error: errorMessage };
    }
  }

  public logout(redirect: boolean = true) {
    this.clearAuthData();
    
    // Rediriger vers la page de login si demandé
    if (redirect && typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  public isTokenExpired(token: string): boolean {
    try {
      if (!token || token.split('.').length !== 3) {
        return true;
      }
      
      const tokenParts = token.split('.');
      if (tokenParts.length !== 3 || !tokenParts[1]) {
        return true;
      }
      const payload = JSON.parse(atob(tokenParts[1]));
      const currentTime = Date.now() / 1000;
      
      // Ajouter une marge de 5 minutes pour éviter les expirations de dernière minute
      return payload.exp < (currentTime + 300);
    } catch (error) {
      console.error("Erreur vérification expiration token:", error);
      return true; // Considérer comme expiré si erreur de parsing
    }
  }

  public async refreshTokenIfNeeded(): Promise<boolean> {
    const { token } = this.getAuthState();
    
    if (!token) {
      return false;
    }

    if (this.isTokenExpired(token)) {
      this.logout();
      return false;
    }

    return true;
  }

  public async validateSession(): Promise<boolean> {
    const { token } = this.getAuthState();
    
    if (!token) {
      return false;
    }

    try {
      // Test avec un appel API simple pour valider le token
      await api.get('/config');
      return true;
    } catch (error: any) {
      if (error.response?.status === 401) {
        this.logout();
        return false;
      }
      // Autres erreurs ne signifient pas forcément un problème d'auth
      return true;
    }
  }
}

// Hook React pour l'authentification
export function useAuth() {
  const authService = AuthService.getInstance();
  const [authState, setAuthState] = useState(authService.getAuthState());

  useEffect(() => {
    const unsubscribe = authService.subscribe(() => {
      setAuthState(authService.getAuthState());
    });

    return () => {
      unsubscribe();
    };
  }, [authService]);

  return {
    ...authState,
    login: authService.login.bind(authService),
    logout: authService.logout.bind(authService),
    refreshToken: authService.refreshTokenIfNeeded.bind(authService),
    validateSession: authService.validateSession.bind(authService),
  };
}

export const authService = AuthService.getInstance();