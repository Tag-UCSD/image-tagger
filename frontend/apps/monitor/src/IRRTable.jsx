import React, { useState, useMemo } from 'react';
import { EmptyState } from '@shared';
import { BarChart2, ChevronUp, ChevronDown } from 'lucide-react';

const COLUMNS = [
    { key: 'attribute_name', label: 'Attribute' },
    { key: 'irr',            label: 'IRR' },
    { key: 'n_pairs',        label: 'Pairs' },
    { key: 'bin',            label: 'Bin' },
];

const BIN_ORDER = { high: 0, medium: 1, low: 2 };

function compareRows(a, b, key, dir) {
    let av = a[key];
    let bv = b[key];
    if (key === 'bin') {
        av = BIN_ORDER[av] ?? 99;
        bv = BIN_ORDER[bv] ?? 99;
    }
    if (typeof av === 'string') av = av.toLowerCase();
    if (typeof bv === 'string') bv = bv.toLowerCase();
    if (av < bv) return dir === 'asc' ? -1 : 1;
    if (av > bv) return dir === 'asc' ? 1 : -1;
    return 0;
}

export function IRRTable({ rows }) {
    const [sortKey, setSortKey] = useState('irr');
    const [sortDir, setSortDir] = useState('desc');

    const handleHeaderClick = (key) => {
        if (sortKey === key) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const sorted = useMemo(
        () => [...rows].sort((a, b) => compareRows(a, b, sortKey, sortDir)),
        [rows, sortKey, sortDir],
    );

    return (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <BarChart2 className="text-purple-500" size={18} />
                <h2 className="font-semibold text-gray-900 text-sm">Inter-Rater Reliability</h2>
            </div>

            {rows.length === 0 ? (
                <EmptyState
                    title="No IRR data yet"
                    message="IRR statistics will appear once multiple raters have labeled the same attributes."
                />
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="border-b border-gray-100">
                                {COLUMNS.map(col => (
                                    <th
                                        key={col.key}
                                        scope="col"
                                        aria-sort={
                                            sortKey === col.key
                                                ? sortDir === 'asc' ? 'ascending' : 'descending'
                                                : 'none'
                                        }
                                        className="py-3 px-4 whitespace-nowrap"
                                    >
                                        <button
                                            type="button"
                                            className="inline-flex items-center gap-1 text-xs font-bold text-gray-500 uppercase tracking-wider hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 rounded"
                                            onClick={() => handleHeaderClick(col.key)}
                                        >
                                            {col.label}
                                            {sortKey === col.key
                                                ? sortDir === 'asc'
                                                    ? <ChevronUp size={12} />
                                                    : <ChevronDown size={12} />
                                                : <span className="w-3 inline-block" aria-hidden="true" />}
                                        </button>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {sorted.map(row => (
                                <IRRRow key={row.attribute_key} row={row} />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

const BIN_CLASS = {
    high:   'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    low:    'bg-red-100 text-red-700',
};

function IRRRow({ row }) {
    const binClass = BIN_CLASS[row.bin] ?? 'bg-gray-100 text-gray-700';
    return (
        <tr className="hover:bg-gray-50 transition-colors">
            <td className="py-3 px-4">
                <span className="font-medium text-gray-900">{row.attribute_name}</span>
                <span className="ml-2 text-xs text-gray-600 font-mono">{row.attribute_key}</span>
            </td>
            <td className="py-3 px-4 font-mono text-gray-700">{(row.irr ?? 0).toFixed(2)}</td>
            <td className="py-3 px-4 text-gray-600">{row.n_pairs}</td>
            <td className="py-3 px-4">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${binClass}`}>
                    {row.bin}
                </span>
            </td>
        </tr>
    );
}
