import React, { useState, useEffect } from 'react';
import { Modal, TrustBadge, Skeleton } from '@shared';
import { Loader2, AlertCircle } from 'lucide-react';

/**
 * ImageDetailModal component for the explorer journey.
 * Shows full image with Overview, Science Features, and Affordances tabs.
 */
export function ImageDetailModal({
  open,
  onClose,
  image,
  loading = false,
  error = null,
}) {
  const [activeTab, setActiveTab] = useState('overview');

  // Reset tab on image change
  useEffect(() => {
    setActiveTab('overview');
  }, [image?.id]);

  if (!open) return null;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'science', label: 'Science Features', visible: image?.science },
    { id: 'affordances', label: 'Affordances', visible: image?.science?.affordances?.length > 0 },
  ];

  const visibleTabs = tabs.filter(t => t.visible !== false);

  return (
    <Modal open={open} onClose={onClose} title={`Image ${image?.id || ''}`}>
      <div className="max-h-[80vh] overflow-y-auto flex flex-col gap-4">
        {/* Error state */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm"
          >
            <AlertCircle size={16} className="text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Loading state */}
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
            {/* Full image */}
            {image.url && (
              <img
                src={image.url}
                alt={`Image ${image.id}`}
                className="w-full rounded-lg bg-gray-100"
                style={{ maxHeight: '400px', objectFit: 'cover' }}
              />
            )}

            {/* Tab navigation */}
            {visibleTabs.length > 1 && (
              <div className="flex border-b border-gray-200 gap-4" role="tablist">
                {visibleTabs.map(tab => (
                  <button
                    key={tab.id}
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={[
                      'pb-2 px-1 text-sm font-medium border-b-2 transition-colors',
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900',
                    ].join(' ')}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            )}

            {/* Tab content */}
            {activeTab === 'overview' && (
              <OverviewTab image={image} />
            )}
            {activeTab === 'science' && image.science && (
              <ScienceFeaturesTab science={image.science} />
            )}
            {activeTab === 'affordances' && image.science?.affordances?.length > 0 && (
              <AffordancesTab affordances={image.science.affordances} />
            )}
          </>
        ) : null}
      </div>
    </Modal>
  );
}

/**
 * Overview tab: image metadata and tags
 */
function OverviewTab({ image }) {
  return (
    <div className="space-y-4">
      {/* Dimensions */}
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

      {/* Room type */}
      {image.room_type && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Room Type</p>
          <span className="inline-block px-2.5 py-1 bg-blue-50 border border-blue-200 rounded text-sm text-blue-900">
            {image.room_type}
          </span>
        </div>
      )}

      {/* Canonical tags */}
      {image.canonical_tags && image.canonical_tags.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Tags</p>
          <div className="flex flex-wrap gap-2">
            {image.canonical_tags.map(tag => (
              <span
                key={tag}
                className="inline-block px-2.5 py-1 bg-gray-100 border border-gray-300 rounded text-sm text-gray-700"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Science run status */}
      {image.science && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Science Status</p>
          <div className="flex items-center gap-2">
            <span className={[
              'px-2.5 py-1 rounded text-sm font-medium',
              image.science.run_status === 'completed'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : image.science.run_status === 'running'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : image.science.run_status === 'failed'
                ? 'bg-red-50 text-red-700 border border-red-200'
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
    </div>
  );
}

/**
 * Science Features tab: displays trust-wrapped feature values
 */
function ScienceFeaturesTab({ science }) {
  if (!science.features || Object.keys(science.features).length === 0) {
    return (
      <div className="py-6 text-center text-gray-500">
        <p>No science features available for this image.</p>
      </div>
    );
  }

  const featureEntries = Object.entries(science.features);

  return (
    <div className="space-y-3">
      {featureEntries.map(([key, envelope]) => (
        <div key={key} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <p className="text-xs font-mono text-gray-500 uppercase tracking-wide">{key}</p>
              <p className="text-sm font-semibold text-gray-900">{envelope.value.toFixed(3)}</p>
            </div>
            <TrustBadge evaluation_status={envelope.evaluation_status} />
          </div>

          {/* Confidence interval */}
          {envelope.confidence_interval_95 && (
            <div className="text-xs text-gray-600 mb-1">
              95% CI: [{envelope.confidence_interval_95[0].toFixed(3)}, {envelope.confidence_interval_95[1].toFixed(3)}]
            </div>
          )}

          {/* Model info */}
          <div className="text-xs text-gray-500 space-y-0.5">
            {envelope.model_id && (
              <div><span className="font-semibold">Model:</span> {envelope.model_id}</div>
            )}
            {envelope.n_training > 0 && (
              <div><span className="font-semibold">Training samples:</span> {envelope.n_training}</div>
            )}
            {envelope.notes && (
              <div className="italic mt-1">{envelope.notes}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Affordances tab: displays predictions with confidence envelopes
 */
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
            {aff.confidence && (
              <TrustBadge evaluation_status={aff.confidence.evaluation_status} />
            )}
          </div>

          {/* Confidence data */}
          {aff.confidence && (
            <div className="text-xs text-gray-500 space-y-0.5">
              {aff.confidence.confidence_interval_95 && (
                <div>
                  95% CI: [{aff.confidence.confidence_interval_95[0].toFixed(2)}, {aff.confidence.confidence_interval_95[1].toFixed(2)}]
                </div>
              )}
              {aff.confidence.model_id && (
                <div><span className="font-semibold">Model:</span> {aff.confidence.model_id}</div>
              )}
              {aff.confidence.n_training > 0 && (
                <div><span className="font-semibold">Training samples:</span> {aff.confidence.n_training}</div>
              )}
              {aff.confidence.notes && (
                <div className="italic mt-1">{aff.confidence.notes}</div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
