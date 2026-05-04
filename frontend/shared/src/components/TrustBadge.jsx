import React from 'react';

const CONFIGS = {
  validated: {
    className: 'bg-green-100 text-green-800 border-green-300',
    symbol: '✓',
    label: 'Validated',
  },
  proxy_validated: {
    className: 'bg-amber-100 text-amber-800 border-amber-300',
    symbol: '~',
    label: 'Proxy Validated',
  },
  untested: {
    className: 'bg-red-100 text-red-800 border-red-300',
    symbol: '!',
    label: 'Untested',
  },
};

export function TrustBadge({ evaluation_status }) {
  const cfg = CONFIGS[evaluation_status] ?? CONFIGS.untested;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cfg.className}`}
      title={`Model evaluation status: ${evaluation_status ?? 'unknown'}`}
    >
      <span aria-hidden="true">{cfg.symbol}</span>
      <span>{cfg.label}</span>
    </span>
  );
}
