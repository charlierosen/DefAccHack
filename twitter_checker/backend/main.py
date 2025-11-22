import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # Load environment variables from .env if present.

# Support running both as package (uvicorn backend.main:app) and as script (uvicorn main:app).
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))
    from claim_extractor import extract_claim
    from classifier import classify_claim
    from google_query import make_search_query
    from searcher import search_web
else:
    from .claim_extractor import extract_claim
    from .classifier import classify_claim
    from .google_query import make_search_query
    from .searcher import search_web


class InvestigateRequest(BaseModel):
    text: str


app = FastAPI(title="Twitter Checker", version="0.1.0")

# Allow extension requests during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/investigate")
def investigate(payload: InvestigateRequest):
    original_text = payload.text
    claim = extract_claim(original_text)
    query = make_search_query(claim)
    results = search_web(query)
    verdict, reason, sources = classify_claim(claim, results)
    return {
        "claim": claim,
        "verdict": verdict,
        "reason": reason,
        "sources": sources,
        "results": results,
        "query": query,
    }
