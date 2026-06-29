import { Component, StrictMode } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { AppProvider } from './state/AppContext';
import { App } from './App';
import './styles/globals.css';

// Step 1 — confirm the JS bundle reached this line
console.log('[Codescope] main.tsx executing');

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[Codescope] render error:', error.message, info.componentStack);
  }

  render() {
    if (this.state.error) {
      const err = this.state.error as Error;
      return (
        <div style={{ padding: 16, fontFamily: 'monospace', fontSize: 12, color: '#f38ba8', background: '#1e1e2e', minHeight: '100vh' }}>
          <strong>Codescope crashed</strong>
          <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {err.message}{'\n\n'}{err.stack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const root = document.getElementById('root');
console.log('[Codescope] #root element:', root);

if (!root) {
  document.body.innerHTML = '<pre style="color:red;padding:16px">[Codescope] #root not found — wrong HTML loaded</pre>';
} else {
  console.log('[Codescope] calling createRoot');
  createRoot(root).render(
    <StrictMode>
      <ErrorBoundary>
        <AppProvider>
          <App />
        </AppProvider>
      </ErrorBoundary>
    </StrictMode>
  );
  console.log('[Codescope] render called');
}
