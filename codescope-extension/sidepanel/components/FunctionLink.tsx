import { useAppContext } from '../state/AppContext';

interface FunctionLinkProps {
  name: string;
  file?: string;
  githubUrl?: string;
  onClick?: (name: string) => void;
}

export function FunctionLink({ name, onClick }: FunctionLinkProps) {
  const { navigateTo } = useAppContext();

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    if (onClick) {
      onClick(name);
    } else {
      navigateTo(name);
    }
  }

  return (
    <button className="function-link" onClick={handleClick} title={name}>
      {name}
    </button>
  );
}
