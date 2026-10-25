# Spring Week intern agent

Local search agent that uses **Ollama `qwen3:8b`** to find currently listed **Spring Week / Spring Insight** internships in tech.

It can search the web, open careers pages, and write a short report plus JSON under `output/`.

## Prerequisites

- [Ollama](https://ollama.com) running locally
- The `qwen3:8b` model pulled (`ollama list` should show it)

```bash
ollama serve          # if it is not already running
ollama pull qwen3:8b  # only if you need to re-download
```

## Setup

```bash
cd ~/Code/spring-week-intern-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m intern_agent
```

Useful flags:

```bash
python -m intern_agent --year 2027
python -m intern_agent --model qwen3:8b --max-steps 12
python -m intern_agent --extra "Prefer software engineering in London"
```

Outputs:

- `output/leads.md` — search-extracted tech Spring Week / Insight links (best first stop)
- `output/candidates.json` — the same leads as JSON
- `output/report.md` — Qwen 3 8B's write-up after it reads pages
- `output/spring_week_internships.json` — programmes the model chose to keep

The model sometimes misses a listing or invents a deadline. Treat apply links and dates as leads and confirm on the company site before you apply.
