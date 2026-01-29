'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuth } from '../lib/auth';

interface InactivityConfig {
  /** Timeout duration in milliseconds (default: 30 minutes) */
  timeoutMs?: number;
  /** Warning before timeout in milliseconds (default: 2 minutes) */
  warningMs?: number;
  /** Events to track as activity */
  events?: string[];
}

interface InactivityState {
  /** Time remaining before logout in seconds */
  remainingSeconds: number;
  /** Whether the warning modal should be shown */
  showWarning: boolean;
  /** Whether the user is currently active */
  isActive: boolean;
  /** Reset the inactivity timer (extends session) */
  resetTimer: () => void;
  /** Force logout now */
  forceLogout: () => void;
}

const DEFAULT_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const DEFAULT_WARNING_MS = 2 * 60 * 1000; // 2 minutes before timeout
const DEFAULT_EVENTS = [
  'mousedown',
  'mousemove',
  'keydown',
  'scroll',
  'touchstart',
  'click',
  'wheel',
];

export function useInactivityTimeout(config: InactivityConfig = {}): InactivityState {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    warningMs = DEFAULT_WARNING_MS,
    events = DEFAULT_EVENTS,
  } = config;

  const { isAuthenticated, logout } = useAuth();
  const [remainingSeconds, setRemainingSeconds] = useState(Math.floor(timeoutMs / 1000));
  const [showWarning, setShowWarning] = useState(false);
  const [isActive, setIsActive] = useState(true);

  const lastActivityRef = useRef<number>(Date.now());
  const timeoutIdRef = useRef<NodeJS.Timeout | null>(null);
  const intervalIdRef = useRef<NodeJS.Timeout | null>(null);

  // Reset the inactivity timer
  const resetTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    setShowWarning(false);
    setIsActive(true);
    setRemainingSeconds(Math.floor(timeoutMs / 1000));

    // Store last activity time for cross-tab sync
    if (typeof window !== 'undefined') {
      localStorage.setItem('last_activity', lastActivityRef.current.toString());
    }
  }, [timeoutMs]);

  // Force logout
  const forceLogout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('last_activity');
    }
    logout(true);
  }, [logout]);

  // Handle user activity
  const handleActivity = useCallback(() => {
    if (!showWarning) {
      // Only reset if warning is not showing
      // (user must click "Continue" to extend session when warning is shown)
      resetTimer();
    }
  }, [resetTimer, showWarning]);

  // Check inactivity and update state
  const checkInactivity = useCallback(() => {
    if (!isAuthenticated) return;

    const now = Date.now();
    const elapsed = now - lastActivityRef.current;
    const remaining = timeoutMs - elapsed;
    const remainingSec = Math.max(0, Math.floor(remaining / 1000));

    setRemainingSeconds(remainingSec);

    // Check if we should show warning
    if (remaining <= warningMs && remaining > 0) {
      setShowWarning(true);
      setIsActive(false);
    }

    // Check if we should logout
    if (remaining <= 0) {
      console.log('⏰ Session expired due to inactivity');
      forceLogout();
    }
  }, [isAuthenticated, timeoutMs, warningMs, forceLogout]);

  // Cross-tab sync: listen for activity in other tabs
  useEffect(() => {
    if (typeof window === 'undefined' || !isAuthenticated) return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'last_activity' && e.newValue) {
        const otherTabActivity = parseInt(e.newValue, 10);
        if (otherTabActivity > lastActivityRef.current) {
          lastActivityRef.current = otherTabActivity;
          setShowWarning(false);
          setIsActive(true);
          setRemainingSeconds(Math.floor(timeoutMs / 1000));
        }
      }
      // Handle logout from another tab
      if (e.key === 'auth_token' && e.newValue === null) {
        window.location.href = '/login';
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [isAuthenticated, timeoutMs]);

  // Set up activity listeners
  useEffect(() => {
    if (typeof window === 'undefined' || !isAuthenticated) return;

    // Initialize last activity from localStorage (cross-tab sync)
    const storedActivity = localStorage.getItem('last_activity');
    if (storedActivity) {
      const stored = parseInt(storedActivity, 10);
      if (stored > lastActivityRef.current) {
        lastActivityRef.current = stored;
      }
    } else {
      localStorage.setItem('last_activity', lastActivityRef.current.toString());
    }

    // Add event listeners for activity tracking
    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Start interval to check inactivity every second
    intervalIdRef.current = setInterval(checkInactivity, 1000);

    return () => {
      // Clean up event listeners
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });

      // Clear interval
      if (intervalIdRef.current) {
        clearInterval(intervalIdRef.current);
      }
    };
  }, [isAuthenticated, events, handleActivity, checkInactivity]);

  // Reset timer when user logs in
  useEffect(() => {
    if (isAuthenticated) {
      resetTimer();
    }
  }, [isAuthenticated, resetTimer]);

  return {
    remainingSeconds,
    showWarning,
    isActive,
    resetTimer,
    forceLogout,
  };
}

/**
 * Format remaining seconds as MM:SS
 */
export function formatTimeRemaining(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
