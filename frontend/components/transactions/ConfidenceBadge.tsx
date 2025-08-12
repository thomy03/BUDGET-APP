'use client';

interface ConfidenceBadgeProps {
  confidence?: number;
  isAutoDetected?: boolean;
  isLoading?: boolean;
  className?: string;
}

export function ConfidenceBadge({ 
  confidence, 
  isAutoDetected = false, 
  isLoading = false,
  className = '' 
}: ConfidenceBadgeProps) {
  // Si pas de classification automatique, retourner un placeholder
  if (!isAutoDetected && !isLoading) {
    return (
      <div className={`text-center ${className}`}>
        <span className="text-xs text-gray-400">--</span>
      </div>
    );
  }

  // État de chargement
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
      </div>
    );
  }

  if (!confidence) {
    return (
      <div className={`text-center ${className}`}>
        <span className="text-xs text-gray-400">N/A</span>
      </div>
    );
  }

  const percentage = Math.round(confidence * 100);
  
  // Déterminer les couleurs selon le niveau de confiance
  let colorClass = '';
  let bgClass = '';
  let borderClass = '';
  let progressClass = '';
  
  if (percentage >= 90) {
    colorClass = 'text-green-700';
    bgClass = 'bg-green-50';
    borderClass = 'border-green-200';
    progressClass = 'bg-green-500';
  } else if (percentage >= 70) {
    colorClass = 'text-orange-700';
    bgClass = 'bg-orange-50';
    borderClass = 'border-orange-200';
    progressClass = 'bg-orange-500';
  } else {
    colorClass = 'text-red-700';
    bgClass = 'bg-red-50';
    borderClass = 'border-red-200';
    progressClass = 'bg-red-500';
  }

  // Texte du tooltip
  const tooltipText = `Confiance IA: ${percentage}% - ${
    percentage >= 90 
      ? 'Très fiable' 
      : percentage >= 70 
        ? 'Fiable' 
        : 'Peu fiable'
  }`;

  return (
    <div className={`flex flex-col items-center gap-1 ${className}`} title={tooltipText}>
      {/* Pourcentage */}
      <div className={`
        inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold border
        ${bgClass} ${colorClass} ${borderClass}
      `}>
        <span className="mr-1">🤖</span>
        <span>{percentage}%</span>
      </div>

      {/* Barre de progression mini */}
      <div className="w-8 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ${progressClass}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
}

// Version compacte pour usage dans les tables denses
interface CompactConfidenceBadgeProps {
  confidence?: number;
  isAutoDetected?: boolean;
  isLoading?: boolean;
  showProgressBar?: boolean;
}

export function CompactConfidenceBadge({ 
  confidence, 
  isAutoDetected = false, 
  isLoading = false,
  showProgressBar = true
}: CompactConfidenceBadgeProps) {
  if (!isAutoDetected && !isLoading) {
    return <span className="text-xs text-gray-400">--</span>;
  }

  if (isLoading) {
    return (
      <div className="w-4 h-4 animate-spin rounded-full border border-blue-600 border-t-transparent mx-auto"></div>
    );
  }

  if (!confidence) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  const percentage = Math.round(confidence * 100);
  
  let colorClass = '';
  let progressClass = '';
  
  if (percentage >= 90) {
    colorClass = 'text-green-600';
    progressClass = 'bg-green-500';
  } else if (percentage >= 70) {
    colorClass = 'text-orange-600';
    progressClass = 'bg-orange-500';
  } else {
    colorClass = 'text-red-600';
    progressClass = 'bg-red-500';
  }

  const tooltipText = `Confiance IA: ${percentage}%`;

  return (
    <div className="flex flex-col items-center gap-0.5" title={tooltipText}>
      <span className={`text-xs font-medium ${colorClass}`}>
        {percentage}%
      </span>
      {showProgressBar && (
        <div className="w-6 h-1 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-300 ${progressClass}`}
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
      )}
    </div>
  );
}

export default ConfidenceBadge;