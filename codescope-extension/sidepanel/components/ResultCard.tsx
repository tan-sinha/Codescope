import { useAppContext } from '../state/AppContext';
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
    const bare = item.signature.replace(/^[^(]+/, '').trim();
    const ret = item.return_type ? ` → ${item.return_type}` : '';
    return bare + ret;
  }
  return null;
}

interface ResultCardProps {
  item: SearchItem;
  score: number;
}

export function ResultCard({ item, score }: ResultCardProps) {
  const { navigateTo } = useAppContext();
  const { icon, color } = TYPE[item.type];
  const ctx = contextLine(item);

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    navigateTo(item.name);
  }

  function handleGhClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (item.github_url) window.open(item.github_url, '_blank', 'noreferrer');
  }

  return (
    <div className="result-card" onClick={handleClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && navigateTo(item.name)}>
      {/* Row 1: icon · name · GH link · score */}
      <div className="result-card__row1">
        <span className="result-card__icon" style={{ color }}>{icon}</span>
        <span className="result-card__name">{item.name}</span>
        {item.github_url && (
          <button className="result-card__gh" onClick={handleGhClick} title="Open in GitHub">
            ↗
          </button>
        )}
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
    </div>
  );
}
