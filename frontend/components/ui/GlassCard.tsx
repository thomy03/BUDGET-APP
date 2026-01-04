'use client';

import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'gradient' | 'hover';
  gradient?: 'green' | 'blue' | 'orange' | 'purple' | 'red';
  onClick?: () => void;
}

/**
 * GlassCard - Composant avec effet glassmorphism
 * Design moderne avec fond semi-transparent et backdrop-filter blur
 */
export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  variant = 'default',
  gradient,
  onClick
}) => {
  const baseStyles = 'rounded-2xl border transition-all duration-300';

  const getVariantStyles = () => {
    switch (variant) {
      case 'gradient':
        return 'bg-white/95 backdrop-blur-xl border-white/30 shadow-lg';
      case 'hover':
        return 'bg-white/95 backdrop-blur-xl border-white/30 hover:shadow-xl hover:scale-[1.02] cursor-pointer';
      default:
        return 'bg-white/95 backdrop-blur-xl border-white/30';
    }
  };

  const getGradientStyles = () => {
    if (!gradient) return '';
    const gradients: Record<string, string> = {
      green: 'bg-gradient-to-br from-green-500 to-emerald-600',
      blue: 'bg-gradient-to-br from-blue-500 to-indigo-600',
      orange: 'bg-gradient-to-br from-orange-500 to-red-500',
      purple: 'bg-gradient-to-br from-purple-500 to-pink-500',
      red: 'bg-gradient-to-br from-red-500 to-rose-600'
    };
    return `${gradients[gradient]} text-white border-transparent`;
  };

  const finalStyles = gradient
    ? `${baseStyles} ${getGradientStyles()}`
    : `${baseStyles} ${getVariantStyles()}`;

  return (
    <div
      className={`${finalStyles} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

/**
 * KPICard - Carte KPI avec icone et gradient
 */
interface KPICardProps {
  title: string;
  value: string | number;
  icon: string;
  gradient: 'green' | 'blue' | 'orange' | 'purple' | 'red';
  subtitle?: string;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'stable';
  };
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  icon,
  gradient,
  subtitle,
  trend,
  onClick
}) => {
  const iconGradients: Record<string, string> = {
    green: 'bg-gradient-to-r from-green-500 to-emerald-500',
    blue: 'bg-gradient-to-r from-blue-500 to-indigo-500',
    orange: 'bg-gradient-to-r from-orange-500 to-red-500',
    purple: 'bg-gradient-to-r from-purple-500 to-pink-500',
    red: 'bg-gradient-to-r from-red-500 to-rose-500'
  };

  const valueColors: Record<string, string> = {
    green: 'text-green-600',
    blue: 'text-blue-600',
    orange: 'text-orange-600',
    purple: 'text-purple-600',
    red: 'text-red-600'
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.direction === 'up') return '↑';
    if (trend.direction === 'down') return '↓';
    return '→';
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.direction === 'up') return 'text-green-500';
    if (trend.direction === 'down') return 'text-red-500';
    return 'text-gray-500';
  };

  return (
    <GlassCard
      variant="hover"
      className="p-6"
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className={`text-2xl font-bold ${valueColors[gradient]}`}>
            {typeof value === 'number' ? value.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }) : value}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
          {trend && (
            <p className={`text-xs mt-1 ${getTrendColor()}`}>
              {getTrendIcon()} {Math.abs(trend.value)}% vs mois dernier
            </p>
          )}
        </div>
        <div className={`w-12 h-12 ${iconGradients[gradient]} rounded-xl flex items-center justify-center text-xl`}>
          {icon}
        </div>
      </div>
    </GlassCard>
  );
};

export default GlassCard;
