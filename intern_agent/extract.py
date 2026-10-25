from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from intern_agent.tools import web_search

SPRING_RE = re.compile(
    r"spring\s*week|spring\s*insight|insight\s*week|insight\s*event",
    re.I,
)
TECH_RE = re.compile(
    r"software|engineer|technolog|computing|developer|data|cyber|"
    r"quant tech|sre|product|digital|programmer|machine learning|ai\b",
    re.I,
)
SKIP_HOSTS = {
    "simplytk.com",
    "www.simplytk.com",
    "www.indeed.com",
    "indeed.com",
    "www.linkedin.com",
    "linkedin.com",
    "www.extern.com",
    "www.simplyhired.co.uk",
    "simplyhired.co.uk",
    "talents.studysmarter.co.uk",
    "www.signalstaffing.co.uk",
}
GUIDE_RE = re.compile(r"what they are|when to apply|how to|guide|tracker", re.I)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _company_from_title(title: str) -> str:
    for sep in (" | ", " - ", " – ", " — "):
        if sep in title:
            left, right = title.split(sep, 1)
            if SPRING_RE.search(left) and not SPRING_RE.search(right):
                return right.strip()[:80]
            return left.strip()[:80]
    return title.strip()[:80]


def parse_search_json(blob: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return []
    items: list[dict[str, str]] = []
    for hit in payload.get("results") or []:
        title = hit.get("title") or ""
        url = hit.get("url") or ""
        snippet = hit.get("snippet") or ""
        blob_text = f"{title}\n{snippet}"
        if not url or _host(url) in SKIP_HOSTS:
            continue
        if not SPRING_RE.search(blob_text):
            continue
        if not TECH_RE.search(blob_text):
            continue
        if GUIDE_RE.search(title) and not TECH_RE.search(title):
            continue
        path = urlparse(url).path.rstrip("/").lower()
        if path.endswith("/apply"):
            continue
        items.append(
            {
                "company": _company_from_title(title),
                "programme": title[:120],
                "location": "unknown",
                "eligibility": "unknown",
                "deadline": "unknown",
                "apply_url": url,
                "source_url": url,
                "why_tech": snippet[:240] or "Tech-related Spring Week / Insight listing",
                "status": "unclear",
            }
        )
    return items


def collect_candidates(year: int) -> list[dict[str, str]]:
    queries = [
        f"Software Engineering Spring Week {year}",
        f"Women in Technology Spring Week {year}",
        f"BlackRock {year} Spring Insight Technology Software Engineering",
        f"JPMorgan Spring Insights {year} technology",
        f"Bloomberg spring insight {year} engineering UK",
        f"Bending Spoons Spring Week {year} software",
        f"GSA Capital Technology Insight Programme {year}",
        f"site:careers.microsoft.com spring insight {year} UK",
    ]
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for query in queries:
        for item in parse_search_json(web_search(query, max_results=6)):
            key = item["apply_url"].split("?")[0].rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def write_leads_markdown(items: list[dict[str, str]]) -> str:
    lines = [
        "# Tech Spring Week leads (search extract)",
        "",
        "These came from live web search, filtered to Spring Week / Spring Insight + tech keywords.",
        "Confirm every deadline on the apply page before you submit.",
        "",
    ]
    if not items:
        lines.append("No matching listings in this run.")
        return "\n".join(lines) + "\n"
    for item in items:
        lines.append(
            f"- **{item['company']}** — {item['programme']}  \n"
            f"  {item['why_tech']}  \n"
            f"  {item['apply_url']}"
        )
        lines.append("")
    return "\n".join(lines)
