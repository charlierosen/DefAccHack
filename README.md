# DefAccHack Monorepo

This repo now contains two pieces:
- **Honeypot Guardrail (root)** — LLM/heuristic guardrail in front of a deliberately vulnerable SQLite backend.
- **Fact Checker (`fact_checker/`)** — Chrome extension + FastAPI backend that classifies highlighted or in-page text via Gemini and web search.

---

## 1) Honeypot Guardrail (`honey_pot/`)
- Streamlit UI accepts raw user input that would normally hit SQL directly.
- Guardrail layer (Gemini if `GEMINI_API_KEY` is set; otherwise regex heuristics) decides SAFE vs BLOCKED.
- If SAFE, the backend runs an intentionally insecure interpolated SQL query.
- If BLOCKED, the app returns fake/decoy data instead of touching the real database.

### Run it
```bash
cd honey_pot
pip install -r requirements.txt
streamlit run app.py
```
Try safe input (`Alice`) and malicious input (`Alice'; DROP TABLE employees;--`).  
Optional: export `GEMINI_API_KEY` to use Gemini for the guardrail; otherwise the regex heuristic is used.

### Files
- `honey_pot/app.py` — Streamlit UI wiring guardrail → backend or fake data.
- `honey_pot/guardrail.py` — LLM/heuristic SAFE/BLOCK decisions.
- `honey_pot/data_backend.py` — Seeds `private.db` and exposes the intentionally insecure query.
- `honey_pot/requirements.txt` — Python deps.

---

## 2) Fact Checker (`fact_checker/`)
Chrome context-menu extension plus FastAPI backend that sends highlighted text to Gemini 2.5 Flash, rewrites it into a search query, fetches web evidence, and returns a verdict.

### Project layout
```
fact_checker/
  backend/
    main.py
    requirements.txt
    claim_extractor.py
    google_query.py
    searcher.py
    classifier.py
    gemini_client.py
  extension/
    manifest.json
    background.js
    content.js
    popup.html
    popup.js
    styles.css
```

### Setup
1) Create/activate Python 3.10+ venv.  
2) Install backend deps:
   ```bash
   cd fact_checker/backend
   pip install -r requirements.txt
   ```
3) Set env vars (loaded from `.env` if present):
   - `GEMINI_API_KEY` (or edit `gemini_client.py` placeholder)
   - `BRAVE_API_KEY` or `SERPAPI_API_KEY` (search); mock results otherwise.
   - Optional: `GEMINI_BUDGET` (default 10 calls) for scan mode.

### Run backend
```bash
cd fact_checker/backend
uvicorn main:app --reload
```
API at `http://localhost:8000` with CORS open for the extension.

### Load the Chrome extension
1) Go to `chrome://extensions` → enable Developer Mode.  
2) “Load unpacked” → select `fact_checker/extension`.  
3) Context menu entry “Investigate this claim” appears.

### Usage
- **Single claim:** highlight text → right-click “Investigate this claim.” The popup shows verdict, reason, sources, search query, and original text; graph visualizes sources.
- **Page scan:** popup → “Scan this page.” Content script gathers visible blocks; backend pre-screens with one Gemini call, then investigates highest-priority claims within budget (false/dangerous→red, uncertain→amber, not-checked due to budget→blue, passed→green). Hover highlights for reason/search/sources; “Clear highlights” to remove.

### Notes on Gemini
- Prompts live in `gemini_client.py`, `claim_extractor.py`, `google_query.py`, `classifier.py`.
- Combined extract+query uses one Gemini call; classify is another. Pre-screen is one call per scan.
- Stub responses are returned if Gemini is unavailable so UI still works for dev.

### Future ideas
- Visual evidence graph/timeline overlays; embedding-based clustering; bot/coordination detection; audit trails and shareable permalinks.
