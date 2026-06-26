import { useCallback, useState } from 'react';
import { useAppContext } from '../state/AppContext';

export function useApi() {
  const { apiBase } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useCallback(
    async <T>(method: string, path: string, body?: unknown): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${apiBase}${path}`, {
          method,
          headers: body ? { 'Content-Type': 'application/json' } : {},
          body: body ? JSON.stringify(body) : undefined,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `HTTP ${res.status}`);
        }
        return (await res.json()) as T;
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unknown error');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [apiBase]
  );

  const get = useCallback(
    <T>(path: string) => request<T>('GET', path),
    [request]
  );

  const post = useCallback(
    <T>(path: string, body: unknown) => request<T>('POST', path, body),
    [request]
  );

  return { get, post, loading, error };
}
