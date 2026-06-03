import React from 'react';
import { Input, Select, Button } from '@shared';
import { Search, X } from 'lucide-react';

const LATENT_TAG_OPTIONS = [
  { value: '', label: 'All latent tags' },
  { value: 'social.sociopetal_seating', label: 'Sociopetal Seating' },
  { value: 'social.shared_attention_anchor', label: 'Shared Attention Anchor' },
  { value: 'social.interactional_visibility', label: 'Interactional Visibility' },
  { value: 'spatial.prospect', label: 'Prospect' },
  { value: 'social.chance_encounter_potential', label: 'Chance Encounter Potential' },
  { value: 'social.disengagement_ease', label: 'Disengagement Ease' },
];

const EFFECT_DOMAIN_OPTIONS = [
  { value: '', label: 'All effect domains' },
  { value: 'cognitive', label: 'Cognitive' },
  { value: 'affective', label: 'Affective' },
  { value: 'behavioral', label: 'Behavioral' },
  { value: 'social', label: 'Social' },
  { value: 'physiological', label: 'Physiological' },
  { value: 'neural', label: 'Neural' },
  { value: 'health', label: 'Health' },
];

export function SearchBar({
  query,
  roomType,
  roomTypes = [],
  imageSet,
  imageSets = [],
  latentTag,
  effectDomain,
  minValue,
  onSearchChange,
  onRoomTypeChange,
  onImageSetChange,
  onLatentTagChange,
  onEffectDomainChange,
  onMinValueChange,
  onMinValueCommit,
  onSearch,
  onClear,
  loading = false,
  hasActiveFilters = false,
}) {
  const showThreshold = latentTag || effectDomain;

  return (
    <div className="bg-white border-b border-gray-200 p-4 shadow-sm space-y-3">
      {/* Row 1: text search + room type + actions */}
      <form
        onSubmit={(e) => { e.preventDefault(); onSearch(); }}
        className="flex flex-col gap-3 md:flex-row md:gap-2 md:items-end"
      >
        <div className="flex-1">
          <Input
            id="search-query"
            label="Search"
            type="text"
            value={query}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="e.g., window, daylight, modern"
            disabled={loading}
          />
        </div>

        <div className="md:w-44">
          <Select
            id="room-type-filter"
            label="Room Type"
            value={roomType}
            onChange={(e) => onRoomTypeChange(e.target.value)}
            options={[
              { value: '', label: 'All rooms' },
              ...roomTypes.map(rt => ({ value: rt, label: rt })),
            ]}
            disabled={loading}
          />
        </div>

        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={loading} className="self-end">
            <Search size={16} />
            Search
          </Button>
          {hasActiveFilters && (
            <Button type="button" variant="ghost" onClick={onClear} disabled={loading} className="self-end" title="Clear all filters">
              <X size={16} />
              Clear
            </Button>
          )}
        </div>
      </form>

      {/* Row 2: Workplan 2 filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-2 sm:items-end">
        <div className="sm:w-52">
          <Select
            id="image-set-filter"
            label="Image Set"
            value={imageSet}
            onChange={(e) => onImageSetChange(e.target.value)}
            options={[
              { value: '', label: 'All image sets' },
              ...imageSets.map(s => ({ value: s.slug, label: s.name })),
            ]}
            disabled={loading}
          />
        </div>

        <div className="sm:w-52">
          <Select
            id="latent-tag-filter"
            label="Latent Tag"
            value={latentTag}
            onChange={(e) => onLatentTagChange(e.target.value)}
            options={LATENT_TAG_OPTIONS}
            disabled={loading}
          />
        </div>

        <div className="sm:w-44">
          <Select
            id="effect-domain-filter"
            label="Effect Domain"
            value={effectDomain}
            onChange={(e) => onEffectDomainChange(e.target.value)}
            options={EFFECT_DOMAIN_OPTIONS}
            disabled={loading}
          />
        </div>

        {showThreshold && (
          <div className="sm:w-28">
            <Input
              id="min-value-filter"
              label="Min Score (0–4)"
              type="number"
              value={minValue}
              min={0}
              max={4}
              step={0.5}
              onChange={(e) => onMinValueChange(e.target.value)}
              onBlur={onMinValueCommit}
              disabled={loading}
            />
          </div>
        )}
      </div>
    </div>
  );
}
