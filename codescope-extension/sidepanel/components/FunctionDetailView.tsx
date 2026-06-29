import { useEffect, useMemo, useRef, useState } from 'react';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import { FunctionLink } from './FunctionLink';
import type {
  CallersResponse,
  ClassInfo,
  FunctionInfo,
  GraphData,
  MethodSignature,
} from '../state/types';

hljs.registerLanguage('python', python);

function highlight(code: string): string {
  return hljs.highlight(code, { language: 'python' }).value;
}

function ghUrl(owner: string, repo: string, file: string, start: number, end: number) {
  return `https://github.com/${owner}/${repo}/blob/main/${file}#L${start}-L${end}`;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function ParamRow({ name, annotation }: { name: string; annotation?: string | null }) {
  return (
    <tr className="fn-detail__param-row">
      <td className="fn-detail__param-name">{name}</td>
      <td className="fn-detail__param-type">{annotation ?? <em>any</em>}</td>
    </tr>
  );
}

function RefList({ title, names, onNavigate }: { title: string; names: string[]; onNavigate: (n: string) => void }) {
  if (!names.length) return null;
  return (
    <section className="fn-detail__refs">
      <h4 className="fn-detail__refs-title">{title}</h4>
      <div className="fn-detail__refs-list">
        {names.map((n) => (
          <FunctionLink key={n} name={n} onClick={onNavigate} />
        ))}
      </div>
    </section>
  );
}

// ── Full-function detail ────────────────────────────────────────────────────

interface FnProps {
  fn: FunctionInfo;
  file: string;
  calls: string[];
  callers: string[];
  onNavigate: (name: string) => void;
}

function architectureNote(calls: string[], callers: string[]): string | null {
  if (callers.length === 0 && calls.length > 0)
    return 'Not called by any indexed function — likely an entry point or public API.';
  if (callers.length > 5)
    return `Called from ${callers.length} places — likely a shared utility.`;
  if (calls.length === 0 && callers.length > 0)
    return 'Makes no tracked calls — likely a leaf function (side-effectful or wraps external code).';
  return null;
}

function FnDetail({ fn, file, calls, callers, onNavigate }: FnProps) {
  const { owner, repo } = useAppContext();
  const { post } = useApi();
  const highlighted = useMemo(() => highlight(fn.source_code), [fn.source_code]);
  const url = ghUrl(owner, repo, file, fn.start_line, fn.end_line);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const explained = useRef(false);

  async function handleExplain() {
    if (explained.current) return;
    setExplaining(true);
    const res = await post<{ explanation: string }>(
      `/explain/${owner}/${repo}`,
      { name: fn.name, source: fn.source_code }
    );
    setExplaining(false);
    if (res?.explanation) {
      setExplanation(res.explanation);
      explained.current = true;
    }
  }

  const note = architectureNote(calls, callers);

  return (
    <div className="fn-detail">
      <div className="fn-detail__header">
        <span className="fn-detail__icon fn-detail__icon--fn">ƒ</span>
        <span className="fn-detail__name">{fn.name}</span>
        <button
          className="fn-detail__explain-btn"
          onClick={handleExplain}
          disabled={explaining}
          title="Ask Gemini to explain this function"
        >
          {explaining ? '…' : '✦ Explain'}
        </button>
        <a className="fn-detail__gh" href={url} target="_blank" rel="noreferrer">↗ GH</a>
      </div>

      {explanation && (
        <div className="fn-detail__explanation">{explanation}</div>
      )}

      <div className="fn-detail__file">{file}:{fn.start_line}</div>

      {fn.return_type && (
        <div className="fn-detail__return">
          → <span className="fn-detail__return-type">{fn.return_type}</span>
        </div>
      )}

      {fn.parameters.length > 0 && (
        <section className="fn-detail__section">
          <h4 className="fn-detail__section-title">Parameters</h4>
          <table className="fn-detail__params">
            <tbody>
              {fn.parameters.map((p) => (
                <ParamRow key={p.name} name={p.name} annotation={p.annotation} />
              ))}
            </tbody>
          </table>
        </section>
      )}

      {(fn.summary || fn.docstring) && (
        <section className="fn-detail__section">
          <h4 className="fn-detail__section-title">Summary</h4>
          <p className="fn-detail__summary">{fn.summary || fn.docstring}</p>
        </section>
      )}

      {fn.decorators.length > 0 && (
        <div className="fn-detail__decorators">
          {fn.decorators.map((d) => <code key={d} className="fn-detail__decorator">{d}</code>)}
        </div>
      )}

      <RefList title="Calls" names={calls} onNavigate={onNavigate} />
      <RefList title="Called by" names={callers} onNavigate={onNavigate} />

      {note && <p className="fn-detail__arch-note">{note}</p>}

      <section className="fn-detail__section">
        <h4 className="fn-detail__section-title">Source</h4>
        <pre className="fn-detail__source hljs">
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
      </section>
    </div>
  );
}

// ── Method detail (no source_code available from MethodSignature) ───────────

interface MethodProps {
  method: MethodSignature;
  className: string;
  file: string;
  calls: string[];
  callers: string[];
  onNavigate: (name: string) => void;
}

function MethodDetail({ method, className, file, calls, callers, onNavigate }: MethodProps) {
  const { owner, repo } = useAppContext();
  const url = `https://github.com/${owner}/${repo}/search?q=${encodeURIComponent(`def ${method.name}`)}`;

  return (
    <div className="fn-detail">
      <div className="fn-detail__header">
        <span className="fn-detail__icon fn-detail__icon--method">M</span>
        <span className="fn-detail__name">{className}.{method.name}</span>
        <a className="fn-detail__gh" href={url} target="_blank" rel="noreferrer">↗ GH</a>
      </div>

      <div className="fn-detail__file">{file}</div>

      {method.return_type && (
        <div className="fn-detail__return">
          → <span className="fn-detail__return-type">{method.return_type}</span>
        </div>
      )}

      {method.parameters.length > 0 && (
        <section className="fn-detail__section">
          <h4 className="fn-detail__section-title">Parameters</h4>
          <table className="fn-detail__params">
            <tbody>
              {method.parameters.map((name) => (
                <ParamRow key={name} name={name} />
              ))}
            </tbody>
          </table>
        </section>
      )}

      <RefList title="Calls" names={calls} onNavigate={onNavigate} />
      <RefList title="Called by" names={callers} onNavigate={onNavigate} />
    </div>
  );
}

// ── Class detail ─────────────────────────────────────────────────────────────

interface ClsProps {
  cls: ClassInfo;
  file: string;
  onNavigate: (name: string) => void;
}

function ClsDetail({ cls, file, onNavigate }: ClsProps) {
  const { owner, repo } = useAppContext();
  const url = ghUrl(owner, repo, file, cls.start_line, cls.end_line);

  return (
    <div className="fn-detail">
      <div className="fn-detail__header">
        <span className="fn-detail__icon fn-detail__icon--cls">C</span>
        <span className="fn-detail__name">{cls.name}</span>
        <a className="fn-detail__gh" href={url} target="_blank" rel="noreferrer">↗ GH</a>
      </div>

      <div className="fn-detail__file">{file}:{cls.start_line}</div>

      {cls.base_classes.length > 0 && (
        <div className="fn-detail__bases">
          inherits: {cls.base_classes.join(', ')}
        </div>
      )}

      {cls.docstring && (
        <section className="fn-detail__section">
          <h4 className="fn-detail__section-title">Docstring</h4>
          <p className="fn-detail__summary">{cls.docstring}</p>
        </section>
      )}

      {cls.methods.length > 0 && (
        <section className="fn-detail__section">
          <h4 className="fn-detail__section-title">Methods ({cls.methods.length})</h4>
          <div className="fn-detail__method-list">
            {cls.methods.map((m) => (
              <FunctionLink
                key={m.name}
                name={`${cls.name}.${m.name}`}
                onClick={onNavigate}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Root component ───────────────────────────────────────────────────────────

interface Props {
  name: string;
  onNavigate: (name: string) => void;
}

export function FunctionDetailView({ name, onNavigate }: Props) {
  const { owner, repo } = useAppContext();
  const { get, loading, error } = useApi();

  const [fn, setFn] = useState<FunctionInfo | null>(null);
  const [cls, setCls] = useState<ClassInfo | null>(null);
  const [file, setFile] = useState('');
  const [calls, setCalls] = useState<string[]>([]);
  const [callers, setCallers] = useState<string[]>([]);

  const isMethod = name.includes('.');
  const [className, methodName] = isMethod ? name.split('.', 2) : ['', name];

  useEffect(() => {
    if (!owner || !repo) return;

    setFn(null);
    setCls(null);
    setCalls([]);
    setCallers([]);

    const enc = encodeURIComponent(name);

    // Calls outgoing
    get<GraphData>(`/graph/${owner}/${repo}?type=calls&root=${enc}&depth=1`).then((data) => {
      if (data) {
        const thisNode = name.split('.').pop()!;
        setCalls([...new Set(data.edges.map((e) => e.to).filter((t) => t !== thisNode && t !== name))]);
      }
    });

    // Callers (incoming)
    get<CallersResponse>(`/explore/${owner}/${repo}/callers/${enc}`).then((data) => {
      if (data) setCallers(data.callers.filter((c) => c !== name));
    });

    if (isMethod) {
      // Fetch the parent class
      get<ClassInfo>(`/explore/${owner}/${repo}/class/${encodeURIComponent(className)}`).then((c) => {
        if (c) {
          setCls(c);
          // Find the file from classes index key via explore repo
          get<{ classes: string[] }>(`/explore/${owner}/${repo}`).then((overview) => {
            const key = overview?.classes.find((k) => k.endsWith(`::${className}`));
            setFile(key ? key.split('::')[0] : '');
          });
        }
      });
    } else {
      // Fetch standalone function
      get<FunctionInfo & { _file?: string }>(
        `/explore/${owner}/${repo}/function/${encodeURIComponent(name)}`
      ).then((f) => {
        if (f) {
          setFn(f);
          // Recover file path from the repo overview
          get<{ functions: string[] }>(`/explore/${owner}/${repo}`).then((overview) => {
            const key = overview?.functions.find((k) => k.split('::').pop() === name);
            setFile(key ? key.split('::')[0] : '');
          });
        }
      });
    }
  }, [name, owner, repo, get, isMethod, className]);

  if (loading && !fn && !cls) {
    return <div className="fn-detail__loading">Loading…</div>;
  }

  if (error) {
    return <div className="fn-detail__error">{error}</div>;
  }

  if (fn) {
    return <FnDetail fn={fn} file={file} calls={calls} callers={callers} onNavigate={onNavigate} />;
  }

  if (cls) {
    if (isMethod) {
      const method = cls.methods.find((m) => m.name === methodName);
      if (method) {
        return (
          <MethodDetail
            method={method}
            className={className}
            file={file}
            calls={calls}
            callers={callers}
            onNavigate={onNavigate}
          />
        );
      }
    }
    return <ClsDetail cls={cls} file={file} onNavigate={onNavigate} />;
  }

  return <div className="fn-detail__error">Not found: {name}</div>;
}
