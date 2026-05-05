import React, { useState, useCallback, useEffect, useRef } from 'react';
import { workbench, demoAccess, Header, EmptyState, ErrorBanner } from '@shared';
import { AttributeForm } from './AttributeForm';
import { KeyboardShortcuts } from './KeyboardShortcuts';
import { RefreshCw, Inbox, AlertTriangle, Loader2, ShieldOff } from 'lucide-react';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Possible states: 'loading' | 'assignment' | 'empty' | 'error' | 'no-token'
export default function WorkbenchApp() {
  const [appState, setAppState] = useState('loading');
  const [current, setCurrent] = useState(null); // { image, assignment }
  const [errorMsg, setErrorMsg] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [count, setCount] = useState(0);
  const formRef = useRef(null);

  const loadNext = useCallback(async () => {
    setAppState('loading');
    setErrorMsg(null);
    setSubmitError(null);
    try {
      const data = await workbench.getNext();
      if (data.empty) {
        setCurrent(null);
        setAppState('empty');
      } else {
        setCurrent(data);
        setAppState('assignment');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load next assignment');
      setAppState('error');
    }
  }, []);

  useEffect(() => {
    if (!USE_MOCKS && !demoAccess.hasTaggerToken()) {
      setAppState('no-token');
      return;
    }
    loadNext();
  }, [loadNext]);

  const handleSubmit = useCallback(async (value, duration_ms) => {
    if (!current) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await workbench.validate({
        image_id: current.image.id,
        attribute_key: current.assignment.attribute_key,
        value,
        duration_ms,
      });
      setCount((c) => c + 1);
      await loadNext();
    } catch (err) {
      setSubmitError(err.message || 'Submission failed — please try again');
      setSubmitting(false);
    }
  }, [current, loadNext]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header title="Workbench" appName="Image Tagger" />

      <KeyboardShortcuts
        enabled={appState === 'assignment' && !submitting}
        onSubmit={() => formRef.current?.submit()}
      />

      <div className="flex-1 overflow-y-auto">
        {appState === 'loading' && <LoadingView />}
        {appState === 'no-token' && <NoTokenView />}
        {appState === 'error' && (
          <ErrorView message={errorMsg} onRetry={loadNext} />
        )}
        {appState === 'empty' && <EmptyQueueView onRetry={loadNext} />}
        {appState === 'assignment' && current && (
          <AssignmentView
            current={current}
            count={count}
            formRef={formRef}
            submitting={submitting}
            submitError={submitError}
            onSubmit={handleSubmit}
            onDismissError={() => setSubmitError(null)}
          />
        )}
      </div>
    </div>
  );
}

function LoadingView() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-500">
      <Loader2 size={32} className="animate-spin" />
      <p className="text-sm">Loading next assignment…</p>
    </div>
  );
}

function NoTokenView() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 px-6 text-center">
      <ShieldOff size={40} className="text-amber-500" />
      <h2 className="text-base font-semibold text-gray-900">Demo access not configured</h2>
      <p className="text-sm text-gray-600 max-w-sm">
        Set <code className="bg-gray-100 px-1 rounded text-xs">VITE_DEMO_TAGGER_JWT</code> in your{' '}
        <code className="bg-gray-100 px-1 rounded text-xs">.env</code> file to enable live workbench access.
      </p>
    </div>
  );
}

function ErrorView({ message, onRetry }) {
  return (
    <EmptyState
      icon={<AlertTriangle size={32} className="text-red-500" />}
      title="Could not load assignment"
      message={message}
      action={{ label: 'Retry', onClick: onRetry, variant: 'secondary' }}
    />
  );
}

function EmptyQueueView({ onRetry }) {
  return (
    <EmptyState
      icon={<Inbox size={32} className="text-gray-400" />}
      title="No items available to label right now"
      message="The queue is empty. Check back shortly or click Refresh to try again."
      action={{ label: 'Refresh', onClick: onRetry, variant: 'secondary' }}
    />
  );
}

function AssignmentView({ current, count, formRef, submitting, submitError, onSubmit, onDismissError }) {
  const { image, assignment } = current;
  return (
    <div className="flex flex-col lg:flex-row h-full">
      {/* Image panel */}
      <div className="lg:flex-1 bg-black flex items-center justify-center min-h-48 lg:min-h-0">
        <img
          src={image.url}
          alt={`Image ${image.id}`}
          className="max-w-full max-h-full object-contain"
          style={{ maxHeight: '100%' }}
        />
      </div>

      {/* Form panel */}
      <aside className="w-full lg:w-96 bg-white border-t lg:border-t-0 lg:border-l border-gray-200 flex flex-col overflow-y-auto">
        {/* Progress indicator */}
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Assignment</span>
          {count > 0 && (
            <span className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5 font-medium">
              {count} submitted
            </span>
          )}
        </div>

        {/* Image metadata */}
        <div className="px-5 py-3 border-b border-gray-100 text-xs text-gray-500 space-y-1">
          <div>ID: <span className="font-mono text-gray-700">{image.id}</span></div>
          {image.room_type && (
            <div>Room: <span className="text-gray-700">{image.room_type}</span></div>
          )}
        </div>

        {/* Form */}
        <div className="flex-1 px-5 py-5">
          {submitError && (
            <div className="mb-4">
              <ErrorBannerInline message={submitError} onDismiss={onDismissError} />
            </div>
          )}
          <AttributeForm
            ref={formRef}
            assignment={assignment}
            onSubmit={onSubmit}
            submitting={submitting}
          />
        </div>

        {/* Keyboard hint */}
        <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400 flex items-center gap-1.5">
          <kbd className="bg-gray-100 border border-gray-300 rounded px-1 py-0.5 font-mono text-[10px]">Enter</kbd>
          <span>to submit</span>
        </div>
      </aside>
    </div>
  );
}

function ErrorBannerInline({ message, onDismiss }) {
  return (
    <div role="alert" className="flex items-start gap-2 bg-red-50 border border-red-200 rounded px-3 py-2 text-sm text-red-800">
      <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-red-500" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-400 hover:text-red-600 ml-1" aria-label="Dismiss">×</button>
      )}
    </div>
  );
}
