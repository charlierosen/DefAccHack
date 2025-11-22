# DefAccHack

LLM guardrail MVP that sits in front of a deliberately vulnerable SQLite backend.

## What it does
- Streamlit UI accepts raw user input that would normally hit SQL directly.
- Guardrail layer (Gemini if `GEMINI_API_KEY` is set; otherwise regex heuristics) decides SAFE vs BLOCKED.
- If SAFE, the backend runs an intentionally insecure interpolated SQL query.
- If BLOCKED, the app returns fake/decoy data instead of touching the real database.

## Quick start
1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the demo
   ```bash
   streamlit run app.py
   ```
3. Try safe input (`Alice`) and malicious input (`Alice'; DROP TABLE employees;--`).
4. Optional: export `GEMINI_API_KEY` to use Gemini for the guardrail; otherwise the regex heuristic is used.

## Files
- `app.py` — Streamlit UI wiring guardrail → backend or fake data.
- `guardrail.py` — LLM/heuristic SAFE/BLOCK decisions.
- `data_backend.py` — Seeds `private.db` and exposes the intentionally insecure query.
- `requirements.txt` — Python deps.
