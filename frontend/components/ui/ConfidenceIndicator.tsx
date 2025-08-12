'use client';

import { validateRequiredProps } from '../../types/defensive-programming';

interface ConfidenceIndicatorProps {
  confidence: number; // 0.0 to 1.0
  size?: 'xs' | 'sm' | 'md' | 'lg';
  showPercentage?: boolean;
  showLabel?: boolean;
  variant?: 'badge' | 'bar' | 'circle';
  className?: string;
}

export function ConfidenceIndicator({ 
  confidence, 
  size = 'sm',
  showPercentage = true,
  showLabel = false,
  variant = 'badge',
  className = ''
}: ConfidenceIndicatorProps) {
  // DEFENSIVE PROGRAMMING: Validate props
  if (!validateRequiredProps({ confidence }, ['confidence'], 'ConfidenceIndicator')) {
    return null;
  }

  // Validate confidence range
  const normalizedConfidence = Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(normalizedConfidence * 100);

  // Determine confidence level and colors
  const getConfidenceLevel = (conf: number) => {
    if (conf >= 0.8) return 'high';
    if (conf >= 0.5) return 'medium';
    return 'low';
  };

  const level = getConfidenceLevel(normalizedConfidence);

  const levelConfig = {
    high: {
      bgColor: 'bg-green-100',
      textColor: 'text-green-800',
      borderColor: 'border-green-300',
      fillColor: 'bg-green-500',
      icon: '✓',
      label: 'Confiance élevée'
    },
    medium: {
      bgColor: 'bg-yellow-100',
      textColor: 'text-yellow-800',
      borderColor: 'border-yellow-300',
      fillColor: 'bg-yellow-500',
      icon: '⚠',
      label: 'Confiance moyenne'
    },
    low: {
      bgColor: 'bg-red-100',
      textColor: 'text-red-800',
      borderColor: 'border-red-300',
      fillColor: 'bg-red-500',
      icon: '⚠',
      label: 'Confiance faible'
    }
  };

  const config = levelConfig[level];

  const sizeClasses = {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base'
  };

  const barSizes = {
    xs: 'h-1',
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3'
  };

  const circleSizes = {
    xs: 'w-4 h-4',
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  if (variant === 'badge') {
    const badgeClasses = [
      'inline-flex items-center gap-1.5 font-medium border rounded-full transition-all duration-200',
      sizeClasses[size],
      config.bgColor,
      config.textColor,
      config.borderColor,
      className
    ].filter(Boolean).join(' ');

    return (
      <span 
        className={badgeClasses}
        title={`${config.label}: ${percentage}%`}
      >
        <span className="flex-shrink-0">{config.icon}</span>
        {showPercentage && <span className="font-bold">{percentage}%</span>}
        {showLabel && <span>{config.label}</span>}
      </span>
    );
  }

  if (variant === 'bar') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className={`flex-1 bg-gray-200 rounded-full overflow-hidden ${barSizes[size]}`}>
          <div 
            className={`${config.fillColor} transition-all duration-500 ${barSizes[size]}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {showPercentage && (
          <span className={`text-xs font-medium ${config.textColor}`}>
            {percentage}%
          </span>
        )}
      </div>
    );
  }

  if (variant === 'circle') {
    const strokeDasharray = 2 * Math.PI * 8; // radius = 8
    const strokeDashoffset = strokeDasharray * (1 - normalizedConfidence);

    return (
      <div className={`relative inline-flex items-center justify-center ${className}`}>
        <svg className={circleSizes[size]} viewBox="0 0 20 20">
          {/* Background circle */}
          <circle
            cx="10"
            cy="10"
            r="8"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx="10"
            cy="10"
            r="8"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            className={config.textColor}
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: '50% 50%',
              transition: 'stroke-dashoffset 0.5s ease'
            }}
          />
        </svg>
        {showPercentage && (
          <span className={`absolute text-xs font-bold ${config.textColor}`}>
            {percentage}
          </span>
        )}
      </div>
    );
  }

  return null;
}

// Composant pour afficher une liste de niveaux de confiance
interface ConfidenceLegendProps {
  className?: string;
}

export function ConfidenceLegend({ className = '' }: ConfidenceLegendProps) {
  const levels = [
    { level: 'high', min: 80, label: 'Confiance élevée', color: 'text-green-600' },
    { level: 'medium', min: 50, label: 'Confiance moyenne', color: 'text-yellow-600' },
    { level: 'low', min: 0, label: 'Confiance faible', color: 'text-red-600' }
  ];

  return (
    <div className={`space-y-2 ${className}`}>
      <h4 className="text-sm font-medium text-gray-700">Niveaux de confiance</h4>
      <div className="space-y-1">
        {levels.map(({ level, min, label, color }) => (
          <div key={level} className="flex items-center gap-2 text-xs">
            <ConfidenceIndicator 
              confidence={min === 80 ? 0.9 : min === 50 ? 0.65 : 0.3} 
              size="xs" 
              showPercentage={false}
              variant="circle"
            />
            <span className={`font-medium ${color}`}>{label}</span>
            <span className="text-gray-500">
              ({min === 0 ? '<50%' : `${min}%+`})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Composant pour les statistiques de confiance globales
interface ConfidenceStatsProps {
  stats: {
    high: number;
    medium: number;
    low: number;
    total: number;
  };
  className?: string;
}

export function ConfidenceStats({ stats, className = '' }: ConfidenceStatsProps) {
  const { high, medium, low, total } = stats;
  
  if (total === 0) return null;

  const highPercentage = Math.round((high / total) * 100);
  const mediumPercentage = Math.round((medium / total) * 100);
  const lowPercentage = Math.round((low / total) * 100);

  return (
    <div className={`space-y-3 ${className}`}>
      <h4 className="text-sm font-semibold text-gray-700">Répartition des niveaux de confiance</h4>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div className="h-full flex">
          <div 
            className="bg-green-500 transition-all duration-500"
            style={{ width: `${highPercentage}%` }}
          />
          <div 
            className="bg-yellow-500 transition-all duration-500"
            style={{ width: `${mediumPercentage}%` }}
          />
          <div 
            className="bg-red-500 transition-all duration-500"
            style={{ width: `${lowPercentage}%` }}
          />
        </div>
      </div>

      {/* Legend */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-green-700 font-medium">Élevée</span>
          <span className="text-gray-500">({high})</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-yellow-500 rounded-full" />
          <span className="text-yellow-700 font-medium">Moyenne</span>
          <span className="text-gray-500">({medium})</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-red-500 rounded-full" />
          <span className="text-red-700 font-medium">Faible</span>
          <span className="text-gray-500">({low})</span>
        </div>
      </div>
    </div>
  );
}