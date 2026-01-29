'use client';

import React from 'react';
import { Achievement } from '@/lib/api';

interface AchievementBadgeProps {
  achievement: Achievement;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
  onClick?: () => void;
}

const tierColors = {
  bronze: {
    bg: 'bg-amber-100',
    border: 'border-amber-300',
    text: 'text-amber-800',
    glow: 'shadow-amber-200'
  },
  silver: {
    bg: 'bg-gray-100',
    border: 'border-gray-300',
    text: 'text-gray-700',
    glow: 'shadow-gray-200'
  },
  gold: {
    bg: 'bg-yellow-100',
    border: 'border-yellow-400',
    text: 'text-yellow-800',
    glow: 'shadow-yellow-300'
  },
  platinum: {
    bg: 'bg-purple-100',
    border: 'border-purple-400',
    text: 'text-purple-800',
    glow: 'shadow-purple-300'
  }
};

const sizeClasses = {
  sm: {
    container: 'w-12 h-12',
    icon: 'text-xl',
    padding: 'p-2'
  },
  md: {
    container: 'w-16 h-16',
    icon: 'text-2xl',
    padding: 'p-3'
  },
  lg: {
    container: 'w-20 h-20',
    icon: 'text-3xl',
    padding: 'p-4'
  }
};

export function AchievementBadge({
  achievement,
  size = 'md',
  showDetails = false,
  onClick
}: AchievementBadgeProps) {
  const tier = tierColors[achievement.tier] || tierColors.bronze;
  const sizeClass = sizeClasses[size];

  const isEarned = achievement.is_earned;
  const hasProgress = !isEarned && achievement.progress > 0;

  return (
    <div
      className={`inline-flex flex-col items-center ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      {/* Badge Circle */}
      <div className="relative">
        <div
          className={`
            ${sizeClass.container} ${sizeClass.padding}
            ${isEarned ? tier.bg : 'bg-gray-200'}
            ${isEarned ? tier.border : 'border-gray-300'}
            border-2 rounded-full
            flex items-center justify-center
            transition-all duration-300
            ${isEarned ? `shadow-lg ${tier.glow}` : 'opacity-60 grayscale'}
            ${onClick ? 'hover:scale-110' : ''}
          `}
        >
          <span className={`${sizeClass.icon} ${isEarned ? '' : 'opacity-50'}`}>
            {achievement.icon}
          </span>
        </div>

        {/* Progress ring for partial progress */}
        {hasProgress && (
          <svg
            className="absolute inset-0"
            viewBox="0 0 36 36"
          >
            <path
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#8b5cf6"
              strokeWidth="3"
              strokeDasharray={`${achievement.progress}, 100`}
              strokeLinecap="round"
            />
          </svg>
        )}

        {/* Earned checkmark */}
        {isEarned && (
          <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center border-2 border-white">
            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
        )}

        {/* Points badge */}
        {isEarned && size !== 'sm' && (
          <div className="absolute -top-1 -right-1 bg-purple-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
            +{achievement.points}
          </div>
        )}
      </div>

      {/* Details */}
      {showDetails && (
        <div className="mt-2 text-center max-w-[100px]">
          <p className={`text-xs font-semibold ${isEarned ? tier.text : 'text-gray-500'} truncate`}>
            {achievement.name}
          </p>
          {size === 'lg' && (
            <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
              {achievement.description}
            </p>
          )}
          {hasProgress && (
            <p className="text-xs text-purple-500 mt-0.5">
              {Math.round(achievement.progress)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// Grid of achievements
interface AchievementGridProps {
  achievements: Achievement[];
  size?: 'sm' | 'md' | 'lg';
  maxDisplay?: number;
  showAll?: boolean;
  onAchievementClick?: (achievement: Achievement) => void;
}

export function AchievementGrid({
  achievements,
  size = 'md',
  maxDisplay = 6,
  showAll = false,
  onAchievementClick
}: AchievementGridProps) {
  const displayed = showAll ? achievements : achievements.slice(0, maxDisplay);
  const remaining = achievements.length - maxDisplay;

  return (
    <div className="flex flex-wrap gap-3 items-center">
      {displayed.map((ach) => (
        <AchievementBadge
          key={ach.id}
          achievement={ach}
          size={size}
          showDetails={size !== 'sm'}
          onClick={onAchievementClick ? () => onAchievementClick(ach) : undefined}
        />
      ))}
      {!showAll && remaining > 0 && (
        <div className="w-12 h-12 rounded-full bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center">
          <span className="text-sm text-gray-500 font-medium">+{remaining}</span>
        </div>
      )}
    </div>
  );
}

// Achievement unlock notification
interface AchievementUnlockProps {
  achievement: Achievement;
  onClose: () => void;
}

export function AchievementUnlockNotification({
  achievement,
  onClose
}: AchievementUnlockProps) {
  const tier = tierColors[achievement.tier] || tierColors.bronze;

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/50 animate-fade-in">
      <div className={`
        ${tier.bg} ${tier.border}
        border-4 rounded-2xl p-6 shadow-2xl
        transform animate-bounce-in
        max-w-sm mx-4
      `}>
        <div className="text-center">
          <div className="text-5xl mb-3">{achievement.icon}</div>
          <h3 className={`text-lg font-bold ${tier.text}`}>
            Badge Debloque!
          </h3>
          <p className="text-xl font-semibold mt-1">{achievement.name}</p>
          <p className="text-sm text-gray-600 mt-2">{achievement.description}</p>
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className="text-2xl font-bold text-purple-600">+{achievement.points}</span>
            <span className="text-sm text-gray-500">points</span>
          </div>
          <button
            onClick={onClose}
            className={`
              mt-4 px-6 py-2 rounded-full
              ${tier.bg} ${tier.border} border-2
              ${tier.text} font-semibold
              hover:shadow-lg transition-all
            `}
          >
            Super!
          </button>
        </div>
      </div>
    </div>
  );
}

export default AchievementBadge;
