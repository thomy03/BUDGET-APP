'use client';

import { validateRequiredProps } from '../../types/defensive-programming';

export type TagSource = 'ai_pattern' | 'web_research' | 'manual' | 'modified';

interface TagSourceBadgeProps {
  source: TagSource;
  size?: 'xs' | 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

export function TagSourceBadge({ 
  source, 
  size = 'sm',
  showLabel = true,
  className = ''
}: TagSourceBadgeProps) {
  // DEFENSIVE PROGRAMMING: Validate props
  if (!validateRequiredProps({ source }, ['source'], 'TagSourceBadge')) {
    return null;
  }

  const sizeClasses = {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm'
  };

  const sourceConfig = {
    ai_pattern: {
      icon: '🤖',
      label: 'IA Pattern',
      bgColor: 'bg-emerald-100',
      textColor: 'text-emerald-800',
      borderColor: 'border-emerald-300',
      description: 'Classification automatique par reconnaissance de motifs'
    },
    web_research: {
      icon: '🌐',
      label: 'Recherche Web',
      bgColor: 'bg-cyan-100',
      textColor: 'text-cyan-800',
      borderColor: 'border-cyan-300',
      description: 'Classification enrichie par recherche web'
    },
    manual: {
      icon: '👤',
      label: 'Manuel',
      bgColor: 'bg-slate-100',
      textColor: 'text-slate-700',
      borderColor: 'border-slate-300',
      description: 'Tag créé manuellement par l\'utilisateur'
    },
    modified: {
      icon: '🔄',
      label: 'Modifié',
      bgColor: 'bg-purple-100',
      textColor: 'text-purple-800',
      borderColor: 'border-purple-300',
      description: 'Suggestion IA modifiée par l\'utilisateur'
    }
  };

  const config = sourceConfig[source];
  
  if (!config) {
    console.warn(`TagSourceBadge: Invalid source "${source}"`);
    return null;
  }

  const badgeClasses = [
    'inline-flex items-center gap-1.5 font-medium border rounded-full transition-all duration-200',
    sizeClasses[size],
    config.bgColor,
    config.textColor,
    config.borderColor,
    'hover:shadow-sm',
    className
  ].filter(Boolean).join(' ');

  return (
    <span 
      className={badgeClasses} 
      title={config.description}
    >
      <span className="flex-shrink-0">{config.icon}</span>
      {showLabel && (
        <span className="font-semibold">{config.label}</span>
      )}
    </span>
  );
}

// Composant pour afficher multiple sources
interface TagSourceBadgesProps {
  sources: TagSource[];
  size?: 'xs' | 'sm' | 'md';
  showLabels?: boolean;
  className?: string;
  maxDisplay?: number;
}

export function TagSourceBadges({ 
  sources, 
  size = 'sm',
  showLabels = true,
  className = '',
  maxDisplay = 3
}: TagSourceBadgesProps) {
  if (!sources || sources.length === 0) return null;

  const displaySources = sources.slice(0, maxDisplay);
  const remainingCount = sources.length - maxDisplay;

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {displaySources.map((source, index) => (
        <TagSourceBadge
          key={`${source}-${index}`}
          source={source}
          size={size}
          showLabel={showLabels}
        />
      ))}
      {remainingCount > 0 && (
        <span className="text-xs text-gray-500 ml-1">
          +{remainingCount}
        </span>
      )}
    </div>
  );
}