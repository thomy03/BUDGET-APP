'use client';

import React from 'react';

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

/**
 * Animation fade-in fluide pour l'apparition des éléments
 */
export const FadeIn: React.FC<FadeInProps> = ({ 
  children, 
  delay = 0, 
  duration = 300,
  className = '' 
}) => {
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`
        transition-all ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
        ${className}
      `}
      style={{
        transitionDuration: `${duration}ms`
      }}
    >
      {children}
    </div>
  );
};

interface CountUpProps {
  value: number;
  duration?: number;
  formatter?: (value: number) => string;
  className?: string;
}

/**
 * Animation count-up pour les montants financiers
 */
export const CountUp: React.FC<CountUpProps> = ({ 
  value, 
  duration = 800,
  formatter = (v) => v.toFixed(0),
  className = '' 
}) => {
  const [displayValue, setDisplayValue] = React.useState(0);

  React.useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      // Easing function pour une animation plus naturelle
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      setDisplayValue(value * easeOutQuart);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [value, duration]);

  return (
    <span className={className}>
      {formatter(displayValue)}
    </span>
  );
};

interface ProgressBarProps {
  value: number;
  max?: number;
  height?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'danger';
  animated?: boolean;
  showLabel?: boolean;
  className?: string;
}

/**
 * Barre de progression animée avec variantes colorées
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  height = 'md',
  variant = 'default',
  animated = true,
  showLabel = false,
  className = ''
}) => {
  const percentage = Math.min((value / max) * 100, 100);
  
  const getHeightClass = () => {
    switch (height) {
      case 'sm': return 'h-1';
      case 'md': return 'h-2';
      case 'lg': return 'h-3';
      default: return 'h-2';
    }
  };

  const getVariantClass = () => {
    switch (variant) {
      case 'success': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'danger': return 'bg-red-500';
      default: return 'bg-blue-500';
    }
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {showLabel && (
        <div className="flex justify-between text-xs text-gray-600">
          <span>Progression</span>
          <span>{percentage.toFixed(0)}%</span>
        </div>
      )}
      
      <div className={`bg-gray-200 rounded-full ${getHeightClass()}`}>
        <div
          className={`
            ${getVariantClass()} 
            ${getHeightClass()} 
            rounded-full 
            transition-all 
            ${animated ? 'duration-700 ease-out' : 'duration-200'}
          `}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface PulseProps {
  children: React.ReactNode;
  intensity?: 'low' | 'medium' | 'high';
  className?: string;
}

/**
 * Animation pulse pour attirer l'attention
 */
export const Pulse: React.FC<PulseProps> = ({ 
  children, 
  intensity = 'medium',
  className = '' 
}) => {
  const getIntensityClass = () => {
    switch (intensity) {
      case 'low': return 'animate-pulse opacity-90';
      case 'medium': return 'animate-pulse opacity-80';
      case 'high': return 'animate-pulse opacity-70';
      default: return 'animate-pulse opacity-80';
    }
  };

  return (
    <div className={`${getIntensityClass()} ${className}`}>
      {children}
    </div>
  );
};

interface SlideInProps {
  children: React.ReactNode;
  direction?: 'left' | 'right' | 'up' | 'down';
  duration?: number;
  delay?: number;
  className?: string;
}

/**
 * Animation slide-in depuis différentes directions
 */
export const SlideIn: React.FC<SlideInProps> = ({
  children,
  direction = 'up',
  duration = 400,
  delay = 0,
  className = ''
}) => {
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  const getTransformClass = () => {
    if (isVisible) return 'translate-x-0 translate-y-0';
    
    switch (direction) {
      case 'left': return '-translate-x-8';
      case 'right': return 'translate-x-8';
      case 'up': return 'translate-y-8';
      case 'down': return '-translate-y-8';
      default: return 'translate-y-8';
    }
  };

  return (
    <div
      className={`
        transition-all ease-out
        ${isVisible ? 'opacity-100' : 'opacity-0'}
        ${getTransformClass()}
        ${className}
      `}
      style={{
        transitionDuration: `${duration}ms`
      }}
    >
      {children}
    </div>
  );
};

interface ScaleOnHoverProps {
  children: React.ReactNode;
  scale?: number;
  className?: string;
}

/**
 * Animation scale au hover pour les éléments interactifs
 */
export const ScaleOnHover: React.FC<ScaleOnHoverProps> = ({
  children,
  scale = 1.05,
  className = ''
}) => {
  return (
    <div
      className={`
        transition-transform duration-200 ease-out
        hover:scale-${scale === 1.05 ? '105' : '110'}
        ${className}
      `}
    >
      {children}
    </div>
  );
};

// Exports déjà définis dans les composants ci-dessus