'use client';

import React, { useState, useEffect } from 'react';
import { Card, Input, Button, LoadingSpinner } from '../ui';
import { balanceApi, AccountBalance, BalanceTransferCalculation } from '../../lib/api';
import { useRouter } from 'next/navigation';

interface AccountBalanceProps {
  month: string;
  onBalanceUpdate?: (balance: number) => void;
}

export function AccountBalanceComponent({ month, onBalanceUpdate }: AccountBalanceProps) {
  const [balance, setBalance] = useState<AccountBalance | null>(null);
  const [transferCalc, setTransferCalc] = useState<BalanceTransferCalculation | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  // Load balance data on mount and when month changes
  useEffect(() => {
    loadBalanceData();
  }, [month]);

  const loadBalanceData = async () => {
    if (!month) return;
    
    setLoading(true);
    setError('');
    
    try {
      // Load balance and transfer calculation in parallel
      const [balanceData, transferData] = await Promise.all([
        balanceApi.get(month),
        balanceApi.getTransferCalculation(month).catch(() => null) // Non-critical if fails
      ]);
      
      setBalance(balanceData);
      setTransferCalc(transferData);
      setEditValue(balanceData.account_balance.toString());
      setNotes(balanceData.notes || '');
    } catch (err: any) {
      console.error('Error loading balance data:', err);
      setError('Erreur lors du chargement du solde');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!balance) return;
    
    const newBalance = parseFloat(editValue);
    if (isNaN(newBalance)) {
      setError('Veuillez entrer un montant valide');
      return;
    }
    
    setSaving(true);
    setError('');
    
    try {
      const updatedBalance = await balanceApi.update(month, {
        account_balance: newBalance,
        notes: notes.trim() || undefined
      });
      
      setBalance(updatedBalance);
      setEditMode(false);
      onBalanceUpdate?.(newBalance);
      
      // Reload transfer calculation with new balance
      try {
        const newTransferCalc = await balanceApi.getTransferCalculation(month);
        setTransferCalc(newTransferCalc);
      } catch (err) {
        console.warn('Failed to reload transfer calculation:', err);
      }
      
    } catch (err: any) {
      console.error('Error updating balance:', err);
      setError('Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (balance) {
      setEditValue(balance.account_balance.toString());
      setNotes(balance.notes || '');
    }
    setEditMode(false);
    setError('');
  };

  const getBalanceStatusColor = (status?: string) => {
    switch (status) {
      case 'surplus': return 'text-green-700 bg-green-100';
      case 'sufficient': return 'text-blue-700 bg-blue-100';
      case 'tight': return 'text-orange-700 bg-orange-100';
      case 'deficit': return 'text-red-700 bg-red-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  const getBalanceStatusIcon = (status?: string) => {
    switch (status) {
      case 'surplus': return '💰';
      case 'sufficient': return '✅';
      case 'tight': return '⚠️';
      case 'deficit': return '🚨';
      default: return '💳';
    }
  };

  const getBalanceStatusText = (status?: string) => {
    switch (status) {
      case 'surplus': return 'Excédent important';
      case 'sufficient': return 'Solde suffisant';
      case 'tight': return 'Solde serré';
      case 'deficit': return 'Déficit';
      default: return 'En attente';
    }
  };

  if (loading) {
    return (
      <Card className="p-6 border-l-4 border-l-indigo-500 bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex justify-center py-8">
          <LoadingSpinner size="md" text="Chargement du solde..." />
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 border-l-4 border-l-indigo-500 bg-gradient-to-r from-indigo-50 to-purple-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">💳</span>
        <div>
          <h2 className="text-xl font-bold text-indigo-900">SOLDE DE COMPTE</h2>
          <p className="text-sm text-indigo-700">Gestion du solde mensuel et calcul des virements</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* Balance Display/Edit Section */}
        <div className="bg-white rounded-xl p-5 border border-indigo-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-indigo-900">Solde Actuel</h3>
            {!editMode ? (
              <button
                onClick={() => setEditMode(true)}
                className="px-3 py-1 text-sm bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors"
              >
                ✏️ Modifier
              </button>
            ) : (
              <div className="flex space-x-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1 text-sm bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50"
                >
                  {saving ? '⏳' : '💾'} Sauver
                </button>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  ❌ Annuler
                </button>
              </div>
            )}
          </div>
          
          {editMode ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Montant (€)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  placeholder="0.00"
                  className="text-xl font-bold"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notes (optionnel)
                </label>
                <Input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Remarques sur le solde..."
                  maxLength={200}
                />
              </div>
            </div>
          ) : (
            <div>
              <div className="text-3xl font-bold text-indigo-900 mb-2">
                {balance ? balance.account_balance.toFixed(2) : '0.00'} €
              </div>
              {balance?.notes && (
                <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                  💬 {balance.notes}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Transfer Calculation Section */}
        {transferCalc && (
          <div className="bg-white rounded-xl p-5 border border-indigo-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-indigo-900">Calcul des Virements</h3>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getBalanceStatusColor(transferCalc.balance_status)}`}>
                <span className="mr-1">{getBalanceStatusIcon(transferCalc.balance_status)}</span>
                {getBalanceStatusText(transferCalc.balance_status)}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                <div className="text-sm font-medium text-blue-700 mb-1">Membre 1 - Virement</div>
                <div className="text-xl font-bold text-blue-900">
                  {transferCalc.suggested_transfer_member1.toFixed(2)} €
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  Part totale: {transferCalc.total_member1.toFixed(2)} €
                </div>
              </div>
              
              <div className="bg-green-50 rounded-lg p-4 border border-green-100">
                <div className="text-sm font-medium text-green-700 mb-1">Membre 2 - Virement</div>
                <div className="text-xl font-bold text-green-900">
                  {transferCalc.suggested_transfer_member2.toFixed(2)} €
                </div>
                <div className="text-xs text-green-600 mt-1">
                  Part totale: {transferCalc.total_member2.toFixed(2)} €
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
                <div>
                  <div className="font-medium text-gray-700">Total Dépenses</div>
                  <div className="text-lg font-bold text-gray-900">
                    {transferCalc.total_expenses.toFixed(2)} €
                  </div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Solde Actuel</div>
                  <div className="text-lg font-bold text-gray-900">
                    {transferCalc.current_balance.toFixed(2)} €
                  </div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Total Virements</div>
                  <div className="text-lg font-bold text-gray-900">
                    {(transferCalc.suggested_transfer_member1 + transferCalc.suggested_transfer_member2).toFixed(2)} €
                  </div>
                </div>
                <div>
                  <div className="font-medium text-gray-700">Solde Final</div>
                  <div className={`text-lg font-bold ${
                    transferCalc.final_balance_after_transfers >= 0 ? 'text-green-700' : 'text-red-700'
                  }`}>
                    {transferCalc.final_balance_after_transfers.toFixed(2)} €
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => router.push('/transactions')}
            className="inline-flex items-center px-4 py-2 bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors text-sm font-medium"
          >
            <span className="mr-2">📊</span>
            Voir Transactions
          </button>
          <button
            onClick={() => router.push('/settings')}
            className="inline-flex items-center px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-sm font-medium"
          >
            <span className="mr-2">⚙️</span>
            Paramètres
          </button>
        </div>
      </div>
    </Card>
  );
}

export default AccountBalanceComponent;