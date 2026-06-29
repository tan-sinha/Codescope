import { useState } from 'react';
import { useAppContext } from './state/AppContext';
import { useApi } from './hooks/useApi';
import { CodemapView } from './components/CodemapView';
import { SearchView } from './components/SearchView';
import { ExplorerView } from './components/ExplorerView';
import { GraphView } from './components/GraphView';
import type { IndexResponse, View } from './state/types';

const TABS: { id: View; label: string; icon: string; title: string }[] = [
  { id: 'codemap',  label: 'Codemap',  icon: '◈', title: 'Technical overview — architecture, subsystems, request flows' },
  { id: 'search',   label: 'Search',   icon: '⌕', title: 'Ask questions in plain English — "where is routing handled?"' },
  { id: 'explorer', label: 'Explorer', icon: '⊞', title: 'Browse files, functions and classes' },
  { id: 'graph',    label: 'Graph',    icon: '⌀', title: 'Visualise call chains and import dependencies' },
];

export function App() {
  const { owner, repo, view, isIndexed, setView, setIsIndexed } = useAppContext();
  const { post, loading } = useApi();
  const [indexError, setIndexError] = useState<string | null>(null);

  async function handleIndex() {
    if (!owner || !repo) return;
    setIndexError(null);
    const res = await post<IndexResponse>('/index', { owner, repo });
    if (res?.status === 'ready') {
      setIsIndexed(true);
    } else {
      setIndexError('Indexing failed — check that the backend is running.');
    }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app__header">
        <span className="app__logo">Codescope</span>
        {owner && repo && (
          <span className="app__repo">{owner}/{repo}</span>
        )}
        <button
          className="app__index-btn"
          onClick={handleIndex}
          disabled={loading || !owner || !repo}
          title={isIndexed ? 'Re-index this repository' : 'Analyse this repository'}
        >
          {loading ? '…' : isIndexed ? '↻' : 'Index'}
        </button>
      </header>

      {indexError && <p className="app__index-error">{indexError}</p>}

      {/* No repo state */}
      {!owner && !repo && (
        <div className="app__onboarding">
          <p className="app__onboarding-title">Navigate to a GitHub repository to begin</p>
          <p className="app__onboarding-sub">
            Open any repo on github.com, then come back here and click <strong>Index</strong>.
          </p>
        </div>
      )}

      {/* Not yet indexed */}
      {!isIndexed && owner && repo && (
        <div className="app__onboarding">
          <p className="app__onboarding-title">Click <strong>Index</strong> to analyse this repo</p>
          <ol className="app__workflow">
            {[
              { step: '1', label: 'Index',    desc: 'Parses every .py file into functions, classes, imports and call graph' },
              { step: '2', label: 'Codemap',  desc: 'Architecture overview — subsystems, flows, tech stack' },
              { step: '3', label: 'Search',   desc: 'Ask in plain English — results ranked by semantic + keyword relevance' },
              { step: '4', label: 'Explorer', desc: 'Browse files, drill into any function, see who calls what' },
              { step: '5', label: 'Graph',    desc: 'Visualise call chains or import dependencies' },
            ].map((w) => (
              <li key={w.step} className="app__workflow-item">
                <span className="app__workflow-step">{w.step}</span>
                <span className="app__workflow-label">{w.label}</span>
                <span className="app__workflow-desc">{w.desc}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Main layout: vertical nav + content */}
      <div className="app__body">
        <nav className="app__sidenav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`app__sidenav-btn${view === tab.id ? ' app__sidenav-btn--active' : ''}`}
              onClick={() => setView(tab.id)}
              title={tab.title}
            >
              <span className="app__sidenav-icon">{tab.icon}</span>
              <span className="app__sidenav-label">{tab.label}</span>
            </button>
          ))}
        </nav>

        <main className="app__content">
          {view === 'codemap'  && <CodemapView />}
          {view === 'search'   && <SearchView />}
          {view === 'explorer' && <ExplorerView />}
          {view === 'graph'    && <GraphView />}
        </main>
      </div>
    </div>
  );
}
