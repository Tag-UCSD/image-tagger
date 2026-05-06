import { useState, useEffect } from 'react';

const QUERIES = {
  sm:  '(min-width: 640px)',
  md:  '(min-width: 768px)',
  lg:  '(min-width: 1024px)',
  xl:  '(min-width: 1280px)',
  '2xl': '(min-width: 1536px)',
};

/**
 * Returns true when the viewport matches the given Tailwind breakpoint.
 * Supported breakpoints: sm, md, lg, xl, 2xl
 *
 * @param {'sm'|'md'|'lg'|'xl'|'2xl'} breakpoint
 * @returns {boolean}
 */
export function useBreakpoint(breakpoint) {
  const query = QUERIES[breakpoint];
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (!query) return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
