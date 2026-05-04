import React from 'react';

export function Skeleton({ className = '', variant = 'rect' }) {
  const shapes = {
    rect: 'rounded',
    line: 'rounded h-4',
    circle: 'rounded-full',
  };
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-gray-200 ${shapes[variant] ?? shapes.rect} ${className}`}
    />
  );
}
