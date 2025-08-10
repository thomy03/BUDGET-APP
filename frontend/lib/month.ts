'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const KEY = 'selectedMonth';

export function useGlobalMonth(): [string, (m: string) => void] {
  // Helper function to get current month in YYYY-MM format
  const getCurrentMonth = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  };

  // Initialize with current month - consistent between server and client
  const [month, setMonthState] = useState<string>(getCurrentMonth());
  const [isMounted, setIsMounted] = useState(false);

  // Handle client-side mounting and localStorage initialization
  useEffect(() => {
    setIsMounted(true);
    // Only read from localStorage after mounting
    if (typeof window !== 'undefined') {
      const saved = window.localStorage.getItem(KEY);
      if (saved && saved !== month) {
        setMonthState(saved);
      }
    }
  }, []);

  // Save to localStorage when month changes (only after mounting)
  useEffect(() => {
    if (isMounted && typeof window !== 'undefined') {
      window.localStorage.setItem(KEY, month);
    }
  }, [month, isMounted]);

  // Fonction pour changer le mois avec logging
  const setMonth = useCallback((newMonth: string) => {
    console.log('🗓️  Global month change:', month, '->', newMonth);
    setMonthState(newMonth);
  }, [month]);

  return [month, setMonth];
}

/**
 * Hook pour synchroniser le mois global avec les paramètres URL sur les pages de navigation
 * Utilisé spécifiquement dans transactions.tsx pour gérer la synchronisation URL/state
 */
export function useGlobalMonthWithUrl(): [string, (m: string) => void] {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [globalMonth, setGlobalMonth] = useGlobalMonth();
  
  // État pour suivre la synchronisation initiale et éviter les boucles
  const [syncState, setSyncState] = useState<{
    initialized: boolean;
    lastUrlMonth: string | null;
    lastGlobalMonth: string | null;
  }>({
    initialized: false,
    lastUrlMonth: null,
    lastGlobalMonth: null
  });

  // Synchroniser le mois entre l'URL et le state global
  useEffect(() => {
    const monthParam = searchParams.get('month');
    
    // Si c'est la première fois ou si l'URL a changé
    if (!syncState.initialized || monthParam !== syncState.lastUrlMonth) {
      if (monthParam && monthParam !== globalMonth) {
        console.log('🔄 Sync from URL:', monthParam, '(was:', globalMonth, ')');
        setGlobalMonth(monthParam);
        setSyncState({
          initialized: true,
          lastUrlMonth: monthParam,
          lastGlobalMonth: monthParam
        });
        return;
      }
      
      // Si pas de paramètre month dans l'URL, l'initialiser avec le mois global
      if (!monthParam && !syncState.initialized) {
        console.log('🔄 Initialize URL with global month:', globalMonth);
        const newParams = new URLSearchParams(searchParams.toString());
        newParams.set('month', globalMonth);
        const newUrl = `/transactions?${newParams.toString()}`;
        router.replace(newUrl, { scroll: false });
        setSyncState({
          initialized: true,
          lastUrlMonth: globalMonth,
          lastGlobalMonth: globalMonth
        });
        return;
      }
    }
    
    // Marquer comme initialisé si on n'a pas fait d'action
    if (!syncState.initialized) {
      setSyncState({
        initialized: true,
        lastUrlMonth: monthParam,
        lastGlobalMonth: globalMonth
      });
    }
  }, [searchParams, globalMonth, setGlobalMonth, router, syncState]);

  // Fonction pour changer le mois et mettre à jour l'URL
  const setMonth = useCallback((newMonth: string) => {
    console.log('🗓️  Month change with URL sync:', globalMonth, '->', newMonth);
    
    // Mettre à jour le state global immédiatement
    setGlobalMonth(newMonth);
    
    // Mettre à jour l'URL
    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('month', newMonth);
    const newUrl = `/transactions?${newParams.toString()}`;
    router.replace(newUrl, { scroll: false });
    
    // Mettre à jour l'état de synchronisation
    setSyncState(prev => ({
      ...prev,
      lastUrlMonth: newMonth,
      lastGlobalMonth: newMonth
    }));
  }, [globalMonth, setGlobalMonth, searchParams, router]);

  return [globalMonth, setMonth];
}
