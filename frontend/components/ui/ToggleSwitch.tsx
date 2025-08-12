'use client';

import { useState, useEffect } from 'react';

export type ExpenseType = 'variable' | 'fixed';

interface ToggleSwitchProps {
  value: ExpenseType;
  onChange: (type: ExpenseType) => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showLabels?: boolean;
  className?: string;
}

export function ToggleSwitch({
  value,
  onChange,
  disabled = false,
  size = 'md',
  showLabels = true,
  className = ''
}: ToggleSwitchProps) {
  const [isAnimating, setIsAnimating] = useState(false);

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled || isAnimating) return;
    
    setIsAnimating(true);
    const newType = value === 'variable' ? 'fixed' : 'variable';
    
    // Déclencher le changement immédiatement
    onChange(newType);
    
    // Reset animation flag after animation completes
    setTimeout(() => setIsAnimating(false), 300);
  };

  // Size configurations
  const sizeConfig = {
    sm: {
      switch: 'h-6 w-11',
      thumb: 'h-4 w-4',
      translate: value === 'fixed' ? 'translate-x-5' : 'translate-x-1',
      text: 'text-xs',
      icon: 'text-xs',
      gap: 'gap-1'
    },
    md: {
      switch: 'h-7 w-12',
      thumb: 'h-5 w-5',
      translate: value === 'fixed' ? 'translate-x-5' : 'translate-x-1',
      text: 'text-sm',
      icon: 'text-sm',
      gap: 'gap-2'
    },
    lg: {
      switch: 'h-8 w-14',
      thumb: 'h-6 w-6',
      translate: value === 'fixed' ? 'translate-x-6' : 'translate-x-1',
      text: 'text-base',
      icon: 'text-base',
      gap: 'gap-3'
    }
  };

  const config = sizeConfig[size];

  return (
    <div className={`flex items-center ${config.gap} ${className}`}>
      {showLabels && (
        <div className={`flex items-center ${config.gap} ${config.text} font-medium select-none`}>
          <span className={`${config.icon}`}>📊</span>
          <span 
            className={`transition-colors font-semibold ${
              value === 'variable' 
                ? 'text-orange-600' 
                : 'text-gray-500'
            }`}
          >
            Variable
          </span>
        </div>
      )}

      <div className="relative">
        <button
          type="button"
          onClick={handleToggle}
          disabled={disabled}
          className={`
            relative inline-flex ${config.switch} rounded-full p-1 
            transition-all duration-300 ease-in-out 
            focus:outline-none focus:ring-4 focus:ring-offset-2
            border-2 shadow-md
            ${value === 'fixed' 
              ? 'bg-emerald-500 border-emerald-600 focus:ring-emerald-500 hover:bg-emerald-600 hover:border-emerald-700' 
              : 'bg-orange-500 border-orange-600 focus:ring-orange-500 hover:bg-orange-600 hover:border-orange-700'
            }
            ${disabled 
              ? 'opacity-50 cursor-not-allowed' 
              : 'hover:shadow-lg cursor-pointer hover:scale-110 active:scale-95'
            }
            ${isAnimating ? 'scale-110 shadow-xl' : 'scale-100'}
          `}
          aria-label={`Changer le type de dépense à ${value === 'variable' ? 'fixe' : 'variable'}`}
          title={`Cliquer pour changer: ${value === 'variable' ? 'Variable → Fixe' : 'Fixe → Variable'}`}
        >
          <span
            className={`
              ${config.thumb} bg-white rounded-full shadow-lg
              transform transition-transform duration-200 ease-in-out
              ${config.translate}
              flex items-center justify-center
              ${isAnimating ? 'scale-110' : 'scale-100'}
            `}
          >
            <span className={`${config.icon} transition-all duration-200 font-bold`}>
              {value === 'fixed' ? '📌' : '📊'}
            </span>
          </span>
        </button>

        {/* Animation de feedback améliorée */}
        {isAnimating && (
          <div 
            className={`
              absolute inset-0 ${config.switch} rounded-full 
              ${value === 'fixed' ? 'bg-emerald-500' : 'bg-orange-500'}
              opacity-40 animate-ping border-2
              ${value === 'fixed' ? 'border-emerald-600' : 'border-orange-600'}
            `}
          />
        )}
      </div>

      {showLabels && (
        <div className={`flex items-center ${config.gap} ${config.text} font-medium select-none`}>
          <span 
            className={`transition-colors font-semibold ${
              value === 'fixed' 
                ? 'text-emerald-600' 
                : 'text-gray-500'
            }`}
          >
            Fixe
          </span>
          <span className={`${config.icon}`}>📌</span>
        </div>
      )}
    </div>
  );
}

// Composant plus compact pour utilisation dans les tableaux
export function CompactToggleSwitch({
  value,
  onChange,
  disabled = false,
  className = ''
}: Omit<ToggleSwitchProps, 'size' | 'showLabels'>) {
  return (
    <ToggleSwitch
      value={value}
      onChange={onChange}
      disabled={disabled}
      size="sm"
      showLabels={false}
      className={className}
    />
  );
}

export default ToggleSwitch;