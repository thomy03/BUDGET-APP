'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { gamificationApi, Achievement, Challenge, UserStats } from '@/lib/api';
import { AchievementBadge, AchievementGrid, AchievementUnlockNotification } from './AchievementBadge';
import { ChallengeCard, ChallengeList } from './ChallengeCard';

interface GamificationWidgetProps {
  className?: string;
  compact?: boolean;
}

export function GamificationWidget({ className = '', compact = false }: GamificationWidgetProps) {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [recentAchievements, setRecentAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'achievements' | 'challenges'>('overview');
  const [newAchievement, setNewAchievement] = useState<Achievement | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Initialize achievements if needed (first time)
      try {
        await gamificationApi.initAchievements();
      } catch {
        // Ignore if already initialized
      }

      // Track daily login
      try {
        await gamificationApi.trackActivity('daily_login');
      } catch {
        // Ignore tracking errors
      }

      // Load all data in parallel
      const [statsData, achievementsData, challengesData, recentData] = await Promise.all([
        gamificationApi.getStats().catch(() => null),
        gamificationApi.getAchievements().catch(() => []),
        gamificationApi.getActiveChallenges().catch(() => []),
        gamificationApi.getRecentAchievements(3).catch(() => [])
      ]);

      setStats(statsData);
      setAchievements(achievementsData);
      setChallenges(challengesData);
      setRecentAchievements(recentData);

      // Check for new achievements
      try {
        const checkResult = await gamificationApi.checkAchievements();
        if (checkResult.awarded.length > 0) {
          // Reload achievements to get the newly awarded one
          const updatedAchievements = await gamificationApi.getAchievements();
          setAchievements(updatedAchievements);

          // Show notification for first new achievement
          const newlyAwarded = updatedAchievements.find(a => checkResult.awarded.includes(a.code));
          if (newlyAwarded) {
            setNewAchievement(newlyAwarded);
          }
        }
      } catch {
        // Ignore check errors
      }

    } catch (err) {
      console.error('Failed to load gamification data:', err);
      setError('Impossible de charger les donnees');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleChallengeJoin = () => {
    // Reload challenges after joining
    gamificationApi.getActiveChallenges()
      .then(setChallenges)
      .catch(console.error);
  };

  if (loading) {
    return (
      <div className={`rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-200/50 p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="h-8 bg-gray-200 rounded w-2/3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-xl bg-red-50 border border-red-200 p-4 ${className}`}>
        <p className="text-red-600 text-sm">{error}</p>
        <button onClick={loadData} className="mt-2 text-sm text-red-500 underline">
          Reessayer
        </button>
      </div>
    );
  }

  const earnedAchievements = achievements.filter(a => a.is_earned);
  const joinedChallenges = challenges.filter(c => c.is_joined);

  if (compact) {
    return (
      <div className={`rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-200/50 p-4 ${className}`}>
        {/* Compact header with level */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg">
              {stats?.level || 1}
            </div>
            <div>
              <p className="text-xs text-gray-500">Niveau</p>
              <p className="font-semibold text-gray-900">{stats?.total_points || 0} pts</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">
              {earnedAchievements.length}/{achievements.length} badges
            </p>
            {stats?.current_streak ? (
              <p className="text-xs text-purple-600">{stats.current_streak}j de suite</p>
            ) : null}
          </div>
        </div>

        {/* Level progress bar */}
        <div className="mt-3">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-indigo-600 transition-all"
              style={{ width: `${stats?.level_progress || 0}%` }}
            />
          </div>
        </div>

        {/* Recent achievements */}
        {recentAchievements.length > 0 && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-gray-500">Recents:</span>
            {recentAchievements.map(ach => (
              <span key={ach.id} title={ach.name} className="text-lg">
                {ach.icon}
              </span>
            ))}
          </div>
        )}

        {/* Achievement unlock notification */}
        {newAchievement && (
          <AchievementUnlockNotification
            achievement={newAchievement}
            onClose={() => setNewAchievement(null)}
          />
        )}
      </div>
    );
  }

  return (
    <div className={`rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-200/50 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-purple-200/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏆</span>
            <h3 className="font-semibold text-gray-900">Mes Accomplissements</h3>
          </div>
          {/* Tabs */}
          <div className="flex bg-white/50 rounded-lg p-0.5">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                activeTab === 'overview' ? 'bg-white shadow text-purple-700' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Vue d'ensemble
            </button>
            <button
              onClick={() => setActiveTab('achievements')}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                activeTab === 'achievements' ? 'bg-white shadow text-purple-700' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Badges
            </button>
            <button
              onClick={() => setActiveTab('challenges')}
              className={`px-3 py-1 text-xs rounded-md transition-all ${
                activeTab === 'challenges' ? 'bg-white shadow text-purple-700' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Challenges
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Stats cards */}
            <div className="grid grid-cols-4 gap-3">
              <div className="bg-white/70 rounded-lg p-3 text-center">
                <div className="w-10 h-10 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white font-bold">
                  {stats?.level || 1}
                </div>
                <p className="text-xs text-gray-500 mt-1">Niveau</p>
              </div>
              <div className="bg-white/70 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-purple-600">{stats?.total_points || 0}</p>
                <p className="text-xs text-gray-500">Points</p>
              </div>
              <div className="bg-white/70 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-green-600">{earnedAchievements.length}</p>
                <p className="text-xs text-gray-500">Badges</p>
              </div>
              <div className="bg-white/70 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-amber-600">{stats?.current_streak || 0}</p>
                <p className="text-xs text-gray-500">Jours</p>
              </div>
            </div>

            {/* Level progress */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Progression niveau {stats?.level || 1}</span>
                <span className="text-purple-600 font-medium">{Math.round(stats?.level_progress || 0)}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-indigo-600 transition-all"
                  style={{ width: `${stats?.level_progress || 0}%` }}
                />
              </div>
            </div>

            {/* Recent achievements */}
            {recentAchievements.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Badges recents</h4>
                <AchievementGrid achievements={recentAchievements} size="sm" />
              </div>
            )}

            {/* Active challenges preview */}
            {joinedChallenges.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Challenges en cours</h4>
                <ChallengeList challenges={joinedChallenges.slice(0, 2)} compact onChallengeJoin={handleChallengeJoin} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'achievements' && (
          <div className="space-y-4">
            <div className="text-sm text-gray-600 mb-2">
              {earnedAchievements.length} sur {achievements.length} badges obtenus
            </div>

            {/* Group by category */}
            {['budget', 'savings', 'import', 'engagement'].map(category => {
              const categoryAchievements = achievements.filter(a => a.category === category);
              if (categoryAchievements.length === 0) return null;

              const categoryNames: Record<string, string> = {
                budget: 'Budget',
                savings: 'Epargne',
                import: 'Import',
                engagement: 'Engagement'
              };

              return (
                <div key={category}>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    {categoryNames[category] || category}
                  </h4>
                  <AchievementGrid achievements={categoryAchievements} size="md" showAll />
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'challenges' && (
          <div className="space-y-4">
            {challenges.length > 0 ? (
              <ChallengeList challenges={challenges} onChallengeJoin={handleChallengeJoin} />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <span className="text-4xl">🎯</span>
                <p className="mt-2">Aucun challenge disponible</p>
                <p className="text-sm">Revenez bientot!</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Achievement unlock notification */}
      {newAchievement && (
        <AchievementUnlockNotification
          achievement={newAchievement}
          onClose={() => setNewAchievement(null)}
        />
      )}
    </div>
  );
}

export default GamificationWidget;
