#!/usr/bin/env python3
"""
browse_page.py - OpenClaw Free Web Search: Browse/Viewing Module v2.0
======================================================================
Fetch and extract readable content from a URL using pure stdlib.
Zero API keys required. 100% free.

Features:
- Browse/Viewing : fetches full page HTML, extracts main content as clean text
- Anti-hallucination checks:
    * Detects paywall / login walls / empty pages
    * Extracts and displays publication date when available
    * Reports content confidence level (high/medium/low)
    * Warns agent when content is insufficient to answer from
- Invalid page detection: 404, 403, CAPTCHA, JS-only pages
- Structured output: title, url, published_date, word_count, content, confidence

Usage:
  python3 browse_page.py --url "https://example.com/article"
  python3 browse_page.py --url "https://github.com/owner/repo" --max-words 800
  python3 browse_page.py --url "https://example.com" --json
"""

from __future__ import annotations
import argparse, html, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path
from typing import Optional

USER_AGENT = "OpenClawFreeSearch/2.0 (compatible; Readability)"
MAX_WORDS_DEFAULT = 600

# Tags whose content we want to strip entirely
STRIP_TAGS = re.compile(
    r"<(script|style|nav|header|footer|aside|form|button|noscript|iframe|svg|ads?)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
# HTML tag stripper
TAG_RE = re.compile(r"<[^>]+>")
# Multiple whitespace normaliser
WS_RE = re.compile(r"[ \t]+")
NL_RE = re.compile(r"\n{3,}")

# Patterns that indicate the page is blocked/gated
BLOCKED_PATTERNS = [
    r"subscribe to (read|continue|access)",
    r"sign in to (continue|read|view)",
    r"create (a free )?account to",
    r"this (article|content|page) is (for|behind) (subscribers|paywall)",
    r"please enable (javascript|cookies)",
    r"access denied",
    r"403 forbidden",
    r"404 not found",
    r"page not found",
    r"enable javascript to",
]
BLOCKED_RE = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)

# Patterns to extract publication date from HTML meta tags
DATE_META_PATTERNS = [
    r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|pubdate|date|og:updated_time|datePublished)["\'][^>]+content=["\']([0-9T:Z.+-]{10,25})["\'][^>]*/?>',
    r'<meta[^>]+content=["\']([0-9T:Z.+-]{10,25})["\'][^>]+(?:property|name)=["\'](?:article:published_time|pubdate|date)["\'][^>]*/?>',
    r'<time[^>]+datetime=["\']([0-9T:Z.+-]{10,25})["\'][^>]*>',
]

# Main content container selectors (heuristic, no external libs)
MAIN_CONTENT_SELECTORS = [
    r"<article[^>]*>(.*?)</article>",
    r'<div[^>]+(?:class|id)=["\'][^"\']*(?:article|post|content|main|entry|body)[^"\']*["\'][^>]*>(.*?)</div>',
    r"<main[^>]*>(.*?)</main>",
]


def _strip_html(html_text: str) -> str:
    """Remove scripts/styles/nav, strip all tags, normalise whitespace."""
    text = STRIP_TAGS.sub(" ", html_text)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text)
    text = NL_RE.sub("\n\n", text)
    return text.strip()


def _extract_title(html_text: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    if m:
        return html.unescape(TAG_RE.sub("", m.group(1))).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    if m:
        return html.unescape(TAG_RE.sub("", m.group(1))).strip()
    return ""


def _extract_date(html_text: str) -> str:
    for pat in DATE_META_PATTERNS:
        m = re.search(pat, html_text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def _extract_main_content(html_text: str) -> str:
    """Try to extract the main content block; fall back to full body."""
    for pat in MAIN_CONTENT_SELECTORS:
        m = re.search(pat, html_text, re.IGNORECASE | re.DOTALL)
        if m:
            candidate = _strip_html(m.group(1))
            if len(candidate.split()) > 80:
                return candidate
    # Fallback: extract body
    m = re.search(r"<body[^>]*>(.*?)</body>", html_text, re.IGNORECASE | re.DOTALL)
    if m:
        return _strip_html(m.group(1))
    return _strip_html(html_text)


def _confidence_level(word_count: int, is_blocked: bool, has_date: bool) -> str:
    if is_blocked:
        return "low"
    if word_count < 80:
        return "low"
    if word_count < 250:
        return "medium"
    return "high"


def fetch_and_extract(url: str, max_words: int) -> dict:
    """Fetch URL and return structured extraction result."""
    result = {
        "url": url,
        "title": "",
        "published_date": "",
        "word_count": 0,
        "content": "",
        "confidence": "low",
        "is_blocked": False,
        "error": None,
    }

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            # Check content type
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct and "text/plain" not in ct and "application/xhtml" not in ct:
                result["error"] = f"Unsupported content type: {ct}"
                return result
            raw = resp.read()
            # Detect encoding
            charset = "utf-8"
            m = re.search(r"charset=([\w-]+)", ct)
            if m:
                charset = m.group(1)
            html_text = raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

    result["title"] = _extract_title(html_text)
    result["published_date"] = _extract_date(html_text)
    content = _extract_main_content(html_text)

    # Check for blocked content
    is_blocked = bool(BLOCKED_RE.search(content[:2000]))
    result["is_blocked"] = is_blocked

    # Truncate to max_words
    words = content.split()
    truncated = len(words) > max_words
    if truncated:
        content = " ".join(words[:max_words]) + "\n\n[... content truncated to " + str(max_words) + " words ...]"
    result["word_count"] = min(len(words), max_words)
    result["content"] = content
    result["confidence"] = _confidence_level(result["word_count"], is_blocked, bool(result["published_date"]))

    return result


def main() -> int:
    p = argparse.ArgumentParser(description="OpenClaw Browse/Viewing Module v2.0 - zero API key.")
    p.add_argument("--url", required=True, help="URL to fetch and extract")
    p.add_argument("--max-words", type=int, default=MAX_WORDS_DEFAULT,
                   help=f"Max words to return (default: {MAX_WORDS_DEFAULT})")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    args = p.parse_args()

    result = fetch_and_extract(args.url, args.max_words)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if not result["error"] else 1

    if result["error"]:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        return 1

    print(f"URL        : {result['url']}")
    print(f"Title      : {result['title'] or '(no title)'}")
    if result["published_date"]:
        print(f"Published  : {result['published_date']}")
    print(f"Words      : {result['word_count']}")
    print(f"Confidence : {result['confidence'].upper()}", end="")
    if result["is_blocked"]:
        print("  [WARNING: page may be paywalled or blocked]", end="")
    print()
    print()
    print("─" * 60)
    print(result["content"])
    print("─" * 60)
    print()

    # Anti-hallucination advisory
    if result["confidence"] == "low":
        print("AGENT NOTE: Content confidence is LOW.")
        if result["is_blocked"]:
            print("  -> Page appears to be paywalled or requires login.")
            print("  -> Do NOT fabricate content. Try a different URL from search results.")
        else:
            print("  -> Very little content was extracted (JS-heavy page or empty).")
            print("  -> Do NOT answer from this page alone. Try another source.")
    elif result["confidence"] == "medium":
        print("AGENT NOTE: Content confidence is MEDIUM.")
        print("  -> Some content extracted but may be incomplete.")
        print("  -> Cross-check with another source if answering factual questions.")
    else:
        print("AGENT NOTE: Content confidence is HIGH. Safe to use for answering.")
        if not result["published_date"]:
            print("  -> No publication date found — verify recency if time-sensitive.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
