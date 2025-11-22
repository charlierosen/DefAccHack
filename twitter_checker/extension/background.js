const CONTEXT_MENU_ID = "investigate-claim";
const BACKEND_URL = "http://localhost:8000/investigate";

// Create context menu on install or update.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Investigate this claim",
    contexts: ["selection"],
  });
});

async function getSelectionFromTab(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "GET_SELECTION" }, (response) => {
      resolve(response?.text || "");
    });
  });
}

async function sendToBackend(text) {
  try {
    const res = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(`Backend error: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Backend request failed", err);
    return { verdict: "uncertain", reason: "Backend unavailable", claim: text };
  }
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID || !tab?.id) return;

  const selectedText = info.selectionText || (await getSelectionFromTab(tab.id));
  if (!selectedText) return;

  const result = await sendToBackend(selectedText);
  await chrome.storage.local.set({
    claim: result.claim,
    verdict: result.verdict,
    reason: result.reason,
    sources: result.sources || [],
    results: result.results || [],
  });

  // Try to surface the popup with the latest result.
  if (chrome.action && chrome.action.openPopup) {
    try {
      await chrome.action.openPopup();
    } catch (err) {
      console.warn("Could not open popup automatically.", err);
    }
  }
});
