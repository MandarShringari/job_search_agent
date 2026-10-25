from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

MAX_PAGE_CHARS = 24_000
OUTPUT_DIR = Path("output")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current internship listings and careers pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'spring week 2027 software engineering'.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10). Default 8.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Download a URL and return readable page text (titles, dates, apply links).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "http(s) URL to fetch."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_findings",
            "description": "Persist the internship list as JSON under output/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Internship objects.",
                        "items": {"type": "object"},
                    }
                },
                "required": ["items"],
            },
        },
    },
]


def web_search(query: str, max_results: int = 8) -> str:
    n = max(1, min(int(max_results or 8), 8))
    rows: list[dict[str, str]] = []
    try:
        with DDGS() as ddgs:
            for hit in ddgs.text(query, max_results=n):
                rows.append(
                    {
                        "title": hit.get("title") or "",
                        "url": hit.get("href") or "",
                        "snippet": hit.get("body") or "",
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return f"Search error for {query!r}: {exc}"
    if not rows:
        return f"No results for: {query}"
    return json.dumps({"query": query, "results": rows}, indent=2)


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_page(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Invalid URL. Only http(s) is allowed."
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Failed to fetch {url}: {exc}"

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return f"Skipped non-text content at {url} ({content_type})"

    body = _visible_text(response.text)
    if len(body) > MAX_PAGE_CHARS:
        body = body[:MAX_PAGE_CHARS] + "\n…[truncated]"
    return json.dumps({"url": str(response.url), "text": body})


def save_findings(items: Any) -> str:
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            return "items must be a JSON array of objects"
    if not isinstance(items, list):
        return "items must be a list"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "spring_week_internships.json"
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return f"Saved {len(items)} item(s) to {path}"


HANDLERS: dict[str, Callable[..., str]] = {
    "web_search": web_search,
    "fetch_page": fetch_page,
    "save_findings": save_findings,
}


def run_tool(name: str, arguments: dict[str, Any]) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}"
    try:
        return handler(**arguments)
    except TypeError as exc:
        return f"Bad arguments for {name}: {exc}"
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the model
        return f"Tool {name} failed: {exc}"
