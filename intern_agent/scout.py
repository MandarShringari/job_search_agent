import json

from intern_agent.extract import collect_candidates, write_leads_markdown
from intern_agent.tools import OUTPUT_DIR, fetch_page


def seed_search_block(year: int) -> str:
    candidates = collect_candidates(year)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "candidates.json"
    path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "leads.md").write_text(write_leads_markdown(candidates), encoding="utf-8")

    excerpts: list[str] = ["Official page excerpts for the top candidate URLs:"]
    for item in candidates[:4]:
        excerpts.append(fetch_page(item["apply_url"])[:4500])

    listing = json.dumps(candidates, indent=2)
    return (
        f"Python already searched the web and saved {len(candidates)} candidate "
        f"listings to {path}. Filter this list to real tech Spring Week / Spring "
        "Insight programmes, fetch_page if you need a deadline, then save_findings "
        "and write the report.\n\n"
        f"{listing}\n\n" + "\n\n".join(excerpts)
    )
