import React, { useState, useEffect } from 'react';

const STORAGE_KEY = 'demo_access_granted';
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD;

/**
 * Full-screen password gate for demo deployments.
 *
 * Renders only when VITE_DEMO_PASSWORD is set. Stores the grant in
 * sessionStorage so users aren't re-prompted within the same browser
 * session. Children are rendered once the password is accepted.
 */
export function DemoPasswordGate({ children }) {
  const [unlocked, setUnlocked] = useState(false);
  const [input, setInput] = useState('');
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!DEMO_PASSWORD || sessionStorage.getItem(STORAGE_KEY) === '1') {
      setUnlocked(true);
    }
  }, []);

  if (unlocked) return children;

  function handleSubmit(e) {
    e.preventDefault();
    if (input === DEMO_PASSWORD) {
      sessionStorage.setItem(STORAGE_KEY, '1');
      setUnlocked(true);
    } else {
      setError(true);
      setInput('');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm mx-4 rounded-2xl bg-white shadow-2xl p-8">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">Image Tagger Demo</h1>
        <p className="text-sm text-gray-500 mb-6">Enter the demo password to continue.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            autoFocus
            type="password"
            value={input}
            onChange={e => { setInput(e.target.value); setError(false); }}
            placeholder="Password"
            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {error && (
            <p className="text-xs text-red-600 -mt-2">Incorrect password. Try again.</p>
          )}
          <button
            type="submit"
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Enter
          </button>
        </form>
      </div>
    </div>
  );
}
