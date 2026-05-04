import React from 'react';

const BASE = [
  'inline-flex items-center justify-center gap-2 rounded font-semibold',
  'transition-colors duration-150',
  'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600',
  'disabled:opacity-50 disabled:cursor-not-allowed',
].join(' ');

const VARIANTS = {
  primary:   'bg-blue-600 hover:bg-blue-700 text-white shadow-sm',
  secondary: 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 shadow-sm',
  danger:    'bg-red-600 hover:bg-red-700 text-white shadow-sm focus:ring-red-600',
  ghost:     'bg-transparent hover:bg-gray-100 text-gray-700',
  outline:   'bg-transparent border border-gray-300 text-gray-700 hover:bg-gray-50',
};

const SIZES = {
  xs: 'px-2 py-1 text-xs',
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

export const Button = ({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
}) => (
  <button
    type={type}
    onClick={onClick}
    disabled={disabled}
    className={`${BASE} ${VARIANTS[variant] ?? VARIANTS.primary} ${SIZES[size] ?? SIZES.md} ${className}`}
  >
    {children}
  </button>
);