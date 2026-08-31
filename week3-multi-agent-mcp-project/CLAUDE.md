# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal, runnable **MCP + LangGraph multi-agent system** where agents talk to an MCP server for both **tools** (actions) and **resources** (read-only data). The graph orchestrates a stock analysis workflow with a **conditional edge** that routes to either auto-publish or human review — the same shape as a production agent-approval checkpoint.

## Architecture

### Graph Structure
A 7-node LangGraph with a conditional edge that branches on the decision node:

```
research → context → analyst → compliance → decision ──(approve)──→ publish ──→ END
                                                     └──(review)───→ human_review → END
```

**Node Behaviors:**
- **research**: Calls the MCP tool `get_stock_price` to fetch live stock data from Yahoo Finance
- **context**: Reads two MCP resources (`stock://{ticker}/profile`, `stock://{ticker}/news`) for company info and news sentiment
- **analyst**: LLM summarizes the price, profile, and news into a 2-3 sentence snapshot
- **compliance**: **RAG agent** — retrieves the top 2 most relevant policy snippets from a local TF-IDF index using the analyst's summary as the query, then asks the LLM to note considerations grounded *only* in that retrieved text
- **decision**: LLM classifies the decision as `"approve"` or `"review"` based on summary + compliance notes; output of this node drives the conditional edge
- **publish** / **human_review**: Terminal nodes simulating real action (auto-publish vs. pause for human sign-off)

### MCP Server
**[mcp_server.py](mcp_server.py)** exposes:
- **Tools** (actions the agents call):
  - `get_stock_price(ticker)` — fetches live price from yfinance (no API key needed)
  - `retrieve_policy_context(query, top_k=2)` — TF-IDF RAG retrieval over [knowledge_base/](knowledge_base/) `.txt` files
- **Resources** (read-only data):
  - `stock://{ticker}/profile` — company overview (Alpha Vantage API, or labeled mock data)
  - `stock://{ticker}/news` — recent news sentiment (Alpha Vantage API, or labeled mock data)

The server runs as a subprocess via stdio transport (launched by the MCP client in [graph.py](graph.py)). If `ALPHA_VANTAGE_API_KEY` is not set, both resources return clearly-labeled mock data so the project runs with zero external signup.

### State Flow
**AgentState** (TypedDict in [graph.py](graph.py)) flows through all nodes:
```python
{
    "ticker": str,           # input
    "price_data": dict,      # from research_node
    "profile": dict,         # from context_node
    "news": list,            # from context_node
    "summary": str,          # from analyst_node
    "compliance_notes": str, # from compliance_node
    "retrieved_docs": list,  # from compliance_node (RAG output)
    "decision": str,         # from decision_node ("approve" | "review")
    "reason": str,           # from decision_node
    "status": str,           # from publish/human_review nodes (final outcome)
}
```

## Running the Project

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `ANTHROPIC_API_KEY` — **required** (analyst + decision nodes call Claude)
- `ALPHA_VANTAGE_API_KEY` — **optional**; leave blank for mock data

### CLI — Run the Full Graph
```bash
python3 main.py AAPL
```

Use any ticker symbol. Mock mode uses `BADNEWS` to trigger the `human_review` branch.

### Jupyter — Step-by-Step Walkthrough
```bash
jupyter notebook walkthrough.ipynb
```

Runs the MCP server tools directly first (no agents), then each LangGraph node individually so you can inspect state after every step, then the full compiled graph for comparison.

### Direct MCP Server Inspection
```bash
python3 mcp_server.py
```

The server waits on stdin for MCP protocol messages — this is the same handshake [graph.py](graph.py)'s `MultiServerMCPClient` performs under the hood. Use `Ctrl+C` to exit. Good for understanding the raw protocol layer without agents in the way.

## Key Files

| File | Purpose |
|---|---|
| [main.py](main.py) | CLI entry point — initializes state and calls `app.ainvoke()` |
| [graph.py](graph.py) | LangGraph definition: 7 nodes, 1 conditional edge, state schema, LLM client |
| [mcp_server.py](mcp_server.py) | MCP server: 2 tools, 2 resources, TF-IDF RAG indexing at startup |
| [walkthrough.ipynb](walkthrough.ipynb) | Jupyter notebook: raw MCP calls, then per-node inspection, then full graph |
| [knowledge_base/](knowledge_base/) | 4 `.txt` files (compliance policies) — indexed by TF-IDF at server startup |
| requirements.txt | Dependencies (langgraph, langchain-mcp-adapters, langchain-anthropic, mcp, yfinance, scikit-learn, jupyter) |
| .env.example | Template for environment variables |

## RAG Pipeline

The **compliance node** demonstrates full retrieve-then-generate RAG:

1. **Ingestion & Chunking** ([mcp_server.py:23–51](mcp_server.py#L23-L51)): Load raw `.txt` files from `knowledge_base/`, split into overlapping chunks (~256 tokens, 50-token overlap) to preserve context while enabling fine-grained retrieval
2. **Embedding** ([mcp_server.py:53–64](mcp_server.py#L53-L64)): Embed all chunks with `sentence-transformers` (all-MiniLM-L6-v2, 384-dim embeddings) for semantic similarity — falls back to TF-IDF if the model isn't installed
3. **Retrieval** ([mcp_server.py:102–145](mcp_server.py#L102-L145)): `retrieve_policy_context(query, top_k=2)` embeds the analyst's summary and returns the top-k most similar chunks by cosine similarity; deduplicates by source document for diversity
4. **Generation** ([graph.py:102–112](graph.py#L102-L112)): Feed the retrieved chunks to the LLM as grounding context; prompt it to note considerations *only* from that text, not general knowledge

The pattern is retrieval-agnostic — swap the embedding backend (e.g., `sentence-transformers` → real embeddings API, or add a vector DB like Chroma/pgvector) without changing the tool's interface or the nodes that call it.

## Extending the Project

### Add a Policy Document
Drop a new `.txt` file into [knowledge_base/](knowledge_base/) — `mcp_server.py` re-indexes everything at startup.

### Add a Second Resource
Define a new `@mcp.resource(...)` function in [mcp_server.py](mcp_server.py), then read it in `context_node` and fold it into the analyst's prompt.

### Add a Second Tool
Define a new `@mcp.tool()` function in [mcp_server.py](mcp_server.py), then call it from the appropriate node via the MCP client's tools list.

### Replace TF-IDF with Real Embeddings
In [mcp_server.py](mcp_server.py), swap the `TfidfVectorizer` / `cosine_similarity` logic for `sentence-transformers` or an embeddings API (e.g., Anthropic's embeddings). The `retrieve_policy_context` interface stays the same — compliance_node doesn't change.

### Replace the Decision Rule
Replace [graph.py:115–138](graph.py#L115-L138) (decision_node) with deterministic logic (e.g., `if "error" in price_data: return "review"`) and compare reliability vs. an LLM-based classifier.

## Notes

- All nodes are async (`async def`) — the graph runs with `await app.ainvoke()`.
- The MCP client is created fresh in each node (per [graph.py:43–50](graph.py#L43-L50)) — a simpler pattern than caching a single client, good for a learning project.
- LLM model is `claude-sonnet-4-6` — update [graph.py:40](graph.py#L40) if needed.
- The decision node returns JSON; if parsing fails, it defaults to `"review"` for safety.
- **Embeddings**: `sentence-transformers` (all-MiniLM-L6-v2, ~40MB) is downloaded on first run. If not installed, retrieval falls back to TF-IDF automatically.
- **Chunking strategy**: Overlapping chunks (256 words, 50-word overlap) preserve context across boundaries and enable fine-grained retrieval of the most relevant *part* of a policy, not just the whole document.
