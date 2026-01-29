'use client';

import { useAuth } from '../../lib/auth';
import { useInactivityTimeout, formatTimeRemaining } from '../../hooks/useInactivityTimeout';
import { InactivityWarningModal } from './InactivityWarningModal';

// Configuration: 30 minutes d'inactivite, alerte 2 minutes avant
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_BEFORE_MS = 2 * 60 * 1000; // 2 minutes avant

export function SessionStatus() {
  const { isAuthenticated, user } = useAuth();
  const {
    remainingSeconds,
    showWarning,
    isActive,
    resetTimer,
    forceLogout,
  } = useInactivityTimeout({
    timeoutMs: INACTIVITY_TIMEOUT_MS,
    warningMs: WARNING_BEFORE_MS,
  });

  if (!isAuthenticated) {
    return null;
  }

  // Determine status color based on remaining time
  const getStatusColor = () => {
    if (remainingSeconds <= 60) return 'red'; // Less than 1 minute
    if (remainingSeconds <= 300) return 'amber'; // Less than 5 minutes
    return 'green'; // Normal
  };

  const statusColor = getStatusColor();
  const colorClasses = {
    green: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      text: 'text-green-700',
      dot: 'bg-green-500',
      secondary: 'text-green-600',
    },
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      dot: 'bg-amber-500',
      secondary: 'text-amber-600',
    },
    red: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-700',
      dot: 'bg-red-500',
      secondary: 'text-red-600',
    },
  };

  const colors = colorClasses[statusColor];

  // Format remaining time for display
  const formatSessionTime = () => {
    const mins = Math.floor(remainingSeconds / 60);
    if (mins >= 10) {
      return `${mins} min restantes`;
    }
    return formatTimeRemaining(remainingSeconds);
  };

  return (
    <>
      {/* Session Status Badge */}
      <div
        className={`
          fixed bottom-4 right-4 ${colors.bg} border ${colors.border}
          rounded-lg px-3 py-2 text-sm ${colors.text} shadow-sm z-50
          transition-all duration-300
        `}
      >
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 ${colors.dot} rounded-full ${
              isActive ? 'animate-pulse' : ''
            }`}
          />
          <span className="font-medium">{user}</span>
          <span className={colors.secondary}>|</span>
          <span className={colors.secondary}>
            {isActive ? formatSessionTime() : 'Inactif'}
          </span>
        </div>
      </div>

      {/* Inactivity Warning Modal */}
      <InactivityWarningModal
        isOpen={showWarning}
        remainingSeconds={remainingSeconds}
        onContinue={resetTimer}
        onLogout={forceLogout}
      />
    </>
  );
}
