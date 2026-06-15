import React from 'react';
import { LayoutGrid } from 'lucide-react';

const NAV_LINKS = [
  { label: 'Explorer',   href: '/' },
  { label: 'Workbench',  href: '/workbench' },
  { label: 'Monitor',    href: '/monitor' },
  { label: 'Admin',      href: '/admin' },
];

function isActive(href) {
  if (typeof window === 'undefined') return false;
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  const target = href.replace(/\/$/, '') || '/';
  return path === target;
}

export const Header = ({ title, appName }) => {
    return (
        <header className="bg-enterprise-blue text-white shadow-md z-50">
            <div className="flex justify-between items-center px-4 py-3">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center font-bold shadow-inner">
                        <LayoutGrid size={18} />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold leading-none tracking-tight">{appName}</h1>
                        <span className="text-xs text-gray-400 font-mono">v3.0 Enterprise</span>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-sm font-medium bg-surface-dark px-3 py-1 rounded border border-gray-700">
                        {title}
                    </div>
                    <div className="w-8 h-8 rounded-full bg-gray-600 border-2 border-gray-500" aria-hidden="true"></div>
                </div>
            </div>
            <nav className="flex gap-1 px-4 pb-0">
                {NAV_LINKS.map(({ label, href }) => {
                    const active = isActive(href);
                    return (
                        <a
                            key={href}
                            href={href}
                            className={[
                                'px-4 py-2 text-sm font-medium rounded-t transition-colors',
                                active
                                    ? 'bg-white text-gray-900'
                                    : 'text-gray-300 hover:text-white hover:bg-white/10',
                            ].join(' ')}
                        >
                            {label}
                        </a>
                    );
                })}
            </nav>
        </header>
    );
};