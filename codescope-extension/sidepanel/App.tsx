import { useState } from 'react';
import { useAppContext } from './state/AppContext';
import { useApi } from './hooks/useApi';
import { SearchView } from './components/SearchView';
import { ExplorerView } from './components/ExplorerView';
import { GraphView } from './components/GraphView';
import type { IndexResponse, View } from './state/types';

const TABS: { id: View; label: string }[] = [
  { id: 'search', label: 'Search' },
  { id: 'explorer', label: 'Explorer' },
  { id: 'graph', label: 'Graph' },
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
      <header className="app__header">
        <span className="app__logo">Codescope</span>
        {owner && repo && (
          <span className="app__repo">
            {owner}/{repo}
          </span>
        )}
        <button
          className="app__index-btn"
          onClick={handleIndex}
          disabled={loading || !owner || !repo}
          title={isIndexed ? 'Re-index' : 'Index this repository'}
        >
          {loading ? '…' : isIndexed ? '↻' : 'Index'}
        </button>
      </header>

      {indexError && <p className="app__index-error">{indexError}</p>}

      {!isIndexed && owner && repo && (
        <div className="app__notice">
          Repository not indexed yet. Click <strong>Index</strong> to analyse it.
        </div>
      )}

      <nav className="app__tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`app__tab${view === tab.id ? ' app__tab--active' : ''}`}
            onClick={() => setView(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="app__content">
        {view === 'search' && <SearchView />}
        {view === 'explorer' && <ExplorerView />}
        {view === 'graph' && <GraphView />}
      </main>
    </div>
  );
}
