import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ToastProvider, MaintenanceOverlay, explorer, workbench, monitor, admin, demoAccess } from '@shared';
import '../../../index.css'

if (import.meta.env.DEV) {
  window.__api = { explorer, workbench, monitor, admin, demoAccess };
}
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <MaintenanceOverlay />
      <App />
    </ToastProvider>
  </React.StrictMode>,
)