// Cache fix timestamp: 2025-08-10T16:44:30Z
'use client';
import { useState, useCallback } from 'react';

// Helper function to get current month in YYYY-MM format
const getCurrentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

// Global month state - simple approach without localStorage
let globalMonth = getCurrentMonth();

// Debug log to verify fresh code is loading
console.log('✅ month.ts loaded fresh at:', new Date().toISOString());

export function useGlobalMonth(): [string, (m: string) => void] {
  const [, forceUpdate] = useState({});
  
  const setMonth = useCallback((newMonth: string) => {
    globalMonth = newMonth;
    forceUpdate({});  // Force re-render
  }, []);

  return [globalMonth, setMonth];
}

/**
 * Simplified hook for transactions - same as global for now
 */
export function useGlobalMonthWithUrl(): [string, (m: string) => void] {
  return useGlobalMonth();
}