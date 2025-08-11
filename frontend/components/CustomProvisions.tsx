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

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  const activeProvisions = provisions.filter(p => p.is_active);
  const inactiveProvisions = provisions.filter(p => !p.is_active);

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
      <ProvisionsSummary activeProvisions={activeProvisions} config={config} />

      {/* Active Provisions */}
      {activeProvisions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Provisions Actives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {activeProvisions.map(provision => (
              <ProvisionCard
                key={provision.id}
                provision={provision}
                config={config}
                isLoading={actionLoading === provision.id}
                onEdit={setEditingProvision}
                onToggleStatus={toggleProvisionStatus}
                onDelete={deleteProvision}
              />
            ))}
          </div>
        </div>
      )}

      {/* Inactive Provisions */}
      {inactiveProvisions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-500">Provisions Inactives</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {inactiveProvisions.map(provision => (
              <InactiveProvisionCard
                key={provision.id}
                provision={provision}
                isLoading={actionLoading === provision.id}
                onToggleStatus={toggleProvisionStatus}
                onDelete={deleteProvision}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {provisions.length === 0 && (
        <ProvisionsEmptyState onAddProvision={() => setShowAddModal(true)} />
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
          onSave={handleUpdateProvision_}
        />
      )}
    </div>
  );
}