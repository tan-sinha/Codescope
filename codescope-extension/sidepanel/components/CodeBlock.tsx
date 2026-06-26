interface CodeBlockProps {
  code: string;
  language?: string;
  maxLines?: number;
}

export function CodeBlock({ code, maxLines }: CodeBlockProps) {
  const lines = code.split('\n');
  const visible = maxLines ? lines.slice(0, maxLines) : lines;
  const truncated = maxLines && lines.length > maxLines;

  return (
    <div className="code-block">
      <pre>
        <code>{visible.join('\n')}</code>
      </pre>
      {truncated && (
        <span className="code-block__truncated">
          +{lines.length - maxLines!} more lines
        </span>
      )}
    </div>
  );
}
