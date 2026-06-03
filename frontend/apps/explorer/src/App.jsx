import React, { useState, useEffect, useCallback } from 'react';
import { Header, explorer, ErrorBanner, EmptyState, Pagination } from '@shared';
import { Search as SearchIcon, AlertCircle } from 'lucide-react';
import { SearchBar } from './SearchBar';
import { ImageGrid } from './ImageGrid';
import { ImageDetailModal } from './ImageDetailModal';

export default function ExplorerApp() {
  const [query, setQuery] = useState('');
  const [roomType, setRoomType] = useState('');
  const [imageSet, setImageSet] = useState('');
  const [latentTag, setLatentTag] = useState('');
  const [effectDomain, setEffectDomain] = useState('');
  const [minValue, setMinValue] = useState('2.5');
  const [page, setPage] = useState(1);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [imageSets, setImageSets] = useState([]);

  const [selectedImageId, setSelectedImageId] = useState(null);
  const [detailImage, setDetailImage] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const [roomTypes, setRoomTypes] = useState([]);

  useEffect(() => {
    explorer.listImageSets().then(r => setImageSets(r.items ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q') ?? '';
    const rt = params.get('room_type') ?? '';
    const is = params.get('image_set') ?? '';
    const lt = params.get('latent_tag') ?? '';
    const ed = params.get('effect_domain') ?? '';
    const mv = params.get('min_value') ?? '2.5';
    const pg = Math.max(1, parseInt(params.get('page') || '1', 10));
    setQuery(q);
    setRoomType(rt);
    setImageSet(is);
    setLatentTag(lt);
    setEffectDomain(ed);
    setMinValue(mv);
    setPage(pg);
    performSearch(q, rt, is, lt, ed, mv, pg);
  }, []);

  const updateUrl = useCallback((q, rt, is, lt, ed, mv, p) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (rt) params.set('room_type', rt);
    if (is) params.set('image_set', is);
    if (lt) params.set('latent_tag', lt);
    if (ed) params.set('effect_domain', ed);
    if ((lt || ed) && mv) params.set('min_value', mv);
    if (p > 1) params.set('page', String(p));
    const newUrl = `${window.location.pathname}${params.toString() ? '?' + params : ''}`;
    window.history.replaceState(null, '', newUrl);
  }, []);

  const performSearch = useCallback(async (q, rt, is, lt, ed, mv, p) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await explorer.search({
        q,
        page: p,
        page_size: 20,
        room_type: rt || undefined,
        image_set: is || undefined,
        latent_tag: lt || undefined,
        effect_domain: ed || undefined,
        min_value: (lt || ed) && mv !== '' ? Number(mv) : undefined,
      });
      setResults(response);
      if (response.items?.length > 0) {
        const types = new Set(
          response.items.filter(i => i.room_type).map(i => i.room_type)
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

  useEffect(() => {
    if (!selectedImageId) { setDetailImage(null); return; }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    setDetailImage(null);
    (async () => {
      try {
        const image = await explorer.getImage(selectedImageId);
        if (!cancelled) { setDetailImage(image); setDetailError(null); }
      } catch (err) {
        if (!cancelled) { setDetailError(err.message || 'Failed to load image details'); setDetailImage(null); }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedImageId]);

  const triggerSearch = useCallback((overrides = {}) => {
    const q = overrides.q !== undefined ? overrides.q : query;
    const rt = overrides.roomType !== undefined ? overrides.roomType : roomType;
    const is = overrides.imageSet !== undefined ? overrides.imageSet : imageSet;
    const lt = overrides.latentTag !== undefined ? overrides.latentTag : latentTag;
    const ed = overrides.effectDomain !== undefined ? overrides.effectDomain : effectDomain;
    const mv = overrides.minValue !== undefined ? overrides.minValue : minValue;
    const p = overrides.page !== undefined ? overrides.page : 1;
    setPage(p);
    updateUrl(q, rt, is, lt, ed, mv, p);
    performSearch(q, rt, is, lt, ed, mv, p);
  }, [query, roomType, imageSet, latentTag, effectDomain, minValue, updateUrl, performSearch]);

  const handleSearch = () => triggerSearch({ page: 1 });

  const handleQueryChange = (value) => setQuery(value);

  const handleRoomTypeChange = (value) => {
    setRoomType(value);
    triggerSearch({ roomType: value });
  };

  const handleImageSetChange = (value) => {
    setImageSet(value);
    triggerSearch({ imageSet: value });
  };

  const handleLatentTagChange = (value) => {
    setLatentTag(value);
    triggerSearch({ latentTag: value });
  };

  const handleEffectDomainChange = (value) => {
    setEffectDomain(value);
    triggerSearch({ effectDomain: value });
  };

  const handleMinValueChange = (value) => {
    setMinValue(value);
  };

  const handleMinValueCommit = () => {
    triggerSearch({ minValue });
  };

  const handleClear = () => {
    setQuery('');
    setRoomType('');
    setImageSet('');
    setLatentTag('');
    setEffectDomain('');
    setMinValue('2.5');
    triggerSearch({ q: '', roomType: '', imageSet: '', latentTag: '', effectDomain: '', minValue: '2.5', page: 1 });
  };

  const handlePageChange = (newPage) => triggerSearch({ page: newPage });

  const hasActiveFilters = query || roomType || imageSet || latentTag || effectDomain;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header title="Explorer" appName="Image Tagger" />

      <div className="flex-1 flex flex-col overflow-hidden">
        <SearchBar
          query={query}
          roomType={roomType}
          roomTypes={roomTypes}
          imageSet={imageSet}
          imageSets={imageSets}
          latentTag={latentTag}
          effectDomain={effectDomain}
          minValue={minValue}
          onSearchChange={handleQueryChange}
          onRoomTypeChange={handleRoomTypeChange}
          onImageSetChange={handleImageSetChange}
          onLatentTagChange={handleLatentTagChange}
          onEffectDomainChange={handleEffectDomainChange}
          onMinValueChange={handleMinValueChange}
          onMinValueCommit={handleMinValueCommit}
          onSearch={handleSearch}
          onClear={handleClear}
          loading={loading}
          hasActiveFilters={!!hasActiveFilters}
        />

        {error && (
          <div className="px-4 py-3">
            <ErrorBanner message={error} code="SEARCH_ERROR" onDismiss={() => setError(null)} />
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {loading && !results ? (
            <div className="p-8 text-center text-gray-500">
              <div className="animate-spin inline-block mb-3"><SearchIcon size={24} /></div>
              <p>Searching...</p>
            </div>
          ) : error ? (
            <EmptyState
              icon={<AlertCircle size={32} />}
              title="Search failed"
              message={error}
              action={{ label: 'Try again', onClick: handleSearch, variant: 'primary' }}
            />
          ) : results && results.items.length === 0 ? (
            <EmptyState
              icon={<SearchIcon size={32} />}
              title="No images found"
              message={hasActiveFilters ? 'Try adjusting your search or filters.' : 'No images available.'}
            />
          ) : results ? (
            <>
              <ImageGrid images={results.items} loading={loading} onImageClick={setSelectedImageId} effectDomain={effectDomain} />
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

      <ImageDetailModal
        open={selectedImageId !== null}
        onClose={() => setSelectedImageId(null)}
        image={detailImage}
        loading={detailLoading}
        error={detailError}
      />
    </div>
  );
}
