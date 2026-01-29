'use client';

import React, { useState } from 'react';
import { Challenge, gamificationApi } from '@/lib/api';

interface ChallengeCardProps {
  challenge: Challenge;
  onJoin?: (challenge: Challenge) => void;
  compact?: boolean;
}

export function ChallengeCard({
  challenge,
  onJoin,
  compact = false
}: ChallengeCardProps) {
  const [isJoining, setIsJoining] = useState(false);

  // Calculate time remaining
  const endDate = new Date(challenge.end_date);
  const now = new Date();
  const daysRemaining = Math.max(0, Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));

  const handleJoin = async () => {
    if (challenge.is_joined || isJoining) return;

    setIsJoining(true);
    try {
      await gamificationApi.joinChallenge(challenge.id);
      if (onJoin) onJoin(challenge);
    } catch (err) {
      console.error('Failed to join challenge:', err);
    } finally {
      setIsJoining(false);
    }
  };

  const typeColors = {
    weekly: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', badge: 'bg-blue-100' },
    monthly: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', badge: 'bg-purple-100' },
    special: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100' }
  };

  const colors = typeColors[challenge.challenge_type] || typeColors.weekly;

  if (compact) {
    return (
      <div className={`${colors.bg} ${colors.border} border rounded-lg p-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">{challenge.icon}</span>
            <div>
              <p className="font-medium text-sm">{challenge.name}</p>
              <p className="text-xs text-gray-500">{daysRemaining}j restants</p>
            </div>
          </div>
          {challenge.is_joined ? (
            <div className="text-right">
              <div className="text-sm font-semibold text-purple-600">
                {Math.round(challenge.progress_percent)}%
              </div>
              {challenge.is_completed && (
                <span className="text-xs text-green-600">Termine</span>
              )}
            </div>
          ) : (
            <button
              onClick={handleJoin}
              disabled={isJoining}
              className="px-3 py-1 text-xs bg-white border border-purple-300 rounded-full text-purple-600 hover:bg-purple-50 disabled:opacity-50"
            >
              {isJoining ? '...' : 'Rejoindre'}
            </button>
          )}
        </div>
        {/* Progress bar */}
        {challenge.is_joined && (
          <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${challenge.is_completed ? 'bg-green-500' : 'bg-purple-500'} transition-all`}
              style={{ width: `${challenge.progress_percent}%` }}
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`${colors.bg} ${colors.border} border rounded-xl p-4 transition-all hover:shadow-md`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-full ${colors.badge} flex items-center justify-center text-2xl`}>
            {challenge.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">{challenge.name}</h3>
              <span className={`px-2 py-0.5 text-xs rounded-full ${colors.badge} ${colors.text}`}>
                {challenge.challenge_type === 'weekly' ? 'Semaine' :
                 challenge.challenge_type === 'monthly' ? 'Mois' : 'Special'}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-0.5">{challenge.description}</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold text-purple-600">+{challenge.reward_points}</span>
          <p className="text-xs text-gray-500">pts</p>
        </div>
      </div>

      {/* Goal details */}
      <div className="mt-4 flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1 text-gray-600">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Objectif: {challenge.goal_value} {challenge.goal_category || ''}</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{daysRemaining} jours restants</span>
        </div>
      </div>

      {/* Progress section */}
      {challenge.is_joined && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-600">Progression</span>
            <span className="text-sm font-semibold">
              {challenge.progress.toFixed(0)} / {challenge.goal_value}
            </span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${challenge.is_completed ? 'bg-green-500' : 'bg-gradient-to-r from-purple-400 to-purple-600'}`}
              style={{ width: `${Math.min(challenge.progress_percent, 100)}%` }}
            />
          </div>
          {challenge.is_completed && (
            <p className="mt-2 text-sm text-green-600 font-medium flex items-center gap-1">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Challenge termine! +{challenge.reward_points} points
            </p>
          )}
        </div>
      )}

      {/* Join button */}
      {!challenge.is_joined && (
        <button
          onClick={handleJoin}
          disabled={isJoining}
          className="mt-4 w-full py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isJoining ? 'Inscription...' : 'Rejoindre le challenge'}
        </button>
      )}
    </div>
  );
}

// List of challenges
interface ChallengeListProps {
  challenges: Challenge[];
  compact?: boolean;
  onChallengeJoin?: (challenge: Challenge) => void;
}

export function ChallengeList({
  challenges,
  compact = false,
  onChallengeJoin
}: ChallengeListProps) {
  if (challenges.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <span className="text-4xl">🎯</span>
        <p className="mt-2">Aucun challenge actif pour le moment</p>
      </div>
    );
  }

  return (
    <div className={compact ? 'space-y-2' : 'space-y-4'}>
      {challenges.map((challenge) => (
        <ChallengeCard
          key={challenge.id}
          challenge={challenge}
          compact={compact}
          onJoin={onChallengeJoin}
        />
      ))}
    </div>
  );
}

export default ChallengeCard;
