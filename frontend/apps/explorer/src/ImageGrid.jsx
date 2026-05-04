import React from 'react';
import { Skeleton } from '@shared';
import { Image as ImageIcon } from 'lucide-react';

/**
 * ImageGrid component for the explorer journey.
 * Displays a responsive grid of image thumbnails.
 * Each image is clickable to open the detail modal.
 */
export function ImageGrid({ images, loading = false, onImageClick }) {
  if (loading) {
    return (
      <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square rounded-lg" />
        ))}
      </div>
    );
  }

  if (!images?.length) {
    return null;
  }

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

          {/* Badge: validation count */}
          {image.validation_count > 0 && (
            <div className="absolute top-1 right-1 bg-blue-600 text-white rounded-full px-2 py-0.5 text-xs font-semibold">
              {image.validation_count}
            </div>
          )}

          {/* Badge: room type */}
          {image.room_type && (
            <div className="absolute bottom-1 left-1 bg-gray-900/70 text-white rounded px-1.5 py-0.5 text-xs font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
              {image.room_type}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
