"""Classify claims using Gemini and search results."""

import json
import re
from typing import Dict, List, Tuple

try:
    from .gemini_client import call_gemini
except ImportError:  # Support running as a script without package context.
    from gemini_client import call_gemini


PROMPT_TEMPLATE = (
    'Here is a factual claim:\n\n"{claim}"\n\n'
    "Here are the top search results:\n{results}\n\n"
    "Based only on these results, classify the claim as TRUE, FALSE, or UNCERTAIN.\n"
    "Rules:\n"
    "- If several reputable sources confirm it → TRUE\n"
    "- If multiple fact-checks or reputable outlets say it is false → FALSE\n"
    "- If evidence is mixed or unclear → UNCERTAIN\n\n"
    "Respond ONLY in this JSON format:\n\n"
    '{{\n  "verdict": "true | false | uncertain",\n'
    '  "reason": "short explanation summarising the evidence",\n'
    '  "sources": ["url1", "url2", "url3"]\n}}\n'
)


def _format_results(results: List[Dict]) -> str:
    formatted = []
    for item in results:
        formatted.append(
            f"- Title: {item.get('title','')}\n"
            f"  Snippet: {item.get('snippet','')}\n"
            f"  Domain: {item.get('domain','')}\n"
            f"  URL: {item.get('url','')}"
        )
    return "\n".join(formatted)


def classify_claim(claim: str, results: List[Dict]) -> Tuple[str, str, List[str]]:
    """
    Return a verdict and reason tuple (sources are extracted separately).

    Verdict is one of: true | false | uncertain
    """
    prompt = PROMPT_TEMPLATE.format(claim=claim, results=_format_results(results))
    response = call_gemini(prompt)

    def _parse_json(text: str) -> Dict:
        """Try direct JSON parse, then fallback to the first braces block."""
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
        return {}

    data = _parse_json(response or "")
    verdict = data.get("verdict", "uncertain")
    reason = data.get("reason", response if response else "")
    sources_raw = data.get("sources", [])
    sources = [str(src) for src in sources_raw if isinstance(src, (str, bytes))]

    if verdict not in {"true", "false", "uncertain"}:
        verdict = "uncertain"
    if not reason:
        reason = "Gemini response could not be parsed."

    return verdict, reason, sources
