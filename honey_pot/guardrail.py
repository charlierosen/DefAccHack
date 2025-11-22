import os
import re
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # Load variables from .env if present.

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    genai = None


SUSPICIOUS_PATTERNS = [
    r"(?i)\bunion\b",
    r"(?i)\bdrop\b",
    r"(?i)\binsert\b",
    r"(?i)\bdelete\b",
    r"(?i)\bupdate\b",
    r"(?i)or\s+1=1",
    r";",
    r"--",
    r"/\*",
    r"(?i)\bselect\b.+\bfrom\b",
]


@dataclass
class GuardrailDecision:
    safe: bool
    reason: str
    source: str  # "heuristic" or "gemini"


def _heuristic_guard(user_input: str) -> GuardrailDecision:
    hits = [p for p in SUSPICIOUS_PATTERNS if re.search(p, user_input)]
    if hits:
        return GuardrailDecision(
            safe=False,
            reason=f"Suspicious patterns detected: {', '.join(hits)}",
            source="heuristic",
        )
    return GuardrailDecision(
        safe=True, reason="No obvious SQL injection markers detected.", source="heuristic"
    )


def _gemini_guard(user_input: str) -> Optional[GuardrailDecision]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key or genai is None:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            "You are a security filter. Given a user input that will be placed directly into an "
            "SQL query, classify it strictly as SAFE or UNSAFE. If UNSAFE, briefly say why. "
            f"User input: ```{user_input}```"
        )
        response = model.generate_content(prompt)
        verdict = (response.text or "").upper()
        if "UNSAFE" in verdict:
            return GuardrailDecision(
                safe=False, reason=verdict.strip(), source="gemini"
            )
        if "SAFE" in verdict:
            return GuardrailDecision(
                safe=True, reason=verdict.strip(), source="gemini"
            )
    except Exception as exc:  # pragma: no cover - best-effort path
        return GuardrailDecision(
            safe=False,
            reason=f"Gemini call failed: {exc}. Falling back to heuristic.",
            source="gemini",
        )
    return None


def evaluate_input(user_input: str) -> GuardrailDecision:
    """Try Gemini if available, otherwise use a regex heuristic."""
    if user_input.strip() == "":
        return GuardrailDecision(
            safe=False, reason="Empty input is not allowed.", source="heuristic"
        )

    gemini_decision = _gemini_guard(user_input)
    if gemini_decision:
        return gemini_decision
    return _heuristic_guard(user_input)
