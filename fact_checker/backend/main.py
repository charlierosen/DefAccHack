import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()  # Load environment variables from .env if present.

# Support running both as package (uvicorn backend.main:app) and as script (uvicorn main:app).
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))
    from classifier import classify_claim
    from google_query import extract_and_make_query
    from searcher import search_web
    from gemini_client import call_gemini
else:
    from .classifier import classify_claim
    from .google_query import extract_and_make_query
    from .searcher import search_web
    from .gemini_client import call_gemini


class InvestigateRequest(BaseModel):
    text: str


class Block(BaseModel):
    id: str
    text: str


class ScanRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    blocks: List[Block]


GEMINI_BUDGET = int(os.getenv("GEMINI_BUDGET", "10"))
# Rough estimate: combined extract+query (1) + classify (1) per investigation.
CALLS_PER_INVESTIGATION = 2


app = FastAPI(title="Fact Checker", version="0.3.0")

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
    claim, query = extract_and_make_query(original_text)
    results = search_web(query)
    verdict, reason, sources = classify_claim(claim, results, page_context="")
    return {
        "claim": claim,
        "verdict": verdict,
        "reason": reason,
        "sources": sources,
        "results": results,
        "query": query,
        "original_text": original_text,
    }


def pre_screen_blocks(blocks: List[Dict]) -> List[Dict]:
    """
    Use a single Gemini call to decide which blocks look like claims and how suspicious they are.

    Returns list of dicts: {"id": str, "is_claim": bool, "suspicion": "high|medium|low", "reason": str}
    """
    # Trim text to keep prompt small.
    trimmed = [{"id": b["id"], "text": (b["text"][:400] + "..." if len(b["text"]) > 400 else b["text"])} for b in blocks]
    prompt = (
        "You have a limited budget. For each text block, decide if it contains a factual claim that might be mis/disinformation. "
        "For claims, assign a suspicion level: high, medium, or low. Skip non-claims. "
        "Respond ONLY as a JSON array of objects: [{\"id\": \"...\", \"is_claim\": true/false, \"suspicion\": \"high|medium|low\", \"reason\": \"...\"}]. "
        "Blocks:\n"
    )
    for b in trimmed:
        prompt += f"- id: {b['id']}\n  text: {b['text']}\n"

    response = call_gemini(prompt)

    def _parse(text: str) -> List[Dict]:
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        # Fallback: try to find the first JSON array.
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return data
            except Exception:
                return []
        return []

    parsed = _parse(response or "")
    output = []
    for item in parsed:
        if not isinstance(item, dict) or "id" not in item:
            continue
        output.append(
            {
                "id": item.get("id"),
                "is_claim": bool(item.get("is_claim", False)),
                "suspicion": (item.get("suspicion") or "low").lower(),
                "reason": item.get("reason", ""),
            }
        )
    return output


@app.post("/scan")
def scan(payload: ScanRequest):
    """Process multiple blocks; skip non-claims and respect a Gemini call budget."""
    flags = []
    limit = payload.blocks[:20]  # safety limit
    # First call: pre-screen to pick which blocks merit investigation.
    pre_screen_data = pre_screen_blocks([b.model_dump() for b in limit])
    pre_screen_map = {item["id"]: item for item in pre_screen_data}

    remaining_budget = max(GEMINI_BUDGET - 1, 0)
    max_investigations = remaining_budget // CALLS_PER_INVESTIGATION if CALLS_PER_INVESTIGATION else 0
    min_calls_target = 8
    min_investigations = 0
    if GEMINI_BUDGET >= min_calls_target and CALLS_PER_INVESTIGATION:
        min_investigations = math.ceil((min_calls_target - 1) / CALLS_PER_INVESTIGATION)

    suspicion_order = {"high": 0, "medium": 1, "low": 2}
    claim_candidates = []

    # Build a short page context string: url, title, and a few snippets.
    snippets = []
    for b in limit[:3]:
        snippet = b.text.strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160] + "..."
        snippets.append(snippet)
    page_context = f"URL: {payload.url or ''}\nTitle: {payload.title or ''}\nSnippets:\n" + "\n".join(snippets)

    for block in limit:
        original = block.text.strip()
        pre = pre_screen_map.get(block.id) or {}
        is_claim = pre.get("is_claim", False)
        suspicion = pre.get("suspicion", "low")
        pre_reason = pre.get("reason", "")

        # Skip non-claims
        if not is_claim:
            flags.append(
                {
                    "id": block.id,
                    "verdict": "skip",
                    "reason": pre_reason or "No clear claim detected.",
                    "claim": original,
                    "severity": "none",
                    "sources": [],
                }
            )
            continue
        claim_candidates.append(
            {
                "block": block,
                "suspicion": suspicion,
                "pre_reason": pre_reason,
                "original": original,
            }
        )

    # Prioritize candidates based on suspicion level.
    claim_candidates.sort(key=lambda c: suspicion_order.get(c["suspicion"], 3))
    target_count = max_investigations
    if max_investigations < min_investigations:
        target_count = max_investigations  # budget too low
    else:
        target_count = max(min_investigations, max_investigations)
    to_investigate = claim_candidates[:target_count] if target_count > 0 else []
    skipped_due_to_budget = claim_candidates[target_count:]

    # Investigate top candidates.
    for item in to_investigate:
        block = item["block"]
        original = item["original"]
        claim, query = extract_and_make_query(original)
        results = search_web(query)
        verdict, reason, sources = classify_claim(claim, results, page_context=page_context)

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
                "query": query,
                "severity": severity,
                "sources": sources,
            }
        )

    # Mark remaining claim-like blocks as not checked due to budget.
    for item in skipped_due_to_budget:
        block = item["block"]
        flags.append(
            {
                "id": block.id,
                "verdict": "not_checked",
                "reason": f"Not checked (budget limit). Suspicion: {item['suspicion']}. {item['pre_reason'] or ''}".strip(),
                "claim": item["original"],
                "severity": "blue",
                "sources": [],
            }
        )

    return {
        "flags": flags,
        "count": len(flags),
        "budget": {
            "total_calls": GEMINI_BUDGET,
            "used_calls": 1 + CALLS_PER_INVESTIGATION * len(to_investigate),
            "investigated": len(to_investigate),
            "skipped_due_to_budget": len(skipped_due_to_budget),
        },
    }
