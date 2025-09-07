'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api';
import { 
  CurrencyEuroIcon, 
  BanknotesIcon,
  ChartBarIcon,
  CalendarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  WalletIcon,
  CalculatorIcon
} from '@heroicons/react/24/outline';

interface Provision {
  id: number;
  name: string;
  monthly_amount: number;
  category: string;
  icon?: string;
  is_active: boolean;
}

interface Config {
  member1: string;
  member2: string;
  rev1: number; // revenus bruts mensuels
  rev2: number;
  tax_rate1: number;
  tax_rate2: number;
  split_mode?: string;
}

interface Transaction {
  id: number;
  label: string;
  amount: number;
  date_op: string;
  tags: string;
  category: string;
  month: string;
  exclude?: boolean;
}

export default function Dashboard() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<Config | null>(null);
  const [provisions, setProvisions] = useState<Provision[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [accountBalance, setAccountBalance] = useState<number>(0);
  const [balanceInput, setBalanceInput] = useState<string>('');
  const [editingBalance, setEditingBalance] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    // Charger le solde sauvegardé
    const savedBalance = localStorage.getItem('accountBalance');
    if (savedBalance) {
      setAccountBalance(parseFloat(savedBalance));
      setBalanceInput(savedBalance);
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (!isAuthenticated) return;
      
      try {
        setLoading(true);
        
        const [configRes, provisionsRes, transactionsRes] = await Promise.all([
          api.get('/config'),
          api.get('/custom-provisions'),
          api.get(`/transactions?month=${selectedMonth}`)
        ]);
        
        setConfig(configRes.data);
        // Filtrer seulement les provisions actives
        const activeProvisions = (provisionsRes.data || []).filter((p: Provision) => p.is_active);
        setProvisions(activeProvisions);
        setTransactions(transactionsRes.data || []);
      } catch (error) {
        console.error('Erreur chargement dashboard:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [isAuthenticated, selectedMonth]);

  const saveBalance = () => {
    const newBalance = parseFloat(balanceInput) || 0;
    setAccountBalance(newBalance);
    localStorage.setItem('accountBalance', newBalance.toString());
    setEditingBalance(false);
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Calculs avec les bonnes données
  const rev1Net = (config?.rev1 || 0) * (1 - (config?.tax_rate1 || 0) / 100);
  const rev2Net = (config?.rev2 || 0) * (1 - (config?.tax_rate2 || 0) / 100);
  const totalRevenuBrut = (config?.rev1 || 0) + (config?.rev2 || 0);
  const totalRevenuNet = rev1Net + rev2Net;
  
  // Provisions actives seulement
  const totalProvisions = provisions.reduce((sum, p) => sum + (p.monthly_amount || 0), 0);
  
  // Virements programmés FIXES de 826€ par personne pour les prêts
  const virementsFixesParPersonne = 826; // Montant fixe par personne
  const totalVirementsProgammes = virementsFixesParPersonne * 2; // Total pour les deux personnes
  
  // Dépenses du mois sélectionné (transactions négatives, non exclues)
  const depensesVariables = transactions
    .filter(t => t.amount < 0 && !t.exclude)
    .reduce((sum, t) => sum + Math.abs(t.amount), 0);
  
  // Revenus du mois (transactions positives, non exclues)
  const revenusTransactions = transactions
    .filter(t => t.amount > 0 && !t.exclude)
    .reduce((sum, t) => sum + t.amount, 0);
  
  // Solde prévu en fin de mois (inclure les virements programmés dans le calcul)
  const soldeFinMois = accountBalance + totalRevenuNet + revenusTransactions - depensesVariables - totalProvisions - totalVirementsProgammes;
  
  // Charges SANS les virements programmés (pour la répartition proportionnelle)
  const chargesSansVirements = depensesVariables + totalProvisions;
  
  // Charges totales AVEC les virements programmés
  const chargesTotales = chargesSansVirements + totalVirementsProgammes;
  
  // Calcul de la répartition selon le mode
  let member1Share = 0.5;
  let member2Share = 0.5;
  
  if (config?.split_mode === 'revenus' || !config?.split_mode) {
    // Répartition au prorata des revenus nets
    member1Share = totalRevenuNet > 0 ? rev1Net / totalRevenuNet : 0.5;
    member2Share = 1 - member1Share;
  }
  
  // Répartition séparée pour dépenses courantes et provisions (proportionnelle)
  const member1Depenses = depensesVariables * member1Share;
  const member2Depenses = depensesVariables * member2Share;
  const member1Provisions = totalProvisions * member1Share;
  const member2Provisions = totalProvisions * member2Share;
  
  // Sous-total SANS virements programmés
  const member1SousTotal = member1Depenses + member1Provisions;
  const member2SousTotal = member2Depenses + member2Provisions;
  
  // Virements programmés FIXES (826€ chacun)
  const member1Virements = virementsFixesParPersonne;
  const member2Virements = virementsFixesParPersonne;
  
  // Total FINAL avec virements programmés
  const member1Contribution = member1SousTotal + member1Virements;
  const member2Contribution = member2SousTotal + member2Virements;

  // Mois pour la sélection
  const months = [];
  for (let i = -2; i <= 2; i++) {
    const date = new Date();
    date.setMonth(date.getMonth() + i);
    const monthStr = date.toISOString().slice(0, 7);
    months.push({
      value: monthStr,
      label: date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
    });
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Dashboard Budget Famille
          </h1>
          
          {/* Sélecteur de mois */}
          <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-lg shadow">
            <CalendarIcon className="h-5 w-5 text-gray-500" />
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="border-none focus:ring-0 text-gray-700 font-medium"
            >
              {months.map(month => (
                <option key={month.value} value={month.value}>
                  {month.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Métriques principales */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Solde actuel avec édition */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <WalletIcon className="h-8 w-8 text-green-500" />
              <span className="text-sm text-gray-500">Solde actuel</span>
            </div>
            {editingBalance ? (
              <div className="flex gap-2">
                <input
                  type="number"
                  value={balanceInput}
                  onChange={(e) => setBalanceInput(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-xl font-bold"
                  step="0.01"
                  autoFocus
                />
                <button
                  onClick={saveBalance}
                  className="px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600"
                >
                  ✓
                </button>
                <button
                  onClick={() => {
                    setEditingBalance(false);
                    setBalanceInput(accountBalance.toString());
                  }}
                  className="px-2 py-1 bg-gray-500 text-white rounded hover:bg-gray-600"
                >
                  ✗
                </button>
              </div>
            ) : (
              <div 
                className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 rounded p-1"
                onClick={() => setEditingBalance(true)}
              >
                <p className="text-2xl font-bold">€{accountBalance.toFixed(2)}</p>
                <span className="text-xs text-gray-400">✏️</span>
              </div>
            )}
          </div>
          
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <ArrowTrendingUpIcon className="h-8 w-8 text-blue-500" />
              <span className="text-sm text-gray-500">Revenus nets</span>
            </div>
            <p className="text-2xl font-bold">€{totalRevenuNet.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-1">
              Brut: €{totalRevenuBrut.toFixed(2)}
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <ArrowTrendingDownIcon className="h-8 w-8 text-orange-500" />
              <span className="text-sm text-gray-500">Dépenses</span>
            </div>
            <p className="text-2xl font-bold">€{depensesVariables.toFixed(2)}</p>
            <p className="text-xs text-gray-500 mt-1">
              {transactions.filter(t => t.amount < 0 && !t.exclude).length} transactions
              {transactions.filter(t => t.amount < 0 && t.exclude).length > 0 && (
                <span className="text-orange-600 font-medium">
                  {' '}({transactions.filter(t => t.amount < 0 && t.exclude).length} exclues)
                </span>
              )}
            </p>
          </div>
          
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <ChartBarIcon className="h-8 w-8 text-purple-500" />
              <span className="text-sm text-gray-500">Fin de mois</span>
            </div>
            <p className={`text-2xl font-bold ${soldeFinMois >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              €{soldeFinMois.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Après provisions
            </p>
          </div>
        </div>
        
        {/* Détail des flux */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">📊 Flux du mois</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">Solde début de mois</span>
              <span className="font-medium">€{accountBalance.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center py-2 text-green-600">
              <span>+ Revenus nets du foyer</span>
              <span className="font-medium">+€{totalRevenuNet.toFixed(2)}</span>
            </div>
            {revenusTransactions > 0 && (
              <div className="flex justify-between items-center py-2 text-green-600">
                <span>+ Autres revenus (transactions)</span>
                <span className="font-medium">+€{revenusTransactions.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between items-center py-2 text-orange-600">
              <span>- Dépenses variables</span>
              <span className="font-medium">-€{depensesVariables.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center py-2 text-blue-600">
              <span>- Provisions mensuelles</span>
              <span className="font-medium">-€{totalProvisions.toFixed(2)}</span>
            </div>
            <div className="border-t pt-3 mt-3">
              <div className="flex justify-between items-center">
                <span className="font-semibold">Solde prévisionnel fin de mois</span>
                <span className={`text-xl font-bold ${soldeFinMois >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  €{soldeFinMois.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Provisions */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">💰 Provisions Actives</h2>
            <div className="space-y-3">
              {provisions.length > 0 ? provisions.map(p => (
                <div key={p.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{p.icon || '💰'}</span>
                    <div>
                      <p className="font-medium">{p.name}</p>
                      <p className="text-sm text-gray-500">{p.category}</p>
                    </div>
                  </div>
                  <span className="font-semibold">€{(p.monthly_amount || 0).toFixed(2)}</span>
                </div>
              )) : (
                <p className="text-gray-500">Aucune provision active</p>
              )}
              <div className="pt-3 border-t">
                <div className="flex justify-between font-semibold text-blue-600">
                  <span>Total mensuel</span>
                  <span>€{totalProvisions.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Répartition */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">⚖️ Répartition des Charges</h2>
            
            {/* Totaux */}
            <div className="mb-4 p-3 bg-gray-50 rounded">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Dépenses courantes</span>
                <span className="font-medium">€{depensesVariables.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Provisions (épargne)</span>
                <span className="font-medium">€{totalProvisions.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm font-semibold pt-2 border-t mb-2">
                <span>Sous-total (répartition proportionnelle)</span>
                <span>€{chargesSansVirements.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm text-gray-600 mb-2 bg-red-50 p-2 rounded">
                <span>🏠 Virements programmés (826€ × 2)</span>
                <span className="font-medium">€{totalVirementsProgammes.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm font-bold pt-2 border-t text-lg">
                <span>TOTAL MENSUEL</span>
                <span>€{chargesTotales.toFixed(2)}</span>
              </div>
            </div>
            
            <div className="space-y-4">
              {/* Membre 1 */}
              <div className="p-4 bg-blue-50 rounded">
                <div className="flex justify-between mb-3">
                  <span className="font-medium text-lg">{config?.member1 || 'Membre 1'}</span>
                  <span className="text-sm bg-blue-200 px-2 py-1 rounded">
                    {(member1Share * 100).toFixed(1)}%
                  </span>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">💳 Dépenses courantes</span>
                    <span className="font-medium">€{member1Depenses.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">💰 Provisions épargne</span>
                    <span className="font-medium">€{member1Provisions.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm font-semibold pt-2 border-t border-blue-200">
                    <span>Sous-total</span>
                    <span>€{member1SousTotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm bg-red-50 p-2 rounded mt-2">
                    <span className="text-gray-700">🏠 Virement programmé (fixe)</span>
                    <span className="font-bold text-red-600">€{member1Virements.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t-2 border-blue-300 mt-2">
                    <span className="font-bold text-lg">TOTAL À PAYER</span>
                    <span className="text-xl font-bold text-blue-900">€{member1Contribution.toFixed(2)}</span>
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  Revenu net: €{rev1Net.toFixed(2)}
                </p>
              </div>
              
              {/* Membre 2 */}
              <div className="p-4 bg-green-50 rounded">
                <div className="flex justify-between mb-3">
                  <span className="font-medium text-lg">{config?.member2 || 'Membre 2'}</span>
                  <span className="text-sm bg-green-200 px-2 py-1 rounded">
                    {(member2Share * 100).toFixed(1)}%
                  </span>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">💳 Dépenses courantes</span>
                    <span className="font-medium">€{member2Depenses.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">💰 Provisions épargne</span>
                    <span className="font-medium">€{member2Provisions.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm font-semibold pt-2 border-t border-green-200">
                    <span>Sous-total</span>
                    <span>€{member2SousTotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm bg-red-50 p-2 rounded mt-2">
                    <span className="text-gray-700">🏠 Virement programmé (fixe)</span>
                    <span className="font-bold text-red-600">€{member2Virements.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t-2 border-green-300 mt-2">
                    <span className="font-bold text-lg">TOTAL À PAYER</span>
                    <span className="text-xl font-bold text-green-900">€{member2Contribution.toFixed(2)}</span>
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  Revenu net: €{rev2Net.toFixed(2)}
                </p>
              </div>
            </div>
            
            <div className="mt-4 p-3 bg-yellow-50 rounded text-sm text-yellow-800">
              💡 Répartition {config?.split_mode === 'revenus' ? 'proportionnelle aux revenus nets' : 'personnalisée'}
            </div>
          </div>
        </div>
        
        {/* Dernières transactions */}
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">📝 Dernières transactions ({selectedMonth})</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {transactions.filter(t => !t.exclude).length > 0 ? (
              transactions.filter(t => !t.exclude).slice(0, 10).map(t => (
                <div key={t.id} className="flex justify-between items-center p-2 hover:bg-gray-50 rounded">
                  <div>
                    <p className="font-medium text-sm">{t.label}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(t.date_op).toLocaleDateString('fr-FR')} • {t.tags || 'Non classé'}
                    </p>
                  </div>
                  <span className={`font-semibold ${t.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {t.amount < 0 ? '-' : '+'}€{Math.abs(t.amount).toFixed(2)}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-gray-500">Aucune transaction pour ce mois</p>
            )}
          </div>
          {transactions.length > 10 && (
            <div className="mt-3 pt-3 border-t text-center">
              <a href="/transactions" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                Voir toutes les {transactions.length} transactions →
              </a>
            </div>
          )}
        </div>
        
        {/* Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <a href="/transactions" className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-2">📊 Transactions</h2>
            <p className="text-gray-600">Gérer et catégoriser</p>
          </a>
          
          <a href="/upload" className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-2">📤 Import</h2>
            <p className="text-gray-600">Importer un relevé</p>
          </a>
          
          <a href="/settings" className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
            <h2 className="text-xl font-semibold mb-2">⚙️ Paramètres</h2>
            <p className="text-gray-600">Configurer le budget</p>
          </a>
        </div>
        
        <div className="mt-8 flex justify-between">
          <button
            onClick={() => {
              localStorage.clear();
              router.push('/login');
            }}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            🚪 Déconnexion
          </button>
          
          <p className="text-sm text-gray-500">
            Version 2.3.7 • Budget Famille
          </p>
        </div>
      </div>
    </div>
  );
}