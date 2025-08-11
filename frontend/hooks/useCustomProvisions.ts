'use client';

import { useState, useEffect } from 'react';
import { api, CustomProvision, CustomProvisionCreate } from '../lib/api';

interface UseCustomProvisionsReturn {
  provisions: CustomProvision[];
  loading: boolean;
  error: string;
  actionLoading: number | null;
  loadProvisions: () => Promise<void>;
  handleAddProvision: (provisionData: CustomProvisionCreate) => Promise<void>;
  handleUpdateProvision: (provisionData: CustomProvisionCreate, editingProvision: CustomProvision) => Promise<void>;
  toggleProvisionStatus: (provision: CustomProvision) => Promise<void>;
  deleteProvision: (provision: CustomProvision) => Promise<void>;
  onDataChange?: () => void;
}

export function useCustomProvisions(onDataChange?: () => void): UseCustomProvisionsReturn {
  const [provisions, setProvisions] = useState<CustomProvision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    // Vérifier l'authentification avant de charger
    const token = localStorage.getItem('auth_token');
    if (!token) {
      console.warn('⚠️ Pas de token d\'authentification trouvé');
      setError('Authentification requise - Veuillez vous connecter');
      setLoading(false);
      return;
    }
    
    loadProvisions();
  }, []);

  const loadProvisions = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Debug: vérifier l'authentification
      const token = localStorage.getItem('auth_token');
      const tokenType = localStorage.getItem('token_type');
      
      console.log('🔍 Debug loadProvisions:', {
        hasToken: !!token,
        tokenType,
        tokenPrefix: token?.substring(0, 10) + '...',
        url: '/custom-provisions'
      });
      
      const response = await api.get<CustomProvision[]>('/custom-provisions');
      console.log('✅ Provisions chargées:', {
        status: response.status,
        hasData: !!response.data,
        dataType: typeof response.data,
        isArray: Array.isArray(response.data),
        count: Array.isArray(response.data) ? response.data.length : 0,
        data: response.data
      });
      
      // Vérification robuste de la réponse
      const provisions = Array.isArray(response.data) ? response.data : [];
      setProvisions(provisions);
      
      if (!Array.isArray(response.data)) {
        console.warn('⚠️ La réponse n\'est pas un tableau:', response.data);
      }
    } catch (err: any) {
      const errorDetails = {
        status: err.response?.status,
        statusText: err.response?.statusText,
        message: err.message,
        data: err.response?.data,
        url: err.config?.url,
        hasAuth: !!err.config?.headers?.Authorization
      };
      
      console.error('❌ Erreur loadProvisions:', errorDetails);
      
      // Message d'erreur plus descriptif
      let errorMessage = 'Erreur lors du chargement des provisions';
      if (err.response?.status === 401) {
        errorMessage = 'Session expirée - Veuillez vous reconnecter';
      } else if (err.response?.status === 403) {
        errorMessage = 'Accès refusé aux provisions';
      } else if (err.response?.status === 500) {
        errorMessage = 'Erreur serveur - Réessayez dans quelques instants';
      } else if (err.code === 'ERR_NETWORK') {
        errorMessage = 'Impossible de contacter le serveur';
      } else if (err.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProvision = async (provisionData: CustomProvisionCreate) => {
    try {
      console.log('🔍 Debug création provision:', {
        data: provisionData,
        url: '/custom-provisions',
        hasToken: !!localStorage.getItem('auth_token')
      });
      
      const response = await api.post<CustomProvision>('/custom-provisions', provisionData);
      
      console.log('✅ Provision créée:', {
        status: response.status,
        data: response.data
      });
      
      setProvisions(prev => [...prev, response.data]);
      onDataChange?.();
    } catch (err: any) {
      const errorDetails = {
        status: err.response?.status,
        statusText: err.response?.statusText,
        message: err.message,
        data: err.response?.data,
        url: err.config?.url,
        hasAuth: !!err.config?.headers?.Authorization
      };
      
      console.error('❌ Erreur création provision:', errorDetails);
      
      // Message d'erreur plus descriptif
      let errorMessage = 'Erreur lors de la création';
      if (err.response?.status === 401) {
        errorMessage = 'Session expirée - Reconnectez-vous';
      } else if (err.response?.status === 403) {
        errorMessage = 'Accès refusé pour créer une provision';
      } else if (err.response?.status === 422) {
        errorMessage = 'Données de provision invalides';
      } else if (err.response?.data?.detail) {
        errorMessage = `Erreur: ${err.response.data.detail}`;
      }
      
      throw new Error(errorMessage);
    }
  };

  const handleUpdateProvision = async (provisionData: CustomProvisionCreate, editingProvision: CustomProvision) => {
    try {
      const response = await api.put<CustomProvision>(
        `/custom-provisions/${editingProvision.id}`,
        provisionData
      );
      setProvisions(prev =>
        prev.map(p => (p.id === editingProvision.id ? response.data : p))
      );
      onDataChange?.();
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Erreur lors de la mise à jour');
    }
  };

  const toggleProvisionStatus = async (provision: CustomProvision) => {
    try {
      setActionLoading(provision.id);
      const response = await api.patch<CustomProvision>(
        `/custom-provisions/${provision.id}`,
        { is_active: !provision.is_active }
      );
      setProvisions(prev =>
        prev.map(p => (p.id === provision.id ? response.data : p))
      );
      onDataChange?.();
    } catch (err: any) {
      setError('Erreur lors de la mise à jour du statut');
    } finally {
      setActionLoading(null);
    }
  };

  const deleteProvision = async (provision: CustomProvision) => {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la provision "${provision.name}" ?`)) {
      return;
    }

    try {
      setActionLoading(provision.id);
      await api.delete(`/custom-provisions/${provision.id}`);
      setProvisions(prev => prev.filter(p => p.id !== provision.id));
      onDataChange?.();
    } catch (err: any) {
      setError('Erreur lors de la suppression');
    } finally {
      setActionLoading(null);
    }
  };

  return {
    provisions,
    loading,
    error,
    actionLoading,
    loadProvisions,
    handleAddProvision,
    handleUpdateProvision,
    toggleProvisionStatus,
    deleteProvision,
    onDataChange
  };
}
