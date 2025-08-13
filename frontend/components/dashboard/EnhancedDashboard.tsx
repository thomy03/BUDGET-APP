'use client';

import React, { useState, useEffect } from 'react';

// Utility function for consistent number formatting
const formatAmount = (amount: number, type: 'revenue' | 'expense' | 'saving' = 'saving'): string => {
  if (type === 'revenue') return `+${amount.toFixed(2)} €`;
  if (type === 'expense') return `-${amount.toFixed(2)} €`;
  return `${amount.toFixed(2)} €`;
};

// Utility function for consistent text color classes
const getAmountColorClass = (type: 'revenue' | 'expense' | 'saving'): string => {
  if (type === 'revenue') return 'text-green-600';
  if (type === 'expense') return 'text-red-600';
  return 'text-purple-600';
};
import { useEnhancedDashboard, EnhancedSummaryData, SavingsDetail, FixedExpenseDetail, VariableDetail } from '../../hooks/useEnhancedDashboard';
import { Card, LoadingSpinner } from '../ui';
import { ErrorBoundary } from './ErrorBoundary';
import { TransactionDetailModal } from './TransactionDetailModal';
import { AccountBalanceComponent } from './AccountBalance';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';

interface EnhancedDashboardProps {
  month: string;
  isAuthenticated: boolean;
}

const EnhancedDashboard = React.memo<EnhancedDashboardProps>(({ month, isAuthenticated }) => {
  const { data, loading, error, reload, convertExpenseType, bulkConvertExpenseType } = useEnhancedDashboard(month, isAuthenticated);
  const [convertingIds, setConvertingIds] = useState<Set<number>>(new Set());
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    category: 'provision' | 'fixed' | 'variable';
    categoryName?: string;
    tagFilter?: string;
  }>({ isOpen: false, title: '', category: 'variable' });
  const router = useRouter();

  const handleConvertExpenseType = async (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION') => {
    setConvertingIds(prev => new Set(prev).add(transactionId));
    
    try {
      await convertExpenseType(transactionId, newType);
    } catch (error) {
      console.error('Conversion failed:', error);
    } finally {
      setConvertingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(transactionId);
        return newSet;
      });
    }
  };

  // Enhanced authentication and access control
  if (!isAuthenticated) {
    console.warn('Unauthorized access attempt to dashboard');
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
        Vous devez être connecté pour accéder au tableau de bord.
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
        <div className="flex items-center justify-between">
          <span>{error}</span>
          <button 
            onClick={reload}
            className="text-red-600 hover:text-red-800 underline text-sm"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="space-y-8">
        {/* Loading Skeleton */}
        <div className="animate-pulse">
          {/* Revenue Section Skeleton */}
          <div className="h-48 bg-gray-200 rounded-xl mb-8"></div>
          
          {/* Metrics Overview Skeleton */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
          
          {/* Main Content Skeleton */}
          <div className="grid lg:grid-cols-2 gap-8 mb-8">
            <div className="h-64 bg-gray-200 rounded-xl"></div>
            <div className="h-64 bg-gray-200 rounded-xl"></div>
          </div>
          
          {/* Summary Skeleton */}
          <div className="h-32 bg-gray-200 rounded-xl"></div>
        </div>
        
        <div className="flex justify-center py-8">
          <LoadingSpinner size="lg" text="Chargement du dashboard..." />
        </div>
      </div>
    );
  }

  const openModal = (category: 'provision' | 'fixed' | 'variable', categoryName?: string, tagFilter?: string) => {
    console.log('🖱️ Dashboard modal opened:', { category, categoryName, tagFilter });
    
    const titles = {
      provision: `Détail des Provisions${categoryName ? ` - ${categoryName}` : ''}`,
      fixed: `Détail des Charges Fixes${categoryName ? ` - ${categoryName}` : ''}`,
      variable: `Détail des Dépenses Variables${categoryName ? ` - ${categoryName}` : ''}`
    };
    
    // Add tag filter to title if present
    let finalTitle = titles[category];
    if (tagFilter) {
      if (tagFilter.includes(',')) {
        const tagList = tagFilter.split(',').map(t => t.trim()).join(', ');
        finalTitle += ` - Tags: ${tagList} (auto-généré)`;
      } else {
        finalTitle += ` - ${tagFilter} (auto-généré)`;
      }
    }
    
    setModalState({
      isOpen: true,
      title: finalTitle,
      category,
      categoryName,
      tagFilter
    });
  };

  const closeModal = () => {
    setModalState({ isOpen: false, title: '', category: 'variable' });
  };

  return (
    <ErrorBoundary>
    <div className="max-w-full mx-auto space-y-8">
      {/* Revenue Details Section */}
      <RevenueSection data={data} />
      
      {/* Account Balance Section */}
      <AccountBalanceComponent month={month} onBalanceUpdate={reload} />
      
      {/* Key Metrics Overview */}
      <MetricsOverview data={data} onCategoryClick={openModal} />
      
      {/* Strict Separation Info Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <span className="text-blue-500 text-xl flex-shrink-0">✅</span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Séparation Stricte Revenus/Dépenses</h3>
            <div className="grid md:grid-cols-4 gap-3 text-xs text-blue-700">
              <div className="bg-emerald-50 p-2 rounded-lg border border-emerald-100">
                <div className="font-medium text-emerald-800 mb-1">💰 REVENUS</div>
                <div>Montants positifs uniquement (salaires, primes...)</div>
              </div>
              <div className="bg-green-50 p-2 rounded-lg border border-green-100">
                <div className="font-medium text-green-800 mb-1">🎯 ÉPARGNE</div>
                <div>Provisions pour objectifs futurs</div>
              </div>
              <div className="bg-blue-50 p-2 rounded-lg border border-blue-100">
                <div className="font-medium text-blue-800 mb-1">💳 CHARGES FIXES</div>
                <div>⚙️ Manuelles + 🤖 Auto-détectées</div>
              </div>
              <div className="bg-orange-50 p-2 rounded-lg border border-orange-100">
                <div className="font-medium text-orange-800 mb-1">📊 VARIABLES</div>
                <div>Dépenses variables par tags</div>
              </div>
            </div>
            <p className="text-xs text-blue-600 mt-2 font-medium">
              💡 Revenus (positifs) séparés des dépenses (négatives). Conversion possible entre types de dépenses.
            </p>
          </div>
        </div>
      </div>
      
      {/* Main Content - Equal Height 3-Column Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-10 min-h-[600px] max-w-none">
        {/* LEFT: REVENUS (INCOME) */}
        <div className="flex flex-col h-full">
          <RevenueTransactionsSection data={data} month={month} />
        </div>
        
        {/* CENTER: ÉPARGNE (PROVISIONS) */}
        <div className="flex flex-col h-full">
          <SavingsSection data={data} onCategoryClick={openModal} />
        </div>
        
        {/* RIGHT: DÉPENSES (FIXED + VARIABLES) */}
        <div className="flex flex-col h-full">
          <ExpensesSection 
            data={data} 
            convertingIds={convertingIds}
            onConvertExpenseType={handleConvertExpenseType}
            onCategoryClick={openModal}
          />
        </div>
      </div>
      
      {/* Summary Totals */}
      <TotalsSummary data={data} />
      
      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        category={modalState.category}
        categoryName={modalState.categoryName}
        month={month}
        tagFilter={modalState.tagFilter}
      />
    </div>
    </ErrorBoundary>
  );
});

EnhancedDashboard.displayName = 'EnhancedDashboard';

// Revenue Section Component
const RevenueSection = React.memo<{ data: EnhancedSummaryData }>(({ data }) => {
  // Defensive checks for revenue data
  const safeData = data ?? {
    revenues: { member1_revenue: 0, member2_revenue: 0, total_revenue: 0, provision_needed: 0 },
    member1: 'Membre 1',
    member2: 'Membre 2',
    fixed_expenses: { total: 0 },
    savings: { total: 0 },
    totals: { total_expenses: 0 }
  };
  
  // Always show the revenue section, even with zero values
  const revenues = data?.revenues ?? safeData.revenues;
  
  // Calculate recommended provision amount: Total Fixed Expenses + Suggested Provisions
  const recommendedProvision = (
    (safeData.fixed_expenses?.total ?? 0) + 
    (safeData.savings?.total ?? 0)
  );
  
  return (
    <Card className="p-8 border-l-4 border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-green-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">💰</span>
        <div>
          <h2 className="text-xl font-bold text-emerald-900">DÉTAIL DES REVENUS</h2>
          <p className="text-sm text-emerald-700">Répartition des revenus mensuels par membre</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg p-5 border border-emerald-100">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap overflow-hidden text-ellipsis" title={safeData.member1 ?? 'Membre 1'}>{safeData.member1 ?? 'Membre 1'}</div>
          <div className={`text-xl font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.member1_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-5 border border-emerald-100">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap overflow-hidden text-ellipsis" title={safeData.member2 ?? 'Membre 2'}>{safeData.member2 ?? 'Membre 2'}</div>
          <div className={`text-xl font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.member2_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-5 border border-emerald-100 ring-2 ring-emerald-200">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap">Total Revenus</div>
          <div className={`text-xl font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.total_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus combinés</div>
        </div>
        <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg p-5 border border-orange-200">
          <div className="text-sm font-medium text-orange-700 mb-2 whitespace-normal leading-relaxed">Montant à Provisionner</div>
          <div className={`text-xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(recommendedProvision || 0, 'expense')}</div>
          <div className="text-xs text-orange-600 mt-2 leading-relaxed">Charges fixes + Épargne</div>
        </div>
      </div>

      {/* Detailed calculation breakdown */}
      <div className="mt-4 bg-white rounded-lg p-4 border border-emerald-100">
        <div className="text-sm font-medium text-emerald-700 mb-2">Calcul du montant à provisionner:</div>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="text-center">
            <div className={`font-semibold ${getAmountColorClass('expense')}`}>{formatAmount(safeData?.fixed_expenses?.total || 0, 'expense')}</div>
            <div className="text-gray-600">Charges fixes</div>
          </div>
          <div className="text-center">
            <div className={`font-semibold ${getAmountColorClass('expense')}`}>{formatAmount(safeData?.savings?.total || 0, 'expense')}</div>
            <div className="text-gray-600">Provisions épargne</div>
          </div>
          <div className="text-center">
            <div className={`font-bold ${getAmountColorClass('expense')}`}>{formatAmount(recommendedProvision || 0, 'expense')}</div>
            <div className="text-gray-600">Total recommandé</div>
          </div>
        </div>
      </div>

      {/* Progress bar showing coverage */}
      <div className="mt-4">
        <div className="flex justify-between text-sm text-emerald-700 mb-2">
          <span>Couverture Budget Total</span>
          <span>{(safeData?.totals?.total_expenses && revenues?.total_revenue ? ((revenues.total_revenue / safeData.totals.total_expenses) * 100).toFixed(1) : '0.0')}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-emerald-400 to-green-500 h-3 rounded-full transition-all duration-300"
            style={{ 
              width: `${safeData?.totals?.total_expenses && revenues?.total_revenue ? Math.min(100, (revenues.total_revenue / safeData.totals.total_expenses) * 100) : 0}%` 
            }}
          ></div>
        </div>
      </div>
    </Card>
  );
});

RevenueSection.displayName = 'RevenueSection';

// Metrics Overview Component
const MetricsOverview = React.memo<{ 
  data: EnhancedSummaryData;
  onCategoryClick: (category: 'provision' | 'fixed' | 'variable', categoryName?: string, tagFilter?: string) => void;
}>(({ data, onCategoryClick }) => {
  return (
    <div className="space-y-4">
      {/* Total Dépenses - Enhanced with clear visual separation */}
      <Card className="p-6 border-2 border-red-300 bg-gradient-to-r from-red-50 to-pink-50 shadow-lg">
        <div className="text-center">
          <h3 className="text-lg font-bold text-red-900 mb-4 flex items-center justify-center">
            <span className="mr-2">💸</span>
            TOTAL DES DÉPENSES
          </h3>
          
          {/* Main total */}
          <div className={`text-4xl font-bold mb-4 ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.total_expenses || 0, 'expense')}</div>
          
          {/* Breakdown with visual separation */}
          <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-orange-400">
              <div className="text-sm font-medium text-orange-700 mb-1">Variables</div>
              <div className={`text-xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.variables?.total || 0, 'expense')}</div>
              <div className="text-xs text-orange-600 mt-1">{data?.variables?.total_transactions || 0} transactions</div>
            </div>
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-blue-400">
              <div className="text-sm font-medium text-blue-700 mb-1">Fixes</div>
              <div className={`text-xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.fixed_expenses?.total || 0, 'expense')}</div>
              <div className="text-xs text-blue-600 mt-1">{data?.fixed_expenses?.count || 0} charges</div>
            </div>
          </div>
          
          {/* Sum equation */}
          <div className={`text-sm mt-4 font-medium ${getAmountColorClass('expense')}`}>
            {formatAmount(data?.variables?.total || 0, 'expense')} + {formatAmount(data?.fixed_expenses?.total || 0, 'expense')} = {formatAmount(data?.totals?.total_expenses || 0, 'expense')}
          </div>
        </div>
      </Card>
      
      {/* Métriques détaillées */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <MetricCard 
          title="Épargne" 
          value={data?.savings?.total || 0} 
          color="purple"
          icon="🎯"
          subtitle={`${data?.savings?.count || 0} provision${(data?.savings?.count || 0) > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('provision')}
          clickable
        />
        <MetricCard 
          title="Charges Fixes" 
          value={data?.fixed_expenses?.total || 0} 
          color="blue"
          icon="💳"
          subtitle={`${data?.fixed_expenses?.count || 0} charge${(data?.fixed_expenses?.count || 0) > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('fixed')}
          clickable
        />
        <MetricCard 
          title="Variables" 
          value={data?.variables?.total || 0} 
          color="orange"
          icon="📊"
          subtitle={`${data?.variables?.total_transactions || 0} transaction${(data?.variables?.total_transactions || 0) > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('variable')}
          clickable
        />
        <MetricCard 
          title="Total Budget" 
          value={data?.totals?.grand_total || 0} 
          color="purple"
          icon="📈"
          subtitle="Budget complet"
          isTotal
        />
      </div>
    </div>
  );
});

MetricsOverview.displayName = 'MetricsOverview';

// Savings Section Component (LEFT)
const SavingsSection = React.memo<{ 
  data: EnhancedSummaryData;
  onCategoryClick: (category: 'provision' | 'fixed' | 'variable', categoryName?: string, tagFilter?: string) => void;
}>(({ data, onCategoryClick }) => {
  return (
    <Card className="p-8 border-l-4 border-l-purple-500 bg-gradient-to-r from-purple-50 to-indigo-50 h-full flex flex-col">
      <div className="flex items-center mb-6 flex-shrink-0">
        <span className="text-2xl mr-3">🎯</span>
        <div>
          <h2 className="text-xl font-bold text-purple-900">ÉPARGNE</h2>
          <p className="text-sm text-purple-700">Provisions pour objectifs futurs</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {data.savings.detail.length > 0 ? (
          <>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 -mr-2">
              {data.savings.detail.map((saving, index) => (
                <SavingRow 
                  key={index} 
                  saving={saving} 
                  member1={data.member1} 
                  member2={data.member2}
                  onClick={() => onCategoryClick('provision', saving.name)}
                />
              ))}
            </div>
            
            <div className="border-t-2 border-purple-200 pt-3 mt-4 flex-shrink-0">
              <div className="flex justify-between items-center font-bold text-purple-900">
                <span>Total Épargne</span>
                <div className="flex space-x-6">
                  <span className={getAmountColorClass('saving')}>{formatAmount(data?.savings?.member1_total || 0, 'saving')}</span>
                  <span className={getAmountColorClass('saving')}>{formatAmount(data?.savings?.member2_total || 0, 'saving')}</span>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-purple-600">
            <div className="text-center">
              <p>Aucune provision configurée</p>
              <p className="text-sm mt-2">Configurez vos objectifs d'épargne dans les paramètres</p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
});

SavingsSection.displayName = 'SavingsSection';

// Expenses Section Component (RIGHT)  
const ExpensesSection = React.memo<{ 
  data: EnhancedSummaryData;
  convertingIds: Set<number>;
  onConvertExpenseType: (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION') => void;
  onCategoryClick: (category: 'provision' | 'fixed' | 'variable', categoryName?: string, tagFilter?: string) => void;
}>(({ data, convertingIds, onConvertExpenseType, onCategoryClick }) => {
  return (
    <Card className="p-8 border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-orange-50 h-full flex flex-col">
      <div className="flex items-center mb-6 flex-shrink-0">
        <span className="text-2xl mr-3">💸</span>
        <div>
          <h2 className="text-xl font-bold text-red-900">DÉPENSES</h2>
          <p className="text-sm text-red-700">Charges fixes et variables</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0 space-y-6">
        {/* Fixed Expenses Subsection */}
        {data.fixed_expenses.detail.length > 0 && (
          <div className="flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-blue-900 flex items-center">
                <span className="mr-2">💳</span>
                Charges Fixes
              </h3>
              <div className="flex items-center space-x-3 text-xs">
                <div className="flex items-center space-x-1">
                  <span>⚙️</span>
                  <span className="text-blue-600">Manuelles</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span>🤖</span>
                  <span className="text-purple-600">IA</span>
                </div>
              </div>
            </div>
            <div className="space-y-2 mb-4 max-h-48 overflow-y-auto pr-2 -mr-2">
              {data.fixed_expenses.detail.map((expense, index) => (
                <FixedExpenseRow 
                  key={index} 
                  expense={expense} 
                  member1={data.member1} 
                  member2={data.member2}
                  onClick={() => onCategoryClick('fixed', expense.name, expense.tag)}
                />
              ))}
            </div>
            <div className="border-b border-blue-200 pb-2 mb-4">
              <div className="flex justify-between items-center font-semibold text-blue-800">
                <span>Sous-total Fixes</span>
                <div className="flex space-x-6">
                  <span className={getAmountColorClass('expense')}>{formatAmount(data?.fixed_expenses?.member1_total || 0, 'expense')}</span>
                  <span className={getAmountColorClass('expense')}>{formatAmount(data?.fixed_expenses?.member2_total || 0, 'expense')}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Variables Subsection - DETAILED BY TAGS */}
        <div className="flex-1 flex flex-col min-h-0">
          <h3 className="text-lg font-semibold text-orange-900 mb-3 flex items-center flex-shrink-0">
            <span className="mr-2">📊</span>
            Dépenses Variables
            <span className="ml-2 text-sm font-normal text-orange-600">
              ({data.variables.tagged_count} tag{data.variables.tagged_count > 1 ? 's' : ''}, {data.variables.untagged_count} non-taggées)
            </span>
          </h3>
          
          {data.variables.detail.length > 0 ? (
            <>
              <div className="flex-1 overflow-y-auto space-y-2 mb-4 pr-2 -mr-2">
                {data.variables.detail.map((variable, index) => (
                  <VariableRow 
                    key={index} 
                    variable={variable} 
                    member1={data.member1} 
                    member2={data.member2}
                    convertingIds={convertingIds}
                    onConvert={onConvertExpenseType}
                    onClick={() => onCategoryClick('variable', variable.name, variable.tag)}
                  />
                ))}
              </div>
              
              <div className="border-b border-orange-200 pb-2 flex-shrink-0">
                <div className="flex justify-between items-center font-semibold text-orange-800">
                  <span>Sous-total Variables</span>
                  <div className="flex space-x-6">
                    <span className={getAmountColorClass('expense')}>{formatAmount(data?.variables?.member1_total || 0, 'expense')}</span>
                    <span className={getAmountColorClass('expense')}>{formatAmount(data?.variables?.member2_total || 0, 'expense')}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-orange-600 text-sm">Aucune dépense variable ce mois</p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
});

ExpensesSection.displayName = 'ExpensesSection';

// Individual Row Components
const SavingRow = React.memo<{ 
  saving: SavingsDetail; 
  member1: string; 
  member2: string;
  onClick?: () => void;
}>(({ saving, member1, member2, onClick }) => {
  if (!saving) return null;
  return (
    <div 
      className={`flex justify-between items-center py-2 px-3 bg-white rounded-lg border border-purple-100 transition-colors ${
        onClick ? 'hover:bg-purple-50 cursor-pointer hover:shadow-md' : 'hover:bg-purple-25'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center space-x-2">
        <span className="text-lg">{saving.icon}</span>
        <div className="min-w-0 flex-1">
          <span className="font-medium text-purple-900 truncate">{saving.name}</span>
          <div className="w-2 h-2 rounded-full mt-1" style={{ backgroundColor: saving.color }}></div>
        </div>
      </div>
      <div className="flex space-x-6 text-sm font-mono tabular-nums flex-shrink-0 min-w-[160px]">
        <span className={getAmountColorClass('saving')}>{formatAmount(saving?.member1_amount || 0, 'saving')}</span>
        <span className={getAmountColorClass('saving')}>{formatAmount(saving?.member2_amount || 0, 'saving')}</span>
      </div>
    </div>
  );
});

SavingRow.displayName = 'SavingRow';

const FixedExpenseRow = React.memo<{ 
  expense: FixedExpenseDetail; 
  member1: string; 
  member2: string;
  onClick?: () => void;
}>(({ expense, member1, member2, onClick }) => {
  if (!expense) return null;
  const isAIGenerated = expense.source === 'ai_classified';
  
  return (
    <div 
      className={`flex justify-between items-center py-2 px-3 bg-white rounded-lg border transition-colors ${
        isAIGenerated 
          ? 'border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50' 
          : 'border-blue-100'
      } ${
        onClick ? 'cursor-pointer hover:shadow-md hover:scale-[1.02]' : 'hover:bg-blue-50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start space-x-3 min-w-0 flex-1">
        <span className="text-lg flex-shrink-0 mt-0.5">{expense.icon}</span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="text-sm font-medium text-blue-900 whitespace-normal leading-relaxed" title={expense.name} style={{ wordWrap: 'break-word', overflowWrap: 'break-word' }}>
            {expense.name}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded flex-shrink-0">
              {expense.category}
            </span>
            {isAIGenerated && (
              <span className="text-xs bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
                IA
              </span>
            )}
            {expense.tag && (
              <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full flex-shrink-0" title={expense.tag}>
                {expense.tag.length > 25 ? expense.tag.substring(0, 25) + '...' : expense.tag}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex space-x-6 text-sm font-mono tabular-nums flex-shrink-0 min-w-[160px]">
        <span className={getAmountColorClass('expense')}>{formatAmount(expense?.member1_amount || 0, 'expense')}</span>
        <span className={getAmountColorClass('expense')}>{formatAmount(expense?.member2_amount || 0, 'expense')}</span>
      </div>
    </div>
  );
});

FixedExpenseRow.displayName = 'FixedExpenseRow';

const VariableRow = React.memo<{ 
  variable: VariableDetail; 
  member1: string; 
  member2: string;
  convertingIds: Set<number>;
  onConvert: (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION') => void;
  onClick?: () => void;
}>(({ variable, member1, member2, convertingIds, onConvert, onClick }) => {
  if (!variable) return null;
  const isUntagged = variable.type === 'untagged_variable';
  
  return (
    <div 
      className={`flex justify-between items-center py-2 px-3 bg-white rounded-lg border border-orange-100 transition-colors ${
        onClick ? 'cursor-pointer hover:bg-orange-50 hover:shadow-md hover:scale-[1.02]' : 'hover:bg-orange-25'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center min-w-0 flex-1">
        <div className="flex items-center space-x-2 min-w-0 flex-1 mr-2">
          <span className={`text-sm font-medium whitespace-normal leading-relaxed ${isUntagged ? 'text-gray-700' : 'text-orange-900'}`} style={{ wordWrap: 'break-word', overflowWrap: 'break-word' }}>
            {variable.name}
          </span>
          {!isUntagged && variable.tag && (
            <span 
              className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full flex-shrink-0" 
              title={variable.tag}
            >
              {variable.tag.length > 25 ? variable.tag.substring(0, 25) + '...' : variable.tag}
            </span>
          )}
        </div>
        <span className="text-xs text-orange-600 bg-orange-100 px-2 py-0.5 rounded flex-shrink-0">
          {variable.transaction_count} tx
        </span>
        {/* Type Toggle Button - Placeholder for transaction ID */}
        {variable.transaction_ids && variable.transaction_ids.length > 0 && (
          <TypeToggleButton
            currentType="VARIABLE"
            transactionId={variable.transaction_ids[0]}
            isConverting={convertingIds.has(variable.transaction_ids[0])}
            onConvert={onConvert}
          />
        )}
      </div>
      <div className="flex space-x-6 text-sm font-mono tabular-nums flex-shrink-0 min-w-[160px]">
        <span className={getAmountColorClass('expense')}>{formatAmount(variable?.member1_amount || 0, 'expense')}</span>
        <span className={getAmountColorClass('expense')}>{formatAmount(variable?.member2_amount || 0, 'expense')}</span>
      </div>
    </div>
  );
});

VariableRow.displayName = 'VariableRow';

// Totals Summary Component
const TotalsSummary = React.memo<{ data: EnhancedSummaryData }>(({ data }) => {
  return (
    <Card className="p-6 border-2 border-purple-300 bg-gradient-to-r from-purple-50 to-indigo-50">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-purple-900 mb-4 flex items-center justify-center">
          <span className="mr-3">🏆</span>
          BUDGET TOTAL - {data.month}
        </h2>
        
        <div className="grid grid-cols-3 gap-6 max-w-2xl mx-auto">
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">{data.member1}</p>
            <p className={`text-2xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.member1_total || 0, 'expense')}</p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">TOTAL</p>
            <p className={`text-3xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.grand_total || 0, 'expense')}</p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">{data.member2}</p>
            <p className={`text-2xl font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.member2_total || 0, 'expense')}</p>
          </div>
        </div>
        
        <div className="mt-4 text-xs text-purple-600">
          Calcul: {data.metadata.active_provisions} provisions + {data.metadata.active_fixed_expenses} charges fixes + {data.variables.total_transactions} variables ({data.metadata.unique_tags} tags uniques)
        </div>
      </div>
    </Card>
  );
});

TotalsSummary.displayName = 'TotalsSummary';

// Individual metric card component
interface MetricCardProps {
  title: string; 
  value: number | null | undefined; 
  color: 'green' | 'blue' | 'orange' | 'purple'; 
  icon: string;
  subtitle?: string;
  isTotal?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}

const MetricCard = React.memo<MetricCardProps>(({ title, value, color, icon, subtitle, isTotal = false, onClick, clickable = false }) => {
  const colorClasses = {
    green: 'border-l-green-500 bg-gradient-to-r from-green-50 to-green-100 text-green-900',
    blue: 'border-l-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 text-blue-900',
    orange: 'border-l-orange-500 bg-gradient-to-r from-orange-50 to-orange-100 text-orange-900',
    purple: 'border-l-purple-500 bg-gradient-to-r from-purple-50 to-purple-100 text-purple-900'
  };

  const safeValue = (
    typeof value === 'number' && 
    !isNaN(value) && 
    isFinite(value)
  ) ? value : 0;

  return (
    <Card 
      className={`p-5 border-l-4 ${colorClasses[color as keyof typeof colorClasses]} ${
        isTotal ? 'ring-2 ring-purple-200 shadow-lg' : ''
      } ${
        clickable ? 'cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200 hover:ring-2 hover:ring-opacity-30' : ''
      } ${
        clickable && color === 'green' ? 'hover:ring-green-300' : ''
      } ${
        clickable && color === 'blue' ? 'hover:ring-blue-300' : ''
      } ${
        clickable && color === 'orange' ? 'hover:ring-orange-300' : ''
      }`}
      onClick={clickable ? onClick : undefined}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg">{icon}</span>
        <div className="flex items-center space-x-2">
          {isTotal && <span className="text-xs font-medium px-2 py-1 bg-purple-200 rounded-full">TOTAL</span>}
          {clickable && (
            <span className="text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded-full">
              Cliquer pour détails
            </span>
          )}
        </div>
      </div>
      <div className="text-sm font-medium mb-1">{title}</div>
      <div className={`text-xl font-bold ${isTotal ? 'text-2xl' : ''} ${
        color === 'green' ? getAmountColorClass('saving') : 
        (color === 'blue' || color === 'orange') ? getAmountColorClass('expense') : 
        color === 'purple' ? getAmountColorClass('expense') : 
        'text-gray-900'
      }`}>
        {color === 'green' ? formatAmount(safeValue, 'saving') : 
         (color === 'blue' || color === 'orange') ? formatAmount(safeValue, 'expense') :
         color === 'purple' ? formatAmount(safeValue, 'expense') :
         `${safeValue.toFixed(2)} €`}
      </div>
      {subtitle && <div className="text-xs opacity-75 mt-1">{subtitle}</div>}
    </Card>
  );
});

MetricCard.displayName = 'MetricCard';

// Type Toggle Button Component
const TypeToggleButton = React.memo<{
  currentType: 'FIXED' | 'VARIABLE' | 'PROVISION';
  transactionId: number;
  isConverting: boolean;
  onConvert: (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION') => void;
}>(({ currentType, transactionId, isConverting, onConvert }) => {
  const getNextType = (current: string) => {
    if (current === 'VARIABLE') return 'FIXED';
    if (current === 'FIXED') return 'PROVISION';
    return 'VARIABLE';
  };

  const getTypeInfo = (type: string) => {
    switch (type) {
      case 'FIXED':
        return { icon: '🔒', label: 'Fixe', color: 'blue' };
      case 'PROVISION':
        return { icon: '🎯', label: 'Provision', color: 'green' };
      default:
        return { icon: '📊', label: 'Variable', color: 'orange' };
    }
  };

  const currentInfo = getTypeInfo(currentType);
  const nextType = getNextType(currentType) as 'FIXED' | 'VARIABLE' | 'PROVISION';
  const nextInfo = getTypeInfo(nextType);

  return (
    <button
      onClick={() => onConvert(transactionId, nextType)}
      disabled={isConverting}
      className={`
        inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium
        transition-all duration-200 hover:scale-105 active:scale-95
        ${isConverting ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md cursor-pointer'}
        ${currentInfo.color === 'orange' ? 'bg-orange-100 text-orange-800 border border-orange-200' : ''}
        ${currentInfo.color === 'blue' ? 'bg-blue-100 text-blue-800 border border-blue-200' : ''}
        ${currentInfo.color === 'green' ? 'bg-green-100 text-green-800 border border-green-200' : ''}
      `}
      title={`Cliquer pour convertir en ${nextInfo.label}`}
    >
      <span>{currentInfo.icon}</span>
      <span>{currentInfo.label}</span>
      {isConverting ? (
        <span className="animate-spin">⏳</span>
      ) : (
        <span className="text-gray-400">→ {nextInfo.icon}</span>
      )}
    </button>
  );
});

TypeToggleButton.displayName = 'TypeToggleButton';

// Revenue Transactions Section Component - Shows Virements and Avoirs separately
const RevenueTransactionsSection = React.memo<{ 
  data: EnhancedSummaryData;
  month: string;
}>(({ data, month }) => {
  const [revenueTransactions, setRevenueTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    type: 'virements' | 'avoirs' | null;
    transactions: any[];
  }>({ isOpen: false, title: '', type: null, transactions: [] });
  
  // Load revenue transactions from the API
  useEffect(() => {
    const loadRevenueTransactions = async () => {
      if (!month) return;
      
      setLoading(true);
      try {
        // Query transactions with positive amounts (revenues)
        const response = await api.get('/transactions', {
          params: { 
            month: month,
            is_expense: false,
            exclude: false
          }
        });
        
        // Filter to only positive amounts on the client side for safety
        const positiveTransactions = response.data.filter((tx: any) => tx.amount > 0);
        setRevenueTransactions(positiveTransactions);
      } catch (error) {
        console.error('Error loading revenue transactions:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadRevenueTransactions();
  }, [month]);
  
  // Separate transactions by type
  const virements = revenueTransactions.filter(tx => 
    tx.label?.toUpperCase().startsWith('VIR') || 
    tx.label?.toLowerCase().includes('virement')
  );
  
  const avoirs = revenueTransactions.filter(tx => 
    tx.label?.toUpperCase().startsWith('AVOIR') || 
    tx.label?.toLowerCase().includes('avoir')
  );
  
  // Calculate totals
  const totalVirements = virements.reduce((sum, tx) => sum + (tx.amount || 0), 0);
  const totalAvoirs = avoirs.reduce((sum, tx) => sum + (tx.amount || 0), 0);
  
  // Modal handlers
  const openModal = (type: 'virements' | 'avoirs') => {
    const transactions = type === 'virements' ? virements : avoirs;
    const title = type === 'virements' ? 'Détail des Virements' : 'Détail des Avoirs';
    setModalState({
      isOpen: true,
      title,
      type,
      transactions
    });
  };
  
  const closeModal = () => {
    setModalState({ isOpen: false, title: '', type: null, transactions: [] });
  };
  
  return (
    <Card className="p-8 border-l-4 border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-green-50 h-full flex flex-col">
      <div className="flex items-center mb-6 flex-shrink-0">
        <span className="text-2xl mr-3">💰</span>
        <div>
          <h2 className="text-xl font-bold text-emerald-900">REVENUS</h2>
          <p className="text-sm text-emerald-700">Virements et Avoirs séparés</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-emerald-600">
            <p>Chargement des revenus...</p>
          </div>
        ) : revenueTransactions.length > 0 ? (
          <>
            <div className="flex-1 space-y-4">
              {/* Virements Summary Card */}
              {virements.length > 0 && (
                <div 
                  onClick={() => openModal('virements')}
                  className="cursor-pointer transition-all duration-300 transform hover:scale-[1.02] hover:shadow-lg group"
                >
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-200 group-hover:border-green-300 group-hover:shadow-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-3xl group-hover:scale-110 transition-transform duration-300">💸</span>
                        <div>
                          <h3 className="text-lg font-bold text-green-900">Virements</h3>
                          <p className="text-sm text-green-700">{virements.length} transaction{virements.length > 1 ? 's' : ''}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-2xl font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
                          {formatAmount(totalVirements, 'revenue')}
                        </div>
                        <div className="text-xs text-green-600 mt-1 flex items-center justify-end space-x-1">
                          <span>Cliquer pour détails</span>
                          <svg className="w-3 h-3 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Avoirs Summary Card */}
              {avoirs.length > 0 && (
                <div 
                  onClick={() => openModal('avoirs')}
                  className="cursor-pointer transition-all duration-300 transform hover:scale-[1.02] hover:shadow-lg group"
                >
                  <div className="bg-gradient-to-r from-emerald-50 to-green-50 rounded-xl p-6 border-2 border-emerald-200 group-hover:border-emerald-300 group-hover:shadow-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-3xl group-hover:scale-110 transition-transform duration-300">💰</span>
                        <div>
                          <h3 className="text-lg font-bold text-emerald-900">Avoirs</h3>
                          <p className="text-sm text-emerald-700">{avoirs.length} transaction{avoirs.length > 1 ? 's' : ''}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-2xl font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
                          {formatAmount(totalAvoirs, 'revenue')}
                        </div>
                        <div className="text-xs text-emerald-600 mt-1 flex items-center justify-end space-x-1">
                          <span>Cliquer pour détails</span>
                          <svg className="w-3 h-3 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Empty state for specific types */}
              {virements.length === 0 && avoirs.length === 0 && (
                <div className="bg-white rounded-xl p-6 border-2 border-emerald-200 text-center">
                  <div className="text-emerald-600">
                    <p>Aucun virement ou avoir trouvé</p>
                    <p className="text-sm mt-2">Les revenus de ce mois ne correspondent pas aux catégories VIR ou AVOIR</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Total Section */}
            <div className="border-t-2 border-emerald-200 pt-4 mt-6 flex-shrink-0">
              <div className="bg-white rounded-xl p-4 border border-emerald-200 shadow-sm">
                <div className="flex justify-between items-center font-bold text-emerald-900">
                  <span>Total Revenus</span>
                  <span className={`font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
                    {formatAmount(revenueTransactions.reduce((sum, tx) => sum + (tx.amount || 0), 0), 'revenue')}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm text-emerald-700 mt-2">
                  <span>Virements: {formatAmount(totalVirements, 'revenue')}</span>
                  <span>Avoirs: {formatAmount(totalAvoirs, 'revenue')}</span>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-emerald-600">
            <div className="text-center">
              <p>Aucun revenu trouvé pour ce mois</p>
              <p className="text-sm mt-2">Les revenus sont des transactions avec des montants positifs</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Revenue Detail Modal */}
      {modalState.isOpen && (
        <RevenueDetailModal
          isOpen={modalState.isOpen}
          onClose={closeModal}
          title={modalState.title}
          transactions={modalState.transactions}
        />
      )}
    </Card>
  );
});

RevenueTransactionsSection.displayName = 'RevenueTransactionsSection';

// Revenue Detail Modal Component - Shows detailed transaction list
const RevenueDetailModal = React.memo<{
  isOpen: boolean;
  onClose: () => void;
  title: string;
  transactions: any[];
}>(({ isOpen, onClose, title, transactions }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
        onClick={onClose}
      ></div>
      
      {/* Modal Content */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">💰</span>
            <h2 className="text-xl font-bold text-emerald-900">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors duration-200 group"
          >
            <svg className="w-5 h-5 text-gray-500 group-hover:text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Transaction List */}
        <div className="flex-1 overflow-y-auto p-6">
          {transactions.length > 0 ? (
            <div className="space-y-3">
              {transactions.map((transaction, index) => (
                <div 
                  key={index}
                  className="flex justify-between items-center py-3 px-4 bg-gradient-to-r from-emerald-50 to-green-50 rounded-lg border border-emerald-200 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex-1 min-w-0">
                    <div 
                      className="text-sm font-medium text-emerald-900 whitespace-normal leading-relaxed mb-1" 
                      title={transaction.label || 'Revenu'}
                      style={{
                        wordWrap: 'break-word',
                        overflowWrap: 'break-word'
                      }}
                    >
                      {transaction.label || 'Revenu'}
                    </div>
                    <div className="flex items-center space-x-3 text-xs text-emerald-600">
                      <span>
                        {transaction.date_op ? new Date(transaction.date_op).toLocaleDateString('fr-FR') : ''}
                      </span>
                      {transaction.category && (
                        <span className="bg-emerald-100 px-2 py-1 rounded-full">
                          {transaction.category}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 min-w-[120px]">
                    <div className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
                      {formatAmount(transaction.amount || 0, 'revenue')}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-emerald-600 py-8">
              <p>Aucune transaction trouvée</p>
            </div>
          )}
        </div>
        
        {/* Footer with Total */}
        <div className="border-t border-gray-200 p-6 flex-shrink-0">
          <div className="flex justify-between items-center">
            <span className="text-lg font-semibold text-emerald-900">
              Total ({transactions.length} transaction{transactions.length !== 1 ? 's' : ''})
            </span>
            <span className={`text-2xl font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
              {formatAmount(transactions.reduce((sum, tx) => sum + (tx.amount || 0), 0), 'revenue')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

RevenueDetailModal.displayName = 'RevenueDetailModal';

export default EnhancedDashboard;