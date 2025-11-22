"""Search helper using Brave Search or SerpAPI."""

import logging
import os
from typing import Dict, List

import requests


def _search_brave(query: str, api_key: str) -> List[Dict]:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"X-Subscription-Token": api_key}
    params = {"q": query, "count": 5}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("web", {}).get("results", [])
    parsed = []
    for item in results:
        parsed.append(
            {
                "title": item.get("title", ""),
                "snippet": item.get("description", ""),
                "url": item.get("url", ""),
                "domain": item.get("domain", ""),
            }
        )
    return parsed


def _search_serpapi(query: str, api_key: str) -> List[Dict]:
    url = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": query, "api_key": api_key, "num": 5}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("organic_results", [])
    parsed = []
    for item in results:
        parsed.append(
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", "") or item.get("snippet_highlighted_words", ""),
                "url": item.get("link", ""),
                "domain": item.get("displayed_link", ""),
            }
        )
    return parsed


def _mock_results(query: str) -> List[Dict]:
    """Return deterministic mock results for environments without API keys."""
    return [
        {
            "title": f"Background information on: {query}",
            "snippet": "Mock result because no search API key is configured.",
            "url": "https://example.com/mock-info",
            "domain": "example.com",
        }
    ]


def search_web(query: str) -> List[Dict]:
    """
    Search the web via Brave Search or SerpAPI.

    Env vars:
    - BRAVE_API_KEY
    - SERPAPI_API_KEY
    """
    brave_key = os.getenv("BRAVE_API_KEY")
    serp_key = os.getenv("SERPAPI_API_KEY")

    try:
        if brave_key:
            return _search_brave(query, brave_key)
        if serp_key:
            return _search_serpapi(query, serp_key)
        logging.warning("No search API key found; returning mock results.")
    except Exception as exc:  # pragma: no cover - external API
        logging.exception("Search API call failed: %s", exc)
    return _mock_results(query)
