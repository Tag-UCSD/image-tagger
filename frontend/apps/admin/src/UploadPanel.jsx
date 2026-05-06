import React, { useState, useRef, useCallback } from 'react';
import { admin, Button } from '@shared';
import { UploadCloud, X, CheckCircle } from 'lucide-react';

const MAX_FILES = 200;
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const ALLOWED_EXTS = new Set(['jpg', 'jpeg', 'png', 'webp']);

function isAllowed(file) {
    if (ALLOWED_TYPES.has(file.type)) return true;
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    return ALLOWED_EXTS.has(ext);
}

function validateFiles(files) {
    if (files.length > MAX_FILES) {
        return [`Batch too large: ${files.length} files selected (max ${MAX_FILES}).`];
    }
    const errors = [];
    for (const file of files) {
        if (!isAllowed(file)) {
            errors.push(`"${file.name}" is not a JPEG, PNG, or WebP file.`);
        } else if (file.size > MAX_SIZE_BYTES) {
            errors.push(`"${file.name}" exceeds 10 MiB (${(file.size / 1024 / 1024).toFixed(1)} MiB).`);
        }
    }
    return errors;
}

export function UploadPanel() {
    const [dragging, setDragging] = useState(false);
    const [errors, setErrors] = useState([]);
    const [queue, setQueue] = useState([]);
    const [uploading, setUploading] = useState(false);
    const inputRef = useRef(null);

    const handleFiles = useCallback(async (fileList) => {
        const files = Array.isArray(fileList) ? fileList : Array.from(fileList);
        setErrors([]);
        const errs = validateFiles(files);
        if (errs.length) {
            setErrors(errs);
            return;
        }
        setUploading(true);
        try {
            const data = await admin.upload(files);
            setQueue(prev => [{ ...data, _key: `${data.job_id}-${Date.now()}` }, ...prev]);
        } catch (err) {
            setErrors([err.message || 'Upload failed.']);
        } finally {
            setUploading(false);
        }
    }, []);

    const onDrop = useCallback((e) => {
        e.preventDefault();
        setDragging(false);
        const dt = e.dataTransfer;
        // Prefer files (most browsers); fall back to items for broader compatibility.
        if (dt.files?.length) {
            handleFiles(Array.from(dt.files));
        } else if (dt.items?.length) {
            const files = Array.from(dt.items)
                .filter(item => item.kind === 'file')
                .map(item => item.getAsFile())
                .filter(Boolean);
            if (files.length) handleFiles(files);
        }
    }, [handleFiles]);

    return (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                <UploadCloud className="text-blue-500" size={18} />
                <h2 className="font-semibold text-gray-900 text-sm">Upload Images</h2>
            </div>
            <div className="p-4 space-y-3">
                <p className="text-xs text-gray-500">
                    JPEG, PNG, or WebP only · max 10 MiB per file · max 200 files per batch
                </p>

                <div
                    role="button"
                    tabIndex={0}
                    aria-label="Drop zone — click or drag images to upload"
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                        dragging
                            ? 'border-blue-400 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                    onDrop={onDrop}
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onClick={() => inputRef.current?.click()}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
                    }}
                >
                    <UploadCloud size={28} className="mx-auto text-gray-300 mb-2" />
                    <p className="text-sm text-gray-500">
                        {uploading ? 'Uploading…' : 'Drop images here or click to browse'}
                    </p>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                    className="sr-only"
                    aria-hidden="true"
                    onChange={(e) => {
                        if (e.target.files?.length) {
                            handleFiles(e.target.files);
                            e.target.value = '';
                        }
                    }}
                />

                {errors.length > 0 && (
                    <div role="alert" className="rounded-lg bg-red-50 border border-red-200 p-3 space-y-1">
                        {errors.map((msg, i) => (
                            <p key={i} className="text-xs text-red-700 flex items-start gap-1.5">
                                <X size={12} className="mt-0.5 flex-shrink-0 text-red-500" />
                                {msg}
                            </p>
                        ))}
                    </div>
                )}

                {queue.length > 0 && (
                    <div role="status" className="space-y-2">
                        {queue.map((job) => (
                            <div key={job._key} className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 space-y-0.5">
                                <div className="flex items-center gap-2 mb-1">
                                    <CheckCircle size={14} className="text-emerald-600" />
                                    <span className="text-xs font-semibold text-emerald-800">
                                        Queued — {job.items} file{job.items !== 1 ? 's' : ''}
                                    </span>
                                </div>
                                <p className="text-xs text-emerald-700">
                                    Status: <span className="font-mono">{job.status}</span>
                                </p>
                                <p className="text-xs text-emerald-700">
                                    Job: <span className="font-mono">{job.job_id}</span>
                                </p>
                                <p className="text-xs text-emerald-700">
                                    Image IDs: <span className="font-mono">{job.image_ids?.join(', ')}</span>
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
