'use client';

import { useState, useEffect } from 'react';
import { Card, Button, Input, LoadingSpinner, Alert } from '../ui';
import { ConfigOut, CustomProvision, CustomProvisionCreate, provisionsApi } from '../../lib/api';
import { AddProvisionModal } from '../AddProvisionModal';

interface BudgetConfigurationProps {
  cfg: ConfigOut | null;
  saving: boolean;
  onSave: (formData: FormData) => void;
  onNavigateToExpenses?: () => void;
}

export function BudgetConfiguration({ cfg, saving, onSave, onNavigateToExpenses }: BudgetConfigurationProps) {
  const [provisions, setProvisions] = useState<CustomProvision[]>([]);
  const [loadingProvisions, setLoadingProvisions] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProvision, setEditingProvision] = useState<CustomProvision | null>(null);
  const [error, setError] = useState('');
  
  // États pour la gestion des revenus annuels/mensuels
  const [member1Mode, setMember1Mode] = useState<'monthly' | 'annual'>('annual');
  const [member2Mode, setMember2Mode] = useState<'monthly' | 'annual'>('annual');
  const [member1Value, setMember1Value] = useState<string>('');
  const [member2Value, setMember2Value] = useState<string>('');
  const [taxRate1, setTaxRate1] = useState<string>('0');
  const [taxRate2, setTaxRate2] = useState<string>('0');

  useEffect(() => {
    loadProvisions();
  }, []);
  
  useEffect(() => {
    // Initialiser les valeurs des revenus et taux d'imposition
    if (cfg) {
      // Les valeurs en base sont mensuelles, on les convertit en annuel pour l'affichage par défaut
      const monthly1 = cfg.rev1 || 0;
      const monthly2 = cfg.rev2 || 0;
      setMember1Value((monthly1 * 12).toString());
      setMember2Value((monthly2 * 12).toString());
      setTaxRate1(cfg.tax_rate1?.toString() || '0');
      setTaxRate2(cfg.tax_rate2?.toString() || '0');
    }
  }, [cfg]);

  const loadProvisions = async () => {
    try {
      setLoadingProvisions(true);
      const data = await provisionsApi.getAll();
      setProvisions(data);
    } catch (error) {
      console.error('Erreur chargement provisions:', error);
    } finally {
      setLoadingProvisions(false);
    }
  };
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    onSave(formData);
  };

  if (!cfg) return null;

  // Calcul des revenus bruts et nets
  const rev1Brut = parseFloat(member1Mode === 'annual' ? (parseFloat(member1Value) / 12).toFixed(2) : member1Value) || cfg.rev1 || 0;
  const rev2Brut = parseFloat(member2Mode === 'annual' ? (parseFloat(member2Value) / 12).toFixed(2) : member2Value) || cfg.rev2 || 0;
  const rev1Net = rev1Brut * (1 - parseFloat(taxRate1) / 100);
  const rev2Net = rev2Brut * (1 - parseFloat(taxRate2) / 100);
  
  const totalRevenueBrut = rev1Brut + rev2Brut;
  const totalRevenueNet = rev1Net + rev2Net;
  
  // Pourcentages basés sur les revenus nets pour la répartition
  const member1PercentageNet = totalRevenueNet > 0 ? ((rev1Net / totalRevenueNet) * 100).toFixed(1) : '0';
  const member2PercentageNet = totalRevenueNet > 0 ? ((rev2Net / totalRevenueNet) * 100).toFixed(1) : '0';

  const activeProvisions = provisions.filter(p => p.is_active);
  const totalProvisions = activeProvisions.reduce((sum, p) => sum + (p.monthly_amount || 0), 0);

  const handleDeleteProvision = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette provision ?')) return;
    
    try {
      await provisionsApi.delete(id);
      await loadProvisions();
    } catch (error) {
      console.error('Erreur suppression provision:', error);
    }
  };

  const handleToggleProvision = async (provision: CustomProvision) => {
    try {
      await provisionsApi.patch(provision.id, { is_active: !provision.is_active });
      await loadProvisions();
    } catch (error) {
      console.error('Erreur mise à jour provision:', error);
      setError('Erreur lors de la mise à jour de la provision');
    }
  };

  const handleAddProvision = async (provisionData: CustomProvisionCreate) => {
    try {
      await provisionsApi.create(provisionData);
      setShowAddModal(false);
      await loadProvisions();
    } catch (error) {
      console.error('Erreur création provision:', error);
      setError('Erreur lors de la création de la provision');
    }
  };

  const handleUpdateProvision = async (provisionData: CustomProvisionCreate) => {
    if (!editingProvision) return;
    try {
      // Inclure current_amount de la provision existante
      const updateData = {
        ...provisionData,
        current_amount: editingProvision.current_amount || 0
      };
      await provisionsApi.update(editingProvision.id, updateData);
      setEditingProvision(null);
      await loadProvisions();
    } catch (error) {
      console.error('Erreur mise à jour provision:', error);
      setError('Erreur lors de la mise à jour de la provision');
    }
  };

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Configuration des revenus */}
      <Card>
        <div className="p-3 xs:p-4 md:p-6">
          <h2 className="text-base xs:text-lg md:text-xl font-semibold mb-3 xs:mb-4 text-gray-900">
            ⚙️ Configuration du budget familial
          </h2>

        {/* Alerte informative */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 xs:p-4 mb-4 xs:mb-6">
          <div className="flex gap-2 xs:gap-3">
            <div className="flex-shrink-0 pt-0.5">
              <svg className="h-4 w-4 xs:h-5 xs:w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-xs xs:text-sm font-medium text-blue-800">Configuration des revenus et répartition</h3>
              <div className="mt-1 xs:mt-2 text-xs xs:text-sm text-blue-700 space-y-1">
                <p>Cette section configure les revenus du foyer et la méthode de répartition des dépenses.</p>
                <p className="hidden xs:block">Les provisions personnalisées peuvent être configurées dans l'onglet "Mes Dépenses".</p>
              </div>
            </div>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4 xs:space-y-6">
          {/* Membres du foyer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 xs:gap-4">
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Nom du premier membre
              </label>
              <Input
                name="member1"
                defaultValue={cfg.member1 || ''}
                placeholder="ex: Sarah"
                required
                className="min-h-[44px]"
              />
            </div>
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Nom du second membre
              </label>
              <Input
                name="member2"
                defaultValue={cfg.member2 || ''}
                placeholder="ex: Thomas"
                required
                className="min-h-[44px]"
              />
            </div>
          </div>

          {/* Revenus */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 xs:gap-4">
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Revenu de {cfg.member1 || 'Membre 1'} (€)
              </label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  value={member1Value}
                  onChange={(e) => setMember1Value(e.target.value)}
                  placeholder={member1Mode === 'monthly' ? 'ex: 3000' : 'ex: 36000'}
                  className="flex-1 min-h-[44px]"
                  required
                />
                <select
                  value={member1Mode}
                  onChange={(e) => {
                    const newMode = e.target.value as 'monthly' | 'annual';
                    const currentVal = parseFloat(member1Value) || 0;
                    if (currentVal > 0) {
                      setMember1Value(
                        newMode === 'annual'
                          ? (currentVal * 12).toString()
                          : (currentVal / 12).toFixed(2)
                      );
                    }
                    setMember1Mode(newMode);
                  }}
                  className="px-2 xs:px-3 py-2 text-xs xs:text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[44px]"
                >
                  <option value="monthly">Mensuel</option>
                  <option value="annual">Annuel</option>
                </select>
              </div>
              <input type="hidden" name="rev1" value={
                member1Mode === 'annual'
                  ? (parseFloat(member1Value) / 12 || 0).toFixed(2)
                  : member1Value
              } />
              <p className="text-xs text-gray-500 mt-1">
                Mensuel: {member1Mode === 'annual'
                  ? `${(parseFloat(member1Value) / 12 || 0).toFixed(2)}€`
                  : `${member1Value || '0'}€`
                }
              </p>
            </div>
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Revenu de {cfg.member2 || 'Membre 2'} (€)
              </label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  value={member2Value}
                  onChange={(e) => setMember2Value(e.target.value)}
                  placeholder={member2Mode === 'monthly' ? 'ex: 2500' : 'ex: 30000'}
                  className="flex-1 min-h-[44px]"
                  required
                />
                <select
                  value={member2Mode}
                  onChange={(e) => {
                    const newMode = e.target.value as 'monthly' | 'annual';
                    const currentVal = parseFloat(member2Value) || 0;
                    if (currentVal > 0) {
                      setMember2Value(
                        newMode === 'annual' 
                          ? (currentVal * 12).toString()
                          : (currentVal / 12).toFixed(2)
                      );
                    }
                    setMember2Mode(newMode);
                  }}
                  className="px-2 xs:px-3 py-2 text-xs xs:text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[44px]"
                >
                  <option value="monthly">Mensuel</option>
                  <option value="annual">Annuel</option>
                </select>
              </div>
              <input type="hidden" name="rev2" value={
                member2Mode === 'annual'
                  ? (parseFloat(member2Value) / 12 || 0).toFixed(2)
                  : member2Value
              } />
              <p className="text-xs text-gray-500 mt-1">
                Mensuel: {member2Mode === 'annual'
                  ? `${(parseFloat(member2Value) / 12 || 0).toFixed(2)}€`
                  : `${member2Value || '0'}€`
                }
              </p>
            </div>
          </div>

          {/* Taux d'imposition */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 xs:gap-4">
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Taux d'imposition {cfg.member1 || 'Membre 1'} (%)
              </label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={taxRate1}
                onChange={(e) => setTaxRate1(e.target.value)}
                placeholder="ex: 15"
                className="min-h-[44px]"
              />
              <input type="hidden" name="tax_rate1" value={taxRate1} />
              <p className="text-xs text-gray-500 mt-1 break-words">
                Net mensuel: {rev1Net.toFixed(2)}€ • Part: {member1PercentageNet}% des revenus nets
              </p>
            </div>
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Taux d'imposition {cfg.member2 || 'Membre 2'} (%)
              </label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={taxRate2}
                onChange={(e) => setTaxRate2(e.target.value)}
                placeholder="ex: 20"
                className="min-h-[44px]"
              />
              <input type="hidden" name="tax_rate2" value={taxRate2} />
              <p className="text-xs text-gray-500 mt-1 break-words">
                Net mensuel: {rev2Net.toFixed(2)}€ • Part: {member2PercentageNet}% des revenus nets
              </p>
            </div>
          </div>

          {/* Résumé des revenus */}
          <div className="bg-blue-50 rounded-lg p-3 xs:p-4 space-y-2">
            <div className="flex justify-between items-center gap-2">
              <span className="text-xs xs:text-sm font-medium text-blue-900">Revenu brut total:</span>
              <span className="text-sm xs:text-base md:text-lg font-bold text-blue-900">
                {totalRevenueBrut.toLocaleString('fr-FR', {
                  style: 'currency',
                  currency: 'EUR',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                })}
              </span>
            </div>
            <div className="flex justify-between items-center gap-2">
              <span className="text-xs xs:text-sm font-medium text-green-900">Revenu net total (après impôts):</span>
              <span className="text-base xs:text-lg md:text-xl font-bold text-green-900">
                {totalRevenueNet.toLocaleString('fr-FR', {
                  style: 'currency',
                  currency: 'EUR',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                })}
              </span>
            </div>
            <div className="text-xs text-gray-600">
              💡 La répartition des dépenses se base sur les revenus nets
            </div>
          </div>

          {/* Mode de répartition */}
          <div>
            <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-2">
              Mode de répartition des dépenses
            </label>
            <select
              name="split_mode"
              defaultValue={cfg.split_mode || 'revenus'}
              className="w-full px-3 py-2 text-sm md:text-base border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 min-h-[44px]"
              onChange={(e) => {
                const mode = e.target.value;
                const manuelSection = document.getElementById('manuel-split-section');
                if (manuelSection) {
                  manuelSection.style.display = mode === 'manuel' ? 'block' : 'none';
                }
              }}
            >
              <option value="revenus">Automatique (proportionnel aux revenus)</option>
              <option value="manuel">Personnalisé</option>
            </select>
          </div>

          {/* Répartition manuelle (cachée par défaut) */}
          <div
            id="manuel-split-section"
            style={{ display: cfg.split_mode === 'manuel' ? 'block' : 'none' }}
            className="grid grid-cols-1 md:grid-cols-2 gap-3 xs:gap-4"
          >
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Part de {cfg.member1 || 'Membre 1'} (%)
              </label>
              <Input
                name="split1"
                type="number"
                min="0"
                max="100"
                step="1"
                defaultValue={(cfg.split1 || 0.5) * 100}
                placeholder="ex: 60"
                className="min-h-[44px]"
                onChange={(e) => {
                  const value = parseFloat(e.target.value) || 0;
                  const split2Input = document.querySelector('input[name="split2"]') as HTMLInputElement;
                  if (split2Input) {
                    split2Input.value = String(100 - value);
                  }
                }}
              />
              <p className="text-xs text-gray-500 mt-1">
                Pourcentage des dépenses communes
              </p>
            </div>
            <div>
              <label className="block text-xs xs:text-sm font-medium text-gray-700 mb-1">
                Part de {cfg.member2 || 'Membre 2'} (%)
              </label>
              <Input
                name="split2"
                type="number"
                min="0"
                max="100"
                step="1"
                defaultValue={(cfg.split2 || 0.5) * 100}
                placeholder="ex: 40"
                readOnly
                className="min-h-[44px]"
              />
              <p className="text-xs text-gray-500 mt-1">
                Ajusté automatiquement (100% - part membre 1)
              </p>
            </div>
          </div>

          {/* Bouton de sauvegarde */}
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={saving}
              className="w-full xs:w-auto bg-green-600 hover:bg-green-700 text-white px-4 xs:px-6 py-2 rounded-lg transition-colors disabled:opacity-50 min-h-[44px] text-sm xs:text-base"
            >
              {saving ? 'Sauvegarde...' : '💾 Sauvegarder la configuration'}
            </Button>
          </div>
        </form>
      </div>
    </Card>

    {/* Provisions personnalisées */}
    <Card>
      <div className="p-3 xs:p-4 md:p-6">
        {error && (
          <Alert variant="error" className="mb-3 xs:mb-4">
            {error}
          </Alert>
        )}

        <div className="flex flex-col xs:flex-row xs:items-center xs:justify-between gap-3 xs:gap-4 mb-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-base xs:text-lg md:text-xl font-semibold text-gray-900">
              🎯 Provisions Personnalisées
            </h2>
            <p className="text-xs xs:text-sm text-gray-600 mt-1 line-clamp-2">
              Objectifs d'épargne et provisions pour projets futurs
            </p>
          </div>
          <div className="flex flex-col xs:flex-row items-start xs:items-center gap-2 xs:gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs xs:text-sm text-gray-500">
                Total mensuel:
              </span>
              <span className="text-sm xs:text-base md:text-lg font-bold text-blue-600">
                {totalProvisions.toLocaleString('fr-FR', {
                  style: 'currency',
                  currency: 'EUR',
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </span>
            </div>
            <Button
              onClick={() => setShowAddModal(true)}
              className="w-full xs:w-auto bg-blue-600 hover:bg-blue-700 text-white px-3 xs:px-4 py-2 rounded-lg transition-colors min-h-[44px] text-xs xs:text-sm"
            >
              + Créer une provision
            </Button>
          </div>
        </div>

        {loadingProvisions ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner text="Chargement des provisions..." />
          </div>
        ) : provisions.length === 0 ? (
          <div className="text-center py-6 xs:py-8 text-gray-500">
            <p className="mb-2 xs:mb-4 text-sm xs:text-base">Aucune provision configurée</p>
            <p className="text-xs xs:text-sm">Allez dans l'onglet "Mes Dépenses" pour créer des provisions</p>
          </div>
        ) : (
          <div className="space-y-3">
            {provisions.map((provision) => (
              <div
                key={provision.id}
                className={`border rounded-lg p-3 xs:p-4 transition-all ${
                  provision.is_active
                    ? 'bg-white border-gray-200 hover:shadow-sm'
                    : 'bg-gray-50 border-gray-100 opacity-60'
                }`}
              >
                <div className="flex flex-col xs:flex-row xs:items-center xs:justify-between gap-3">
                  <div className="flex items-center gap-2 xs:gap-3 min-w-0 flex-1">
                    <span className="text-xl xs:text-2xl flex-shrink-0">{provision.icon || '💰'}</span>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm xs:text-base font-medium text-gray-900 truncate">
                        {provision.name}
                      </h3>
                      {provision.description && (
                        <p className="text-xs xs:text-sm text-gray-500 line-clamp-1">{provision.description}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between xs:justify-end gap-2 xs:gap-4">
                    <div className="text-left xs:text-right">
                      <p className="text-sm xs:text-base font-semibold text-gray-900">
                        {(provision.monthly_amount || 0).toLocaleString('fr-FR', {
                          style: 'currency',
                          currency: 'EUR',
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        })}
                      </p>
                      <p className="text-xs text-gray-500">par mois</p>
                    </div>

                    <div className="flex items-center gap-1 xs:gap-2 flex-shrink-0">
                      <Button
                        onClick={() => handleToggleProvision(provision)}
                        variant="outline"
                        className="px-2 xs:px-3 py-1 text-xs xs:text-sm min-h-[44px]"
                      >
                        {provision.is_active ? '✅ Active' : '❌ Inactive'}
                      </Button>
                      <Button
                        onClick={() => setEditingProvision(provision)}
                        variant="outline"
                        className="px-2 xs:px-3 py-1 text-xs xs:text-sm min-h-[44px] min-w-[44px]"
                      >
                        ✏️
                      </Button>
                      <Button
                        onClick={() => handleDeleteProvision(provision.id)}
                        variant="outline"
                        className="px-2 xs:px-3 py-1 text-xs xs:text-sm text-red-600 hover:text-red-700 hover:bg-red-50 min-h-[44px] min-w-[44px]"
                      >
                        🗑️
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Détails de calcul */}
                {provision.is_active && (
                  <div className="mt-3 pt-3 border-t border-gray-100 text-xs xs:text-sm text-gray-600 space-y-1 xs:space-y-0">
                    <div className="flex justify-between items-center gap-2">
                      <span>Base de calcul:</span>
                      <span className="font-medium text-right">
                        {provision.base_calculation === 'revenus' ? 'Revenus totaux' :
                         provision.base_calculation === 'salaire1' ? cfg?.member1 || 'Membre 1' :
                         provision.base_calculation === 'salaire2' ? cfg?.member2 || 'Membre 2' :
                         'Montant fixe'}
                      </span>
                    </div>
                    {provision.percentage && provision.percentage > 0 && (
                      <div className="flex justify-between items-center gap-2">
                        <span>Pourcentage:</span>
                        <span className="font-medium">{provision.percentage}%</span>
                      </div>
                    )}
                    {provision.target_amount && provision.target_amount > 0 && (
                      <div className="flex justify-between items-center gap-2">
                        <span>Objectif:</span>
                        <span className="font-medium">
                          {provision.target_amount.toLocaleString('fr-FR', {
                            style: 'currency',
                            currency: 'EUR',
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0
                          })}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

      </div>
    </Card>

    {/* Modals */}
    {showAddModal && (
      <AddProvisionModal
        config={cfg}
        onClose={() => setShowAddModal(false)}
        onSave={handleAddProvision}
      />
    )}
    
    {editingProvision && (
      <AddProvisionModal
        config={cfg}
        provision={editingProvision}
        onClose={() => setEditingProvision(null)}
        onSave={handleUpdateProvision}
      />
    )}
    </div>
  );
}
