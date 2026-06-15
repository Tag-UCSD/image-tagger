import React, { useEffect, useState, useCallback } from 'react';
import { monitor, explorer, demoAccess, Header, Button } from '@shared';
import { VelocityChart } from './VelocityChart';
import { IRRTable } from './IRRTable';
import { LatentStatusPanel } from './LatentStatusPanel';
import { ShieldOff, Lock, RefreshCcw, Loader2, AlertTriangle, Activity } from 'lucide-react';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Possible states: 'loading' | 'loaded' | 'unauthorized' | 'error' | 'no-token'
export default function MonitorApp() {
    const [appState, setAppState] = useState('loading');
    const [velocity, setVelocity] = useState(null);
    const [irr, setIRR] = useState(null);
    const [errorMsg, setErrorMsg] = useState(null);

    const [imageSets, setImageSets] = useState([]);
    const [selectedSetId, setSelectedSetId] = useState('');
    const [latentStatus, setLatentStatus] = useState(null);
    const [latentLoading, setLatentLoading] = useState(false);
    const [latentError, setLatentError] = useState(null);

    const loadData = useCallback(async () => {
        setAppState('loading');
        setErrorMsg(null);
        try {
            const [velData, irrData, setsData] = await Promise.all([
                monitor.getVelocity(),
                monitor.getIRR(),
                explorer.listImageSets().catch(() => ({ items: [] })),
            ]);
            setVelocity(velData);
            setIRR(irrData);
            setImageSets(setsData?.items ?? []);
            setAppState('loaded');
        } catch (err) {
            if (err.status === 403) {
                setAppState('unauthorized');
            } else {
                setErrorMsg(err.message || 'Failed to load monitor data');
                setAppState('error');
            }
        }
    }, []);

    const handleSetChange = useCallback(async (setId) => {
        setSelectedSetId(setId);
        if (!setId) { setLatentStatus(null); setLatentError(null); return; }
        setLatentLoading(true);
        setLatentError(null);
        setLatentStatus(null);
        try {
            const data = await monitor.getLatentStatus(setId);
            setLatentStatus(data);
        } catch (err) {
            setLatentError(err.message || 'Failed to load latent status');
        } finally {
            setLatentLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!USE_MOCKS && !demoAccess.hasSupervisorToken()) {
            setAppState('no-token');
            return;
        }
        loadData();
    }, [loadData]);

    if (appState === 'no-token') return <NoTokenView />;
    if (appState === 'unauthorized') return <UnauthorizedView />;

    return (
        <div className="min-h-screen bg-gray-100 pb-10">
            <Header appName="Supervisor" title="Quality Control Dashboard" />

            <div className="px-4 py-6 sm:px-8 max-w-5xl mx-auto space-y-6">
                <div className="flex items-center justify-between gap-4">
                    <p className="text-sm text-gray-600">
                        Monitor team validation velocity and inter-rater reliability.
                    </p>
                    <Button variant="secondary" onClick={loadData} disabled={appState === 'loading'}>
                        <RefreshCcw size={16} className="mr-2" />
                        Refresh
                    </Button>
                </div>

                {appState === 'loading' && <LoadingView />}

                {appState === 'error' && (
                    <ErrorView message={errorMsg} onRetry={loadData} />
                )}

                {appState === 'loaded' && (
                    <>
                        <VelocityChart series={velocity?.series ?? []} />
                        <IRRTable rows={irr?.rows ?? []} />

                        {/* Latent status section */}
                        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                            <div className="p-4 border-b border-gray-100 flex items-center gap-2">
                                <Activity className="text-purple-500" size={18} />
                                <h2 className="font-semibold text-gray-900 text-sm">Latent Detector Status</h2>
                            </div>
                            <div className="p-4 space-y-4">
                                <div className="flex items-center gap-3">
                                    <label htmlFor="latent-set-select" className="text-xs font-semibold text-gray-500 uppercase whitespace-nowrap">
                                        Image set
                                    </label>
                                    <select
                                        id="latent-set-select"
                                        value={selectedSetId}
                                        onChange={(e) => handleSetChange(e.target.value)}
                                        className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                    >
                                        <option value="">Select an image set…</option>
                                        {imageSets.map((s) => (
                                            <option key={s.id ?? s.slug} value={s.id ?? s.slug}>
                                                {s.name ?? s.slug}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {!selectedSetId && !latentLoading && (
                                    <p className="text-sm text-gray-500 text-center py-4">
                                        Select an image set above to view latent detector status.
                                    </p>
                                )}

                                <LatentStatusPanel
                                    status={latentStatus}
                                    loading={latentLoading}
                                    error={latentError}
                                />
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

function LoadingView() {
    return (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-gray-500">
            <Loader2 size={32} className="animate-spin" />
            <p className="text-sm">Loading dashboard…</p>
        </div>
    );
}

function ErrorView({ message, onRetry }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
            <AlertTriangle size={36} className="text-red-500" />
            <h3 className="text-base font-semibold text-gray-900">Could not load monitor data</h3>
            {message && <p className="text-sm text-gray-500 max-w-sm">{message}</p>}
            <Button variant="secondary" onClick={onRetry}>Retry</Button>
        </div>
    );
}

function UnauthorizedView() {
    return (
        <div className="min-h-screen bg-gray-100 flex flex-col">
            <Header appName="Supervisor" title="Quality Control Dashboard" />
            <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6 text-center">
                <Lock size={40} className="text-red-400" />
                <h2 className="text-base font-semibold text-gray-900">Access restricted</h2>
                <p className="text-sm text-gray-600 max-w-sm">
                    This dashboard is only available to users with the supervisor role.
                </p>
            </div>
        </div>
    );
}

function NoTokenView() {
    return (
        <div className="min-h-screen bg-gray-100 flex flex-col">
            <Header appName="Supervisor" title="Quality Control Dashboard" />
            <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6 text-center">
                <ShieldOff size={40} className="text-amber-500" />
                <h2 className="text-base font-semibold text-gray-900">Demo access not configured</h2>
                <p className="text-sm text-gray-600 max-w-sm">
                    Set{' '}
                    <code className="bg-gray-100 px-1 rounded text-xs">VITE_DEMO_TOKEN</code>{' '}
                    in your <code className="bg-gray-100 px-1 rounded text-xs">.env</code> file to
                    enable live monitor access.
                </p>
            </div>
        </div>
    );
}
