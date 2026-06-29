import { useEffect, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import { Breadcrumb } from './Breadcrumb';
import { ResultCard } from './ResultCard';
import { FunctionDetailView } from './FunctionDetailView';
import type { FileDetail, RepoOverview } from '../state/types';

type Pane = 'files' | 'file' | 'function';

export function ExplorerView() {
  const { owner, repo, pendingFunction, clearPendingFunction } = useAppContext();
  const { get, loading, error } = useApi();

  const [pane, setPane] = useState<Pane>('files');
  const [overview, setOverview] = useState<RepoOverview | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileDetail, setFileDetail] = useState<FileDetail | null>(null);
  const [filter, setFilter] = useState('');

  // Function navigation history stack
  const [fnStack, setFnStack] = useState<string[]>([]);
  const [currentFn, setCurrentFn] = useState<string | null>(null);

  // Consume pendingFunction from context (set by ResultCard clicks in Search)
  useEffect(() => {
    if (pendingFunction) {
      pushFn(pendingFunction);
      clearPendingFunction();
    }
  }, [pendingFunction]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!owner || !repo) return;
    get<RepoOverview>(`/explore/${owner}/${repo}`).then(setOverview);
  }, [owner, repo, get]);

  function pushFn(name: string) {
    if (currentFn) setFnStack((s) => [...s, currentFn]);
    setCurrentFn(name);
    setPane('function');
  }

  function popFn() {
    if (fnStack.length > 0) {
      setCurrentFn(fnStack[fnStack.length - 1]);
      setFnStack((s) => s.slice(0, -1));
    } else {
      setCurrentFn(null);
      setPane(selectedFile ? 'file' : 'files');
    }
  }

  async function openFile(path: string) {
    setSelectedFile(path);
    setCurrentFn(null);
    setFnStack([]);
    setPane('file');
    const detail = await get<FileDetail>(`/explore/${owner}/${repo}/file/${path}`);
    setFileDetail(detail);
  }

  function goToRoot() {
    setCurrentFn(null);
    setFnStack([]);
    setSelectedFile(null);
    setFileDetail(null);
    setPane('files');
  }

  function goToFile() {
    setCurrentFn(null);
    setFnStack([]);
    setPane('file');
  }

  const filteredFiles = overview?.files.filter((f) =>
    f.toLowerCase().includes(filter.toLowerCase())
  ) ?? [];

  if (!owner || !repo) {
    return <p className="explorer-view__hint">Navigate to a GitHub repository to explore.</p>;
  }

  // Build breadcrumb
  const crumbs = [
    { label: `${owner}/${repo}`, onClick: pane !== 'files' ? goToRoot : undefined },
    ...(selectedFile && pane !== 'files'
      ? [{ label: selectedFile.split('/').pop()!, onClick: pane === 'function' ? goToFile : undefined }]
      : []),
    ...(pane === 'function' && fnStack.length > 0
      ? fnStack.map((n, i) => ({
          label: n,
          onClick: () => {
            setCurrentFn(n);
            setFnStack((s) => s.slice(0, i));
          },
        }))
      : []),
    ...(currentFn ? [{ label: currentFn }] : []),
  ];

  return (
    <div className="explorer-view">
      <div className="explorer-view__top">
        <Breadcrumb segments={crumbs} />
        {pane === 'function' && fnStack.length > 0 && (
          <button className="explorer-view__back" onClick={popFn}>← back</button>
        )}
      </div>

      {error && <p className="explorer-view__error">{error}</p>}

      {pane === 'files' && (
        <div className="explorer-view__files">
          <input
            className="explorer-view__filter"
            type="text"
            placeholder="Filter files…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          {loading && <p className="explorer-view__loading">Loading…</p>}
          <ul className="explorer-view__file-list">
            {filteredFiles.map((f) => (
              <li key={f}>
                <button className="explorer-view__file-btn" onClick={() => openFile(f)}>
                  {f}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {pane === 'file' && (
        <div className="explorer-view__detail">
          {loading && <p className="explorer-view__loading">Loading…</p>}
          {fileDetail?.module.summary && (
            <p className="explorer-view__summary">{fileDetail.module.summary}</p>
          )}
          {fileDetail?.functions.map((fn) => (
            <ResultCard
              score={1}
              key={fn.name}
              item={{
                type: 'function',
                name: fn.name,
                file: selectedFile!,
                lines: [fn.start_line, fn.end_line],
                signature: `${fn.name}(${fn.parameters.map((p) => p.name).join(', ')})`,
                summary: fn.summary,
                source_preview: fn.source_code,
                relevance_score: 1,
              }}
            />
          ))}
          {fileDetail?.classes.map((cls) => (
            <ResultCard
              score={1}
              key={cls.name}
              item={{
                type: 'class',
                name: cls.name,
                file: selectedFile!,
                lines: [cls.start_line, cls.end_line],
                summary: cls.docstring,
                relevance_score: 1,
              }}
            />
          ))}
        </div>
      )}

      {pane === 'function' && currentFn && (
        <FunctionDetailView name={currentFn} onNavigate={pushFn} />
      )}
    </div>
  );
}
