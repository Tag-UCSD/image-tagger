import { useEffect } from 'react';

const SKIP_TAGS = new Set(['textarea', 'select']);

export function KeyboardShortcuts({ onSubmit, enabled = true }) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e) => {
      if (e.key !== 'Enter') return;
      const el = document.activeElement;
      const tag = el?.tagName?.toLowerCase();
      if (SKIP_TAGS.has(tag)) return;
      if (el?.isContentEditable) return;
      if (el?.type === 'submit') return; // let native click handle it
      e.preventDefault();
      onSubmit?.();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, onSubmit]);

  return null;
}
