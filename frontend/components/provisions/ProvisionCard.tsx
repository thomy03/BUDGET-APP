'use client';

import { CustomProvision } from '../../lib/api';
import { Card, Button } from '../ui';
import { useProvisionCalculations } from '../../hooks/useProvisionCalculations';

interface ProvisionCardProps {
  provision: CustomProvision;
  config?: any;
  isLoading: boolean;
  onEdit: (provision: CustomProvision) => void;
  onToggleStatus: (provision: CustomProvision) => void;
  onDelete: (provision: CustomProvision) => void;
}

export function ProvisionCard({ 
  provision, 
  config, 
  isLoading, 
  onEdit, 
  onToggleStatus, 
  onDelete 
}: ProvisionCardProps) {
  const {
    calculateMonthlyAmount,
    calculateMemberSplit,
    formatAmount,
    getBaseCalculationLabel,
    getSplitModeLabel
  } = useProvisionCalculations(config);

  const monthlyAmount = calculateMonthlyAmount(provision);
  const memberSplit = calculateMemberSplit(provision, monthlyAmount);

  return (
    <Card
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
            onClick={() => onEdit(provision)}
            disabled={isLoading}
            className="icon-hover text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded transition-all"
            aria-label={`Modifier la provision ${provision.name}`}
          >
            ✏️
          </Button>
          <Button
            onClick={() => onToggleStatus(provision)}
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
            onClick={() => onDelete(provision)}
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
}
