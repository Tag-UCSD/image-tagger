import React from 'react';
import { DollarSign } from 'lucide-react';

export function BudgetPanel({ budget }) {
    if (!budget) return null;

    const { spent_usd, limit_usd, remaining_usd } = budget;
    const pct = limit_usd > 0 ? Math.min(100, (spent_usd / limit_usd) * 100) : 0;
    const danger = pct >= 80;

    return (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <DollarSign className="text-emerald-500" size={18} />
                <h2 className="font-semibold text-gray-900 text-sm">Budget</h2>
            </div>
            <div className="p-4 space-y-3">
                <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide font-semibold">Spent</p>
                        <p className="text-lg font-bold text-gray-900">${spent_usd.toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide font-semibold">Limit</p>
                        <p className="text-lg font-bold text-gray-900">${limit_usd.toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-[11px] text-gray-500 uppercase tracking-wide font-semibold">Remaining</p>
                        <p className={`text-lg font-bold ${danger ? 'text-red-600' : 'text-emerald-700'}`}>
                            ${remaining_usd.toFixed(2)}
                        </p>
                    </div>
                </div>

                <div>
                    <div
                        className="w-full bg-gray-100 h-2.5 rounded-full overflow-hidden"
                        role="progressbar"
                        aria-valuenow={Math.round(pct)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`Budget: ${pct.toFixed(0)}% used`}
                    >
                        <div
                            className={`h-full rounded-full transition-all ${danger ? 'bg-red-500' : 'bg-emerald-500'}`}
                            style={{ width: `${pct}%` }}
                        />
                    </div>
                    <p className="text-[11px] text-gray-500 mt-1 text-right">
                        {pct.toFixed(0)}% of limit used
                    </p>
                </div>
            </div>
        </div>
    );
}
