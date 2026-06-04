import React, { useState } from 'react';
import { admin, Button } from '@shared';
import { FolderInput, CheckCircle, X, AlertCircle } from 'lucide-react';

const EXAMPLE_MANIFEST = JSON.stringify({
  name: "My Collection",
  slug: "my-collection-2026",
  description: "Example image set",
  images: [
    { filename: "room-01.jpg", url: "https://example.com/room-01.jpg", room_type: "living_room", photographer: "J. Doe", license: "CC BY 4.0" },
    { filename: "room-02.jpg", url: "https://example.com/room-02.jpg", room_type: "bedroom" },
  ],
}, null, 2);

function validateManifest(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { error: 'Invalid JSON — check for missing commas, brackets, or quotes.' };
  }
  if (!Array.isArray(parsed.images) || parsed.images.length === 0) {
    return { error: 'Image list must not be empty. Add at least one entry to "images".' };
  }
  return { parsed };
}

export function ImageSetImportPanel() {
  const [text, setText] = useState('');
  const [validationError, setValidationError] = useState(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError(null);
    setApiError(null);
    setResult(null);

    const { error, parsed } = validateManifest(text);
    if (error) {
      setValidationError(error);
      return;
    }

    setImporting(true);
    try {
      const data = await admin.importImageSet(parsed);
      setResult(data);
    } catch (err) {
      const detail = err.body?.error?.details?.[0]?.message ?? err.message ?? 'Import failed.';
      setApiError(detail);
    } finally {
      setImporting(false);
    }
  };

  const handleReset = () => {
    setText('');
    setResult(null);
    setValidationError(null);
    setApiError(null);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 flex items-center gap-2">
        <FolderInput className="text-purple-500" size={18} />
        <h2 className="font-semibold text-gray-900 text-sm">Import Image Set</h2>
      </div>

      <div className="p-4 space-y-3">
        {result ? (
          <ImportSuccess result={result} onReset={handleReset} />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <p className="text-xs text-gray-500">
              Paste a JSON manifest with <code className="bg-gray-100 px-1 rounded">name</code>,{' '}
              <code className="bg-gray-100 px-1 rounded">slug</code>, and{' '}
              <code className="bg-gray-100 px-1 rounded">images</code> array.
            </p>

            <textarea
              id="manifest-input"
              value={text}
              onChange={(e) => { setText(e.target.value); setValidationError(null); }}
              placeholder="Paste JSON manifest here…"
              rows={7}
              disabled={importing}
              className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-xs font-mono text-gray-800 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-y disabled:opacity-50"
              aria-label="JSON manifest input"
            />

            {validationError && (
              <div role="alert" className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2">
                <X size={14} className="text-red-500 mt-0.5 shrink-0" />
                <p className="text-xs text-red-700">{validationError}</p>
              </div>
            )}

            {apiError && (
              <div role="alert" className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2">
                <AlertCircle size={14} className="text-red-500 mt-0.5 shrink-0" />
                <p className="text-xs text-red-700">{apiError}</p>
              </div>
            )}

            <div className="flex items-center gap-2">
              <Button type="submit" variant="primary" disabled={!text.trim() || importing}>
                {importing ? 'Importing…' : 'Import Set'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={importing}
                onClick={() => { setText(EXAMPLE_MANIFEST); setValidationError(null); }}
              >
                Use example
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function ImportSuccess({ result, onReset }) {
  const hasErrors = result.errors?.length > 0;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <CheckCircle size={16} className="text-emerald-600 shrink-0" />
        <span className="text-sm font-semibold text-emerald-800">Import complete</span>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
        <dt className="text-gray-500">Set ID</dt>
        <dd className="font-mono text-gray-900">{result.image_set_id}</dd>
        <dt className="text-gray-500">Slug</dt>
        <dd className="font-mono text-gray-900">{result.slug}</dd>
        <dt className="text-gray-500">In file</dt>
        <dd className="text-gray-900">{result.total_in_file}</dd>
        <dt className="text-gray-500">Created images</dt>
        <dd className="text-gray-900">{result.created_images}</dd>
        <dt className="text-gray-500">Reused images</dt>
        <dd className="text-gray-900">{result.reused_images}</dd>
        <dt className="text-gray-500">Created items</dt>
        <dd className="text-gray-900">{result.created_items}</dd>
        <dt className="text-gray-500">Skipped items</dt>
        <dd className="text-gray-900">{result.skipped_items}</dd>
      </dl>

      {hasErrors && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 space-y-1">
          <p className="text-xs font-semibold text-amber-800">{result.errors.length} row error{result.errors.length !== 1 ? 's' : ''}:</p>
          {result.errors.map((e, i) => (
            <p key={i} className="text-xs text-amber-700">
              <span className="font-mono">{e.filename}</span>: {e.message}
            </p>
          ))}
        </div>
      )}

      <Button variant="secondary" onClick={onReset}>Import another</Button>
    </div>
  );
}
