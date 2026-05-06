import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from 'lucide-react';

function formatTick(ts) {
    try {
        return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return ts;
    }
}

function VelocityTooltip({ active, payload }) {
    if (!active || !payload?.length) return null;
    const { timestamp, count } = payload[0].payload;
    return (
        <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs space-y-0.5">
            <p className="text-gray-500">{timestamp}</p>
            <p className="font-semibold text-blue-600">{count} validations</p>
        </div>
    );
}

export function VelocityChart({ series }) {
    return (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <TrendingUp className="text-blue-500" size={18} />
                <h2 className="font-semibold text-gray-900 text-sm">Validation Velocity</h2>
            </div>
            {series.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-10">No velocity data yet.</p>
            ) : (
                <div className="p-4">
                    <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={series} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                            <XAxis
                                dataKey="timestamp"
                                tickFormatter={formatTick}
                                tick={{ fontSize: 11, fill: '#9ca3af' }}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                tick={{ fontSize: 11, fill: '#9ca3af' }}
                                tickLine={false}
                                axisLine={false}
                                allowDecimals={false}
                            />
                            <Tooltip content={<VelocityTooltip />} />
                            <Line
                                type="monotone"
                                dataKey="count"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                dot={{ r: 3, fill: '#3b82f6' }}
                                activeDot={{ r: 5 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}
