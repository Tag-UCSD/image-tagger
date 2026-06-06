import React, { useState, useRef, forwardRef, useImperativeHandle } from 'react';

const ORDINAL_VALUES = [0, 1, 2, 3, 4];

function ConfidenceChip({ confidence }) {
  const pct = Math.round(confidence * 100);
  const cls =
    confidence >= 0.5
      ? 'bg-green-50 text-green-700 border-green-200'
      : confidence >= 0.3
        ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
        : 'bg-red-50 text-red-700 border-red-200';
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${cls}`}>
      {pct}% conf.
    </span>
  );
}

function DetectorBar({ value }) {
  const pct = (Math.max(0, Math.min(4, value)) / 4) * 100;
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-20 h-2 rounded-full bg-gray-200 overflow-hidden">
        <span className="block h-full rounded-full bg-blue-400" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-sm font-semibold tabular-nums text-gray-700">{value} / 4</span>
    </span>
  );
}

export const LatentValidationPanel = forwardRef(function LatentValidationPanel(
  { latent, onSubmit, submitting },
  ref,
) {
  const [selected, setSelected] = useState(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const startRef = useRef(performance.now());

  const doSubmit = () => {
    if (selected === null || submitting) return;
    if (selected < 0 || selected > 4) return;
    const duration_ms = Math.round(performance.now() - startRef.current);
    onSubmit(selected, duration_ms);
  };

  useImperativeHandle(ref, () => ({ submit: doSubmit }), [selected, submitting, onSubmit]);

  const evidenceEntries = Object.entries(latent.evidence ?? {});

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); doSubmit(); }}
      className="flex flex-col gap-4"
      noValidate
    >
      {/* Tag identity */}
      <div className="space-y-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-semibold text-gray-900">{latent.label}</p>
          <ConfidenceChip confidence={latent.confidence} />
        </div>
        <p className="text-xs font-mono text-gray-400">{latent.tag_id}</p>
        <p className="text-xs text-gray-500">
          Detector: <span className="font-mono">{latent.detector_version}</span>
        </p>
      </div>

      {/* Detector output */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase mb-1.5">Detector output</p>
        <DetectorBar value={latent.value} />
      </div>

      {/* Evidence */}
      {evidenceEntries.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setEvidenceOpen((o) => !o)}
            className="text-xs text-blue-600 hover:underline"
          >
            {evidenceOpen ? 'Hide' : 'Show'} evidence ({evidenceEntries.length} keys)
          </button>
          {evidenceOpen && (
            <dl className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1">
              {evidenceEntries.map(([k, v]) => (
                <React.Fragment key={k}>
                  <dt className="text-xs font-mono text-gray-500 truncate">{k}</dt>
                  <dd className="text-xs text-gray-800 truncate">{String(v)}</dd>
                </React.Fragment>
              ))}
            </dl>
          )}
        </div>
      )}

      {/* Ordinal correction */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Your correction (0 – 4)</p>
        <div className="flex gap-2" role="group" aria-label="Ordinal correction 0 to 4">
          {ORDINAL_VALUES.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setSelected(v)}
              aria-pressed={selected === v}
              aria-label={`${v} out of 4`}
              className={[
                'w-10 h-10 rounded-lg border-2 text-sm font-semibold transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1',
                selected === v
                  ? 'border-blue-600 bg-blue-600 text-white'
                  : 'border-gray-300 bg-white text-gray-700 hover:border-blue-400',
              ].join(' ')}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={selected === null || submitting}
        className="self-start rounded-lg bg-blue-600 text-white text-sm font-semibold py-2 px-4
          hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
      >
        {submitting ? 'Submitting…' : 'Submit correction  ↵ Enter'}
      </button>
    </form>
  );
});
