"""Generate claims and search queries via Gemini."""

try:
    from .gemini_client import call_gemini
except ImportError:  # Support running as a script without package context.
    from gemini_client import call_gemini


EXTRACT_AND_QUERY_PROMPT = (
    "Extract the core factual claim from the text below as one short, neutral sentence (<=18 words). "
    "If there is no factual claim, return an empty claim and empty query. "
    "Then produce a concise search query (<=10 words) to find fact checks; focus on key entities and add 'fact check' if useful. "
    "Return JSON only:\n"
    '{{\n  "claim": "<cleaned, neutral claim, <=18 words or empty if none>",\n'
    '  "query": "<short search query, <=10 words, add \\"fact check\\" if useful>"\n}}\n\n'
    "Text:\n\"\"\"\n{text}\n\"\"\"\n"
)


def _squash(text: str, max_words: int = 16) -> str:
    words = text.split()
    if len(words) > max_words:
        words = words[:max_words]
    return " ".join(words)


def extract_and_make_query(text: str) -> tuple[str, str]:
    """Single Gemini call: extract claim + make concise search query."""
    prompt = EXTRACT_AND_QUERY_PROMPT.format(text=text)
    response = call_gemini(prompt) or ""
    claim = text.strip()
    query = claim
    try:
        data = __import__("json").loads(response)
        claim = data.get("claim", claim)
        query = data.get("query", claim)
    except Exception:
        # fallback to simple cleanup
        pass
    claim_short = _squash(claim.strip(), max_words=18)
    query_clean = _squash((query or claim).replace("\n", " "), max_words=10)
    return claim_short, query_clean


# Backward compatibility: still allow make_search_query if needed elsewhere.
def make_search_query(claim: str) -> str:
    prompt = EXTRACT_AND_QUERY_PROMPT.format(text=claim)
    response = call_gemini(prompt) or ""
    try:
        data = __import__("json").loads(response)
        return _squash((data.get("query") or claim).replace("\n", " "))
    except Exception:
        return _squash(claim)
