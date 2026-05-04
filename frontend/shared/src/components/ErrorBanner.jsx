import React from 'react';

export function ErrorBanner({ message, code, onDismiss }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex items-start gap-3 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm"
    >
      <span className="mt-0.5 text-red-700 font-bold flex-shrink-0" aria-hidden="true">!</span>
      <div className="flex-1 min-w-0">
        {code && (
          <span className="font-mono text-xs text-red-600 uppercase tracking-wide block mb-0.5">
            {code}
          </span>
        )}
        <p className="text-red-800">{message}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="flex-shrink-0 text-red-600 hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 rounded"
        >
          <span aria-hidden="true">×</span>
        </button>
      )}
    </div>
  );
}
