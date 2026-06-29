import { useRef, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import { ResultCard } from './ResultCard';
import type { SearchGroup, SearchItem, SearchMode } from '../state/types';

const EXAMPLE_QUERIES = [
  'where is routing handled',
  'how does error handling work',
  'what does the request context do',
  'where is authentication',
  'how are templates rendered',
];

function normaliseScores(groups: SearchGroup[]): SearchGroup[] {
  const all = groups.flatMap((g) => g.items.map((i) => i.relevance_score));
  const max = Math.max(...all, 1e-6);
  return groups.map((g) => ({
    ...g,
    relevance_score: g.relevance_score / max,
    items: g.items.map((i) => ({ ...i, relevance_score: i.relevance_score / max })),
  }));
}

function flattenItems(groups: SearchGroup[]) {
  return groups.flatMap((g) =>
    g.items.map((item) => ({ name: item.name, file: g.file, summary: item.summary ?? undefined }))
  );
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
  const [answer, setAnswer] = useState<string | null>(null);
  const [synthesizing, setSynthesizing] = useState(false);

  const modelWarm = useRef(false);
  const showSpinner = loading && !modelWarm.current;

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !owner || !repo) return;
    setAnswer(null);

    const res = await post<{ results: SearchGroup[] }>('/search', {
      owner, repo, query, limit: 10, mode,
    });

    if (res) {
      modelWarm.current = true;
      setGroups(normaliseScores(res.results));
      setSearched(true);
    }
  }

  async function handleSynthesize() {
    if (!groups.length) return;
    setSynthesizing(true);
    setAnswer(null);
    const res = await post<{ answer: string }>('/synthesize', {
      owner, repo, query, results: flattenItems(groups),
    });
    setSynthesizing(false);
    if (res?.answer) setAnswer(res.answer);
  }

  const noRepo = !owner || !repo;
  const totalItems = groups.reduce((n, g) => n + g.items.length, 0);

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

      {/* Example queries shown before first search */}
      {!searched && !noRepo && (
        <div className="search-view__examples">
          <p className="search-view__examples-label">Try asking:</p>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              className="search-view__example-chip"
              onClick={() => setQuery(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {showSpinner && <Spinner />}
      {error && !showSpinner && <p className="search-view__error">{error}</p>}

      {/* Synthesize button + answer */}
      {searched && groups.length > 0 && (
        <div className="search-view__synthesize-bar">
          <span className="search-view__result-count">{totalItems} results</span>
          <button
            className="search-view__synthesize-btn"
            onClick={handleSynthesize}
            disabled={synthesizing}
          >
            {synthesizing ? '…' : '✦ Explain'}
          </button>
        </div>
      )}

      {answer && (
        <div className="search-view__answer">
          <p className="search-view__answer-text">{answer}</p>
        </div>
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
