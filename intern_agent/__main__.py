from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from intern_agent.agent import run_search
from intern_agent.tools import OUTPUT_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search for Spring Week tech internships using a local Ollama model."
    )
    parser.add_argument("--model", default="qwen3:8b", help="Ollama model name")
    parser.add_argument(
        "--year",
        type=int,
        default=date.today().year + 1 if date.today().month >= 8 else date.today().year,
        help="Spring Week year to target (default: next spring intake)",
    )
    parser.add_argument(
        "--region",
        default="UK and Ireland (include remote/EU tech programmes if they are Spring Weeks)",
        help="Geographic focus",
    )
    parser.add_argument("--extra", default=None, help="Optional extra instructions")
    parser.add_argument("--max-steps", type=int, default=6, help="Max model/tool rounds")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(f"Model: {args.model}")
    print(f"Target: Spring Week {args.year}")
    print(f"Region: {args.region}")
    report = run_search(
        model=args.model,
        year=args.year,
        region=args.region,
        extra=args.extra,
        max_steps=args.max_steps,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = Path(OUTPUT_DIR) / "report.md"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nSaved report to {report_path}")
    leads = Path(OUTPUT_DIR) / "leads.md"
    if leads.exists():
        print(f"Search leads: {leads}")


if __name__ == "__main__":
    main()
