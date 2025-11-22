"""Turn a factual claim into a search-friendly query via Gemini."""

try:
    from .gemini_client import call_gemini
except ImportError:  # Support running as a script without package context.
    from gemini_client import call_gemini


PROMPT_TEMPLATE = (
    "Rewrite the following factual claim as a short search engine query.\n"
    "Your output should aim to find fact-checks or authoritative reporting.\n"
    'Add terms like "fact check" if appropriate.\n\n'
    'Claim:\n"{claim}"\n'
)


def _squash(text: str, max_words: int = 16) -> str:
    words = text.split()
    if len(words) > max_words:
        words = words[:max_words]
    return " ".join(words)


def make_search_query(claim: str) -> str:
    """Return a concise search query for fact-check discovery."""
    prompt = PROMPT_TEMPLATE.format(claim=claim)
    response = call_gemini(prompt)
    cleaned = response.strip().replace("\n", " ") if response else claim
    return _squash(cleaned)
