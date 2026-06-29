import { useEffect, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import type { CodemapData, CodemapSubsystem } from '../state/types';

function StatBadge({ value, label }: { value: number; label: string }) {
  return (
    <div className="codemap__stat">
      <span className="codemap__stat-value">{value.toLocaleString()}</span>
      <span className="codemap__stat-label">{label}</span>
    </div>
  );
}

function TechBadge({ name }: { name: string }) {
  return <span className="codemap__tech-badge">{name}</span>;
}

function FlowSteps({ steps }: { steps: string[] }) {
  if (!steps.length) return null;
  return (
    <ol className="codemap__flow">
      {steps.map((step, i) => (
        <li key={i} className="codemap__flow-step">
          <span className="codemap__flow-num">{i + 1}</span>
          <span className="codemap__flow-text">{step}</span>
        </li>
      ))}
    </ol>
  );
}

function SubsystemCard({ sub }: { sub: CodemapSubsystem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="codemap__subsystem">
      <button
        className="codemap__subsystem-header"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        <span className="codemap__subsystem-name">{sub.name}</span>
        <span className="codemap__subsystem-chevron">{expanded ? '▾' : '▸'}</span>
      </button>

      <p className="codemap__subsystem-desc">{sub.description}</p>

      {expanded && (
        <div className="codemap__subsystem-body">
          {sub.flow_steps.length > 0 && (
            <div className="codemap__subsystem-section">
              <p className="codemap__subsystem-section-title">Flow</p>
              <FlowSteps steps={sub.flow_steps} />
            </div>
          )}

          {sub.key_files.length > 0 && (
            <div className="codemap__subsystem-section">
              <p className="codemap__subsystem-section-title">Key files</p>
              <ul className="codemap__file-list">
                {sub.key_files.map((f) => (
                  <li key={f} className="codemap__file-item">{f}</li>
                ))}
              </ul>
            </div>
          )}

          {sub.entry_function && (
            <div className="codemap__subsystem-section">
              <p className="codemap__subsystem-section-title">Entry</p>
              <code className="codemap__entry-fn">{sub.entry_function}</code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function CodemapView() {
  const { owner, repo, isIndexed } = useAppContext();
  const { get, loading, error } = useApi();
  const [data, setData] = useState<CodemapData | null>(null);

  useEffect(() => {
    if (!owner || !repo || !isIndexed) return;
    setData(null);
    get<CodemapData>(`/codemap/${owner}/${repo}`).then((d) => {
      if (d) setData(d);
    });
  }, [owner, repo, isIndexed, get]);

  if (!owner || !repo) {
    return <p className="codemap__hint">Navigate to a GitHub repository to begin.</p>;
  }

  if (!isIndexed) {
    return <p className="codemap__hint">Index the repository first to generate a codemap.</p>;
  }

  if (loading && !data) {
    return (
      <div className="codemap__loading">
        <div className="codemap__spinner" />
        <p>Generating codemap…</p>
        <p className="codemap__loading-sub">Analysing structure + asking Gemini</p>
      </div>
    );
  }

  if (error) {
    return <p className="codemap__error">{error}</p>;
  }

  if (!data) return null;

  return (
    <div className="codemap">
      {/* Stats row */}
      <div className="codemap__stats">
        <StatBadge value={data.file_count} label="files" />
        <StatBadge value={data.function_count} label="functions" />
        <StatBadge value={data.class_count} label="classes" />
      </div>

      {/* Summary */}
      <div className="codemap__summary">
        <p>{data.summary}</p>
        {data.readme_used && (
          <span className="codemap__readme-badge" title="Summary includes README context">README ✓</span>
        )}
      </div>

      {/* README features */}
      {data.readme_features?.length > 0 && (
        <div className="codemap__section">
          <p className="codemap__section-title">Key features (from README)</p>
          <ul className="codemap__feature-list">
            {data.readme_features.map((f, i) => (
              <li key={i} className="codemap__feature-item">{f}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tech stack */}
      {data.tech_stack.length > 0 && (
        <div className="codemap__section">
          <p className="codemap__section-title">Tech stack</p>
          <div className="codemap__tech-list">
            {data.tech_stack.map((t) => <TechBadge key={t} name={t} />)}
          </div>
        </div>
      )}

      {/* Entry points */}
      {data.entry_points.length > 0 && (
        <div className="codemap__section">
          <p className="codemap__section-title">Entry points</p>
          <ul className="codemap__entry-list">
            {data.entry_points.slice(0, 8).map((ep) => (
              <li key={ep} className="codemap__entry-item">
                <code>{ep}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Subsystems */}
      {data.subsystems.length > 0 && (
        <div className="codemap__section">
          <p className="codemap__section-title">Subsystems</p>
          <div className="codemap__subsystems">
            {data.subsystems.map((sub) => (
              <SubsystemCard key={sub.name} sub={sub} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
