'use client';

import React, { useState } from 'react';
import { Card } from '../ui';
// Icônes SVG simplifiées
const ChevronRightIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const ChevronLeftIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

const HomeIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

const EyeIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
);

export interface NavigationStep {
  id: string;
  title: string;
  type: 'overview' | 'category' | 'detail' | 'transaction';
  data?: any;
}

interface NavigationDrillDownProps {
  steps: NavigationStep[];
  currentStep: number;
  onNavigate: (stepIndex: number) => void;
  children: React.ReactNode;
}

/**
 * Composant de navigation hiérarchique avec drill-down
 * Design épuré pour navigation intuitive entre niveaux
 */
export const NavigationDrillDown: React.FC<NavigationDrillDownProps> = ({
  steps,
  currentStep,
  onNavigate,
  children
}) => {
  const currentStepData = steps[currentStep];
  const canGoBack = currentStep > 0;
  const canGoForward = currentStep < steps.length - 1;

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-sm">
        <button
          onClick={() => onNavigate(0)}
          className="flex items-center space-x-1 text-gray-500 hover:text-gray-700 transition-colors"
        >
          <HomeIcon className="w-4 h-4" />
          <span>Accueil</span>
        </button>
        
        {steps.slice(1, currentStep + 1).map((step, index) => (
          <React.Fragment key={step.id}>
            <ChevronRightIcon className="w-4 h-4 text-gray-300" />
            <button
              onClick={() => onNavigate(index + 1)}
              className={`
                transition-colors
                ${index + 1 === currentStep 
                  ? 'text-blue-600 font-medium' 
                  : 'text-gray-500 hover:text-gray-700'
                }
              `}
            >
              {step.title}
            </button>
          </React.Fragment>
        ))}
      </nav>

      {/* Navigation Controls */}
      {(canGoBack || canGoForward) && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => canGoBack && onNavigate(currentStep - 1)}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-lg border transition-all
              ${canGoBack 
                ? 'border-gray-300 text-gray-700 hover:border-gray-400 hover:shadow-sm' 
                : 'border-gray-200 text-gray-400 cursor-not-allowed'
              }
            `}
            disabled={!canGoBack}
          >
            <ChevronLeftIcon className="w-4 h-4" />
            <span>Retour</span>
          </button>

          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <EyeIcon className="w-4 h-4" />
            <span>{currentStepData.title}</span>
          </div>

          <button
            onClick={() => canGoForward && onNavigate(currentStep + 1)}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-lg border transition-all
              ${canGoForward 
                ? 'border-gray-300 text-gray-700 hover:border-gray-400 hover:shadow-sm' 
                : 'border-gray-200 text-gray-400 cursor-not-allowed'
              }
            `}
            disabled={!canGoForward}
          >
            <span>Suivant</span>
            <ChevronRightIcon className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Content Area */}
      <div className="transition-all duration-300 ease-in-out">
        {children}
      </div>
    </div>
  );
};

interface DrillDownCardProps {
  title: string;
  subtitle?: string;
  amount?: number;
  progress?: number;
  variant?: 'default' | 'provision' | 'expense' | 'income';
  onClick?: () => void;
  children?: React.ReactNode;
}

/**
 * Carte cliquable pour navigation drill-down
 * Design harmonisé avec animations fluides
 */
export const DrillDownCard: React.FC<DrillDownCardProps> = ({
  title,
  subtitle,
  amount,
  progress,
  variant = 'default',
  onClick,
  children
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'provision':
        return 'border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-900';
      case 'expense':
        return 'border-red-200 bg-red-50 hover:bg-red-100 text-red-900';
      case 'income':
        return 'border-green-200 bg-green-50 hover:bg-green-100 text-green-900';
      default:
        return 'border-gray-200 bg-white hover:bg-gray-50 text-gray-900';
    }
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(Math.abs(amount));
  };

  return (
    <Card
      className={`
        ${getVariantStyles()}
        ${onClick ? 'cursor-pointer hover:shadow-md' : ''}
        border-2 p-6 transition-all duration-200
      `}
      onClick={onClick}
    >
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="font-semibold text-lg">{title}</h3>
            {subtitle && (
              <p className="text-sm opacity-75">{subtitle}</p>
            )}
          </div>
          
          {amount !== undefined && (
            <div className="text-right">
              <div className="text-2xl font-light">
                {formatAmount(amount)}
              </div>
            </div>
          )}
          
          {onClick && (
            <ChevronRightIcon className="w-5 h-5 opacity-50 ml-4" />
          )}
        </div>

        {/* Progress Bar */}
        {progress !== undefined && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span>Progression</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="bg-white bg-opacity-50 rounded-full h-2">
              <div 
                className="bg-current h-2 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Children Content */}
        {children && (
          <div className="pt-2 border-t border-current border-opacity-20">
            {children}
          </div>
        )}
      </div>
    </Card>
  );
};

/**
 * Hook pour gérer l'état de navigation drill-down
 */
export const useNavigationDrillDown = (initialSteps: NavigationStep[] = []) => {
  const [steps, setSteps] = useState<NavigationStep[]>(initialSteps);
  const [currentStep, setCurrentStep] = useState(0);

  const navigateToStep = (stepIndex: number) => {
    if (stepIndex >= 0 && stepIndex < steps.length) {
      setCurrentStep(stepIndex);
    }
  };

  const addStep = (step: NavigationStep) => {
    const newSteps = [...steps.slice(0, currentStep + 1), step];
    setSteps(newSteps);
    setCurrentStep(newSteps.length - 1);
  };

  const goBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const goHome = () => {
    setCurrentStep(0);
  };

  const reset = (newSteps: NavigationStep[]) => {
    setSteps(newSteps);
    setCurrentStep(0);
  };

  return {
    steps,
    currentStep,
    currentStepData: steps[currentStep],
    navigateToStep,
    addStep,
    goBack,
    goHome,
    reset,
    canGoBack: currentStep > 0,
    canGoForward: currentStep < steps.length - 1
  };
};

export default NavigationDrillDown;