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


def make_search_query(claim: str) -> str:
    """Return a concise search query for fact-check discovery."""
    prompt = PROMPT_TEMPLATE.format(claim=claim)
    response = call_gemini(prompt)
    return response.strip() if response else claim
