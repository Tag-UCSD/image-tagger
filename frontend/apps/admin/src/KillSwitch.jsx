import React, { useState } from 'react';
import { admin, Button, Modal } from '@shared';
import { ShieldAlert, Power } from 'lucide-react';

export function KillSwitch({ active, onToggle }) {
    const [confirming, setConfirming] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const handleConfirm = async () => {
        setConfirming(false);
        setBusy(true);
        setError(null);
        try {
            const resp = await admin.setKillSwitch(!active);
            onToggle(resp);
        } catch (err) {
            setError(err.message || 'Failed to update kill switch');
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className={`rounded-xl border p-4 space-y-3 ${
            active ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'
        }`}>
            <div className="flex items-center gap-2">
                <ShieldAlert className={active ? 'text-red-500' : 'text-gray-400'} size={18} />
                <h2 className={`font-semibold text-sm ${active ? 'text-red-800' : 'text-gray-900'}`}>
                    Kill Switch
                </h2>
                <span className={`ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                    active ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                }`}>
                    {active ? 'ACTIVE' : 'Inactive'}
                </span>
            </div>

            <p className="text-xs text-gray-600">
                When activated, all paid models are disabled globally for all users immediately.
                Requires explicit confirmation to flip.
            </p>

            {error && (
                <p role="alert" className="text-xs text-red-600">{error}</p>
            )}

            <Button
                variant={active ? 'secondary' : 'danger'}
                size="sm"
                disabled={busy}
                onClick={() => setConfirming(true)}
            >
                <Power size={14} className="mr-1" />
                {busy ? 'Updating…' : active ? 'Disable Kill Switch' : 'Activate Kill Switch'}
            </Button>

            <Modal
                open={confirming}
                onClose={() => setConfirming(false)}
                title={active ? 'Disable kill switch?' : 'Activate kill switch?'}
            >
                <p className="text-sm text-gray-600 mb-6">
                    {active
                        ? 'This will re-enable paid models for all users. Are you sure?'
                        : 'This will immediately disable all paid models for all users. This cannot be undone without another confirmation. Are you sure?'}
                </p>
                <div className="flex justify-end gap-3">
                    <Button variant="secondary" size="sm" onClick={() => setConfirming(false)}>
                        Cancel
                    </Button>
                    <Button
                        variant={active ? 'primary' : 'danger'}
                        size="sm"
                        onClick={handleConfirm}
                    >
                        {active ? 'Yes, disable' : 'Yes, activate'}
                    </Button>
                </div>
            </Modal>
        </div>
    );
}
