import React from 'react';

export function Pagination({ page, total, page_size = 20, onChange }) {
  const totalPages = Math.max(1, Math.ceil(total / page_size));
  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  return (
    <nav aria-label="Pagination" className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => onChange(page - 1)}
        disabled={!hasPrev}
        aria-label="Previous page"
        className={[
          'px-3 py-1.5 rounded text-sm font-medium border',
          'focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          hasPrev
            ? 'border-gray-300 text-gray-700 hover:bg-gray-50'
            : 'border-gray-200 text-gray-400',
        ].join(' ')}
      >
        Previous
      </button>

      <span
        aria-current="page"
        aria-label={`Page ${page} of ${totalPages}`}
        className="px-3 py-1.5 text-sm text-gray-700"
      >
        {page} / {totalPages}
      </span>

      <button
        type="button"
        onClick={() => onChange(page + 1)}
        disabled={!hasNext}
        aria-label="Next page"
        className={[
          'px-3 py-1.5 rounded text-sm font-medium border',
          'focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-1',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          hasNext
            ? 'border-gray-300 text-gray-700 hover:bg-gray-50'
            : 'border-gray-200 text-gray-400',
        ].join(' ')}
      >
        Next
      </button>
    </nav>
  );
}
