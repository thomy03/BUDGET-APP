'use client';

import { validateRequiredProps, isValidExpenseType } from '../../types/defensive-programming';

interface ExpenseTypeBadgeProps {
  type: 'fixed' | 'variable' | null;
  size?: 'sm' | 'md';
  interactive?: boolean;
  onClick?: () => void;
  confidenceScore?: number;
  autoDetected?: boolean;
  className?: string;
}

export function ExpenseTypeBadge({ 
  type, 
  size = 'sm',
  interactive = false,
  onClick,
  confidenceScore,
  autoDetected = false,
  className = ''
}: ExpenseTypeBadgeProps) {
  // DEFENSIVE PROGRAMMING: Validate props
  if (!validateRequiredProps({ type }, ['type'], 'ExpenseTypeBadge') || !type) {
    return null;
  }
  
  // DEFENSIVE PROGRAMMING: Type validation
  if (!isValidExpenseType(type)) {
    console.error(`ExpenseTypeBadge: Invalid type "${type}". Expected 'fixed' or 'variable'.`);
    return null;
  }

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base'
  };

  const typeConfig = {
    fixed: {
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
        </svg>
      ),
      label: 'FIXE',
      bgColor: 'bg-blue-100',
      textColor: 'text-blue-900',
      borderColor: 'border-blue-500',
      shadowColor: 'shadow-blue-200/50',
      hoverBg: interactive ? 'hover:bg-blue-200 hover:shadow-lg hover:scale-105 hover:border-blue-600 hover:shadow-blue-300/60' : '',
      focusRing: 'focus:ring-blue-500 focus:ring-2'
    },
    variable: {
      icon: (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      ),
      label: 'VARIABLE',
      bgColor: 'bg-orange-100',
      textColor: 'text-orange-900',
      borderColor: 'border-orange-500',
      shadowColor: 'shadow-orange-200/50',
      hoverBg: interactive ? 'hover:bg-orange-200 hover:shadow-lg hover:scale-105 hover:border-orange-600 hover:shadow-orange-300/60' : '',
      focusRing: 'focus:ring-orange-500 focus:ring-2'
    }
  };

  const config = typeConfig[type];
  
  // Vérifier que la config existe pour le type donné
  if (!config) {
    console.warn(`ExpenseTypeBadge: Invalid type "${type}". Expected 'fixed' or 'variable'.`);
    return null;
  }

  // Déterminer le tooltip
  let tooltipText = `Dépense ${config.label.toLowerCase()}`;
  if (autoDetected && confidenceScore) {
    tooltipText += ` - Auto-détecté (${Math.round(confidenceScore * 100)}%)`;
  }
  if (interactive) {
    tooltipText += ' - Cliquer pour modifier';
  }

  const badgeClasses = [
    'inline-flex items-center gap-2 font-bold border-2 rounded-lg transition-all duration-200 select-none shadow-lg',
    sizeClasses[size],
    config.bgColor,
    config.textColor,
    config.borderColor,
    config.shadowColor,
    config.hoverBg,
    interactive ? `cursor-pointer focus:outline-none ring-offset-2 active:scale-95 ${config.focusRing}` : '',
    autoDetected ? 'ring-2 ring-purple-400 shadow-xl' : '',
    'transform hover:rotate-1',
    className
  ].filter(Boolean).join(' ');

  const badgeContent = (
    <>
      <span className="flex-shrink-0">{config.icon}</span>
      <span className="font-black tracking-wide text-sm uppercase">{config.label}</span>
      {autoDetected && (
        <span 
          className="text-xs opacity-80 ml-1"
          title="Classification automatique"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
          </svg>
        </span>
      )}
      {confidenceScore && confidenceScore > 0.8 && (
        <span 
          className="text-xs opacity-70 ml-1"
          title={`Confiance: ${Math.round(confidenceScore * 100)}%`}
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </span>
      )}
      {interactive && (
        <span className="text-xs opacity-60 ml-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
        </span>
      )}
    </>
  );

  if (interactive && onClick) {
    return (
      <button
        onClick={onClick}
        className={badgeClasses}
        title={tooltipText}
      >
        {badgeContent}
      </button>
    );
  }

  return (
    <span className={badgeClasses} title={tooltipText}>
      {badgeContent}
    </span>
  );
}

// Composant pour afficher plusieurs badges de type
interface ExpenseTypeBadgesProps {
  types: ('fixed' | 'variable')[];
  onTypeClick?: (type: 'fixed' | 'variable') => void;
  className?: string;
}

export function ExpenseTypeBadges({ types, onTypeClick, className = '' }: ExpenseTypeBadgesProps) {
  if (!types || types.length === 0) return null;

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {types.map((type, index) => (
        <ExpenseTypeBadge
          key={`${type}-${index}`}
          type={type}
          interactive={!!onTypeClick}
          onClick={onTypeClick ? () => onTypeClick(type) : undefined}
        />
      ))}
    </div>
  );
}

// Composant pour les transactions en attente de classification
interface PendingClassificationBadgeProps {
  size?: 'sm' | 'md';
  interactive?: boolean;
  onClick?: () => void;
  className?: string;
  hasAISuggestion?: boolean;
}

export function PendingClassificationBadge({ 
  size = 'sm',
  interactive = false,
  onClick,
  className = '',
  hasAISuggestion = false
}: PendingClassificationBadgeProps) {
  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base'
  };

  const badgeClasses = [
    'inline-flex items-center gap-2 font-semibold border-2 rounded-full transition-all duration-200 select-none',
    sizeClasses[size],
    hasAISuggestion 
      ? 'bg-purple-50 text-purple-700 border-purple-300 hover:bg-purple-100 hover:shadow-md hover:scale-105 shadow-sm'
      : 'bg-slate-50 text-slate-600 border-slate-300 hover:bg-slate-100 hover:shadow-md hover:scale-105',
    interactive ? `cursor-pointer focus:outline-none focus:ring-4 focus:ring-offset-2 active:scale-95 ${
      hasAISuggestion ? 'focus:ring-purple-500' : 'focus:ring-slate-500'
    }` : '',
    hasAISuggestion ? 'ring-1 ring-purple-200 animate-pulse' : '',
    className
  ].filter(Boolean).join(' ');

  const badgeContent = (
    <>
      <span className={size === 'sm' ? 'text-sm' : 'text-base'}>
        {hasAISuggestion ? '⚠️' : '⏳'}
      </span>
      <span className="font-medium">
        {hasAISuggestion ? 'Suggestion IA' : 'À classifier'}
      </span>
      {interactive && (
        <span className="text-xs opacity-50">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <path d="M5 7l2-2-2-2-.5.5L6 5l-1.5 1.5L5 7z"/>
          </svg>
        </span>
      )}
    </>
  );

  const tooltipText = hasAISuggestion 
    ? 'IA a une suggestion - Cliquer pour voir'
    : 'Transaction en attente de classification - Cliquer pour analyser avec l\'IA';

  if (interactive && onClick) {
    return (
      <button
        onClick={onClick}
        className={badgeClasses}
        title={tooltipText}
      >
        {badgeContent}
      </button>
    );
  }

  return (
    <span className={badgeClasses} title={tooltipText}>
      {badgeContent}
    </span>
  );
}