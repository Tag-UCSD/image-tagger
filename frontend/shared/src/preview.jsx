import React, { useState } from 'react';
import './preview.css';
import './theme.css';
import { Button }      from './components/Button.jsx';
import { Input }       from './components/Input.jsx';
import { Select }      from './components/Select.jsx';
import { Skeleton }    from './components/Skeleton.jsx';
import { EmptyState }  from './components/EmptyState.jsx';
import { ErrorBanner } from './components/ErrorBanner.jsx';
import { TrustBadge }  from './components/TrustBadge.jsx';
import { Modal }       from './components/Modal.jsx';
import { Pagination }  from './components/Pagination.jsx';
import { Header }      from './components/Header.jsx';
import { Toggle }      from './components/Toggle.jsx';
import { ToastProvider, useToast } from './components/Toast.jsx';
import ReactDOM from 'react-dom/client';

function Section({ title, children }) {
  return (
    <section className="mb-14" aria-labelledby={`section-${title.replace(/\s+/g, '-').toLowerCase()}`}>
      <h2
        id={`section-${title.replace(/\s+/g, '-').toLowerCase()}`}
        className="text-xl font-semibold text-gray-900 mb-5 pb-2 border-b border-gray-200"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function Row({ label, children }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{label}</p>
      <div className="flex flex-wrap items-start gap-3">{children}</div>
    </div>
  );
}

function ToastDemo() {
  const toast = useToast();
  return (
    <Row label="Toast (live)">
      <Button onClick={() => toast.success('Image uploaded successfully.')}>Success toast</Button>
      <Button variant="danger" onClick={() => toast.error('Upload failed.', { title: 'Error' })}>Error toast</Button>
      <Button variant="secondary" onClick={() => toast.info('Processing in background.')}>Info toast</Button>
    </Row>
  );
}

function Gallery() {
  const [modalOpen, setModalOpen]   = useState(false);
  const [toggleOn, setToggleOn]     = useState(false);
  const [inputVal, setInputVal]     = useState('');
  const [selectVal, setSelectVal]   = useState('');
  const [page, setPage]             = useState(2);

  const roomOptions = [
    { value: 'living_room', label: 'Living Room' },
    { value: 'bedroom',     label: 'Bedroom' },
    { value: 'kitchen',     label: 'Kitchen' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Header appName="Preview" title="Component Gallery" />

      <main className="max-w-3xl mx-auto px-8 py-10">
        <p className="text-sm text-gray-500 mb-10">
          Image Tagger v3 shared design system — all components in all states.
        </p>

        {/* ── Button ─────────────────────────────────────────────────── */}
        <Section title="Button">
          <Row label="Variants">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="danger">Danger</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="outline">Outline</Button>
          </Row>
          <Row label="Sizes">
            <Button size="xs">Extra Small</Button>
            <Button size="sm">Small</Button>
            <Button size="md">Medium</Button>
            <Button size="lg">Large</Button>
          </Row>
          <Row label="Disabled">
            <Button disabled>Primary disabled</Button>
            <Button variant="secondary" disabled>Secondary disabled</Button>
            <Button variant="danger" disabled>Danger disabled</Button>
          </Row>
        </Section>

        {/* ── Input ──────────────────────────────────────────────────── */}
        <Section title="Input">
          <Row label="Default">
            <Input
              id="input-default"
              label="Search query"
              placeholder="e.g. daylight ratio"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              className="w-64"
            />
          </Row>
          <Row label="Error state">
            <Input
              id="input-error"
              label="Page number"
              type="number"
              value=""
              onChange={() => {}}
              error="Must be greater than or equal to 1"
              className="w-64"
            />
          </Row>
          <Row label="Disabled">
            <Input
              id="input-disabled"
              label="Username"
              value="brandonng"
              onChange={() => {}}
              disabled
              className="w-64"
            />
          </Row>
          <Row label="Required">
            <Input
              id="input-required"
              label="Attribute key"
              placeholder="e.g. light.daylight_ratio"
              value=""
              onChange={() => {}}
              required
              className="w-64"
            />
          </Row>
        </Section>

        {/* ── Select ─────────────────────────────────────────────────── */}
        <Section title="Select">
          <Row label="Default">
            <Select
              id="select-default"
              label="Room type"
              value={selectVal}
              onChange={(e) => setSelectVal(e.target.value)}
              options={roomOptions}
              placeholder="Choose a room type"
              className="w-56"
            />
          </Row>
          <Row label="Error state">
            <Select
              id="select-error"
              label="Room type"
              value=""
              onChange={() => {}}
              options={roomOptions}
              placeholder="Choose a room type"
              error="A room type is required"
              className="w-56"
            />
          </Row>
          <Row label="Disabled">
            <Select
              id="select-disabled"
              label="Room type"
              value="bedroom"
              onChange={() => {}}
              options={roomOptions}
              disabled
              className="w-56"
            />
          </Row>
        </Section>

        {/* ── Skeleton ───────────────────────────────────────────────── */}
        <Section title="Skeleton (loading placeholders)">
          <Row label="Line">
            <div className="space-y-2 w-64">
              <Skeleton variant="line" className="w-full" />
              <Skeleton variant="line" className="w-3/4" />
              <Skeleton variant="line" className="w-1/2" />
            </div>
          </Row>
          <Row label="Rectangle (card)">
            <Skeleton variant="rect" className="w-48 h-32" />
            <Skeleton variant="rect" className="w-48 h-32" />
          </Row>
          <Row label="Circle (avatar)">
            <Skeleton variant="circle" className="w-10 h-10" />
            <Skeleton variant="circle" className="w-14 h-14" />
          </Row>
        </Section>

        {/* ── EmptyState ─────────────────────────────────────────────── */}
        <Section title="Empty State">
          <Row label="With action">
            <div className="border border-gray-200 rounded-lg bg-white w-full max-w-md">
              <EmptyState
                title="No items available"
                message="No items are available to label right now. Check back shortly or refresh."
                action={{ label: 'Retry', onClick: () => {} }}
              />
            </div>
          </Row>
          <Row label="Without action">
            <div className="border border-gray-200 rounded-lg bg-white w-full max-w-md">
              <EmptyState
                title="No results found"
                message="Try adjusting your search query or filters."
              />
            </div>
          </Row>
        </Section>

        {/* ── ErrorBanner ────────────────────────────────────────────── */}
        <Section title="Error Banner">
          <Row label="With code">
            <div className="w-full max-w-md">
              <ErrorBanner
                code="VALIDATION_ERROR"
                message="Page must be greater than or equal to 1."
              />
            </div>
          </Row>
          <Row label="Dismissible">
            <div className="w-full max-w-md">
              <ErrorBanner
                message="Upload failed. Each file must be JPEG, PNG, or WebP and no larger than 10 MiB."
                onDismiss={() => {}}
              />
            </div>
          </Row>
          <Row label="Auth error">
            <div className="w-full max-w-md">
              <ErrorBanner
                code="AUTH_REQUIRED"
                message="Bearer token required or invalid."
              />
            </div>
          </Row>
        </Section>

        {/* ── TrustBadge ─────────────────────────────────────────────── */}
        <Section title="Trust Badge">
          <Row label="All evaluation statuses">
            <TrustBadge evaluation_status="validated" />
            <TrustBadge evaluation_status="proxy_validated" />
            <TrustBadge evaluation_status="untested" />
          </Row>
          <Row label="In context (science feature row)">
            <div className="border border-gray-200 rounded-lg bg-white p-4 space-y-3 w-full max-w-md">
              {[
                { key: 'light.daylight_ratio', value: 0.84, status: 'proxy_validated' },
                { key: 'texture.visual_complexity', value: 0.41, status: 'untested' },
                { key: 'room.biophilic_index', value: 0.72, status: 'validated' },
              ].map((f) => (
                <div key={f.key} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-gray-700 text-xs">{f.key}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-900 font-medium">{f.value}</span>
                    <TrustBadge evaluation_status={f.status} />
                  </div>
                </div>
              ))}
            </div>
          </Row>
        </Section>

        {/* ── Modal ──────────────────────────────────────────────────── */}
        <Section title="Modal">
          <Row label="Trigger">
            <Button onClick={() => setModalOpen(true)}>Open modal</Button>
          </Row>
          <Row label="Content preview (static)">
            <div
              className="border border-gray-200 rounded-lg bg-white p-6 w-full max-w-lg shadow-sm"
              aria-label="Modal content preview"
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Confirm Kill Switch</h3>
                <button
                  type="button"
                  aria-label="Close dialog"
                  className="text-gray-400 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 rounded"
                >
                  <span aria-hidden="true">×</span>
                </button>
              </div>
              <p className="text-sm text-gray-700 mb-6">
                Activating the kill switch will disable all paid models globally.
                This cannot be undone without returning to this screen.
              </p>
              <div className="flex gap-3 justify-end">
                <Button variant="secondary">Cancel</Button>
                <Button variant="danger">Activate Kill Switch</Button>
              </div>
            </div>
          </Row>
        </Section>

        {/* ── Pagination ─────────────────────────────────────────────── */}
        <Section title="Pagination">
          <Row label="Default (interactive)">
            <Pagination page={page} total={200} page_size={20} onChange={setPage} />
          </Row>
          <Row label="First page">
            <Pagination page={1} total={200} page_size={20} onChange={() => {}} />
          </Row>
          <Row label="Last page">
            <Pagination page={10} total={200} page_size={20} onChange={() => {}} />
          </Row>
          <Row label="Single page">
            <Pagination page={1} total={5} page_size={20} onChange={() => {}} />
          </Row>
        </Section>

        {/* ── Toggle ─────────────────────────────────────────────────── */}
        <Section title="Toggle">
          <Row label="Default">
            <Toggle checked={toggleOn} onChange={setToggleOn} label="Enable feature" />
          </Row>
          <Row label="Danger (kill switch)">
            <Toggle checked={true} onChange={() => {}} danger label="Kill switch active" />
          </Row>
          <Row label="Off">
            <Toggle checked={false} onChange={() => {}} label="Kill switch inactive" />
          </Row>
        </Section>

        {/* ── Toast ──────────────────────────────────────────────────── */}
        <Section title="Toast">
          <ToastDemo />
        </Section>
      </main>

      {/* Live modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Confirm Kill Switch">
        <p className="text-sm text-gray-700 mb-6">
          Activating the kill switch will disable all paid models globally.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={() => setModalOpen(false)}>Activate Kill Switch</Button>
        </div>
      </Modal>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <Gallery />
    </ToastProvider>
  </React.StrictMode>
);
