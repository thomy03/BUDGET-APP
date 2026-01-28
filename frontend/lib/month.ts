// Cache fix timestamp: 2026-01-03T15:00:00Z
'use client';
import { useState, useCallback, useEffect, useSyncExternalStore } from 'react';

// Helper function to get current month in YYYY-MM format
const getCurrentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

// Global month state with subscriber pattern for cross-component reactivity
let globalMonth = getCurrentMonth();
let subscribers = new Set<() => void>();

const notifySubscribers = () => {
  subscribers.forEach(callback => callback());
};

const subscribe = (callback: () => void) => {
  subscribers.add(callback);
  return () => subscribers.delete(callback);
};

const getSnapshot = () => globalMonth;

const setGlobalMonth = (newMonth: string) => {
  if (globalMonth !== newMonth) {
    console.log('📅 Global month changed:', globalMonth, '->', newMonth);
    globalMonth = newMonth;
    notifySubscribers();
  }
};

// Debug log to verify fresh code is loading
console.log('✅ month.ts loaded fresh at:', new Date().toISOString());

export function useGlobalMonth(): [string, (m: string) => void] {
  // useSyncExternalStore ensures ALL components using this hook re-render when month changes
  const month = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const setMonth = useCallback((newMonth: string) => {
    setGlobalMonth(newMonth);
  }, []);

  return [month, setMonth];
}

/**
 * Simplified hook for transactions - same as global for now
 */
export function useGlobalMonthWithUrl(): [string, (m: string) => void] {
  return useGlobalMonth();
}