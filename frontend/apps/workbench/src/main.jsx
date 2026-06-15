import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ToastProvider, MaintenanceOverlay, DemoPasswordGate } from '@shared';
import '../../../index.css'
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <DemoPasswordGate>
        <MaintenanceOverlay />
        <App />
      </DemoPasswordGate>
    </ToastProvider>
  </React.StrictMode>,
)