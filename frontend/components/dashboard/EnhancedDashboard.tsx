'use client';

import React, { useState } from 'react';
import { useEnhancedDashboard, EnhancedSummaryData, SavingsDetail, FixedExpenseDetail, VariableDetail } from '../../hooks/useEnhancedDashboard';
import { Card, LoadingSpinner } from '../ui';
import { TransactionDetailModal } from './TransactionDetailModal';
import { useRouter } from 'next/navigation';

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

  if (!isAuthenticated) {
    return null;
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
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" text="Chargement du dashboard..." />
      </div>
    );
  }

  const openModal = (category: 'provision' | 'fixed' | 'variable', categoryName?: string, tagFilter?: string) => {
    const titles = {
      provision: `Détail des Provisions${categoryName ? ` - ${categoryName}` : ''}`,
      fixed: `Détail des Charges Fixes${categoryName ? ` - ${categoryName}` : ''}`,
      variable: `Détail des Dépenses Variables${categoryName ? ` - ${categoryName}` : ''}`
    };
    
    setModalState({
      isOpen: true,
      title: titles[category],
      category,
      categoryName,
      tagFilter
    });
  };

  const closeModal = () => {
    setModalState({ isOpen: false, title: '', category: 'variable' });
  };

  return (
    <div className="space-y-8">
      {/* Revenue Details Section */}
      <RevenueSection data={data} />
      
      {/* Key Metrics Overview */}
      <MetricsOverview data={data} onCategoryClick={openModal} />
      
      {/* Strict Separation Info Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <span className="text-blue-500 text-xl flex-shrink-0">✅</span>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Logique Exclusive - Fini le Double Comptage !</h3>
            <div className="grid md:grid-cols-3 gap-3 text-xs text-blue-700">
              <div className="bg-green-50 p-2 rounded-lg border border-green-100">
                <div className="font-medium text-green-800 mb-1">🎯 ÉPARGNE</div>
                <div>Provisions pour objectifs futurs (vacances, travaux...)</div>
              </div>
              <div className="bg-blue-50 p-2 rounded-lg border border-blue-100">
                <div className="font-medium text-blue-800 mb-1">💳 CHARGES FIXES</div>
                <div>⚙️ Manuelles + 🤖 Auto-détectées par l'IA</div>
              </div>
              <div className="bg-orange-50 p-2 rounded-lg border border-orange-100">
                <div className="font-medium text-orange-800 mb-1">📊 VARIABLES</div>
                <div>Dépenses ponctuelles par tags + non-taggées</div>
              </div>
            </div>
            <p className="text-xs text-blue-600 mt-2 font-medium">
              💡 Chaque transaction appartient à UNE seule catégorie. Utilisez les boutons de conversion pour changer.
            </p>
          </div>
        </div>
      </div>
      
      {/* Main Content - Split Layout */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* LEFT: ÉPARGNE (PROVISIONS) */}
        <SavingsSection data={data} onCategoryClick={openModal} />
        
        {/* RIGHT: DÉPENSES (FIXED + VARIABLES) */}
        <ExpensesSection 
          data={data} 
          convertingIds={convertingIds}
          onConvertExpenseType={handleConvertExpenseType}
          onCategoryClick={openModal}
        />
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
  );
});

EnhancedDashboard.displayName = 'EnhancedDashboard';

// Revenue Section Component
const RevenueSection = React.memo<{ data: EnhancedSummaryData }>(({ data }) => {
  if (!data.revenues) return null;
  
  // Calculate recommended provision amount: Total Fixed Expenses + Suggested Provisions
  const recommendedProvision = data.fixed_expenses.total + data.savings.total;
  
  return (
    <Card className="p-6 border-l-4 border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-green-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">💰</span>
        <div>
          <h2 className="text-xl font-bold text-emerald-900">DÉTAIL DES REVENUS</h2>
          <p className="text-sm text-emerald-700">Répartition des revenus mensuels par membre</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-4 border border-emerald-100">
          <div className="text-sm font-medium text-emerald-700 mb-1">{data.member1}</div>
          <div className="text-xl font-bold text-emerald-900">{data.revenues.member1_revenue.toFixed(2)} €</div>
          <div className="text-xs text-emerald-600 mt-1">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-4 border border-emerald-100">
          <div className="text-sm font-medium text-emerald-700 mb-1">{data.member2}</div>
          <div className="text-xl font-bold text-emerald-900">{data.revenues.member2_revenue.toFixed(2)} €</div>
          <div className="text-xs text-emerald-600 mt-1">Revenus individuels</div>
        </div>
        <div className="bg-white rounded-lg p-4 border border-emerald-100 ring-2 ring-emerald-200">
          <div className="text-sm font-medium text-emerald-700 mb-1">Total Revenus</div>
          <div className="text-xl font-bold text-emerald-900">{data.revenues.total_revenue.toFixed(2)} €</div>
          <div className="text-xs text-emerald-600 mt-1">Revenus combinés</div>
        </div>
        <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg p-4 border border-orange-200">
          <div className="text-sm font-medium text-orange-700 mb-1">Montant à Provisionner</div>
          <div className="text-xl font-bold text-orange-900">{recommendedProvision.toFixed(2)} €</div>
          <div className="text-xs text-orange-600 mt-1">Charges fixes + Épargne</div>
        </div>
      </div>

      {/* Detailed calculation breakdown */}
      <div className="mt-4 bg-white rounded-lg p-4 border border-emerald-100">
        <div className="text-sm font-medium text-emerald-700 mb-2">Calcul du montant à provisionner:</div>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="text-center">
            <div className="text-blue-600 font-semibold">{data.fixed_expenses.total.toFixed(2)} €</div>
            <div className="text-gray-600">Charges fixes</div>
          </div>
          <div className="text-center">
            <div className="text-green-600 font-semibold">+ {data.savings.total.toFixed(2)} €</div>
            <div className="text-gray-600">Provisions épargne</div>
          </div>
          <div className="text-center">
            <div className="text-orange-600 font-bold">{recommendedProvision.toFixed(2)} €</div>
            <div className="text-gray-600">Total recommandé</div>
          </div>
        </div>
      </div>

      {/* Progress bar showing coverage */}
      <div className="mt-4">
        <div className="flex justify-between text-sm text-emerald-700 mb-2">
          <span>Couverture Budget Total</span>
          <span>{((data.revenues.total_revenue / data.totals.total_expenses) * 100).toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-emerald-400 to-green-500 h-3 rounded-full transition-all duration-300"
            style={{ 
              width: `${Math.min(100, (data.revenues.total_revenue / data.totals.total_expenses) * 100)}%` 
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
          <div className="text-4xl font-bold text-red-900 mb-4">{data.totals.total_expenses.toFixed(2)} €</div>
          
          {/* Breakdown with visual separation */}
          <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-orange-400">
              <div className="text-sm font-medium text-orange-700 mb-1">Variables</div>
              <div className="text-xl font-bold text-orange-900">{data.variables.total.toFixed(2)} €</div>
              <div className="text-xs text-orange-600 mt-1">{data.variables.total_transactions} transactions</div>
            </div>
            <div className="bg-white rounded-lg p-4 border-l-4 border-l-blue-400">
              <div className="text-sm font-medium text-blue-700 mb-1">Fixes</div>
              <div className="text-xl font-bold text-blue-900">{data.fixed_expenses.total.toFixed(2)} €</div>
              <div className="text-xs text-blue-600 mt-1">{data.fixed_expenses.count} charges</div>
            </div>
          </div>
          
          {/* Sum equation */}
          <div className="text-sm text-red-700 mt-4 font-medium">
            {data.variables.total.toFixed(2)} € + {data.fixed_expenses.total.toFixed(2)} € = {data.totals.total_expenses.toFixed(2)} €
          </div>
        </div>
      </Card>
      
      {/* Métriques détaillées */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          title="Épargne" 
          value={data.savings.total} 
          color="green"
          icon="🎯"
          subtitle={`${data.savings.count} provision${data.savings.count > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('provision')}
          clickable
        />
        <MetricCard 
          title="Charges Fixes" 
          value={data.fixed_expenses.total} 
          color="blue"
          icon="💳"
          subtitle={`${data.fixed_expenses.count} charge${data.fixed_expenses.count > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('fixed')}
          clickable
        />
        <MetricCard 
          title="Variables" 
          value={data.variables.total} 
          color="orange"
          icon="📊"
          subtitle={`${data.variables.total_transactions} transaction${data.variables.total_transactions > 1 ? 's' : ''}`}
          onClick={() => onCategoryClick('variable')}
          clickable
        />
        <MetricCard 
          title="Total Budget" 
          value={data.totals.grand_total} 
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
    <Card className="p-6 border-l-4 border-l-green-500 bg-gradient-to-r from-green-50 to-emerald-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">🎯</span>
        <div>
          <h2 className="text-xl font-bold text-green-900">ÉPARGNE</h2>
          <p className="text-sm text-green-700">Provisions pour objectifs futurs</p>
        </div>
      </div>

      {data.savings.detail.length > 0 ? (
        <div className="space-y-3">
          {data.savings.detail.map((saving, index) => (
            <SavingRow 
              key={index} 
              saving={saving} 
              member1={data.member1} 
              member2={data.member2}
              onClick={() => onCategoryClick('provision', saving.name)}
            />
          ))}
          
          <div className="border-t-2 border-green-200 pt-3 mt-4">
            <div className="flex justify-between items-center font-bold text-green-900">
              <span>Total Épargne</span>
              <div className="flex space-x-6">
                <span>{data.savings.member1_total.toFixed(2)} €</span>
                <span>{data.savings.member2_total.toFixed(2)} €</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-green-600">
          <p>Aucune provision configurée</p>
          <p className="text-sm mt-2">Configurez vos objectifs d'épargne dans les paramètres</p>
        </div>
      )}
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
    <Card className="p-6 border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-orange-50">
      <div className="flex items-center mb-6">
        <span className="text-2xl mr-3">💸</span>
        <div>
          <h2 className="text-xl font-bold text-red-900">DÉPENSES</h2>
          <p className="text-sm text-red-700">Charges fixes et variables</p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Fixed Expenses Subsection */}
        {data.fixed_expenses.detail.length > 0 && (
          <div>
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
            <div className="space-y-2 mb-4">
              {data.fixed_expenses.detail.map((expense, index) => (
                <FixedExpenseRow 
                  key={index} 
                  expense={expense} 
                  member1={data.member1} 
                  member2={data.member2}
                  onClick={() => onCategoryClick('fixed', expense.name)}
                />
              ))}
            </div>
            <div className="border-b border-blue-200 pb-2 mb-4">
              <div className="flex justify-between items-center font-semibold text-blue-800">
                <span>Sous-total Fixes</span>
                <div className="flex space-x-6">
                  <span>{data.fixed_expenses.member1_total.toFixed(2)} €</span>
                  <span>{data.fixed_expenses.member2_total.toFixed(2)} €</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Variables Subsection - DETAILED BY TAGS */}
        <div>
          <h3 className="text-lg font-semibold text-orange-900 mb-3 flex items-center">
            <span className="mr-2">📊</span>
            Dépenses Variables
            <span className="ml-2 text-sm font-normal text-orange-600">
              ({data.variables.tagged_count} tag{data.variables.tagged_count > 1 ? 's' : ''}, {data.variables.untagged_count} non-taggées)
            </span>
          </h3>
          
          {data.variables.detail.length > 0 ? (
            <div className="space-y-2 mb-4">
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
          ) : (
            <p className="text-orange-600 text-sm mb-4">Aucune dépense variable ce mois</p>
          )}
          
          <div className="border-b border-orange-200 pb-2">
            <div className="flex justify-between items-center font-semibold text-orange-800">
              <span>Sous-total Variables</span>
              <div className="flex space-x-6">
                <span>{data.variables.member1_total.toFixed(2)} €</span>
                <span>{data.variables.member2_total.toFixed(2)} €</span>
              </div>
            </div>
          </div>
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
  return (
    <div 
      className={`flex justify-between items-center py-2 px-3 bg-white rounded-lg border border-green-100 transition-colors ${
        onClick ? 'hover:bg-green-50 cursor-pointer hover:shadow-md' : 'hover:bg-green-25'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center space-x-2">
        <span className="text-lg">{saving.icon}</span>
        <div className="min-w-0 flex-1">
          <span className="font-medium text-green-900 truncate">{saving.name}</span>
          <div className="w-2 h-2 rounded-full mt-1" style={{ backgroundColor: saving.color }}></div>
        </div>
      </div>
      <div className="flex space-x-6 text-sm font-mono">
        <span className="text-green-800">{saving.member1_amount.toFixed(2)} €</span>
        <span className="text-green-800">{saving.member2_amount.toFixed(2)} €</span>
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
      <div className="flex items-center space-x-2 min-w-0 flex-1">
        <span className="text-lg flex-shrink-0">{expense.icon}</span>
        <div className="min-w-0 flex-1">
          <span className="text-sm font-medium text-blue-900 truncate block">{expense.name}</span>
          <div className="flex items-center space-x-1 mt-0.5">
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded">{expense.category}</span>
            {isAIGenerated && (
              <span className="text-xs bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                IA
              </span>
            )}
            {expense.tag && (
              <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full">
                {expense.tag}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex space-x-6 text-sm font-mono flex-shrink-0">
        <span className="text-blue-800">{expense.member1_amount.toFixed(2)} €</span>
        <span className="text-blue-800">{expense.member2_amount.toFixed(2)} €</span>
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
  const isUntagged = variable.type === 'untagged_variable';
  
  return (
    <div 
      className={`flex justify-between items-center py-2 px-3 bg-white rounded-lg border border-orange-100 transition-colors ${
        onClick ? 'cursor-pointer hover:bg-orange-50 hover:shadow-md hover:scale-[1.02]' : 'hover:bg-orange-25'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center space-x-2 min-w-0 flex-1">
        <span className={`text-sm font-medium truncate ${isUntagged ? 'text-gray-700' : 'text-orange-900'}`}>
          {variable.name}
        </span>
        <span className="text-xs text-orange-600 bg-orange-100 px-2 py-0.5 rounded">
          {variable.transaction_count} tx
        </span>
        {!isUntagged && variable.tag && (
          <span className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded-full">
            {variable.tag}
          </span>
        )}
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
      <div className="flex space-x-6 text-sm font-mono">
        <span className="text-orange-800">{variable.member1_amount.toFixed(2)} €</span>
        <span className="text-orange-800">{variable.member2_amount.toFixed(2)} €</span>
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
            <p className="text-2xl font-bold text-purple-900">{data.totals.member1_total.toFixed(2)} €</p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">TOTAL</p>
            <p className="text-3xl font-bold text-purple-900">{data.totals.grand_total.toFixed(2)} €</p>
          </div>
          
          <div className="text-center">
            <p className="text-sm font-medium text-purple-700 mb-1">{data.member2}</p>
            <p className="text-2xl font-bold text-purple-900">{data.totals.member2_total.toFixed(2)} €</p>
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
const MetricCard = React.memo<{ 
  title: string; 
  value: number; 
  color: string; 
  icon: string;
  subtitle?: string;
  isTotal?: boolean;
  onClick?: () => void;
  clickable?: boolean;
}>(({ title, value, color, icon, subtitle, isTotal = false, onClick, clickable = false }) => {
  const colorClasses = {
    green: 'border-l-green-500 bg-gradient-to-r from-green-50 to-green-100 text-green-900',
    blue: 'border-l-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 text-blue-900',
    orange: 'border-l-orange-500 bg-gradient-to-r from-orange-50 to-orange-100 text-orange-900',
    purple: 'border-l-purple-500 bg-gradient-to-r from-purple-50 to-purple-100 text-purple-900'
  };

  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;

  return (
    <Card 
      className={`p-4 border-l-4 ${colorClasses[color as keyof typeof colorClasses]} ${
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
      <div className={`text-xl font-bold ${isTotal ? 'text-2xl' : ''}`}>{safeValue.toFixed(2)} €</div>
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

export default EnhancedDashboard;