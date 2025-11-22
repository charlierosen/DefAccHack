const graphCanvas = () => document.getElementById("graph");

function renderResult({ claim, verdict, reason, sources, results }) {
  const container = document.getElementById("result");
  if (!verdict) {
    container.textContent = "No investigation yet.";
    const canvas = graphCanvas();
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    return;
  }
  const verdictText = verdict === "true"
    ? "This claim appears to be true."
    : verdict === "false"
    ? "This claim appears to be false."
    : "I am uncertain about this claim.";

  container.innerHTML = `
    <p class="verdict">${verdictText}</p>
    ${claim ? `<p class="claim">Claim: ${claim}</p>` : ""}
    ${reason ? `<p class="reason">${reason}</p>` : ""}
    ${Array.isArray(sources) && sources.length
      ? `<div class="sources"><strong>Sources:</strong><ul>${sources
          .slice(0, 5)
          .map((src) => `<li><a href="${src}" target="_blank" rel="noopener">${src}</a></li>`)
          .join("")}</ul></div>`
      : ""}
  `;

  renderGraph(claim, sources, results);
}

function renderScanSummary(summary) {
  const el = document.getElementById("scan-summary");
  if (!summary) {
    el.textContent = "";
    return;
  }
  if (summary.error) {
    el.innerHTML = `<p class="error">Scan error: ${summary.error}</p>`;
    return;
  }
  el.innerHTML = `
    <p class="scan-stats">
      Scanned ${summary.total || 0} blocks. Flags: 
      <span class="badge red">${summary.red || 0} red</span>
      <span class="badge amber">${summary.amber || 0} amber</span>
      <span class="badge blue">${summary.blue || 0} not checked</span>
      <span class="badge green">${summary.green || 0} ok</span>
    </p>
    ${summary.budget ? `<p class="budget">Budget: used ${summary.budget.used_calls}/${summary.budget.total_calls} Gemini calls; investigated ${summary.budget.investigated}, skipped ${summary.budget.skipped_due_to_budget} due to budget.</p>` : ""}
    </p>
  `;
}

function renderGraph(claim, sources = [], results = []) {
  const canvas = graphCanvas();
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!sources.length && !results.length) {
    ctx.fillStyle = "#94a1b2";
    ctx.font = "12px Arial";
    ctx.fillText("No graph yet. Run an investigation.", 10, canvas.height / 2);
    return;
  }

  const nodes = [];
  const edges = [];

  // Claim node at center.
  const center = { x: canvas.width / 2, y: canvas.height / 2, label: claim || "Claim" };
  nodes.push({ ...center, radius: 28, color: "#1b263b" });

  const visibleSources = (sources && sources.length ? sources : [])
    .concat(results ? results.map((r) => r.url).filter(Boolean) : [])
    .slice(0, 8);

  const radius = Math.min(canvas.width, canvas.height) / 2 - 30;
  visibleSources.forEach((src, idx) => {
    const angle = (2 * Math.PI * idx) / visibleSources.length;
    const x = center.x + radius * Math.cos(angle);
    const y = center.y + radius * Math.sin(angle);
    const label = (src || "").replace(/^https?:\/\//, "").slice(0, 28);
    nodes.push({ x, y, label, url: src, radius: 18, color: "#415a77" });
    edges.push({ from: 0, to: nodes.length - 1 });
  });

  // Draw edges.
  ctx.strokeStyle = "#778da9";
  ctx.lineWidth = 1.2;
  edges.forEach(({ from, to }) => {
    const a = nodes[from];
    const b = nodes[to];
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  });

  // Draw nodes.
  nodes.forEach((node) => {
    ctx.beginPath();
    ctx.fillStyle = node.color;
    ctx.strokeStyle = "#e0e1dd";
    ctx.lineWidth = 1;
    ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#e0e1dd";
    ctx.font = "11px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const label = node.label || "";
    const lines = wrapText(ctx, label, node.radius * 2);
    lines.slice(0, 2).forEach((line, i) => {
      ctx.fillText(line, node.x, node.y + (i - (lines.length - 1) / 2) * 12);
    });
  });
}

function wrapText(ctx, text, maxWidth) {
  const words = text.split(" ");
  const lines = [];
  let line = "";
  words.forEach((word) => {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth) {
      if (line) lines.push(line);
      line = word;
    } else {
      line = test;
    }
  });
  if (line) lines.push(line);
  return lines;
}

document.addEventListener("DOMContentLoaded", () => {
  const controls = {
    scanBtn: document.getElementById("scan-btn"),
    clearBtn: document.getElementById("clear-btn"),
  };

  controls.scanBtn?.addEventListener("click", () => {
    controls.scanBtn.disabled = true;
    controls.scanBtn.textContent = "Scanning...";
    chrome.runtime.sendMessage({ type: "START_SCAN" }, () => {
      setTimeout(() => {
        controls.scanBtn.disabled = false;
        controls.scanBtn.textContent = "Scan this page";
      }, 500);
    });
  });

  controls.clearBtn?.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "CLEAR_FLAGS" });
    chrome.storage.local.remove(["scanSummary", "scanFlags"]);
    renderScanSummary(null);
  });

  function load() {
    chrome.storage.local.get(["claim", "verdict", "reason", "sources", "results", "scanSummary"], (data) => {
      renderResult(data);
      renderScanSummary(data.scanSummary);
    });
  }

  chrome.storage.onChanged.addListener((changes) => {
    const snapshot = {};
    ["claim", "verdict", "reason", "sources", "results", "scanSummary"].forEach((k) => {
      if (changes[k]) snapshot[k] = changes[k].newValue;
    });
    if (Object.keys(snapshot).length) {
      const data = {
        claim: snapshot.claim,
        verdict: snapshot.verdict,
        reason: snapshot.reason,
        sources: snapshot.sources,
        results: snapshot.results,
      };
      renderResult({ ...data, ...snapshot });
      renderScanSummary(snapshot.scanSummary);
    }
  });

  load();
});
