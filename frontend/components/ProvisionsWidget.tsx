'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, CustomProvision, ConfigOut } from '../lib/api';
import { Card, LoadingSpinner } from './ui';

interface ProvisionsWidgetProps {
  config?: ConfigOut;
}

interface ProvisionSummary {
  provision: CustomProvision;
  monthlyAmount: number;
  memberSplit: {
    member1: number;
    member2: number;
  };
}

export default function ProvisionsWidget({ config }: ProvisionsWidgetProps) {
  const router = useRouter();
  const [provisions, setProvisions] = useState<CustomProvision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProvisions();
  }, []);

  const loadProvisions = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await api.get<CustomProvision[]>('/custom-provisions');
      setProvisions(response.data || []);
    } catch (err: any) {
      setError('Erreur lors du chargement des provisions');
      console.error('Erreur loadProvisions:', err);
    } finally {
      setLoading(false);
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

  const activeProvisions = provisions.filter(p => p.is_active);
  
  const provisionsSummary: ProvisionSummary[] = activeProvisions.map(provision => {
    const monthlyAmount = calculateMonthlyAmount(provision);
    const memberSplit = calculateMemberSplit(provision, monthlyAmount);
    return {
      provision,
      monthlyAmount,
      memberSplit,
    };
  });

  const totalMonthlyAmount = provisionsSummary.reduce((sum, item) => sum + item.monthlyAmount, 0);
  const totalMember1 = provisionsSummary.reduce((sum, item) => sum + item.memberSplit.member1, 0);
  const totalMember2 = provisionsSummary.reduce((sum, item) => sum + item.memberSplit.member2, 0);

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-center">
          <LoadingSpinner />
        </div>
      </Card>
    );
  }

  if (error || activeProvisions.length === 0) {
    return (
      <Card 
        className="p-6 cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-indigo-500 bg-gradient-to-r from-indigo-50 to-purple-50"
        onClick={() => router.push('/settings')}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🎯</span>
            <div>
              <h3 className="text-lg font-semibold text-indigo-900">Provisions Personnalisables</h3>
              <p className="text-sm text-indigo-600">
                {error ? 'Erreur de chargement' : 'Aucune provision configurée'}
              </p>
            </div>
          </div>
          <div className="text-indigo-600 hover:text-indigo-800">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
        
        <div className="mt-4 text-center py-4">
          <p className="text-indigo-600 text-sm">
            {error 
              ? 'Cliquez pour configurer les provisions' 
              : 'Créez vos premières provisions personnalisées'}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card 
      className="p-6 cursor-pointer hover:shadow-md transition-shadow border-l-4 border-l-indigo-500"
      onClick={() => router.push('/settings')}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">🎯</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Provisions Personnalisables</h3>
            <p className="text-sm text-gray-600">
              {activeProvisions.length} provision{activeProvisions.length > 1 ? 's' : ''} active{activeProvisions.length > 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="text-gray-400 hover:text-gray-600">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-lg font-bold text-indigo-600">{formatAmount(totalMonthlyAmount)}</p>
          <p className="text-xs text-gray-500">Total mensuel</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-blue-600">{formatAmount(totalMember1)}</p>
          <p className="text-xs text-gray-500">{config?.member1 || 'Membre 1'}</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-purple-600">{formatAmount(totalMember2)}</p>
          <p className="text-xs text-gray-500">{config?.member2 || 'Membre 2'}</p>
        </div>
      </div>

      {/* Top 3 Provisions */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700 border-b border-gray-100 pb-1">
          Principales provisions
        </h4>
        {provisionsSummary
          .sort((a, b) => b.monthlyAmount - a.monthlyAmount)
          .slice(0, 3)
          .map((item) => (
            <div key={item.provision.id} className="flex items-center justify-between py-2">
              <div className="flex items-center space-x-2">
                <span 
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.provision.color }}
                ></span>
                <span className="text-sm">{item.provision.icon}</span>
                <span className="text-sm font-medium text-gray-700 truncate max-w-[120px]">
                  {item.provision.name}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-900">
                {formatAmount(item.monthlyAmount)}
              </div>
            </div>
          ))}
        
        {activeProvisions.length > 3 && (
          <div className="text-center py-2">
            <p className="text-xs text-gray-500">
              +{activeProvisions.length - 3} autre{activeProvisions.length - 3 > 1 ? 's' : ''} provision{activeProvisions.length - 3 > 1 ? 's' : ''}
            </p>
          </div>
        )}
      </div>

      {/* Progress indicators for provisions with targets */}
      {provisionsSummary.some(item => item.provision.target_amount) && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Objectifs en cours</h4>
          <div className="space-y-2">
            {provisionsSummary
              .filter(item => item.provision.target_amount)
              .slice(0, 2)
              .map((item) => {
                const progress = ((item.provision.current_amount || 0) / (item.provision.target_amount || 1)) * 100;
                return (
                  <div key={item.provision.id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-600">
                        {item.provision.icon} {item.provision.name}
                      </span>
                      <span className="text-gray-500">
                        {Math.round(progress)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.min(100, progress)}%`,
                          backgroundColor: item.provision.color,
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Call to action */}
      <div className="mt-4 pt-4 border-t border-gray-100 text-center">
        <p className="text-xs text-gray-500">
          Cliquez pour gérer vos provisions
        </p>
      </div>
    </Card>
  );
}