'use client';

import { useState } from 'react';
import { CustomProvision, CustomProvisionCreate, ConfigOut } from '../lib/api';
import { Button, Alert, LoadingSpinner } from './ui';
import { AddProvisionModal } from './AddProvisionModal';
import { useCustomProvisions } from '../hooks/useCustomProvisions';
import { 
  ProvisionsSummary, 
  ProvisionCard, 
  InactiveProvisionCard, 
  ProvisionsEmptyState 
} from './provisions';

interface CustomProvisionsProps {
  config?: ConfigOut;
  onDataChange?: () => void;
}

export default function CustomProvisions({ config, onDataChange }: CustomProvisionsProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProvision, setEditingProvision] = useState<CustomProvision | null>(null);
  
  const {
    provisions,
    loading,
    error,
    actionLoading,
    handleAddProvision: addProvision,
    handleUpdateProvision,
    toggleProvisionStatus,
    deleteProvision
  } = useCustomProvisions(onDataChange);

  const handleAddProvision = async (provisionData: CustomProvisionCreate) => {
    await addProvision(provisionData);
    setShowAddModal(false);
  };

  const handleUpdateProvision_ = async (provisionData: CustomProvisionCreate) => {
    if (!editingProvision) return;
    await handleUpdateProvision(provisionData, editingProvision);
    setEditingProvision(null);
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
      setShowAddModal(false);
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

  const handleUpdateProvision = async (provisionData: CustomProvisionCreate) => {
    if (!editingProvision) return;

    try {
      const response = await api.put<CustomProvision>(
        `/custom-provisions/${editingProvision.id}`,
        provisionData
      );
      setProvisions(prev =>
        prev.map(p => (p.id === editingProvision.id ? response.data : p))
      );
      setEditingProvision(null);
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

  const calculateMonthlyAmount = (provision: CustomProvision): number => {
    if (!config) return 0;

    let base = 0;
    switch (provision.base_calculation) {
      case 'total':
        base = (config.rev1 || 0) + (config.rev2 || 0);
        break;
      case 'member1':
        base = config.rev1 || 0;
        break;
      case 'member2':
        base = config.rev2 || 0;
        break;
      case 'fixed':
        return provision.fixed_amount || 0;
    }

    return (base * provision.percentage / 100) / 12;
  };

  const calculateMemberSplit = (provision: CustomProvision, monthlyAmount: number) => {
    if (!config) return { member1: 0, member2: 0 };

    switch (provision.split_mode) {
      case 'key':
        const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
        if (totalRev > 0) {
          const r1 = (config.rev1 || 0) / totalRev;
          const r2 = (config.rev2 || 0) / totalRev;
          return {
            member1: monthlyAmount * r1,
            member2: monthlyAmount * r2,
          };
        }
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '50/50':
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
      case '100/0':
        return { member1: monthlyAmount, member2: 0 };
      case '0/100':
        return { member1: 0, member2: monthlyAmount };
      case 'custom':
        return {
          member1: monthlyAmount * (provision.split_member1 / 100),
          member2: monthlyAmount * (provision.split_member2 / 100),
        };
      default:
        return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getBaseCalculationLabel = (baseCalc: string) => {
    switch (baseCalc) {
      case 'total':
        return 'Revenus totaux';
      case 'member1':
        return config?.member1 || 'Membre 1';
      case 'member2':
        return config?.member2 || 'Membre 2';
      case 'fixed':
        return 'Montant fixe';
      default:
        return baseCalc;
    }
  };

  const getSplitModeLabel = (splitMode: string) => {
    switch (splitMode) {
      case 'key':
        return 'Clé globale';
      case '50/50':
        return '50/50';
      case '100/0':
        return `100% ${config?.member1 || 'Membre 1'}`;
      case '0/100':
        return `100% ${config?.member2 || 'Membre 2'}`;
      case 'custom':
        return 'Personnalisé';
      default:
        return splitMode;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'savings':
        return '💰';
      case 'investment':
        return '📈';
      case 'project':
        return '🏗️';
      default:
        return '💝';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  const activeProvisions = provisions.filter(p => p.is_active);
  const inactiveProvisions = provisions.filter(p => !p.is_active);
  const totalMonthlyAmount = activeProvisions.reduce((sum, provision) => {
    return sum + calculateMonthlyAmount(provision);
  }, 0);

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="error">
          <div className="space-y-2">
            <p className="font-medium">{error}</p>
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer hover:text-gray-800">Détails techniques</summary>
              <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono">
                <p>API Base: {process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:5000"}</p>
                <p>Token présent: {!!localStorage.getItem('auth_token') ? 'Oui' : 'Non'}</p>
                <p>Endpoint: /custom-provisions</p>
              </div>
            </details>
          </div>
        </Alert>
      )}
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            🎯 Provisions Personnalisables
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Créez vos propres objectifs d'épargne avec des pourcentages personnalisés
          </p>
        </div>
        <Button
          onClick={() => setShowAddModal(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          + Ajouter une provision
        </Button>
      </div>

      {/* Summary */}
      {activeProvisions.length > 0 && (
        <Card className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium text-indigo-700">Provisions Actives</p>
              <p className="text-2xl font-bold text-indigo-900">{activeProvisions.length}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-700">Total Mensuel</p>
              <p className="text-2xl font-bold text-indigo-900">
                {formatAmount(totalMonthlyAmount)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-700">Total Annuel</p>
              <p className="text-2xl font-bold text-indigo-900">
                {formatAmount(totalMonthlyAmount * 12)}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Active Provisions */}
      {activeProvisions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Provisions Actives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeProvisions.map(provision => {
              const monthlyAmount = calculateMonthlyAmount(provision);
              const memberSplit = calculateMemberSplit(provision, monthlyAmount);
              const isLoading = actionLoading === provision.id;

              return (
                <Card
                  key={provision.id}
                  className="provision-card p-4 border-l-4 provision-appear"
                  style={{ borderLeftColor: provision.color }}
                  role="article"
                  aria-labelledby={`provision-${provision.id}-name`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl" role="img" aria-label="icon">
                        {provision.icon}
                      </span>
                      <div>
                        <h4 
                          id={`provision-${provision.id}-name`}
                          className="font-semibold text-gray-900"
                        >
                          {provision.name}
                        </h4>
                        {provision.description && (
                          <p className="text-sm text-gray-600">{provision.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        onClick={() => setEditingProvision(provision)}
                        disabled={isLoading}
                        className="icon-hover text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded transition-all"
                        aria-label={`Modifier la provision ${provision.name}`}
                      >
                        ✏️
                      </Button>
                      <Button
                        onClick={() => toggleProvisionStatus(provision)}
                        disabled={isLoading}
                        className={`icon-hover text-xs px-2 py-1 rounded transition-all ${
                          provision.is_active
                            ? 'bg-orange-100 hover:bg-orange-200 text-orange-700'
                            : 'bg-green-100 hover:bg-green-200 text-green-700'
                        }`}
                        aria-label={`${provision.is_active ? 'Désactiver' : 'Activer'} la provision ${provision.name}`}
                      >
                        {isLoading ? '...' : provision.is_active ? '⏸️' : '▶️'}
                      </Button>
                      <Button
                        onClick={() => deleteProvision(provision)}
                        disabled={isLoading}
                        className="icon-hover text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded transition-all"
                        aria-label={`Supprimer la provision ${provision.name}`}
                      >
                        🗑️
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Base de calcul</p>
                      <p className="font-medium">
                        {getBaseCalculationLabel(provision.base_calculation)}
                        {provision.base_calculation !== 'fixed' && ` (${provision.percentage}%)`}
                        {provision.base_calculation === 'fixed' && 
                          ` (${formatAmount(provision.fixed_amount || 0)})`}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Répartition</p>
                      <p className="font-medium">{getSplitModeLabel(provision.split_mode)}</p>
                    </div>
                  </div>

                  <div className="mt-4 bg-gray-50 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Montant mensuel</span>
                      <span className="text-lg font-bold text-gray-900">
                        {formatAmount(monthlyAmount)}
                      </span>
                    </div>
                    
                    {config && (
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div className="flex justify-between">
                          <span>{config.member1 || 'Membre 1'}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member1)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>{config.member2 || 'Membre 2'}:</span>
                          <span className="font-medium">{formatAmount(memberSplit.member2)}</span>
                        </div>
                      </div>
                    )}

                    {provision.target_amount && (
                      <div className="mt-2">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                          <span>Objectif: {formatAmount(provision.target_amount)}</span>
                          <span>
                            {Math.round(((provision.current_amount || 0) / provision.target_amount) * 100)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="progress-bar h-2 rounded-full"
                            style={{
                              width: `${Math.min(100, ((provision.current_amount || 0) / provision.target_amount) * 100)}%`,
                              backgroundColor: provision.color,
                            }}
                            role="progressbar"
                            aria-valuenow={Math.round(((provision.current_amount || 0) / provision.target_amount) * 100)}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`Progression de l'objectif: ${Math.round(((provision.current_amount || 0) / provision.target_amount) * 100)}%`}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Inactive Provisions */}
      {inactiveProvisions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-500">Provisions Inactives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {inactiveProvisions.map(provision => (
              <Card
                key={provision.id}
                className="p-4 opacity-60 hover:opacity-80 transition-opacity"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl grayscale" role="img" aria-label="icon">
                      {provision.icon}
                    </span>
                    <div>
                      <h4 className="font-semibold text-gray-700">{provision.name}</h4>
                      <p className="text-sm text-gray-500">Inactive</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      onClick={() => toggleProvisionStatus(provision)}
                      disabled={actionLoading === provision.id}
                      className="text-xs bg-green-100 hover:bg-green-200 text-green-700 px-2 py-1 rounded"
                    >
                      ▶️ Activer
                    </Button>
                    <Button
                      onClick={() => deleteProvision(provision)}
                      disabled={actionLoading === provision.id}
                      className="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2 py-1 rounded"
                    >
                      🗑️
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {provisions.length === 0 && (
        <Card className="p-8 text-center">
          <div className="text-6xl mb-4">🎯</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Aucune provision configurée
          </h3>
          <p className="text-gray-600 mb-4">
            Créez votre première provision personnalisée pour commencer à épargner selon vos objectifs.
          </p>
          <Button
            onClick={() => setShowAddModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg"
          >
            Créer ma première provision
          </Button>
        </Card>
      )}

      {/* Modals */}
      {showAddModal && (
        <AddProvisionModal
          config={config}
          onClose={() => setShowAddModal(false)}
          onSave={handleAddProvision}
        />
      )}

      {editingProvision && (
        <AddProvisionModal
          config={config}
          provision={editingProvision}
          onClose={() => setEditingProvision(null)}
          onSave={handleUpdateProvision}
        />
      )}
    </div>
  );
}