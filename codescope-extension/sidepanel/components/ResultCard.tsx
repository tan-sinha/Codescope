import type { SearchItem, SearchItemType } from '../state/types';

const TYPE: Record<SearchItemType, { icon: string; color: string }> = {
  function: { icon: 'ƒ', color: 'var(--c-fn)' },
  class:    { icon: 'C', color: 'var(--c-cls)' },
  method:   { icon: 'M', color: 'var(--c-method)' },
};

function locationLabel(item: SearchItem): string {
  if (!item.lines) return item.file;
  return `${item.file}:${item.lines[0]}`;
}

function contextLine(item: SearchItem): string | null {
  if (item.called_by?.length) {
    return `Called by: ${item.called_by.slice(0, 3).join(', ')}${item.called_by.length > 3 ? '…' : ''}`;
  }
  if (item.signature) {
    const bare = item.signature.replace(/^[^(]+/, '').trim(); // "(a, b) → T"
    const ret = item.return_type ? ` → ${item.return_type}` : '';
    return bare + ret;
  }
  return null;
}

interface ResultCardProps {
  item: SearchItem;
  score: number; // normalised 0-1
}

export function ResultCard({ item, score }: ResultCardProps) {
  const { icon, color } = TYPE[item.type];
  const ctx = contextLine(item);
  const href = item.github_url;

  return (
    <a
      className="result-card"
      href={href}
      target="_blank"
      rel="noreferrer"
      title={item.name}
    >
      {/* Row 1: icon · name · score */}
      <div className="result-card__row1">
        <span className="result-card__icon" style={{ color }}>
          {icon}
        </span>
        <span className="result-card__name">{item.name}</span>
        <span className="result-card__score">{score.toFixed(2)}</span>
      </div>

      {/* Row 2: file:line */}
      <div className="result-card__loc">{locationLabel(item)}</div>

      {/* Row 3: summary */}
      {item.summary && (
        <div className="result-card__summary">{item.summary}</div>
      )}

      {/* Row 4: called_by / signature */}
      {ctx && <div className="result-card__ctx">{ctx}</div>}
    </a>
  );
}
