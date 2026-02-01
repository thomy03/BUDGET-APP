'use client';

import React, { useState } from 'react';
import { Card, LoadingSpinner } from '../ui';
import { FadeIn, CountUp, ProgressBar, SlideIn } from '../ui/AnimatedComponents';
import ExpensesDrillDown from './ExpensesDrillDown';
// Icônes SVG simplifiées pour éviter la dépendance HeroIcons
const ChevronRightIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const PlusIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
  </svg>
);

const MinusIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
  </svg>
);
import { useCleanDashboard } from '../../hooks/useCleanDashboard';
import { AICoachWidget } from './AICoachWidget';
import { GamificationWidget } from '../gamification';
import { AlertsBanner } from '../AlertsBanner';

interface CleanDashboardProps {
  month: string;
  isAuthenticated: boolean;
}

/**
 * Design épuré et ultra-lisible - Provision-First Design
 * Architecture: Vue d'ensemble → Catégorie → Détail
 * Principe: Moins d'éléments, plus de clarté
 */
export const CleanDashboard: React.FC<CleanDashboardProps> = ({ month, isAuthenticated }) => {
  const { data, loading, error, formatters } = useCleanDashboard(month, isAuthenticated);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedExpenseType, setSelectedExpenseType] = useState<'variable' | 'fixed' | null>(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <LoadingSpinner size="lg" text="Chargement de votre budget..." />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-24">
        <p className="text-gray-500">Impossible de charger vos données budgétaires</p>
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header épuré avec animation */}
      <FadeIn delay={0} className="text-center pb-4 md:pb-8 border-b border-gray-100">
        <h1 className="text-xl sm:text-2xl md:text-3xl font-light text-gray-900 mb-1 md:mb-2">
          Budget Familial
        </h1>
        <p className="text-sm md:text-lg text-gray-500">
          {new Date(month).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
        </p>
      </FadeIn>

      {/* Alertes Budget - Notifications ML pour dépassements et anomalies */}
      <FadeIn delay={25}>
        <AlertsBanner
          showPredictions={false}
          showRecommendations={true}
          maxAlerts={3}
          refreshInterval={300}
        />
      </FadeIn>

      {/* AI Coach Widget + Gamification - Conseils budget intelligent et accomplissements */}
      <FadeIn delay={50}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 mb-2">
          <AICoachWidget month={month} />
          <GamificationWidget compact />
        </div>
      </FadeIn>

      {/* Vue d'ensemble - Indicateurs clés avec animations échelonnées */}
      <div className="grid grid-cols-1 xs:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
        
        {/* Revenus nets avec animation */}
        <SlideIn delay={100} direction="up">
          <MetricCard
            title="Revenus nets"
            amount={data.revenue.net}
            variant="revenue"
            subtitle={`${data.revenue.member1.name}: ${formatters.compactCurrency(data.revenue.member1.net)} • ${data.revenue.member2.name}: ${formatters.compactCurrency(data.revenue.member2.net)}`}
            animated
          />
        </SlideIn>

        {/* Épargne/Provisions avec animation */}
        <SlideIn delay={200} direction="up">
          <MetricCard
            title="Épargne & Provisions"
            amount={data.provisions.total}
            variant="savings"
            subtitle={`${data.provisions.count} objectifs en cours`}
            onClick={() => setSelectedCategory('provisions')}
            isClickable
            animated
          />
        </SlideIn>

        {/* Dépenses Totales avec animation */}
        <SlideIn delay={300} direction="up">
          <MetricCard
            title="Dépenses"
            amount={data.expenses.total}
            variant="expense"
            subtitle={`Fixes: ${formatters.compactCurrency(data.expenses.fixed)} • Variables: ${formatters.compactCurrency(data.expenses.variable)}`}
            onClick={() => setSelectedCategory('expenses')}
            isClickable
            animated
          />
        </SlideIn>

        {/* Montant à Provisionner avec animation */}
        <SlideIn delay={400} direction="up">
          <MetricCard
            title="À Provisionner"
            amount={data.familyProvision.needed}
            variant={data.familyProvision.status === 'surplus' ? 'positive' : data.familyProvision.status === 'balanced' ? 'warning' : 'negative'}
            subtitle={
              data.familyProvision.status === 'surplus' ? 'Situation confortable' : 
              data.familyProvision.status === 'balanced' ? 'Équilibre serré' : 
              'Budget sous tension'
            }
            animated
          />
        </SlideIn>
      </div>

      {/* RÉPARTITION FAMILIALE - Section détaillée avec breakdown */}
      <FadeIn delay={500} className="p-4 md:p-6 bg-gray-50 rounded-xl">
        <h2 className="text-xs md:text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">
          Répartition Familiale
        </h2>
        <p className="text-[10px] md:text-xs text-gray-400 mb-3 md:mb-4">
          Contribution par membre = Provisions + Dépenses
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {/* Membre 1 */}
          <div className="bg-white rounded-xl p-4 md:p-5 border border-gray-200">
            <div className="flex items-center gap-2 md:gap-3 mb-3 md:mb-4">
              <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-indigo-900 flex items-center justify-center text-white font-semibold text-sm md:text-base">
                {data.revenue.member1.name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-gray-900 text-sm md:text-base truncate">{data.revenue.member1.name}</div>
                <div className="text-[10px] md:text-xs text-gray-500 truncate">
                  {Math.round((data.revenue.member1.net / (data.revenue.member1.net + data.revenue.member2.net)) * 100)}% de son revenu ({formatters.currency(data.revenue.member1.net)})
                </div>
              </div>
            </div>

            <div className="text-2xl md:text-3xl font-light text-indigo-900 mb-3 md:mb-4">
              {formatters.currency(data.familyProvision.member1)}
            </div>

            {/* Détail provisions et dépenses - VISIBLE */}
            <div className="space-y-2 text-sm bg-indigo-50 rounded-lg p-3 mt-3">
              <div className="flex justify-between items-center">
                <span className="text-indigo-700 font-medium">Provisions</span>
                <span className="font-bold text-indigo-900 text-base">
                  {formatters.currency(data.familyProvision.detail?.provisions?.member1 ?? 0)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-orange-700 font-medium">Dépenses</span>
                <span className="font-bold text-orange-900 text-base">
                  {formatters.currency(data.familyProvision.detail?.expenses?.member1 ?? 0)}
                </span>
              </div>
            </div>

            {/* Barre de progression */}
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full"
                  style={{ width: `${Math.min((data.familyProvision.member1 / data.revenue.member1.net) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Membre 2 */}
          <div className="bg-white rounded-xl p-4 md:p-5 border border-gray-200">
            <div className="flex items-center gap-2 md:gap-3 mb-3 md:mb-4">
              <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-slate-700 flex items-center justify-center text-white font-semibold text-sm md:text-base">
                {data.revenue.member2.name.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-gray-900 text-sm md:text-base truncate">{data.revenue.member2.name}</div>
                <div className="text-[10px] md:text-xs text-gray-500 truncate">
                  {Math.round((data.revenue.member2.net / (data.revenue.member1.net + data.revenue.member2.net)) * 100)}% de son revenu ({formatters.currency(data.revenue.member2.net)})
                </div>
              </div>
            </div>

            <div className="text-2xl md:text-3xl font-light text-slate-700 mb-3 md:mb-4">
              {formatters.currency(data.familyProvision.member2)}
            </div>

            {/* Détail provisions et dépenses - VISIBLE */}
            <div className="space-y-2 text-sm bg-slate-100 rounded-lg p-3 mt-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-700 font-medium">Provisions</span>
                <span className="font-bold text-slate-900 text-base">
                  {formatters.currency(data.familyProvision.detail?.provisions?.member2 ?? 0)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-orange-700 font-medium">Dépenses</span>
                <span className="font-bold text-orange-900 text-base">
                  {formatters.currency(data.familyProvision.detail?.expenses?.member2 ?? 0)}
                </span>
              </div>
            </div>

            {/* Barre de progression */}
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-slate-600 h-2 rounded-full"
                  style={{ width: `${Math.min((data.familyProvision.member2 / data.revenue.member2.net) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </FadeIn>

      {/* PROVISIONS ACTIVES */}
      <FadeIn delay={600} className="p-4 md:p-6 bg-white rounded-xl border border-gray-200">
        <div className="flex justify-between items-center mb-3 md:mb-4">
          <h2 className="text-xs md:text-sm font-semibold text-gray-500 uppercase tracking-wider">
            Provisions Actives
          </h2>
          <a href="/settings" className="text-xs md:text-sm text-indigo-600 hover:text-indigo-800 min-h-[44px] flex items-center">
            Gérer →
          </a>
        </div>

        <div className="space-y-2 md:space-y-3">
          {data.provisions.items.slice(0, 4).map((provision) => (
            <div key={provision.id} className="flex justify-between items-center py-1.5 md:py-2">
              <span className="text-sm md:text-base text-gray-700 truncate flex-1 mr-2">{provision.name}</span>
              <span className="font-medium text-gray-900 text-sm md:text-base whitespace-nowrap">{formatters.currency(provision.currentAmount)}/mois</span>
            </div>
          ))}
          {data.provisions.items.length > 4 && (
            <div className="text-center text-xs md:text-sm text-gray-500 pt-2">
              + {data.provisions.items.length - 4} autres provisions
            </div>
          )}
        </div>
      </FadeIn>

      {/* Drill-down des dépenses */}
      {selectedExpenseType && (
        <ExpensesDrillDown
          month={month}
          type={selectedExpenseType}
          onClose={() => setSelectedExpenseType(null)}
        />
      )}

      {/* Détail catégorie sélectionnée */}
      {selectedCategory && !selectedExpenseType && (
        <CategoryDetail
          category={selectedCategory}
          data={data}
          onClose={() => setSelectedCategory(null)}
          formatters={formatters}
          month={month}
          onExpenseTypeClick={(type) => {
            setSelectedExpenseType(type);
          }}
        />
      )}

      {/* Quick Actions - Minimaliste */}
      <div className="flex justify-center pt-4 md:pt-8">
        <div className="flex flex-col xs:flex-row space-y-2 xs:space-y-0 xs:space-x-4 w-full xs:w-auto px-4 xs:px-0">
          <QuickActionButton
            icon={PlusIcon}
            label="Ajouter Provision"
            onClick={() => {
              // Redirection vers la page settings/provisions
              window.location.href = '/settings';
            }}
          />
          <QuickActionButton
            icon={MinusIcon}
            label="Voir Dépenses"
            onClick={() => setSelectedCategory('expenses')}
          />
        </div>
      </div>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  amount: number;
  variant: 'revenue' | 'savings' | 'expense' | 'positive' | 'negative' | 'warning';
  subtitle?: string;
  onClick?: () => void;
  isClickable?: boolean;
  animated?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  amount, 
  variant, 
  subtitle, 
  onClick, 
  isClickable,
  animated = false
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'revenue':
        return 'border-emerald-200 bg-emerald-50 text-emerald-700';
      case 'savings':
        return 'border-blue-200 bg-blue-50 text-blue-700';
      case 'expense':
        return 'border-orange-200 bg-orange-50 text-orange-700';
      case 'positive':
        return 'border-green-200 bg-green-50 text-green-700';
      case 'warning':
        return 'border-amber-200 bg-amber-50 text-amber-700';
      case 'negative':
        return 'border-red-200 bg-red-50 text-red-700';
      default:
        return 'border-gray-200 bg-gray-50 text-gray-700';
    }
  };

  const formatAmount = (amount: number) => {
    const formatted = Math.abs(amount).toFixed(0);
    const sign = amount >= 0 ? '' : '-';
    return `${sign}${formatted}€`;
  };

  return (
    <Card
      className={`
        ${getVariantStyles()}
        ${isClickable ? 'cursor-pointer hover:shadow-md transition-shadow duration-200' : ''}
        border-2 p-4 md:p-6 text-center
      `}
      onClick={onClick}
    >
      <div className="space-y-2 md:space-y-3">
        <h3 className="text-xs md:text-sm font-medium uppercase tracking-wider">
          {title}
        </h3>

        <div className="text-xl sm:text-2xl md:text-3xl font-light">
          {animated ? (
            <CountUp
              value={amount}
              formatter={(v) => formatAmount(v)}
              duration={800}
            />
          ) : (
            formatAmount(amount)
          )}
        </div>

        {subtitle && (
          <p className="text-[10px] md:text-xs opacity-75 truncate">
            {subtitle}
          </p>
        )}

        {isClickable && (
          <ChevronRightIcon className="w-4 h-4 mx-auto opacity-50" />
        )}
      </div>
    </Card>
  );
};

interface CategoryDetailProps {
  category: string;
  data: any;
  formatters: any;
  onClose: () => void;
  month: string;
  onExpenseTypeClick?: (type: 'variable' | 'fixed') => void;
}

const CategoryDetail: React.FC<CategoryDetailProps> = ({ 
  category, 
  data, 
  formatters,
  onClose, 
  month,
  onExpenseTypeClick
}) => {
  const getCategoryData = () => {
    switch (category) {
      case 'provisions':
        return {
          title: 'Épargne & Provisions',
          items: data.provisions.items.map((p: any) => ({
            name: p.name,
            amount: p.currentAmount,
            progress: p.progress,
            target: p.targetAmount
          }))
        };
      case 'expenses':
        return {
          title: 'Dépenses du Mois',
          items: [
            {
              name: 'Dépenses Variables',
              amount: data.expenses.variable,
              detail: `${data.expenses.count} transactions`,
              category: 'variable',
              clickable: true
            },
            {
              name: 'Dépenses Fixes',
              amount: data.expenses.fixed,
              detail: 'Engagements mensuels',
              category: 'fixed',
              clickable: true
            }
          ]
        };
      default:
        return { title: 'Détail', items: [] };
    }
  };

  const { title, items } = getCategoryData();

  return (
    <Card className="border-2 border-blue-200 bg-blue-50">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-medium text-blue-900">{title}</h3>
          <button
            onClick={onClose}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Fermer
          </button>
        </div>
        
        <div className="space-y-4">
          {items.map((item, index) => (
            <div 
              key={index}
              className={`bg-white rounded-lg p-4 border border-blue-200 ${
                item.clickable ? 'cursor-pointer hover:border-blue-300 hover:shadow-sm transition-all' : ''
              }`}
              onClick={() => {
                if (item.clickable && onExpenseTypeClick) {
                  onExpenseTypeClick(item.category as 'variable' | 'fixed');
                }
              }}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-900">{item.name}</span>
                  {item.clickable && <ChevronRightIcon className="w-4 h-4 text-blue-400" />}
                </div>
                <div className="text-right">
                  <div className="text-lg font-light text-blue-700">
                    {formatters.currency(Math.abs(item.amount))}
                  </div>
                  {item.totalProvisionedSinceJanuary !== undefined && (
                    <div className="text-xs text-green-600 mt-1">
                      Cumulé: {formatters.currency(item.totalProvisionedSinceJanuary)}
                    </div>
                  )}
                </div>
              </div>
              {item.detail && (
                <div className="text-sm text-gray-600 mt-1">{item.detail}</div>
              )}
              
              {item.progress !== undefined && (
                <div className="mt-2">
                  <ProgressBar
                    value={item.progress}
                    max={100}
                    variant="success"
                    animated={true}
                    showLabel={false}
                  />
                  <div className="flex justify-between text-xs text-green-600 mt-1">
                    {item.totalProvisionedSinceJanuary !== undefined && (
                      <span>Provisionné: {formatters.currency(item.totalProvisionedSinceJanuary)}</span>
                    )}
                    {item.targetAmount && (
                      <span>Objectif: {formatters.currency(item.targetAmount)}</span>
                    )}
                  </div>
                  {item.monthProgress !== undefined && (
                    <div className="text-xs text-gray-500 mt-1">
                      Progression année: {item.monthProgress.toFixed(0)}% (mois {new Date(month).getMonth() + 1}/12)
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};

interface QuickActionButtonProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}

const QuickActionButton: React.FC<QuickActionButtonProps> = ({ 
  icon: Icon, 
  label, 
  onClick 
}) => (
  <button
    onClick={onClick}
    className="
      flex items-center space-x-2 px-4 py-2 
      bg-white border border-gray-200 rounded-lg
      hover:border-gray-300 hover:shadow-sm
      transition-all duration-200
      text-sm font-medium text-gray-700
    "
  >
    <Icon className="w-4 h-4" />
    <span>{label}</span>
  </button>
);

export default CleanDashboard;