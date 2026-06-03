import React, { useState, useEffect } from 'react';
import { Modal, TrustBadge, Skeleton } from '@shared';
import { Loader2, AlertCircle } from 'lucide-react';

export function ImageDetailModal({ open, onClose, image, loading = false, error = null }) {
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    setActiveTab('overview');
  }, [image?.id]);

  if (!open) return null;

  const hasLatents = image?.latent_observations?.length > 0;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'latents', label: 'Latents', visible: hasLatents },
    { id: 'science', label: 'Science Features', visible: !!image?.science },
    { id: 'affordances', label: 'Affordances', visible: image?.science?.affordances?.length > 0 },
  ];

  const visibleTabs = tabs.filter(t => t.visible !== false);

  return (
    <Modal open={open} onClose={onClose} title={`Image ${image?.id || ''}`}>
      <div className="max-h-[80vh] overflow-y-auto flex flex-col gap-4">
        {error && (
          <div role="alert" className="flex items-start gap-3 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm">
            <AlertCircle size={16} className="text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="w-full aspect-video rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
        ) : image ? (
          <>
            {image.url && (
              <img
                src={image.url}
                alt={`Image ${image.id}`}
                className="w-full rounded-lg bg-gray-100"
                style={{ maxHeight: '400px', objectFit: 'cover' }}
              />
            )}

            {visibleTabs.length > 1 && (
              <div className="flex flex-wrap border-b border-gray-200 gap-x-4" role="tablist">
                {visibleTabs.map(tab => (
                  <button
                    key={tab.id}
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={[
                      'pb-2 px-1 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900',
                    ].join(' ')}
                  >
                    {tab.label}
                    {tab.id === 'latents' && hasLatents && (
                      <span className="ml-1.5 text-xs bg-blue-100 text-blue-700 rounded-full px-1.5 py-0.5">
                        {image.latent_observations.length}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}

            {activeTab === 'overview' && <OverviewTab image={image} />}
            {activeTab === 'latents' && hasLatents && (
              <LatentsTab observations={image.latent_observations} effects={image.linked_effects} />
            )}
            {activeTab === 'science' && image.science && <ScienceFeaturesTab science={image.science} />}
            {activeTab === 'affordances' && image.science?.affordances?.length > 0 && (
              <AffordancesTab affordances={image.science.affordances} />
            )}
          </>
        ) : null}
      </div>
    </Modal>
  );
}

// ── shared sub-components ────────────────────────────────────────────────────

function ScoreBar({ value }) {
  const pct = Math.max(0, Math.min(1, value / 4)) * 100;
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-20 h-2 rounded-full bg-gray-200 overflow-hidden">
        <span className="block h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-sm font-semibold tabular-nums text-gray-900">{value} / 4</span>
    </span>
  );
}

function ConfidenceChip({ confidence }) {
  const pct = Math.round(confidence * 100);
  const cls = confidence >= 0.5
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

// ── tab panels ───────────────────────────────────────────────────────────────

function OverviewTab({ image }) {
  const memberships = image.image_sets ?? [];
  return (
    <div className="space-y-4">
      {image.width && image.height && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Dimensions</p>
            <p className="text-sm text-gray-900">{image.width} × {image.height}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase">Validations</p>
            <p className="text-sm text-gray-900">{image.validation_count || 0}</p>
          </div>
        </div>
      )}

      {image.room_type && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Room Type</p>
          <span className="inline-block px-2.5 py-1 bg-blue-50 border border-blue-200 rounded text-sm text-blue-900">
            {image.room_type}
          </span>
        </div>
      )}

      {image.canonical_tags?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Tags</p>
          <div className="flex flex-wrap gap-2">
            {image.canonical_tags.map(tag => (
              <span key={tag} className="inline-block px-2.5 py-1 bg-gray-100 border border-gray-300 rounded text-sm text-gray-700">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {image.science && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Science Status</p>
          <div className="flex items-center gap-2">
            <span className={[
              'px-2.5 py-1 rounded text-sm font-medium',
              image.science.run_status === 'completed' ? 'bg-green-50 text-green-700 border border-green-200'
                : image.science.run_status === 'running' ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : image.science.run_status === 'failed' ? 'bg-red-50 text-red-700 border border-red-200'
                : 'bg-gray-50 text-gray-700 border border-gray-200',
            ].join(' ')}>
              {image.science.run_status}
            </span>
            {image.science.run_id && (
              <span className="text-xs text-gray-500 font-mono">run #{image.science.run_id}</span>
            )}
          </div>
        </div>
      )}

      {/* Provenance from image set memberships */}
      {memberships.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Provenance</p>
          <div className="space-y-3">
            {memberships.map(m => (
              <div key={m.image_set_id} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm space-y-1">
                <p className="font-medium text-gray-900">{m.name}</p>
                {m.source_url && (
                  <a href={m.source_url} target="_blank" rel="noopener noreferrer"
                    className="block text-blue-600 hover:underline truncate text-xs">
                    {m.source_url}
                  </a>
                )}
                {m.photographer && (
                  <p className="text-xs text-gray-600">Photo: {m.photographer}</p>
                )}
                {m.license && (
                  <p className="text-xs text-gray-600">
                    License:{' '}
                    {m.license_url
                      ? <a href={m.license_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{m.license}</a>
                      : m.license}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LatentsTab({ observations, effects = [] }) {
  return (
    <div className="space-y-4">
      {/* Linked effects */}
      {effects.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Linked Effects</p>
          <div className="space-y-2">
            {effects.map((e, i) => (
              <div key={i} className="flex gap-2 text-sm">
                <span className="shrink-0 px-2 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-700 text-xs font-medium capitalize">
                  {e.domain}
                </span>
                <p className="text-gray-700">{e.mechanism}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Observations */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
          Latent Observations ({observations.length})
        </p>
        <div className="space-y-3">
          {observations.map((obs, i) => (
            <LatentObservationCard key={obs.tag_id ?? i} obs={obs} />
          ))}
        </div>
      </div>
    </div>
  );
}

function LatentObservationCard({ obs }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidenceEntries = Object.entries(obs.evidence ?? {});

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-gray-900">{obs.label}</p>
          <p className="text-xs font-mono text-gray-400">{obs.tag_id}</p>
        </div>
        <ConfidenceChip confidence={obs.confidence} />
      </div>

      {/* Score bar */}
      <ScoreBar value={obs.value} />

      {/* Detector */}
      <p className="text-xs text-gray-500">Detector: <span className="font-mono">{obs.detector_version}</span></p>

      {/* Evidence toggle */}
      {evidenceEntries.length > 0 && (
        <div>
          <button
            onClick={() => setEvidenceOpen(o => !o)}
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
    </div>
  );
}

function ScienceFeaturesTab({ science }) {
  if (!science.features || Object.keys(science.features).length === 0) {
    return (
      <div className="py-6 text-center text-gray-500">
        <p>No science features available for this image.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {Object.entries(science.features).map(([key, envelope]) => (
        <div key={key} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <p className="text-xs font-mono text-gray-500 uppercase tracking-wide">{key}</p>
              <p className="text-sm font-semibold text-gray-900">{envelope.value.toFixed(3)}</p>
            </div>
            <TrustBadge evaluation_status={envelope.evaluation_status} />
          </div>
          {envelope.confidence_interval_95 && (
            <div className="text-xs text-gray-600 mb-1">
              95% CI: [{envelope.confidence_interval_95[0].toFixed(3)}, {envelope.confidence_interval_95[1].toFixed(3)}]
            </div>
          )}
          <div className="text-xs text-gray-500 space-y-0.5">
            {envelope.model_id && <div><span className="font-semibold">Model:</span> {envelope.model_id}</div>}
            {envelope.n_training > 0 && <div><span className="font-semibold">Training samples:</span> {envelope.n_training}</div>}
            {envelope.notes && <div className="italic mt-1">{envelope.notes}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

function AffordancesTab({ affordances }) {
  return (
    <div className="space-y-3">
      {affordances.map(aff => (
        <div key={aff.key} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <p className="text-xs font-mono text-gray-500 uppercase tracking-wide">{aff.key}</p>
              <p className="text-sm text-gray-700">{aff.label}</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{aff.score.toFixed(2)}</p>
            </div>
            {aff.confidence && <TrustBadge evaluation_status={aff.confidence.evaluation_status} />}
          </div>
          {aff.confidence && (
            <div className="text-xs text-gray-500 space-y-0.5">
              {aff.confidence.confidence_interval_95 && (
                <div>95% CI: [{aff.confidence.confidence_interval_95[0].toFixed(2)}, {aff.confidence.confidence_interval_95[1].toFixed(2)}]</div>
              )}
              {aff.confidence.model_id && <div><span className="font-semibold">Model:</span> {aff.confidence.model_id}</div>}
              {aff.confidence.n_training > 0 && <div><span className="font-semibold">Training samples:</span> {aff.confidence.n_training}</div>}
              {aff.confidence.notes && <div className="italic mt-1">{aff.confidence.notes}</div>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
