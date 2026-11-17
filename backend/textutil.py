"""Turning a feed entry into clean article text. No LLM, no database.

Moved out of the AI Hub's worker.py (whose Gemini path this project does not use).
"""
import html
import logging
import re
from typing import Optional

import httpx
import trafilatura

import config
from feeds import Feed

logger = logging.getLogger("hub.text")
_TAGS = re.compile(r"<[^>]+>")


def html_to_text(fragment: str) -> str:
    text = _TAGS.sub(" ", fragment or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def entry_body(entry) -> str:
    """Text carried inside the feed entry itself."""
    parts = [c.get("value", "") for c in entry.get("content", [])] or [entry.get("summary", "")]
    body = html_to_text(" ".join(parts))
    title = entry.get("title", "").strip()
    return f"{title}\n\n{body}" if body else ""


def resolve_link(url: str) -> str:
    """Bing News links are click-trackers that redirect to the article. Store the real address,
    so the same story is recognised as already seen and the dashboard links to the publisher."""
    if "bing.com/news/apiclick" not in url:
        return url
    try:
        r = httpx.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=20, follow_redirects=True)
        return str(r.url)
    except Exception as e:
        logger.warning(f"Could not resolve {url[:80]}: {e}")
        return url


def fetch_page_text(url: str) -> Optional[str]:
    """Downloads a web page and returns its main text."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=True)
    except Exception as e:
        logger.error(f"Error fetching URL {url}: {e}")
    return None


def get_text(feed: Feed, entry, url: str) -> str:
    text = ""
    if feed.text_from == "page":
        text = fetch_page_text(url) or ""
    if len(text) < 200:
        text = entry_body(entry)
    return text[: config.MAX_ARTICLE_CHARS]
