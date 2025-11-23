const CONTEXT_MENU_ID = "investigate-claim";
const BACKEND_URL = "http://localhost:8000/investigate";
const SCAN_URL = "http://localhost:8000/scan";

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

async function sendScanPayload(payload) {
  const res = await fetch(SCAN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return await res.json();
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
    query: result.query || "",
    original_text: result.original_text || selectedText,
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

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function collectBlocksFromTab(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "COLLECT_BLOCKS" }, (response) => {
      resolve(response);
    });
  });
}

async function applyFlagsToTab(tabId, flags) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "APPLY_FLAGS", flags }, (resp) => resolve(resp));
  });
}

async function startScan() {
  const tab = await getActiveTab();
  if (!tab?.id) return { error: "No active tab." };

  const { blocks = [], url, title } = (await collectBlocksFromTab(tab.id)) || {};
  if (!blocks.length) {
    const summary = { total: 0, red: 0, amber: 0, blue: 0, green: 0, ts: Date.now(), error: "No text blocks found." };
    await chrome.storage.local.set({ scanSummary: summary });
    return summary;
  }

  let response;
  try {
    response = await sendScanPayload({ url: url || tab.url, title: title || tab.title, blocks: blocks.slice(0, 20) });
  } catch (err) {
    const summary = { total: blocks.length, red: 0, amber: 0, blue: 0, green: 0, ts: Date.now(), error: String(err) };
    await chrome.storage.local.set({ scanSummary: summary });
    return summary;
  }

  const flags = (response.flags || []).filter((f) => f.verdict !== "skip");
  const red = flags.filter((f) => f.severity === "red").length;
  const amber = flags.filter((f) => f.severity === "amber").length;
  const blue = flags.filter((f) => f.severity === "blue").length;
  const green = flags.filter((f) => f.severity === "green").length;
  await applyFlagsToTab(tab.id, flags);
  const summary = {
    total: blocks.length,
    red,
    amber,
    blue,
    green,
    ts: Date.now(),
    error: null,
    budget: response.budget || null,
  };
  await chrome.storage.local.set({ scanSummary: summary, scanFlags: flags });
  return summary;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "START_SCAN") {
    startScan().then((summary) => sendResponse({ ok: true, summary })).catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // async
  }
  if (msg.type === "CLEAR_FLAGS") {
    getActiveTab().then((tab) => {
      if (tab?.id) {
        chrome.tabs.sendMessage(tab.id, { type: "CLEAR_FLAGS" });
      }
    });
    sendResponse({ ok: true });
    return true;
  }
  return false;
});
