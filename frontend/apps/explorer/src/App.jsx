import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Header, explorer, ErrorBanner, EmptyState, Pagination } from '@shared';
import { Search as SearchIcon, AlertCircle } from 'lucide-react';
import { SearchBar } from './SearchBar';
import { ImageGrid } from './ImageGrid';
import { ImageDetailModal } from './ImageDetailModal';

/**
 * Explorer app - public image search and detail journey.
 * URL-synced state via query parameters.
 * Anonymous requests (no Authorization header).
 */
export default function ExplorerApp() {
  // State from URL query params
  const [query, setQuery] = useState('');
  const [roomType, setRoomType] = useState('');
  const [page, setPage] = useState(1);
  
  // Search results
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Image detail modal
  const [selectedImageId, setSelectedImageId] = useState(null);
  const [detailImage, setDetailImage] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // Available room types (from first search or static)
  const [roomTypes, setRoomTypes] = useState([]);

  // Initialize from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQuery(params.get('q') ?? '');
    setRoomType(params.get('room_type') ?? '');
    const p = params.get('page');
    setPage(p ? Math.max(1, parseInt(p, 10)) : 1);
  }, []);

  // Update URL whenever search state changes
  const updateUrl = useCallback((q, rt, p) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (rt) params.set('room_type', rt);
    if (p > 1) params.set('page', String(p));
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params : ''}`;
    window.history.replaceState(null, '', newUrl);
  }, []);

  // Perform search
  const performSearch = useCallback(async (q, rt, p) => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await explorer.search({
        q,
        page: p,
        page_size: 20,
        room_type: rt || undefined,
      });

      setResults(response);

      // Extract room types from results for filter options
      if (response.items?.length > 0) {
        const types = new Set(
          response.items
            .filter(item => item.room_type)
            .map(item => item.room_type)
        );
        setRoomTypes(Array.from(types).sort());
      }
    } catch (err) {
      console.error('Search failed:', err);
      setError(err.message || 'Search failed');
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch image detail when selectedImageId changes
  useEffect(() => {
    if (!selectedImageId) {
      setDetailImage(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    setDetailImage(null);

    (async () => {
      try {
        const image = await explorer.getImage(selectedImageId);
        if (!cancelled) {
          setDetailImage(image);
          setDetailError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setDetailError(err.message || 'Failed to load image details');
          setDetailImage(null);
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedImageId]);

  // Handlers
  const handleSearch = () => {
    setPage(1);
    updateUrl(query, roomType, 1);
    performSearch(query, roomType, 1);
  };

  const handleQueryChange = (value) => {
    setQuery(value);
  };

  const handleRoomTypeChange = (value) => {
    setRoomType(value);
    // Reset page and search when filter changes
    setPage(1);
    updateUrl(query, value, 1);
    performSearch(query, value, 1);
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    updateUrl(query, roomType, newPage);
    performSearch(query, roomType, newPage);
  };

  const handleImageClick = (imageId) => {
    setSelectedImageId(imageId);
  };

  const handleModalClose = () => {
    setSelectedImageId(null);
  };

  // Initial search on mount
  useEffect(() => {
    performSearch(query, roomType, page);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <Header title="Explorer" appName="Image Tagger" />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Search bar */}
        <SearchBar
          query={query}
          roomType={roomType}
          onSearchChange={handleQueryChange}
          onRoomTypeChange={handleRoomTypeChange}
          onSearch={handleSearch}
          loading={loading}
          roomTypes={roomTypes}
        />

        {/* Error banner */}
        {error && (
          <div className="px-4 py-3">
            <ErrorBanner
              message={error}
              code="SEARCH_ERROR"
              onDismiss={() => setError(null)}
            />
          </div>
        )}

        {/* Results */}
        <div className="flex-1 overflow-y-auto">
          {loading && !results ? (
            <div className="p-8 text-center text-gray-500">
              <div className="animate-spin inline-block mb-3">
                <SearchIcon size={24} />
              </div>
              <p>Searching...</p>
            </div>
          ) : error ? (
            <EmptyState
              icon={<AlertCircle size={32} />}
              title="Search failed"
              message={error}
              action={{
                label: 'Try again',
                onClick: handleSearch,
                variant: 'primary',
              }}
            />
          ) : results && results.items.length === 0 ? (
            <EmptyState
              icon={<SearchIcon size={32} />}
              title="No images found"
              message={
                query || roomType
                  ? 'Try adjusting your search or filters.'
                  : 'No images available.'
              }
            />
          ) : results ? (
            <>
              <ImageGrid
                images={results.items}
                loading={loading}
                onImageClick={handleImageClick}
              />

              {/* Pagination */}
              {results.total > results.page_size && (
                <div className="px-4 py-4 border-t border-gray-200 bg-white flex justify-center">
                  <Pagination
                    page={results.page}
                    total={results.total}
                    page_size={results.page_size}
                    onChange={handlePageChange}
                  />
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>

      {/* Image detail modal */}
      <ImageDetailModal
        open={selectedImageId !== null}
        onClose={handleModalClose}
        image={detailImage}
        loading={detailLoading}
        error={detailError}
      />
    </div>
  );
}
