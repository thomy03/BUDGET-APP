'use client';

interface TagClassificationBadgeProps {
  expenseType: 'fixed' | 'variable' | null;
  confidence?: number;
  isAutoDetected?: boolean;
  isManualOverride?: boolean;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
  showConfidenceStars?: boolean;
  className?: string;
}

/**
 * Badge spécialisé pour la classification des tags avec indicateurs visuels
 * 
 * Indicateurs visuels selon les spécifications:
 * - Badge couleur : 🟢 Fixe | 🔵 Variable | 🟡 IA
 * - Icône confiance : ⭐⭐⭐ (haute) | ⭐⭐ (moyenne) | ⭐ (faible)
 * - Historique des décisions utilisateur
 */
export function TagClassificationBadge({
  expenseType,
  confidence = 0,
  isAutoDetected = false,
  isManualOverride = false,
  onClick,
  size = 'sm',
  showConfidenceStars = true,
  className = ''
}: TagClassificationBadgeProps) {
  if (!expenseType) {
    return null;
  }

  // Configuration des tailles
  const sizeConfig = {
    sm: {
      padding: 'px-2 py-1',
      text: 'text-xs',
      icon: 'text-xs',
      gap: 'gap-1'
    },
    md: {
      padding: 'px-3 py-1.5',
      text: 'text-sm',
      icon: 'text-sm',
      gap: 'gap-1.5'
    },
    lg: {
      padding: 'px-4 py-2',
      text: 'text-base',
      icon: 'text-base',
      gap: 'gap-2'
    }
  };

  // Configuration des types selon les spécifications (🟢 Fixe | 🔵 Variable)
  const typeConfig = {
    fixed: {
      icon: '🏠',
      label: 'Fixe',
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      borderColor: 'border-green-200',
      ringColor: 'ring-green-500',
      hoverBg: 'hover:bg-green-100',
      // 🟢 Couleur selon specs
      badgeColor: '🟢'
    },
    variable: {
      icon: '📊',
      label: 'Variable',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700',
      borderColor: 'border-blue-200',
      ringColor: 'ring-blue-500',
      hoverBg: 'hover:bg-blue-100',
      // 🔵 Couleur selon specs
      badgeColor: '🔵'
    }
  };

  const config = typeConfig[expenseType];
  const sizes = sizeConfig[size];

  // Icônes de confiance selon les spécifications
  const getConfidenceStars = (confidenceScore: number) => {
    if (confidenceScore >= 0.8) return '⭐⭐⭐'; // Haute
    if (confidenceScore >= 0.6) return '⭐⭐';   // Moyenne
    if (confidenceScore > 0) return '⭐';        // Faible
    return '';
  };

  // État du badge selon l'historique
  const getBadgeState = () => {
    if (isManualOverride) {
      return {
        indicator: '👤', // Décision manuelle utilisateur
        tooltip: 'Classification manuelle par l\'utilisateur',
        ringColor: 'ring-purple-500',
        specialBg: 'bg-purple-50 border-purple-200 text-purple-700'
      };
    }
    if (isAutoDetected) {
      return {
        indicator: '🤖', // IA automatique - 🟡 selon specs
        tooltip: `Classification automatique IA (${Math.round(confidence * 100)}%)`,
        ringColor: 'ring-yellow-500',
        specialBg: 'bg-yellow-50 border-yellow-200 text-yellow-700'
      };
    }
    return {
      indicator: '',
      tooltip: `Dépense ${config.label.toLowerCase()}`,
      ringColor: config.ringColor,
      specialBg: `${config.bgColor} ${config.borderColor} ${config.textColor}`
    };
  };

  const badgeState = getBadgeState();

  const badgeClasses = [
    'inline-flex items-center font-medium border rounded-full transition-all duration-200',
    sizes.padding,
    sizes.text,
    sizes.gap,
    // Utiliser l'état spécial ou la configuration par défaut
    isAutoDetected || isManualOverride ? badgeState.specialBg : `${config.bgColor} ${config.borderColor} ${config.textColor}`,
    onClick ? `cursor-pointer ${config.hoverBg} focus:outline-none focus:ring-2 focus:ring-offset-1 ${badgeState.ringColor}` : '',
    className
  ].filter(Boolean).join(' ');

  const content = (
    <>
      {/* Icône principale */}
      <span className={sizes.icon}>{config.icon}</span>
      
      {/* Indicateur de couleur selon specs */}
      <span className={sizes.icon}>{config.badgeColor}</span>
      
      {/* Label */}
      <span className="font-semibold">{config.label}</span>
      
      {/* Indicateur d'état (IA/Manuel) */}
      {badgeState.indicator && (
        <span 
          className={`${sizes.icon} opacity-80`}
          title={badgeState.tooltip}
        >
          {badgeState.indicator}
        </span>
      )}
      
      {/* Étoiles de confiance */}
      {showConfidenceStars && confidence > 0 && (
        <span 
          className={`${sizes.icon} opacity-70`}
          title={`Confiance: ${Math.round(confidence * 100)}%`}
        >
          {getConfidenceStars(confidence)}
        </span>
      )}
      
      {/* Indicateur de pourcentage pour haute confiance */}
      {confidence >= 0.9 && (
        <span className="text-xs font-bold opacity-60">
          {Math.round(confidence * 100)}%
        </span>
      )}
      
      {/* Flèche si cliquable */}
      {onClick && (
        <span className="opacity-50">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" className={sizes.icon}>
            <path d="M3 2l2 3-2 3V2z"/>
          </svg>
        </span>
      )}
    </>
  );

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className={badgeClasses}
        title={badgeState.tooltip}
      >
        {content}
      </button>
    );
  }

  return (
    <span 
      className={badgeClasses}
      title={badgeState.tooltip}
    >
      {content}
    </span>
  );
}

/**
 * Version compacte du badge pour les tableaux
 */
export function CompactTagClassificationBadge(
  props: Omit<TagClassificationBadgeProps, 'size' | 'showConfidenceStars'>
) {
  return (
    <TagClassificationBadge
      {...props}
      size="sm"
      showConfidenceStars={false}
    />
  );
}

/**
 * Badge avec historique des décisions pour les settings
 */
export function HistoryTagClassificationBadge(
  props: TagClassificationBadgeProps & {
    decisionHistory?: Array<{
      date: string;
      decision: 'ai' | 'manual';
      confidence?: number;
    }>;
  }
) {
  const { decisionHistory, ...badgeProps } = props;

  // Logique d'affichage de l'historique
  const hasMultipleDecisions = decisionHistory && decisionHistory.length > 1;
  const lastDecision = decisionHistory?.[decisionHistory.length - 1];

  return (
    <div className="flex items-center gap-2">
      <TagClassificationBadge {...badgeProps} />
      
      {hasMultipleDecisions && (
        <span 
          className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full"
          title={`${decisionHistory.length} modifications historiques`}
        >
          📊 {decisionHistory.length}x
        </span>
      )}
      
      {lastDecision && (
        <span 
          className="text-xs text-gray-400"
          title={`Dernière modification: ${lastDecision.date}`}
        >
          {lastDecision.decision === 'manual' ? '👤' : '🤖'}
        </span>
      )}
    </div>
  );
}

export default TagClassificationBadge;