import React, { createContext, useContext, useEffect, useState } from 'react';
import type { View } from './types';

const API_BASE = 'http://localhost:8000';

interface AppContextValue {
  owner: string;
  repo: string;
  view: View;
  isIndexed: boolean;
  apiBase: string;
  pendingFunction: string | null;
  setRepo: (owner: string, repo: string) => void;
  setView: (view: View) => void;
  setIsIndexed: (v: boolean) => void;
  navigateTo: (name: string) => void;
  clearPendingFunction: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [owner, setOwner] = useState('');
  const [repo, setRepoName] = useState('');
  const [view, setView] = useState<View>('codemap');
  const [isIndexed, setIsIndexed] = useState(false);
  const [pendingFunction, setPendingFunction] = useState<string | null>(null);

  // Pull current repo from background on mount, with retry until SW responds.
  useEffect(() => {
    let attempts = 0;
    const MAX_ATTEMPTS = 10;

    function tryGetRepo() {
      chrome.runtime.sendMessage({ type: 'GET_REPO' }, (response: { owner: string; repo: string } | null) => {
        // Always access lastError to suppress Chrome's "unchecked" warning.
        void chrome.runtime.lastError;

        if (response?.owner && response?.repo) {
          setOwner(response.owner);
          setRepoName(response.repo);
        } else if (attempts < MAX_ATTEMPTS) {
          attempts++;
          setTimeout(tryGetRepo, 300);
        }
      });
    }

    tryGetRepo();
  }, []);

  // Listen for repo changes pushed from background when user navigates tabs.
  useEffect(() => {
    function onMessage(
      message: { type: string; owner?: string; repo?: string }
    ) {
      if (message.type === 'REPO_UPDATED') {
        setOwner(message.owner ?? '');
        setRepoName(message.repo ?? '');
        setIsIndexed(false);
      }
    }

    chrome.runtime.onMessage.addListener(onMessage);
    return () => chrome.runtime.onMessage.removeListener(onMessage);
  }, []);

  const setRepo = (o: string, r: string) => {
    setOwner(o);
    setRepoName(r);
    setIsIndexed(false);
  };

  const navigateTo = (name: string) => {
    setPendingFunction(name);
    setView('explorer');
  };

  const clearPendingFunction = () => setPendingFunction(null);

  return (
    <AppContext.Provider
      value={{
        owner,
        repo,
        view,
        isIndexed,
        apiBase: API_BASE,
        pendingFunction,
        setRepo,
        setView,
        setIsIndexed,
        navigateTo,
        clearPendingFunction,
      }}
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
