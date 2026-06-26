import React, { createContext, useContext, useEffect, useState } from 'react';
import type { View } from './types';

const API_BASE = 'http://localhost:8000';

interface AppContextValue {
  owner: string;
  repo: string;
  view: View;
  isIndexed: boolean;
  apiBase: string;
  setRepo: (owner: string, repo: string) => void;
  setView: (view: View) => void;
  setIsIndexed: (v: boolean) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [owner, setOwner] = useState('');
  const [repo, setRepoName] = useState('');
  const [view, setView] = useState<View>('search');
  const [isIndexed, setIsIndexed] = useState(false);

  // On mount, ask the background worker for the active GitHub repo
  useEffect(() => {
    chrome.runtime.sendMessage({ type: 'GET_REPO' }, (response) => {
      if (response?.owner && response?.repo) {
        setOwner(response.owner);
        setRepoName(response.repo);
      }
    });
  }, []);

  const setRepo = (o: string, r: string) => {
    setOwner(o);
    setRepoName(r);
    setIsIndexed(false);
  };

  return (
    <AppContext.Provider
      value={{ owner, repo, view, isIndexed, apiBase: API_BASE, setRepo, setView, setIsIndexed }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used inside AppProvider');
  return ctx;
}
