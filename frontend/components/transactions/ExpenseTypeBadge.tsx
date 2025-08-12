'use client';

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
  if (!type) return null;

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm'
  };

  const typeConfig = {
    fixed: {
      icon: '🏠',
      label: 'Fixe',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-700',
      borderColor: 'border-orange-200',
      hoverBg: interactive ? 'hover:bg-orange-100' : '',
      focusRing: 'focus:ring-orange-500'
    },
    variable: {
      icon: '📊',
      label: 'Variable',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700',
      borderColor: 'border-blue-200',
      hoverBg: interactive ? 'hover:bg-blue-100' : '',
      focusRing: 'focus:ring-blue-500'
    }
  };

  const config = typeConfig[type];

  // Déterminer le tooltip
  let tooltipText = `Dépense ${config.label.toLowerCase()}`;
  if (autoDetected && confidenceScore) {
    tooltipText += ` - Auto-détecté (${Math.round(confidenceScore * 100)}%)`;
  }
  if (interactive) {
    tooltipText += ' - Cliquer pour modifier';
  }

  const badgeClasses = [
    'inline-flex items-center gap-1.5 font-medium border rounded-full transition-all duration-200',
    sizeClasses[size],
    config.bgColor,
    config.textColor,
    config.borderColor,
    config.hoverBg,
    interactive ? `cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-1 ${config.focusRing}` : '',
    autoDetected ? 'ring-1 ring-gray-200' : '',
    className
  ].filter(Boolean).join(' ');

  const badgeContent = (
    <>
      <span className={size === 'sm' ? 'text-xs' : 'text-sm'}>{config.icon}</span>
      <span>{config.label}</span>
      {autoDetected && (
        <span 
          className={`text-xs opacity-70 ${size === 'sm' ? 'ml-0' : 'ml-1'}`}
          title="Classification automatique"
        >
          🤖
        </span>
      )}
      {confidenceScore && confidenceScore > 0.8 && (
        <span 
          className="text-xs opacity-60"
          title={`Confiance: ${Math.round(confidenceScore * 100)}%`}
        >
          ✨
        </span>
      )}
      {interactive && (
        <span className="text-xs opacity-50">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <path d="M5 7l2-2-2-2-.5.5L6 5l-1.5 1.5L5 7z"/>
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
      {types.map((type) => (
        <ExpenseTypeBadge
          key={type}
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
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm'
  };

  const badgeClasses = [
    'inline-flex items-center gap-1.5 font-medium border rounded-full transition-all duration-200',
    sizeClasses[size],
    hasAISuggestion 
      ? 'bg-purple-50 text-purple-700 border-purple-300 hover:bg-purple-100 shadow-sm'
      : 'bg-slate-50 text-slate-600 border-slate-300 hover:bg-slate-100',
    interactive ? `cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-1 ${
      hasAISuggestion ? 'focus:ring-purple-500' : 'focus:ring-slate-500'
    }` : '',
    hasAISuggestion ? 'ring-1 ring-purple-200 animate-pulse' : '',
    className
  ].filter(Boolean).join(' ');

  const badgeContent = (
    <>
      <span className={size === 'sm' ? 'text-xs' : 'text-sm'}>
        {hasAISuggestion ? '⚠️' : '⏳'}
      </span>
      <span>
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