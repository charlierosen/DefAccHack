import sys
from pathlib import Path
from typing import List, Optional

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


class Block(BaseModel):
    id: str
    text: str


class ScanRequest(BaseModel):
    url: Optional[str] = None
    blocks: List[Block]


app = FastAPI(title="Fact Checker", version="0.2.0")

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


@app.post("/scan")
def scan(payload: ScanRequest):
    """Process multiple blocks; skip ones without clear claims."""
    flags = []
    limit = payload.blocks[:20]  # safety limit
    for block in limit:
        original = block.text.strip()
        claim = extract_claim(original)
        # Heuristic: if Gemini returns same text and it's short, skip as non-claim.
        if not claim or (claim.strip().lower() == original.lower() and len(claim.split()) < 5):
            flags.append(
                {
                    "id": block.id,
                    "verdict": "skip",
                    "reason": "No clear claim detected.",
                    "claim": claim or original,
                    "severity": "none",
                    "sources": [],
                }
            )
            continue

        query = make_search_query(claim)
        results = search_web(query)
        verdict, reason, sources = classify_claim(claim, results)

        severity = "green"
        if verdict in {"false", "dangerous"}:
            severity = "red"
        elif verdict == "uncertain":
            severity = "amber"

        flags.append(
            {
                "id": block.id,
                "verdict": verdict,
                "reason": reason,
                "claim": claim,
                "severity": severity,
                "sources": sources,
            }
        )

    return {"flags": flags, "count": len(flags)}
