"""Extract the core factual claim from user-provided text using Gemini."""

try:
    from .gemini_client import call_gemini
except ImportError:  # Support running as a script without package context.
    from gemini_client import call_gemini


PROMPT_TEMPLATE = (
    "Extract the core factual claim from the following text. \n"
    "Remove opinions, insults, hashtags, emojis, exaggerations, and emotional language.  \n"
    "Rewrite the claim as one short, neutral, search-friendly sentence.\n\n"
    'Text:\n"{text}"\n\n'
    "Output: the cleaned claim.\n\n"
    "If the text contains no factual claim, return the original text."
)


def extract_claim(text: str) -> str:
    """Return a cleaned factual claim string."""
    prompt = PROMPT_TEMPLATE.format(text=text)
    response = call_gemini(prompt)
    return response.strip() if response else text
