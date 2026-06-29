chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(console.error);

interface RepoMessage {
  type: 'REPO_DETECTED';
  owner: string;
  repo: string;
}

interface GetRepoMessage {
  type: 'GET_REPO';
}

type IncomingMessage = RepoMessage | GetRepoMessage;

chrome.runtime.onMessage.addListener(
  (message: IncomingMessage, _sender, sendResponse) => {

    if (message.type === 'REPO_DETECTED') {
      const repo = { owner: message.owner, repo: message.repo };
      // Persist so the repo survives SW termination
      chrome.storage.session.set({ currentRepo: repo }).then(() => {
        // Broadcast to any open extension pages (side panel)
        chrome.runtime.sendMessage({ type: 'REPO_UPDATED', ...repo })
          .catch(() => {}); // silent if no listeners
        sendResponse({ ok: true });
      });
      return true; // keep channel open for async sendResponse
    }

    if (message.type === 'GET_REPO') {
      // Read from storage, not memory — survives SW restart
      chrome.storage.session.get('currentRepo').then((result) => {
        sendResponse((result.currentRepo as { owner: string; repo: string } | undefined) ?? null);
      });
      return true;
    }

    return true;
  }
);

// Clear stored repo when user leaves GitHub
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (!tab.url?.includes('github.com')) {
      await chrome.storage.session.remove('currentRepo');
      chrome.runtime.sendMessage({ type: 'REPO_UPDATED', owner: '', repo: '' })
        .catch(() => {});
    }
  } catch { /* tab may have closed */ }
});
