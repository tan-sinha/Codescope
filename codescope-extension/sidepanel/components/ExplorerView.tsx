import { useEffect, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import { Breadcrumb } from './Breadcrumb';
import { ResultCard } from './ResultCard';
import type { FileDetail, RepoOverview } from '../state/types';

type ExplorerPane = 'files' | 'file';

export function ExplorerView() {
  const { owner, repo } = useAppContext();
  const { get, loading, error } = useApi();

  const [pane, setPane] = useState<ExplorerPane>('files');
  const [overview, setOverview] = useState<RepoOverview | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileDetail, setFileDetail] = useState<FileDetail | null>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    if (!owner || !repo) return;
    get<RepoOverview>(`/explore/${owner}/${repo}`).then(setOverview);
  }, [owner, repo, get]);

  async function openFile(path: string) {
    setSelectedFile(path);
    setPane('file');
    const detail = await get<FileDetail>(
      `/explore/${owner}/${repo}/file/${path}`
    );
    setFileDetail(detail);
  }

  const filteredFiles = overview?.files.filter((f) =>
    f.toLowerCase().includes(filter.toLowerCase())
  ) ?? [];

  if (!owner || !repo) {
    return <p className="explorer-view__hint">Navigate to a GitHub repository to explore.</p>;
  }

  return (
    <div className="explorer-view">
      <Breadcrumb
        segments={[
          { label: `${owner}/${repo}`, onClick: pane === 'file' ? () => { setPane('files'); setSelectedFile(null); setFileDetail(null); } : undefined },
          ...(selectedFile ? [{ label: selectedFile.split('/').pop()! }] : []),
        ]}
      />

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
                <button
                  className="explorer-view__file-btn"
                  onClick={() => openFile(f)}
                >
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
    </div>
  );
}
