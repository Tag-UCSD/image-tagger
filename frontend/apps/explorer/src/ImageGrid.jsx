import React from 'react';
import { Skeleton } from '@shared';
import { Image as ImageIcon } from 'lucide-react';

function confidenceColor(confidence) {
  if (confidence >= 0.5) return 'bg-green-500';
  if (confidence >= 0.3) return 'bg-yellow-400';
  return 'bg-red-400';
}

function ScoreBar({ value }) {
  const pct = Math.max(0, Math.min(1, value / 4)) * 100;
  return (
    <span className="flex items-center gap-1 shrink-0">
      <span className="w-12 h-1.5 rounded-full bg-white/30 overflow-hidden">
        <span className="block h-full rounded-full bg-white" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-white/90 text-xs font-semibold tabular-nums">{value}/4</span>
    </span>
  );
}

function LatentStrip({ topLatent, effectDomain }) {
  if (!topLatent) return null;
  const { label, value, confidence, effect_mechanism } = topLatent;
  const showMechanism = effectDomain && effect_mechanism;

  return (
    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent px-2 pt-4 pb-1.5">
      <div className="flex items-center gap-1.5 min-w-0">
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${confidenceColor(confidence)}`} />
        <span className="text-white text-xs font-medium truncate flex-1">{label}</span>
        <ScoreBar value={value} />
      </div>
      {showMechanism && (
        <p className="text-white/70 text-xs leading-tight mt-0.5 line-clamp-1">{effect_mechanism}</p>
      )}
    </div>
  );
}

export function ImageGrid({ images, loading = false, onImageClick, effectDomain = '' }) {
  if (loading) {
    return (
      <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square rounded-lg" />
        ))}
      </div>
    );
  }

  if (!images?.length) return null;

  return (
    <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {images.map((image) => (
        <button
          key={image.id}
          onClick={() => onImageClick(image.id)}
          className="relative group overflow-hidden rounded-lg aspect-square bg-gray-100 hover:ring-2 hover:ring-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1 transition-all"
          title={`Image ${image.id}`}
          aria-label={`Image ${image.id}, ${image.room_type || 'unknown room'}`}
        >
          {image.thumbnail_url ? (
            <img
              src={image.thumbnail_url}
              alt={`Image ${image.id}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-200">
              <ImageIcon size={24} className="text-gray-400" />
            </div>
          )}

          {/* validation count */}
          {image.validation_count > 0 && (
            <div className="absolute top-1 right-1 bg-blue-600 text-white rounded-full px-2 py-0.5 text-xs font-semibold">
              {image.validation_count}
            </div>
          )}

          {/* room type — hover only when no latent strip */}
          {image.room_type && !image.top_latent && (
            <div className="absolute bottom-1 left-1 bg-gray-900/70 text-white rounded px-1.5 py-0.5 text-xs font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
              {image.room_type}
            </div>
          )}

          {/* latent summary strip */}
          <LatentStrip topLatent={image.top_latent} effectDomain={effectDomain} />
        </button>
      ))}
    </div>
  );
}
