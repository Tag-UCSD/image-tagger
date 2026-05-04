import React from 'react';
import { Button } from './Button.jsx';

export function EmptyState({ icon, title, message, action }) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center py-16 px-6 text-center"
    >
      {icon && (
        <div className="mb-4 text-gray-400" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
      {message && (
        <p className="text-sm text-gray-500 max-w-sm mb-4">{message}</p>
      )}
      {action && (
        <Button onClick={action.onClick} variant={action.variant ?? 'secondary'}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
