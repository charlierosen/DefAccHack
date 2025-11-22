function renderResult({ claim, verdict, reason, sources }) {
  const container = document.getElementById("result");
  if (!verdict) {
    container.textContent = "No investigation yet.";
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
}

document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.local.get(["claim", "verdict", "reason", "sources"], (data) => {
    renderResult(data);
  });
});
