import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

const WARNING_LABELS = {
  skew_high: 'Skew high',
  skew_low: 'Skew low',
  low_confidence: 'Low confidence',
  all_identical: 'All identical',
};

const TAG_LABELS = {
  'social.sociopetal_seating': 'Sociopetal Seating',
  'social.shared_attention_anchor': 'Shared Attention Anchor',
  'social.interactional_visibility': 'Interactional Visibility',
  'spatial.prospect': 'Prospect',
  'social.chance_encounter_potential': 'Chance Encounter',
  'social.disengagement_ease': 'Disengagement Ease',
};

function MiniBar({ value }) {
  const pct = Math.max(0, Math.min(1, value / 4)) * 100;
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
        <span className="block h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-xs tabular-nums text-gray-700">{value.toFixed(2)}</span>
    </span>
  );
}

function ConfCell({ value }) {
  const pct = Math.round(value * 100);
  const cls = value >= 0.5 ? 'text-green-700' : value >= 0.3 ? 'text-amber-700' : 'text-red-700 font-semibold';
  return <span className={`text-xs tabular-nums ${cls}`}>{pct}%</span>;
}

export function LatentStatusPanel({ status, loading, error }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-10 gap-2 text-gray-500">
        <Loader2 size={20} className="animate-spin" />
        <span className="text-sm">Loading latent status…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
        <AlertTriangle size={16} className="text-red-500 shrink-0" />
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (!status) return null;

  const isEmpty = status.total_images === 0 || status.by_detector.length === 0;
  const warnings = status.warnings ?? [];

  // index warnings by tag for row-level indicators
  const warnByTag = {};
  for (const w of warnings) {
    (warnByTag[w.tag_id] ??= []).push(w);
  }

  return (
    <div className="space-y-4">
      {/* Summary tiles */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total images', value: status.total_images, red: false },
          { label: 'All 6 complete', value: status.images_with_all_six, red: false },
          { label: 'Failures', value: status.failures, red: status.failures > 0 },
        ].map(({ label, value, red }) => (
          <div key={label} className="bg-white rounded-lg border border-gray-200 px-4 py-3 text-center">
            <p className="text-xs text-gray-500 mb-0.5">{label}</p>
            <p className={`text-xl font-bold tabular-nums ${red ? 'text-red-600' : 'text-gray-900'}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Warning list */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-2">
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-amber-600 shrink-0" />
            <p className="text-xs font-semibold text-amber-800">
              {warnings.length} distribution warning{warnings.length !== 1 ? 's' : ''}
            </p>
          </div>
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="shrink-0 px-1.5 py-0.5 rounded bg-amber-100 border border-amber-300 text-amber-800 font-medium whitespace-nowrap">
                {WARNING_LABELS[w.code] ?? w.code}
              </span>
              <span className="text-amber-700">
                <span className="font-mono text-amber-600">{TAG_LABELS[w.tag_id] ?? w.tag_id}</span>
                {' — '}{w.message}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {isEmpty ? (
        <p className="py-8 text-center text-sm text-gray-500">
          No images in this set have been processed yet.
        </p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Detector</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Mean score</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">% &gt; {status.threshold}</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">Mean conf.</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase">N</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {status.by_detector.map((row) => {
                const rowWarns = warnByTag[row.tag_id] ?? [];
                return (
                  <tr key={row.tag_id} className={rowWarns.length > 0 ? 'bg-amber-50/60' : undefined}>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        {rowWarns.length > 0 && (
                          <AlertTriangle size={12} className="text-amber-500 shrink-0" />
                        )}
                        <div>
                          <p className="text-xs font-medium text-gray-900">
                            {TAG_LABELS[row.tag_id] ?? row.tag_id}
                          </p>
                          <p className="text-xs font-mono text-gray-400">{row.tag_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5"><MiniBar value={row.mean_value} /></td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs tabular-nums ${row.pct_above_threshold > 0.8 ? 'text-amber-700 font-semibold' : 'text-gray-700'}`}>
                        {(row.pct_above_threshold * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5"><ConfCell value={row.mean_confidence} /></td>
                    <td className="px-4 py-2.5 text-xs tabular-nums text-gray-600">{row.n_observations}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
