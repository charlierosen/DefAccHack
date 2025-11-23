// Content script: selection helper, block collection, and highlighting.

const TC_STYLE_ID = "tc-flag-style";
let tcBlockRegistry = new Map();

function injectStyles() {
  if (document.getElementById(TC_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = TC_STYLE_ID;
  style.textContent = `
    .tc-flag { position: relative; }
    .tc-flag.tc-flag-red { background: rgba(220, 38, 38, 0.25); outline: 1px solid rgba(220, 38, 38, 0.6); }
    .tc-flag.tc-flag-amber { background: rgba(245, 158, 11, 0.25); outline: 1px solid rgba(245, 158, 11, 0.6); }
    .tc-flag.tc-flag-blue { background: rgba(59, 130, 246, 0.25); outline: 1px solid rgba(59, 130, 246, 0.6); }
    .tc-flag.tc-flag-green { background: rgba(34, 197, 94, 0.22); outline: 1px solid rgba(34, 197, 94, 0.6); }
    .tc-flag-tooltip {
      position: absolute;
      z-index: 2147483647;
      background: #0f172a;
      color: #e2e8f0;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 12px;
      max-width: 260px;
      line-height: 1.3;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
      display: none;
    }
    .tc-flag:hover .tc-flag-tooltip { display: block; }
  `;
  document.head.appendChild(style);
}

function isVisible(el) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
  if (rect.width === 0 || rect.height === 0) return false;
  return rect.bottom > 0 && rect.right > 0 && rect.top < (window.innerHeight || document.documentElement.clientHeight);
}

function clearFlags() {
  document.querySelectorAll(".tc-flag").forEach((el) => {
    el.classList.remove("tc-flag", "tc-flag-red", "tc-flag-amber", "tc-flag-blue", "tc-flag-green");
    const tooltip = el.querySelector(".tc-flag-tooltip");
    if (tooltip) tooltip.remove();
  });
}

function collectBlocks() {
  injectStyles();
  tcBlockRegistry = new Map();
  const blocks = [];
  const candidates = document.querySelectorAll("p, li, blockquote, article, section, h1, h2, h3, h4, h5, h6");
  let id = 0;
  candidates.forEach((el) => {
    if (!isVisible(el)) return;
    const text = (el.innerText || "").trim();
    if (text.length < 40) return; // skip very short fragments
    const blockId = `b${id++}`;
    tcBlockRegistry.set(blockId, el);
    blocks.push({ id: blockId, text });
  });
  return blocks;
}

function applyFlags(flags = []) {
  injectStyles();
  clearFlags();
  flags.forEach((flag) => {
    const el = tcBlockRegistry.get(flag.id);
    if (!el) return;
    el.classList.add("tc-flag");
    if (flag.severity === "red") el.classList.add("tc-flag-red");
    else if (flag.severity === "amber") el.classList.add("tc-flag-amber");
    else if (flag.severity === "blue") el.classList.add("tc-flag-blue");
    else if (flag.severity === "green") el.classList.add("tc-flag-green");

    if (flag.reason || (flag.sources && flag.sources.length)) {
    const tooltip = document.createElement("div");
    tooltip.className = "tc-flag-tooltip";
    const sources = (flag.sources || []).slice(0, 2).map((s) => `<div>${s}</div>`).join("");
      const queryLine = flag.query ? `<div><em>Search:</em> ${truncate(flag.query, 80)}</div>` : "";
    tooltip.innerHTML = `
      <div><strong>${flag.verdict || "flagged"}</strong></div>
        ${flag.reason ? `<div>${flag.reason}</div>` : ""}
        ${queryLine}
        ${sources ? `<div><em>Sources:</em>${sources}</div>` : ""}
      `;
      el.appendChild(tooltip);
    }
  });
}

function truncate(text, maxLen) {
  if (!text) return "";
  return text.length > maxLen ? `${text.slice(0, maxLen - 1)}…` : text;
}

// Responders.
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "GET_SELECTION") {
    sendResponse({ text: window.getSelection().toString() });
    return true;
  }
  if (request.type === "COLLECT_BLOCKS") {
    const blocks = collectBlocks();
    sendResponse({ blocks, url: location.href, title: document.title || "" });
    return true;
  }
  if (request.type === "APPLY_FLAGS") {
    applyFlags(request.flags || []);
    sendResponse({ ok: true });
    return true;
  }
  if (request.type === "CLEAR_FLAGS") {
    clearFlags();
    sendResponse({ ok: true });
    return true;
  }
  return false;
});
