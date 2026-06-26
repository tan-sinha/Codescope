interface BreadcrumbSegment {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  segments: BreadcrumbSegment[];
}

export function Breadcrumb({ segments }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb" aria-label="breadcrumb">
      {segments.map((seg, i) => (
        <span key={i} className="breadcrumb__item">
          {i > 0 && <span className="breadcrumb__sep">/</span>}
          {seg.onClick ? (
            <button className="breadcrumb__link" onClick={seg.onClick}>
              {seg.label}
            </button>
          ) : (
            <span className="breadcrumb__current">{seg.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
