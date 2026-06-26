// Opens the side panel when the extension action is clicked,
// and relays the active GitHub repo from content scripts to the side panel.

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

let currentRepo: { owner: string; repo: string } | null = null;

chrome.runtime.onMessage.addListener(
  (message: IncomingMessage, _sender, sendResponse) => {
    if (message.type === 'REPO_DETECTED') {
      currentRepo = { owner: message.owner, repo: message.repo };
      sendResponse({ ok: true });
    }

    if (message.type === 'GET_REPO') {
      sendResponse(currentRepo);
    }

    return true;
  }
);

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  if (!tab.url?.includes('github.com')) {
    currentRepo = null;
  }
});
