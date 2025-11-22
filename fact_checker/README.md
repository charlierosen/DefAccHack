# Fact Checker

Chrome context-menu extension plus FastAPI backend that sends highlighted text to Gemini 2.5 Flash, rewrites it into a search query, fetches web evidence, and returns a simple verdict.

## Project layout
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

## Setup
1) Create and activate a Python 3.10+ virtualenv.  
2) Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3) Set environment variables (loaded automatically from a local `.env` if present):
   - `GEMINI_API_KEY` (or edit `gemini_client.py` placeholder `YOUR_GEMINI_API_KEY`)
   - Either `BRAVE_API_KEY` or `SERPAPI_API_KEY` for web search. If none are set, mock results are returned.

## Run the backend
```bash
cd backend
uvicorn main:app --reload
```
The API listens on `http://localhost:8000`. CORS is open for local extension use.

## Load the Chrome extension
1) Go to `chrome://extensions`.  
2) Enable Developer Mode.  
3) Click “Load unpacked” and select `fact_checker/extension`.  
4) The extension adds a context menu entry “Investigate this claim”.

## Usage
1) Highlight text on any page, right-click, and choose **Investigate this claim**.  
2) The background script sends the text to `POST /investigate`:
   - `extract_claim()` cleans the claim with Gemini 2.5 Flash.  
   - `make_search_query()` rewrites it for search with Gemini.  
   - `search_web()` queries Brave Search or SerpAPI (or returns mock data).  
   - `classify_claim()` asks Gemini to label the claim as `true | false | uncertain` and return source URLs from the provided results.  
3) The popup displays one of:
   - “This claim appears to be true.”
   - “This claim appears to be false.”
   - “I am uncertain about this claim.”
   - It also lists cited source URLs if Gemini returns them and draws a simple source graph.

### Page scanning
- Use the popup button **Scan this page**. The content script gathers visible text blocks, the backend decides which blocks contain claims (skips non-claims), then flags suspicious ones (red for false/dangerous, amber for uncertain).  
- The backend uses a limited Gemini budget (default 10 calls). It first pre-screens all blocks with one Gemini call, then only investigates the highest-priority claims within the remaining budget. Blocks flagged as suspicious but not investigated are marked blue (“not checked”). Claims that pass are green.  
- Follow-up investigations include a bit of page context (URL, title, and a few snippets) in the Gemini classification prompt.  
- Hover highlighted text on the page to see a tooltip with the reason and sources.  
- Click **Clear highlights** in the popup to remove flags.

## Notes on Gemini 2.5 Flash
- All AI prompts live in `gemini_client.py`, `claim_extractor.py`, `google_query.py`, and `classifier.py`.  
- Replace the `YOUR_GEMINI_API_KEY` placeholder or set `GEMINI_API_KEY`.  
- The code returns stubbed responses if Gemini is unavailable so UI still works for development.

## Future ideas
- Visual evidence graph and timeline overlays.  
- Embedding-based source clustering.  
- Bot/coordination pattern detection.  
- Per-claim audit trails and shareable permalinks.
