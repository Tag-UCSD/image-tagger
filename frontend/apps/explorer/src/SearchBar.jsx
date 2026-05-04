import React, { useState, useCallback } from 'react';
import { Input, Select, Button } from '@shared';
import { Search, X } from 'lucide-react';

/**
 * SearchBar component for the explorer journey.
 * Manages search query and room_type filter.
 * Delegates to parent for search execution.
 */
export function SearchBar({
  query,
  roomType,
  onSearchChange,
  onRoomTypeChange,
  onSearch,
  loading = false,
  roomTypes = [],
}) {
  const handleSubmit = (e) => {
    e?.preventDefault?.();
    onSearch();
  };

  const handleClear = () => {
    onSearchChange('');
    onRoomTypeChange('');
  };

  return (
    <div className="bg-white border-b border-gray-200 p-4 shadow-sm">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 md:flex-row md:gap-2 md:items-end">
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

        <div className="flex-1">
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
          <Button
            type="submit"
            variant="primary"
            disabled={loading}
            className="self-end"
          >
            <Search size={16} />
            Search
          </Button>

          {(query || roomType) && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              disabled={loading}
              className="self-end"
              title="Clear filters"
            >
              <X size={16} />
              Clear
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
