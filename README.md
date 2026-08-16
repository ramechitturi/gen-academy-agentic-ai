# Gen Academy — Agentic AI Program

Portfolio repo for weekly projects submitted as part of the Gen Academy Agentic AI certification program.

Each week's project lives in its own subfolder with a self-contained README, code, and (non-sensitive) sample data.

## Projects

| Week | Project | Description | Status |
|------|---------|-------------|--------|
| 01 | [week1-portfolio-analyzer](./week1-portfolio-analyzer) | Streamlit app for tracking stock holdings, calculating realized/unrealized gains, and visualizing portfolio allocation | Complete |

_(Update this table as each project is added.)_

## Repo Structure

```
gen-academy-agentic-ai/
├── .env.example                  # template for required API keys — copy to .env locally
├── .gitignore                    # root-level — applies to every week folder below
├── README.md                     # this file
└── week1-portfolio-analyzer/
    ├── README.md                 # project-specific writeup
    ├── requirements.txt
    ├── app.py
    ├── src/
    │   ├── data_loader.py
    │   └── analysis.py
    ├── tests/
    └── data/
        └── sample/                # small, safe-to-commit mock data
```

Only add a second `.gitignore` inside a specific week folder if that project has an ignore need the root file doesn't cover (e.g. a one-off large cache folder). Git automatically applies the root `.gitignore` to every subfolder, so duplicating it per week is unnecessary.

## Setup

Each weekly project may have its own dependencies. General setup:

```bash
git clone https://github.com/ramechitturi/gen-academy-agentic-ai.git
cd gen-academy-agentic-ai
cp .env.example .env   # then fill in your own API keys — never commit this file
```

From there, `cd` into the relevant week's folder and follow its own README for setup/run instructions.

## A Note on Secrets

This repo is configured to keep `.env` and other credential files out of version control via `.gitignore`. If you fork or clone this repo, always create your own `.env` locally — never commit API keys, tokens, or credentials.

## Author

Rame — built as part of the Gen Academy Agentic AI certification program.
