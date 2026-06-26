import { useAppContext } from '../state/AppContext';

interface FunctionLinkProps {
  name: string;
  file?: string;
  githubUrl?: string;
}

export function FunctionLink({ name, githubUrl }: FunctionLinkProps) {
  const { owner, repo } = useAppContext();

  const href =
    githubUrl ??
    `https://github.com/${owner}/${repo}/search?q=${encodeURIComponent(name)}`;

  return (
    <a
      className="function-link"
      href={href}
      target="_blank"
      rel="noreferrer"
      title={name}
    >
      {name}
    </a>
  );
}
