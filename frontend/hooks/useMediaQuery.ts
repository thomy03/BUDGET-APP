'use client';

import { useState, useEffect, useCallback } from 'react';

/**
 * Breakpoints following Tailwind CSS convention
 */
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type Breakpoint = keyof typeof breakpoints;

/**
 * Hook to detect if a media query matches
 * @param query - CSS media query string
 * @returns boolean indicating if the query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
    } else {
      // Legacy browsers
      mediaQuery.addListener(handler);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handler);
      } else {
        mediaQuery.removeListener(handler);
      }
    };
  }, [query, mounted]);

  // Return false during SSR to prevent hydration mismatch
  return mounted ? matches : false;
}

/**
 * Hook to detect if viewport is below a specific breakpoint
 * @param breakpoint - Tailwind breakpoint name
 * @returns boolean indicating if viewport is smaller than breakpoint
 */
export function useIsMobile(breakpoint: Breakpoint = 'md'): boolean {
  return useMediaQuery(`(max-width: ${breakpoints[breakpoint] - 1}px)`);
}

/**
 * Hook to detect if viewport is at or above a specific breakpoint
 * @param breakpoint - Tailwind breakpoint name
 * @returns boolean indicating if viewport is at or above breakpoint
 */
export function useIsDesktop(breakpoint: Breakpoint = 'lg'): boolean {
  return useMediaQuery(`(min-width: ${breakpoints[breakpoint]}px)`);
}

/**
 * Hook to detect if viewport is within a range
 * @param minBreakpoint - Minimum breakpoint (inclusive)
 * @param maxBreakpoint - Maximum breakpoint (exclusive)
 * @returns boolean indicating if viewport is within range
 */
export function useBreakpointRange(minBreakpoint: Breakpoint, maxBreakpoint: Breakpoint): boolean {
  return useMediaQuery(
    `(min-width: ${breakpoints[minBreakpoint]}px) and (max-width: ${breakpoints[maxBreakpoint] - 1}px)`
  );
}

/**
 * Hook to get current breakpoint
 * @returns Current breakpoint name or 'xs' for smallest
 */
export function useBreakpoint(): 'xs' | Breakpoint {
  const isSm = useMediaQuery(`(min-width: ${breakpoints.sm}px)`);
  const isMd = useMediaQuery(`(min-width: ${breakpoints.md}px)`);
  const isLg = useMediaQuery(`(min-width: ${breakpoints.lg}px)`);
  const isXl = useMediaQuery(`(min-width: ${breakpoints.xl}px)`);
  const is2Xl = useMediaQuery(`(min-width: ${breakpoints['2xl']}px)`);

  if (is2Xl) return '2xl';
  if (isXl) return 'xl';
  if (isLg) return 'lg';
  if (isMd) return 'md';
  if (isSm) return 'sm';
  return 'xs';
}

/**
 * Hook to detect touch device
 * @returns boolean indicating if device supports touch
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    setIsTouch(
      'ontouchstart' in window ||
      navigator.maxTouchPoints > 0 ||
      // @ts-ignore - msMaxTouchPoints is IE-specific
      navigator.msMaxTouchPoints > 0
    );
  }, []);

  return isTouch;
}

/**
 * Hook to detect user prefers reduced motion
 * @returns boolean indicating reduced motion preference
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * Hook to detect dark mode preference
 * @returns boolean indicating dark mode preference
 */
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * Combined responsive utilities hook
 * @returns Object with common responsive states
 */
export function useResponsive() {
  const isMobile = useIsMobile();
  const isTablet = useBreakpointRange('md', 'lg');
  const isDesktop = useIsDesktop();
  const breakpoint = useBreakpoint();
  const isTouch = useIsTouchDevice();
  const prefersReducedMotion = usePrefersReducedMotion();

  return {
    isMobile,
    isTablet,
    isDesktop,
    breakpoint,
    isTouch,
    prefersReducedMotion,
  };
}

export default useMediaQuery;
