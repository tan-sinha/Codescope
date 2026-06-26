import { useRef, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import { ResultCard } from './ResultCard';
import type { SearchGroup, SearchItem, SearchMode } from '../state/types';

function normaliseScores(groups: SearchGroup[]): SearchGroup[] {
  const all = groups.flatMap((g) => g.items.map((i) => i.relevance_score));
  const max = Math.max(...all, 1e-6);
  return groups.map((g) => ({
    ...g,
    relevance_score: g.relevance_score / max,
    items: g.items.map((i) => ({ ...i, relevance_score: i.relevance_score / max })),
  }));
}

function Spinner() {
  return (
    <div className="search-view__spinner" aria-label="Loading">
      <div className="search-view__spinner-ring" />
      <span>Loading model…</span>
    </div>
  );
}

export function SearchView() {
  const { owner, repo } = useAppContext();
  const { post, loading, error } = useApi();

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('hybrid');
  const [groups, setGroups] = useState<SearchGroup[]>([]);
  const [searched, setSearched] = useState(false);

  // The embedding model is cached after first inference; only show spinner then.
  const modelWarm = useRef(false);
  const showSpinner = loading && !modelWarm.current;

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !owner || !repo) return;

    const res = await post<{ results: SearchGroup[] }>('/search', {
      owner,
      repo,
      query,
      limit: 10,
      mode,
    });

    if (res) {
      modelWarm.current = true;
      setGroups(normaliseScores(res.results));
      setSearched(true);
    }
  }

  const noRepo = !owner || !repo;

  return (
    <div className="search-view">
      <form className="search-view__form" onSubmit={handleSearch}>
        <div className="search-view__input-row">
          <input
            className="search-view__input"
            type="text"
            placeholder={noRepo ? 'Open a GitHub repo first…' : 'Search code…'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={noRepo}
            autoFocus
          />
          <select
            className="search-view__mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as SearchMode)}
            disabled={noRepo}
          >
            <option value="hybrid">Hybrid</option>
            <option value="faiss">Semantic</option>
            <option value="bm25">Keyword</option>
          </select>
        </div>
      </form>

      {showSpinner && <Spinner />}

      {error && !showSpinner && (
        <p className="search-view__error">{error}</p>
      )}

      {searched && groups.length === 0 && !loading && (
        <p className="search-view__empty">No results found.</p>
      )}

      <div className="search-view__results">
        {groups.map((group) => (
          <section key={group.file} className="search-view__group">
            <div className="search-view__group-header">
              <span className="search-view__group-file">{group.file}</span>
              <span className="search-view__group-score">
                {(group.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
            {group.items.map((item: SearchItem, i: number) => (
              <ResultCard
                key={`${item.name}-${i}`}
                item={item}
                score={item.relevance_score}
              />
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
