# tools.py
# Feed validator + trafilatura full-text fetch tool
# These are plain Python functions and a CrewAI @tool-decorated function.

import feedparser
import trafilatura
import requests
from crewai.tools import tool
from typing import Optional


def validate_feeds(candidate_urls: list[str], timeout: int = 8) -> list[str]:
    """
    Try to parse each candidate RSS/Atom URL with feedparser.
    Returns only those that successfully parse and contain at least one entry.
    Silently discards failures — Scout never sees broken feeds.
    """
    valid = []
    for url in candidate_urls:
        try:
            feed = feedparser.parse(url)
            # feedparser sets bozo=True on malformed feeds but still "succeeds"
            # We require at least one parseable entry to count as valid.
            if feed.entries and len(feed.entries) > 0:
                valid.append(url)
        except Exception:
            pass
    return valid


def fetch_full_article_text(url: str) -> str:
    """
    Given a URL to a news article, fetches and extracts the clean plain-text
    body of the article using trafilatura.
    Returns the extracted text, or a short error message if extraction fails.
    This is not an LLM call — trafilatura does rule-based HTML extraction.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"[FETCH FAILED] Could not download content from: {url}"

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if not text or len(text.strip()) < 100:
            return f"[EXTRACTION FAILED] Insufficient text extracted from: {url}"

        # Cap at ~4000 chars to stay within reasonable token budgets
        return text.strip()[:4000]

    except Exception as exc:
        return f"[ERROR] {type(exc).__name__}: {exc}"
