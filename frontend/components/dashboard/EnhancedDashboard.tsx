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
import { HierarchicalNavigationModal } from './HierarchicalNavigationModal';
import { AccountBalanceComponent } from './AccountBalance';
import { useRouter } from 'next/navigation';
import { api, balanceApi } from '../../lib/api';

interface EnhancedDashboardProps {
  month: string;
  isAuthenticated: boolean;
}

const EnhancedDashboard = React.memo<EnhancedDashboardProps>(({ month, isAuthenticated }) => {
  const { data, loading, error, reload, convertExpenseType, bulkConvertExpenseType } = useEnhancedDashboard(month, isAuthenticated);
  const [convertingIds, setConvertingIds] = useState<Set<number>>(new Set());
  const [accountBalance, setAccountBalance] = useState<number>(0);
  
  // Charger le solde au démarrage
  useEffect(() => {
    const loadBalance = async () => {
      try {
        const balanceData = await balanceApi.get(month);
        setAccountBalance(balanceData.account_balance);
      } catch (error) {
        console.error('Erreur chargement solde:', error);
      }
    };
    if (month && isAuthenticated) {
      loadBalance();
    }
  }, [month, isAuthenticated]);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    title: string;
    category: 'provision' | 'fixed' | 'variable';
    categoryName?: string;
    tagFilter?: string;
  }>({ isOpen: false, title: '', category: 'variable' });
  
  // State for savings detail modal
  const [savingsModalState, setSavingsModalState] = useState<{
    isOpen: boolean;
    category: string;
    categoryName: string;
    items: SavingsDetail[];
  }>({
    isOpen: false,
    category: '',
    categoryName: '',
    items: []
  });

  // State for expense detail modal
  const [expenseModalState, setExpenseModalState] = useState<{
    isOpen: boolean;
    category: string;
    categoryName: string;
    items: (FixedExpenseDetail | VariableDetail & { type: string })[];
  }>({
    isOpen: false,
    category: '',
    categoryName: '',
    items: []
  });

  // State for hierarchical navigation modal
  const [hierarchicalModalState, setHierarchicalModalState] = useState<{
    isOpen: boolean;
    title: string;
    initialCategory?: string;
    initialFilters?: {
      expense_type?: 'FIXED' | 'VARIABLE' | 'PROVISION';
      tag?: string;
    };
  }>({
    isOpen: false,
    title: '',
    initialCategory: undefined,
    initialFilters: undefined
  });
  
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

  // Handlers for savings detail modal
  const openSavingsModal = (category: string, categoryName: string, items: SavingsDetail[]) => {
    setSavingsModalState({
      isOpen: true,
      category,
      categoryName,
      items
    });
  };

  const closeSavingsModal = () => {
    setSavingsModalState({
      isOpen: false,
      category: '',
      categoryName: '',
      items: []
    });
  };

  // Handlers for expense detail modal
  const openExpenseModal = (category: string, categoryName: string, items: (FixedExpenseDetail | VariableDetail & { type: string })[]) => {
    setExpenseModalState({
      isOpen: true,
      category,
      categoryName,
      items
    });
  };

  const closeExpenseModal = () => {
    setExpenseModalState({
      isOpen: false,
      category: '',
      categoryName: '',
      items: []
    });
  };

  // Handlers for hierarchical navigation modal
  const openHierarchicalModal = (title: string, initialCategory?: string, initialFilters?: any) => {
    setHierarchicalModalState({
      isOpen: true,
      title,
      initialCategory,
      initialFilters
    });
  };

  const closeHierarchicalModal = () => {
    setHierarchicalModalState({
      isOpen: false,
      title: '',
      initialCategory: undefined,
      initialFilters: undefined
    });
  };

  // Reassignment handlers
  const handleReassignSaving = (itemName: string, newCategory: string) => {
    console.log('Reassigning saving:', itemName, 'to category:', newCategory);
    // TODO: Implement actual reassignment logic
    // This would update the categorization in the backend or local state
    // For now, just log the action
    alert(`Would reassign "${itemName}" to "${newCategory}"`);
  };

  const handleReassignExpense = (itemName: string, newCategory: string) => {
    console.log('Reassigning expense:', itemName, 'to category:', newCategory);
    // TODO: Implement actual reassignment logic
    // This would update the categorization in the backend or local state
    // For now, just log the action
    alert(`Would reassign "${itemName}" to "${newCategory}"`);
  };

  return (
    <ErrorBoundary>
    <div className="max-w-[1600px] mx-auto px-6 space-y-8">
      {/* Revenue Details Section */}
      <RevenueSection data={data} accountBalance={accountBalance} />
      
      {/* Account Balance Section */}
      <AccountBalanceComponent month={month} onBalanceUpdate={(balance) => {
        setAccountBalance(balance);
        reload();
      }} />
      
      {/* Key Metrics Overview */}
      <MetricsOverview 
        data={data} 
        onCategoryClick={openModal} 
        onHierarchicalNavigation={openHierarchicalModal}
      />
      
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
      
      {/* Main Content - Equal Height 3-Column Layout avec centrage amélioré */}
      <div className="flex justify-center">
        <div className="flex flex-col 2xl:flex-row gap-6 min-h-[600px] w-full max-w-[1400px]">
        {/* LEFT: REVENUS (INCOME) */}
        <div className="flex flex-col h-full flex-1 min-w-0 2xl:min-w-[400px] 2xl:max-w-[500px]">
          <RevenueTransactionsSection data={data} month={month} />
        </div>
        
        {/* CENTER: ÉPARGNE (PROVISIONS) */}
        <div className="flex flex-col h-full flex-1 min-w-0 2xl:min-w-[400px] 2xl:max-w-[500px]">
          <SavingsSection 
            data={data} 
            onCategoryClick={openSavingsModal} 
            onHierarchicalNavigation={openHierarchicalModal}
          />
        </div>
        
        {/* RIGHT: DÉPENSES (FIXED + VARIABLES) */}
        <div className="flex flex-col h-full flex-1 min-w-0 2xl:min-w-[400px] 2xl:max-w-[500px]">
          <ExpensesSection 
            data={data} 
            convertingIds={convertingIds}
            onConvertExpenseType={handleConvertExpenseType}
            onCategoryClick={openExpenseModal}
            onHierarchicalNavigation={openHierarchicalModal}
          />
        </div>
        </div>
      </div>
      
      {/* Summary Totals */}
      <TotalsSummary data={data} accountBalance={accountBalance} />
      
      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        category={modalState.category}
        categoryName={modalState.categoryName}
        month={month}
        tagFilter={modalState.tagFilter}
        onOpenHierarchicalNavigation={openHierarchicalModal}
      />
      
      {/* Savings Detail Modal */}
      <SavingsDetailModal
        isOpen={savingsModalState.isOpen}
        onClose={closeSavingsModal}
        category={savingsModalState.category}
        categoryName={savingsModalState.categoryName}
        items={savingsModalState.items}
        onReassign={handleReassignSaving}
      />
      
      {/* Expense Detail Modal */}
      <ExpenseDetailModal
        isOpen={expenseModalState.isOpen}
        onClose={closeExpenseModal}
        category={expenseModalState.category}
        categoryName={expenseModalState.categoryName}
        items={expenseModalState.items}
        onReassign={handleReassignExpense}
      />

      {/* Hierarchical Navigation Modal */}
      <HierarchicalNavigationModal
        isOpen={hierarchicalModalState.isOpen}
        onClose={closeHierarchicalModal}
        title={hierarchicalModalState.title}
        month={month}
        initialCategory={hierarchicalModalState.initialCategory}
        initialFilters={hierarchicalModalState.initialFilters}
      />
    </div>
    </ErrorBoundary>
  );
});

EnhancedDashboard.displayName = 'EnhancedDashboard';

// Revenue Section Component
const RevenueSection = React.memo<{ data: EnhancedSummaryData; accountBalance?: number }>(({ data, accountBalance = 0 }) => {
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
  
  // Calculate recommended provision amount: Total Fixed Expenses + Suggested Provisions - Account Balance
  // If balance is positive, it reduces the need to provision. If negative, it increases it.
  const baseProvision = (
    (safeData.fixed_expenses?.total ?? 0) + 
    (safeData.savings?.total ?? 0)
  );
  const recommendedProvision = Math.max(0, baseProvision - accountBalance);
  
  // Calculate split between members (assuming 50/50 or based on income ratio)
  const member1Income = revenues?.member1_revenue || 0;
  const member2Income = revenues?.member2_revenue || 0;
  const totalIncome = member1Income + member2Income;
  
  let member1Provision = recommendedProvision / 2;
  let member2Provision = recommendedProvision / 2;
  
  if (totalIncome > 0) {
    // Split based on income ratio
    member1Provision = recommendedProvision * (member1Income / totalIncome);
    member2Provision = recommendedProvision * (member2Income / totalIncome);
  }
  
  return (
    <Card className="p-8 border-l-4 border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-green-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">💰</span>
        <div>
          <h2 className="text-xl font-bold text-emerald-900">DÉTAIL DES REVENUS</h2>
          <p className="text-sm text-emerald-700">Répartition des revenus mensuels par membre</p>
        </div>
      </div>

      <div className="flex flex-col sm:grid sm:grid-cols-2 2xl:flex 2xl:flex-row gap-6 max-w-full">
        <div className="bg-white rounded-lg p-5 border border-emerald-100 flex-1">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap" title={safeData.member1 ?? 'Membre 1'}>{safeData.member1 ?? 'Membre 1'}</div>
          <div className={`text-lg font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.member1_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-5 border border-emerald-100 flex-1">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap" title={safeData.member2 ?? 'Membre 2'}>{safeData.member2 ?? 'Membre 2'}</div>
          <div className={`text-lg font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.member2_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-5 border border-emerald-100 ring-2 ring-emerald-200 flex-1">
          <div className="text-sm font-medium text-emerald-700 mb-2 whitespace-nowrap">Total Revenus</div>
          <div className={`text-lg font-bold ${getAmountColorClass('revenue')}`}>{formatAmount(revenues?.total_revenue || 0, 'revenue')}</div>
          <div className="text-xs text-emerald-600 mt-2 leading-relaxed">Revenus combinés</div>
        </div>
        <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg p-5 border border-orange-200 flex-1">
          <div className="text-sm font-medium text-orange-700 mb-2 whitespace-nowrap">Montant à Provisionner</div>
          <div className={`text-lg font-bold ${getAmountColorClass('expense')}`}>{formatAmount(recommendedProvision || 0, 'expense')}</div>
          <div className="text-xs text-orange-600 mt-2 leading-relaxed">
            {accountBalance !== 0 && (
              <span className="block">
                Solde: {accountBalance >= 0 ? '+' : ''}{accountBalance.toFixed(2)}€
              </span>
            )}
            Charges + Épargne {accountBalance > 0 ? '- Solde' : accountBalance < 0 ? '+ Déficit' : ''}
          </div>
        </div>
      </div>

      {/* Detailed calculation breakdown */}
      <div className="mt-4 bg-white rounded-lg p-4 border border-emerald-100">
        <div className="text-sm font-medium text-emerald-700 mb-2">Calcul du montant à provisionner:</div>
        <div className="grid grid-cols-4 gap-3 text-xs">
          <div className="text-center">
            <div className={`font-semibold ${getAmountColorClass('expense')}`}>{formatAmount(safeData?.fixed_expenses?.total || 0, 'expense')}</div>
            <div className="text-gray-600">Charges fixes</div>
          </div>
          <div className="text-center">
            <div className={`font-semibold ${getAmountColorClass('expense')}`}>{formatAmount(safeData?.savings?.total || 0, 'expense')}</div>
            <div className="text-gray-600">Provisions</div>
          </div>
          <div className="text-center">
            <div className={`font-semibold ${accountBalance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {accountBalance >= 0 ? '-' : '+'}{Math.abs(accountBalance).toFixed(2)} €
            </div>
            <div className="text-gray-600">Solde compte</div>
          </div>
          <div className="text-center">
            <div className={`font-bold ${getAmountColorClass('expense')}`}>{formatAmount(recommendedProvision || 0, 'expense')}</div>
            <div className="text-gray-600">Total à provisionner</div>
          </div>
        </div>
        
        {/* Répartition entre membres */}
        <div className="mt-4 pt-4 border-t border-emerald-100">
          <div className="text-sm font-medium text-emerald-700 mb-2">Répartition à provisionner:</div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-emerald-50 rounded-lg p-3 text-center">
              <div className="text-xs text-emerald-600 mb-1">{safeData.member1 ?? 'Membre 1'}</div>
              <div className="font-bold text-emerald-900">{formatAmount(member1Provision, 'expense')}</div>
              <div className="text-xs text-emerald-600 mt-1">
                {totalIncome > 0 ? `${((member1Income / totalIncome) * 100).toFixed(0)}% des revenus` : '50%'}
              </div>
            </div>
            <div className="bg-emerald-50 rounded-lg p-3 text-center">
              <div className="text-xs text-emerald-600 mb-1">{safeData.member2 ?? 'Membre 2'}</div>
              <div className="font-bold text-emerald-900">{formatAmount(member2Provision, 'expense')}</div>
              <div className="text-xs text-emerald-600 mt-1">
                {totalIncome > 0 ? `${((member2Income / totalIncome) * 100).toFixed(0)}% des revenus` : '50%'}
              </div>
            </div>
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
  onHierarchicalNavigation: (title: string, initialCategory?: string, initialFilters?: any) => void;
}>(({ data, onCategoryClick, onHierarchicalNavigation }) => {
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
          <div className={`text-xl font-bold mb-4 ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.total_expenses || 0, 'expense')}</div>
          
          {/* Breakdown with visual separation */}
          <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-orange-400">
              <div className="text-sm font-medium text-orange-700 mb-1">Variables</div>
              <div className={`text-lg font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.variables?.total || 0, 'expense')}</div>
              <div className="text-xs text-orange-600 mt-1">{data?.variables?.total_transactions || 0} transactions</div>
            </div>
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-blue-400">
              <div className="text-sm font-medium text-blue-700 mb-1">Fixes</div>
              <div className={`text-lg font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.fixed_expenses?.total || 0, 'expense')}</div>
              <div className="text-xs text-blue-600 mt-1">{data?.fixed_expenses?.count || 0} charges</div>
            </div>
          </div>
          
          {/* Sum equation */}
          <div className={`text-sm mt-4 font-medium ${getAmountColorClass('expense')}`}>
            {formatAmount(data?.variables?.total || 0, 'expense')} + {formatAmount(data?.fixed_expenses?.total || 0, 'expense')} = {formatAmount(data?.totals?.total_expenses || 0, 'expense')}
          </div>
        </div>
      </Card>
      
      {/* Navigation Hiérarchique Avancée */}
      <Card className="p-4 border border-indigo-200 bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🗂️</span>
            <div>
              <h3 className="text-lg font-bold text-indigo-900">Navigation Hiérarchique</h3>
              <p className="text-sm text-indigo-700">Explorez vos données jusqu'au niveau transaction</p>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => onHierarchicalNavigation('Navigation Complète - Épargne', undefined, { expense_type: 'PROVISION' })}
              className="px-3 py-2 bg-purple-100 text-purple-800 rounded-lg hover:bg-purple-200 transition-colors text-sm font-medium"
            >
              🎯 Épargne
            </button>
            <button
              onClick={() => onHierarchicalNavigation('Navigation Complète - Charges Fixes', undefined, { expense_type: 'FIXED' })}
              className="px-3 py-2 bg-blue-100 text-blue-800 rounded-lg hover:bg-blue-200 transition-colors text-sm font-medium"
            >
              💳 Fixes
            </button>
            <button
              onClick={() => onHierarchicalNavigation('Navigation Complète - Variables', undefined, { expense_type: 'VARIABLE' })}
              className="px-3 py-2 bg-orange-100 text-orange-800 rounded-lg hover:bg-orange-200 transition-colors text-sm font-medium"
            >
              📊 Variables
            </button>
            <button
              onClick={() => onHierarchicalNavigation('Navigation Complète - Toutes les Dépenses')}
              className="px-3 py-2 bg-gray-100 text-gray-800 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
            >
              🔍 Tout
            </button>
          </div>
        </div>
      </Card>
      
      {/* Métriques détaillées */}
      <div className="flex flex-col sm:grid sm:grid-cols-2 2xl:flex 2xl:flex-row gap-6 max-w-full">
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

// Define savings categories with intelligent grouping logic
const savingsCategories = {
  'objectifs': {
    name: '🎯 Objectifs Court Terme',
    keywords: ['vacances', 'voyage', 'projet', 'achat', 'cadeau', 'noel', 'anniversaire'],
    items: [] as SavingsDetail[],
    total: 0
  },
  'investissement': {
    name: '📈 Investissements',
    keywords: ['etf', 'pea', 'assurance-vie', 'investissement', 'placement', 'actions', 'bourse'],
    items: [] as SavingsDetail[],
    total: 0
  },
  'retraite': {
    name: '👴 Retraite',
    keywords: ['retraite', 'per', 'epargne-retraite', 'pension', 'rente'],
    items: [] as SavingsDetail[],
    total: 0
  },
  'urgence': {
    name: '🚨 Épargne de Sécurité',
    keywords: ['urgence', 'securite', 'precaution', 'sante', 'fonds', 'reserve'],
    items: [] as SavingsDetail[],
    total: 0
  },
  'autres': {
    name: '📦 Autres Épargnes',
    keywords: [],
    items: [] as SavingsDetail[],
    total: 0
  }
};

// Intelligent categorization function for savings
function categorizeSaving(saving: SavingsDetail) {
  const savingName = saving.name?.toLowerCase() || '';
  
  // Check each category's keywords
  for (const [key, category] of Object.entries(savingsCategories)) {
    if (key === 'autres') continue; // Skip 'autres' in the loop
    if (category.keywords.some(keyword => savingName.includes(keyword))) {
      return key;
    }
  }
  
  // Default to 'autres'
  return 'autres';
}

// Savings Section Component (LEFT) - Now with intelligent hierarchical grouping
const SavingsSection = React.memo<{ 
  data: EnhancedSummaryData;
  onCategoryClick: (category: string, categoryName: string, items: SavingsDetail[]) => void;
  onHierarchicalNavigation?: (title: string, initialCategory?: string, initialFilters?: any) => void;
}>(({ data, onCategoryClick, onHierarchicalNavigation }) => {
  // Group savings by categories
  const savingsGroups = React.useMemo(() => {
    // Reset categories
    const categories = JSON.parse(JSON.stringify(savingsCategories));
    
    // Categorize each saving
    data.savings.detail.forEach(saving => {
      const categoryKey = categorizeSaving(saving);
      categories[categoryKey].items.push(saving);
      categories[categoryKey].total += (saving.member1_amount || 0) + (saving.member2_amount || 0);
    });
    
    // Remove empty categories (except 'autres')
    const nonEmptyCategories: typeof categories = {};
    Object.entries(categories).forEach(([key, category]) => {
      if (category.items.length > 0 || key === 'autres') {
        nonEmptyCategories[key] = category;
      }
    });
    
    return nonEmptyCategories;
  }, [data.savings.detail]);
  
  const hasAnySavings = data.savings.detail.length > 0;
  const nonEmptyGroups = Object.entries(savingsGroups).filter(([_, group]) => group.items.length > 0);

  return (
    <Card className="p-8 border-l-4 border-l-purple-500 bg-gradient-to-r from-purple-50 to-indigo-50 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">🎯</span>
          <div>
            <h2 className="text-xl font-bold text-purple-900">ÉPARGNE</h2>
            <p className="text-sm text-purple-700">Provisions groupées par objectifs</p>
          </div>
        </div>
        {onHierarchicalNavigation && (
          <button
            onClick={() => onHierarchicalNavigation('Navigation Épargne Détaillée', undefined, { expense_type: 'PROVISION' })}
            className="px-3 py-1.5 bg-purple-100 text-purple-800 rounded-lg hover:bg-purple-200 transition-colors text-xs font-medium flex items-center space-x-1"
          >
            <span>🔍</span>
            <span>Détail</span>
          </button>
        )}
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {hasAnySavings ? (
          <>
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 -mr-2">
              {nonEmptyGroups.map(([key, group]) => (
                <div 
                  key={key}
                  onClick={() => onCategoryClick(key, group.name, group.items)}
                  className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-6 cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border-2 border-purple-200 group"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-purple-900 mb-2">{group.name}</h3>
                      <p className="text-sm text-purple-700 mb-3">{group.items.length} provision{group.items.length > 1 ? 's' : ''}</p>
                      
                      {/* Show first few items as preview */}
                      <div className="space-y-1 mb-2">
                        {group.items.slice(0, 2).map((item, idx) => (
                          <div key={idx} className="text-xs text-purple-600 flex items-center space-x-2">
                            <span className="text-sm">{item.icon}</span>
                            <span className="truncate">{item.name}</span>
                          </div>
                        ))}
                        {group.items.length > 2 && (
                          <div className="text-xs text-purple-500 italic">
                            +{group.items.length - 2} autres...
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0 ml-4">
                      <p className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('saving')}`}>
                        {formatAmount(group.total, 'saving')}
                      </p>
                      <p className="text-xs text-purple-600 mt-1 flex items-center justify-end space-x-1 group-hover:translate-x-1 transition-transform duration-300">
                        <span>Cliquer pour détails</span>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="border-t-2 border-purple-200 pt-4 mt-4 flex-shrink-0">
              <div className="bg-white rounded-xl p-4 border border-purple-200 shadow-sm">
                <div className="flex justify-between items-center font-bold text-purple-900">
                  <span>Total Épargne</span>
                  <div className="flex space-x-6 font-mono tabular-nums">
                    <span className={getAmountColorClass('saving')}>{formatAmount(data?.savings?.member1_total || 0, 'saving')}</span>
                    <span className={getAmountColorClass('saving')}>{formatAmount(data?.savings?.member2_total || 0, 'saving')}</span>
                  </div>
                </div>
                <div className="flex justify-between items-center text-sm text-purple-700 mt-2">
                  <span>{nonEmptyGroups.length} catégorie{nonEmptyGroups.length > 1 ? 's' : ''} active{nonEmptyGroups.length > 1 ? 's' : ''}</span>
                  <span className={`font-mono tabular-nums ${getAmountColorClass('saving')}`}>
                    {formatAmount(data?.savings?.total || 0, 'saving')}
                  </span>
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

// Define expense categories with intelligent grouping logic
const expenseCategories = {
  'logement': {
    name: '🏠 Logement',
    keywords: ['loyer', 'electricite', 'eau', 'gaz', 'internet', 'assurance-habitation', 'chauffage', 'edf', 'engie'],
    tags: ['electricite', 'eau', 'gaz', 'internet', 'loyer'],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  },
  'transport': {
    name: '🚗 Transport',
    keywords: ['essence', 'parking', 'peage', 'transport', 'train', 'metro', 'bus', 'taxi', 'uber', 'voiture'],
    tags: ['essence', 'parking', 'transport', 'peage'],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  },
  'alimentation': {
    name: '🛒 Alimentation',
    keywords: ['courses', 'restaurant', 'resto', 'supermarche', 'alimentaire', 'carrefour', 'leclerc', 'mcdo'],
    tags: ['courses', 'resto', 'petite-depense'],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  },
  'loisirs': {
    name: '🎭 Loisirs & Culture',
    keywords: ['streaming', 'cinema', 'sport', 'loisir', 'culture', 'sortie', 'netflix', 'spotify', 'theatre'],
    tags: ['streaming', 'voyage', 'hotel', 'loisir'],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  },
  'sante': {
    name: '🏥 Santé',
    keywords: ['pharmacie', 'medecin', 'sante', 'mutuelle', 'dentiste', 'hopital', 'medicament'],
    tags: ['sante', 'pharmacie'],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  },
  'autres': {
    name: '📦 Autres',
    keywords: [],
    tags: [],
    items: [] as (FixedExpenseDetail | VariableDetail)[],
    total: 0
  }
};

// Intelligent categorization function for expenses
function categorizeExpense(expense: FixedExpenseDetail | VariableDetail) {
  const expenseName = expense.name?.toLowerCase() || '';
  const expenseTag = expense.tag?.toLowerCase() || '';
  
  // Check by tag first
  for (const [key, category] of Object.entries(expenseCategories)) {
    if (key === 'autres') continue; // Skip 'autres' in the loop
    if (category.tags.some(tag => expenseTag.includes(tag))) {
      return key;
    }
  }
  
  // Check by name/label keywords
  for (const [key, category] of Object.entries(expenseCategories)) {
    if (key === 'autres') continue; // Skip 'autres' in the loop
    if (category.keywords.some(keyword => expenseName.includes(keyword))) {
      return key;
    }
  }
  
  // Default to 'autres'
  return 'autres';
}

// Expenses Section Component (RIGHT) - Now with intelligent hierarchical grouping
const ExpensesSection = React.memo<{ 
  data: EnhancedSummaryData;
  convertingIds: Set<number>;
  onConvertExpenseType: (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION') => void;
  onCategoryClick: (category: string, categoryName: string, items: (FixedExpenseDetail | VariableDetail & { type: string })[]) => void;
  onHierarchicalNavigation?: (title: string, initialCategory?: string, initialFilters?: any) => void;
}>(({ data, convertingIds, onConvertExpenseType, onCategoryClick, onHierarchicalNavigation }) => {
  // Group expenses by categories
  const expenseGroups = React.useMemo(() => {
    // Reset categories
    const categories = JSON.parse(JSON.stringify(expenseCategories));
    
    // Categorize fixed expenses
    data.fixed_expenses.detail.forEach(expense => {
      const categoryKey = categorizeExpense(expense);
      categories[categoryKey].items.push({ ...expense, type: 'fixed' });
      categories[categoryKey].total += (expense.member1_amount || 0) + (expense.member2_amount || 0);
    });
    
    // Categorize variable expenses
    data.variables.detail.forEach(expense => {
      const categoryKey = categorizeExpense(expense);
      categories[categoryKey].items.push({ ...expense, type: 'variable' });
      categories[categoryKey].total += (expense.member1_amount || 0) + (expense.member2_amount || 0);
    });
    
    // Remove empty categories (except 'autres')
    const nonEmptyCategories: typeof categories = {};
    Object.entries(categories).forEach(([key, category]) => {
      if (category.items.length > 0 || key === 'autres') {
        nonEmptyCategories[key] = category;
      }
    });
    
    return nonEmptyCategories;
  }, [data.fixed_expenses.detail, data.variables.detail]);
  
  const hasAnyExpenses = data.fixed_expenses.detail.length > 0 || data.variables.detail.length > 0;
  const nonEmptyGroups = Object.entries(expenseGroups).filter(([_, group]) => group.items.length > 0);

  return (
    <Card className="p-8 border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-orange-50 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">💸</span>
          <div>
            <h2 className="text-xl font-bold text-red-900">DÉPENSES</h2>
            <p className="text-sm text-red-700">Charges groupées par catégories</p>
          </div>
        </div>
        {onHierarchicalNavigation && (
          <div className="flex space-x-1">
            <button
              onClick={() => onHierarchicalNavigation('Navigation Charges Fixes', undefined, { expense_type: 'FIXED' })}
              className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium hover:bg-blue-200 transition-colors"
            >
              💳
            </button>
            <button
              onClick={() => onHierarchicalNavigation('Navigation Variables', undefined, { expense_type: 'VARIABLE' })}
              className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs font-medium hover:bg-orange-200 transition-colors"
            >
              📊
            </button>
            <button
              onClick={() => onHierarchicalNavigation('Navigation Toutes Dépenses')}
              className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-medium hover:bg-red-200 transition-colors"
            >
              🔍
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {hasAnyExpenses ? (
          <>
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 -mr-2">
              {nonEmptyGroups.map(([key, group]) => {
                const fixedItems = group.items.filter((item: any) => item.type === 'fixed');
                const variableItems = group.items.filter((item: any) => item.type === 'variable');
                
                return (
                  <div 
                    key={key}
                    onClick={() => onCategoryClick(key, group.name, group.items)}
                    className="bg-gradient-to-r from-red-50 to-orange-50 rounded-xl p-6 cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border-2 border-red-200 group"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-red-900 mb-2">{group.name}</h3>
                        <p className="text-sm text-red-700 mb-3">
                          {group.items.length} dépense{group.items.length > 1 ? 's' : ''}
                          {fixedItems.length > 0 && variableItems.length > 0 && (
                            <span className="ml-2 text-xs">({fixedItems.length} fixes, {variableItems.length} variables)</span>
                          )}
                        </p>
                        
                        {/* Show type indicators */}
                        <div className="flex items-center space-x-2 mb-2">
                          {fixedItems.length > 0 && (
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full flex items-center space-x-1">
                              <span>💳</span>
                              <span>{fixedItems.length} fixe{fixedItems.length > 1 ? 's' : ''}</span>
                            </span>
                          )}
                          {variableItems.length > 0 && (
                            <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded-full flex items-center space-x-1">
                              <span>📊</span>
                              <span>{variableItems.length} variable{variableItems.length > 1 ? 's' : ''}</span>
                            </span>
                          )}
                        </div>
                        
                        {/* Show first few items as preview */}
                        <div className="space-y-1 mb-2">
                          {group.items.slice(0, 2).map((item: any, idx) => (
                            <div key={idx} className="text-xs text-red-600 flex items-center space-x-2">
                              <span className="text-sm">{item.icon || (item.type === 'fixed' ? '💳' : '📊')}</span>
                              <span className="truncate">{item.name}</span>
                              {item.tag && (
                                <span className="bg-red-100 px-1 py-0.5 rounded text-xs">{item.tag}</span>
                              )}
                            </div>
                          ))}
                          {group.items.length > 2 && (
                            <div className="text-xs text-red-500 italic">
                              +{group.items.length - 2} autres...
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0 ml-4">
                        <p className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('expense')}`}>
                          {formatAmount(group.total, 'expense')}
                        </p>
                        <p className="text-xs text-red-600 mt-1 flex items-center justify-end space-x-1 group-hover:translate-x-1 transition-transform duration-300">
                          <span>Cliquer pour détails</span>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            
            <div className="border-t-2 border-red-200 pt-4 mt-4 flex-shrink-0">
              <div className="bg-white rounded-xl p-4 border border-red-200 shadow-sm">
                <div className="flex justify-between items-center font-bold text-red-900">
                  <span>Total Dépenses</span>
                  <div className="flex space-x-6 font-mono tabular-nums">
                    <span className={getAmountColorClass('expense')}>
                      {formatAmount((data?.fixed_expenses?.member1_total || 0) + (data?.variables?.member1_total || 0), 'expense')}
                    </span>
                    <span className={getAmountColorClass('expense')}>
                      {formatAmount((data?.fixed_expenses?.member2_total || 0) + (data?.variables?.member2_total || 0), 'expense')}
                    </span>
                  </div>
                </div>
                <div className="flex justify-between items-center text-sm text-red-700 mt-2">
                  <span>{nonEmptyGroups.length} catégorie{nonEmptyGroups.length > 1 ? 's' : ''} active{nonEmptyGroups.length > 1 ? 's' : ''}</span>
                  <span className={`font-mono tabular-nums ${getAmountColorClass('expense')}`}>
                    {formatAmount(data?.totals?.total_expenses || 0, 'expense')}
                  </span>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-red-600">
            <div className="text-center">
              <p>Aucune dépense trouvée</p>
              <p className="text-sm mt-2">Les dépenses apparaîtront automatiquement ici</p>
            </div>
          </div>
        )}
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
          <span className="font-medium text-purple-900 whitespace-nowrap" title={saving.name}>{saving.name}</span>
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
          <div className="text-sm font-medium text-blue-900 whitespace-nowrap" title={expense.name}>
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
              <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full flex-shrink-0 whitespace-nowrap" title={expense.tag}>
                {expense.tag}
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
          <span className={`text-sm font-medium whitespace-nowrap ${isUntagged ? 'text-gray-700' : 'text-orange-900'}`} title={variable.name}>
            {variable.name}
          </span>
          {!isUntagged && variable.tag && (
            <span 
              className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full flex-shrink-0 whitespace-nowrap" 
              title={variable.tag}
            >
              {variable.tag}
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
const TotalsSummary = React.memo<{ data: EnhancedSummaryData; accountBalance?: number }>(({ data, accountBalance = 0 }) => {
  // Calcul du budget disponible : solde + revenus - (provisions + fixes + variables)
  const totalRevenues = data?.revenues?.total_revenue || 0;
  const totalProvisions = data?.savings?.total || 0;
  const totalFixed = data?.fixed_expenses?.total || 0;
  const totalVariables = data?.variables?.total || 0;
  const totalExpenses = totalProvisions + totalFixed + totalVariables;
  const budgetDisponible = accountBalance + totalRevenues - totalExpenses;
  return (
    <Card className="p-6 border-2 border-purple-300 bg-gradient-to-r from-purple-50 to-indigo-50">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-purple-900 mb-4 flex items-center justify-center">
          <span className="mr-3">🏆</span>
          BUDGET DISPONIBLE - {data.month}
        </h2>
        
        <div className="grid grid-cols-3 gap-6 max-w-2xl mx-auto mb-6">
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">{data.member1}</p>
            <p className={`text-lg font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.member1_total || 0, 'expense')}</p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">BUDGET DISPONIBLE</p>
            <p className={`text-3xl font-bold ${budgetDisponible >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {budgetDisponible >= 0 ? '+' : ''}{budgetDisponible.toFixed(2)} €
            </p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">{data.member2}</p>
            <p className={`text-lg font-bold ${getAmountColorClass('expense')}`}>{formatAmount(data?.totals?.member2_total || 0, 'expense')}</p>
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-4 border border-purple-200">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-purple-700">Solde début de mois:</span>
              <span className={`ml-2 font-mono ${accountBalance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {accountBalance >= 0 ? '+' : ''}{accountBalance.toFixed(2)} €
              </span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Revenus:</span>
              <span className="ml-2 font-mono text-green-600">+{totalRevenues.toFixed(2)} €</span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Provisions:</span>
              <span className="ml-2 font-mono text-purple-600">-{totalProvisions.toFixed(2)} €</span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Charges fixes:</span>
              <span className="ml-2 font-mono text-blue-600">-{totalFixed.toFixed(2)} €</span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Variables:</span>
              <span className="ml-2 font-mono text-orange-600">-{totalVariables.toFixed(2)} €</span>
            </div>
            <div>
              <span className="font-medium text-purple-700">Total dépenses:</span>
              <span className="ml-2 font-mono text-red-600">-{totalExpenses.toFixed(2)} €</span>
            </div>
          </div>
        </div>
        
        <div className="mt-4 text-xs text-purple-600 text-center">
          Formule: Solde + Revenus - (Provisions + Fixes + Variables) = Budget disponible
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
      <div className={`text-lg font-bold ${isTotal ? 'text-xl' : ''} ${
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
                        <div className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
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
                        <div className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
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
                      className="text-sm font-medium text-emerald-900 whitespace-nowrap mb-1" 
                      title={transaction.label || 'Revenu'}
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
            <span className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('revenue')}`}>
              {formatAmount(transactions.reduce((sum, tx) => sum + (tx.amount || 0), 0), 'revenue')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

RevenueDetailModal.displayName = 'RevenueDetailModal';

// Savings Detail Modal Component - Shows detailed savings list with reassignment
const SavingsDetailModal = React.memo<{
  isOpen: boolean;
  onClose: () => void;
  category: string;
  categoryName: string;
  items: SavingsDetail[];
  onReassign: (itemName: string, newCategory: string) => void;
}>(({ isOpen, onClose, category, categoryName, items, onReassign }) => {
  if (!isOpen) return null;

  const totalAmount = items.reduce((sum, item) => sum + (item.member1_amount || 0) + (item.member2_amount || 0), 0);

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
            <span className="text-2xl">🎯</span>
            <h2 className="text-xl font-bold text-purple-900">{categoryName}</h2>
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
        
        {/* Items List */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {items.map((item, index) => (
              <div 
                key={index}
                className="flex justify-between items-center p-3 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200 hover:shadow-md transition-all duration-200"
              >
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-lg flex-shrink-0">{item.icon}</span>
                    <p className="font-medium text-purple-900 truncate" title={item.name}>
                      {item.name}
                    </p>
                  </div>
                  <select 
                    value={category}
                    onChange={(e) => onReassign(item.name, e.target.value)}
                    className="text-sm mt-1 p-2 border border-purple-200 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white"
                  >
                    <option value="objectifs">🎯 Objectifs Court Terme</option>
                    <option value="investissement">📈 Investissements</option>
                    <option value="retraite">👴 Retraite</option>
                    <option value="urgence">🚨 Épargne de Sécurité</option>
                    <option value="autres">📦 Autres</option>
                  </select>
                </div>
                <div className="text-right flex-shrink-0 min-w-[200px]">
                  <div className="space-y-1">
                    <p className={`font-mono text-sm ${getAmountColorClass('saving')}`}>
                      {formatAmount(item.member1_amount, 'saving')}
                    </p>
                    <p className={`font-mono text-sm ${getAmountColorClass('saving')}`}>
                      {formatAmount(item.member2_amount, 'saving')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Footer with Total */}
        <div className="border-t border-gray-200 p-6 flex-shrink-0">
          <div className="flex justify-between items-center">
            <span className="text-lg font-semibold text-purple-900">
              Total ({items.length} provision{items.length !== 1 ? 's' : ''})
            </span>
            <span className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('saving')}`}>
              {formatAmount(totalAmount, 'saving')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

SavingsDetailModal.displayName = 'SavingsDetailModal';

// Expense Detail Modal Component - Shows detailed expense list with reassignment
const ExpenseDetailModal = React.memo<{
  isOpen: boolean;
  onClose: () => void;
  category: string;
  categoryName: string;
  items: (FixedExpenseDetail | VariableDetail & { type: string })[];
  onReassign: (itemName: string, newCategory: string) => void;
}>(({ isOpen, onClose, category, categoryName, items, onReassign }) => {
  if (!isOpen) return null;

  const totalAmount = items.reduce((sum, item) => sum + (item.member1_amount || 0) + (item.member2_amount || 0), 0);

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
            <span className="text-2xl">💸</span>
            <h2 className="text-xl font-bold text-red-900">{categoryName}</h2>
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
        
        {/* Items List */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {items.map((item, index) => (
              <div 
                key={index}
                className="flex justify-between items-center p-3 bg-gradient-to-r from-red-50 to-orange-50 rounded-lg border border-red-200 hover:shadow-md transition-all duration-200"
              >
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-lg flex-shrink-0">{(item as any).icon || (item.type === 'fixed' ? '💳' : '📊')}</span>
                    <p className="font-medium text-red-900 truncate" title={item.name || (item as any).tag}>
                      {item.name || (item as any).tag}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                      {item.type === 'fixed' ? 'Fixe' : 'Variable'}
                    </span>
                    {(item as any).tag && (
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                        {(item as any).tag}
                      </span>
                    )}
                  </div>
                  <select 
                    value={category}
                    onChange={(e) => onReassign(item.name || (item as any).tag, e.target.value)}
                    className="text-sm p-1 border border-red-200 rounded-md focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-white w-full"
                  >
                    <option value="logement">🏠 Logement</option>
                    <option value="transport">🚗 Transport</option>
                    <option value="alimentation">🛒 Alimentation</option>
                    <option value="loisirs">🎭 Loisirs & Culture</option>
                    <option value="sante">🏥 Santé</option>
                    <option value="autres">📦 Autres</option>
                  </select>
                </div>
                <div className="text-right flex-shrink-0 min-w-[200px]">
                  <div className="space-y-1">
                    <p className={`font-mono text-sm ${getAmountColorClass('expense')}`}>
                      {formatAmount(item.member1_amount, 'expense')}
                    </p>
                    <p className={`font-mono text-sm ${getAmountColorClass('expense')}`}>
                      {formatAmount(item.member2_amount, 'expense')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Footer with Total */}
        <div className="border-t border-gray-200 p-6 flex-shrink-0">
          <div className="flex justify-between items-center">
            <span className="text-lg font-semibold text-red-900">
              Total ({items.length} dépense{items.length !== 1 ? 's' : ''})
            </span>
            <span className={`text-lg font-bold font-mono tabular-nums ${getAmountColorClass('expense')}`}>
              {formatAmount(totalAmount, 'expense')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

ExpenseDetailModal.displayName = 'ExpenseDetailModal';

export default EnhancedDashboard;