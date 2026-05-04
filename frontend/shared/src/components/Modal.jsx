import React, { useEffect, useId, useRef } from 'react';

export function Modal({ open, onClose, title, children }) {
  const titleId = useId();
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handleKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    dialogRef.current?.focus();
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        aria-hidden="true"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6 focus:outline-none"
      >
        <div className="flex items-start justify-between mb-4">
          <h2 id={titleId} className="text-lg font-semibold text-gray-900">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-gray-400 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 rounded"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
