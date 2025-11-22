import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env if present.

try:
    import google.generativeai as genai
except ImportError:  # Library may not be installed in local dev environments.
    genai = None  # type: ignore


MODEL_NAME = "gemini-2.5-flash"
_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")


def _get_client() -> Optional[Any]:
    """Initialise the Gemini client if the library and API key are available."""
    if not genai:
        logging.warning("google-generativeai library not installed; returning stub response.")
        return None
    if not _API_KEY or _API_KEY == "YOUR_GEMINI_API_KEY":
        logging.warning("Gemini API key missing; set GEMINI_API_KEY env var.")
        return None
    genai.configure(api_key=_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


def call_gemini(prompt: str) -> str:
    """
    Call Gemini 2.5 Flash with the provided prompt.

    Returns a string response. If the API is unavailable, returns a stub message
    so downstream code can handle it gracefully.
    """
    client = _get_client()
    if not client:
        return "Gemini API not configured."

    try:
        response = client.generate_content(prompt)
        # google-generativeai returns a response object with .text attribute.
        return response.text or ""
    except Exception as exc:  # pragma: no cover - external API
        logging.exception("Gemini call failed: %s", exc)
        return "Gemini call failed."
