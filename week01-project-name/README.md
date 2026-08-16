# [Project Name]

> One-line summary of what this agent/system does and the problem it solves.

## Overview

Brief paragraph covering the problem, who it's for, and why an agentic approach fits.

## Architecture

```
[Trigger] → [Planner Agent] → [Executor Agent] → [Verification Agent] → [Output]
```

## Folder Guide

- `agents/` — agent definitions (planner, executor, verifier, etc.)
- `tools/` — tool/function definitions the agents call (APIs, retrieval, calculators, etc.)
- `prompts/` — system prompts / prompt templates, kept separate from code for easy iteration
- `data/sample/` — small mock data safe to commit, used for demos and tests
- `data/raw/` — gitignored — real/large/sensitive data goes here only, never committed
- `notebooks/` — exploratory notebooks, prototyping
- `tests/` — unit/integration tests

## Tech Stack

- **LLM/Framework:**
- **Language:**
- **Key libraries:**
- **APIs/Integrations:**

## How It Works

1. ...
2. ...

## Setup & Installation

```bash
cd week0X-project-name
pip install -r requirements.txt
```

Uses the shared `.env` at the repo root — see root README for setup.

## Usage

```bash
python agents/main.py
```

## Design Decisions & Trade-offs

- ...

## Results / Evaluation

- ...

## What's Next

- ...

## Program Context

Built as part of the Gen Academy Agentic AI certification program — Week 0X.
