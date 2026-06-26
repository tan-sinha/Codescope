// Detects the current GitHub repo from the URL and notifies the background worker.

function extractRepo(): { owner: string; repo: string } | null {
  const match = window.location.pathname.match(/^\/([^/]+)\/([^/]+)/);
  if (!match) return null;
  return { owner: match[1], repo: match[2] };
}

function notifyBackground() {
  const repo = extractRepo();
  if (!repo) return;

  chrome.runtime.sendMessage({
    type: 'REPO_DETECTED',
    owner: repo.owner,
    repo: repo.repo,
  }).catch(() => {});
}

notifyBackground();

// Re-detect on GitHub's soft navigations (pjax / turbo)
document.addEventListener('pjax:end', notifyBackground);
document.addEventListener('turbo:load', notifyBackground);
