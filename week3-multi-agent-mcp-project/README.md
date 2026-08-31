# MCP + LangGraph Multi-Agent Demo

A minimal, runnable example of a multi-agent system where agents talk to an
MCP server for both **tools** (actions) and **resources** (read-only data),
orchestrated by **LangGraph** with a **conditional edge** that routes to
either auto-publish or human review — the same shape as a production
agent-approval checkpoint.

## What's in here

| File | Role |
|---|---|
| `mcp_server.py` | MCP server. 2 tools (`get_stock_price` via yfinance; `retrieve_policy_context`, TF-IDF RAG retrieval) + 2 resources (`profile`, `news`, via Alpha Vantage or mock data) |
| `knowledge_base/*.txt` | Small local corpus the RAG tool retrieves from — mock compliance policies |
| `graph.py` | LangGraph graph: 7 nodes, 1 conditional edge |
| `main.py` | Entry point — runs the graph for a ticker and prints the result |
| `walkthrough.ipynb` | Jupyter notebook — runs the same system one small step at a time (raw MCP calls, then each node individually, then the full graph) |
| `requirements.txt` | Dependencies |
| `.env.example` | Copy to `.env` and fill in |

## The graph

```
research -> context -> analyst -> compliance -> decision --(approve)--> publish -----> END
                                                        \--(review)---> human_review -> END
```

- **research** — calls the MCP *tool* `get_stock_price`
- **context** — reads two MCP *resources*: `stock://{ticker}/profile`, `stock://{ticker}/news`
- **analyst** — LLM summarizes price + profile + news
- **compliance** — the **RAG agent**. Calls the MCP *tool* `retrieve_policy_context`, which TF-IDF-ranks the four `.txt` files in `knowledge_base/` against the analyst's summary and returns the top 2 matching chunks. The LLM is then told to note considerations grounded *only* in those retrieved chunks — retrieve, then generate.
- **decision** — LLM classifies `approve` vs `review`, now factoring in the compliance notes; this is the node the conditional edge branches on
- **publish** / **human_review** — terminal nodes simulating what a real system would do next

### Why RAG here specifically

The compliance node never sees the whole knowledge base — only the chunks
retrieval judged relevant to *this ticker's summary*. That's the core RAG
value proposition: ground the LLM's output in your own documents rather than
its training data, and only pay the token cost for the slice that's
actually relevant. Swap in a real embedding model + vector store later
(Chroma, pgvector, Pinecone, etc.) and nothing else in the graph changes —
`compliance_node` still just calls a tool named `retrieve_policy_context`
and gets chunks back.

## Setup

**With pip (standard):**
```bash
cd mcp-agent-project
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**With uv (faster):**
```bash
cd mcp-agent-project
uv venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `ANTHROPIC_API_KEY` — **required** (analyst + decision nodes call Claude)
- `ALPHA_VANTAGE_API_KEY` — **optional**. Leave it blank and the two resources
  return clearly-labeled mock data, so the project runs with zero signup.

## Run it

**Command line — the whole graph at once:**
```bash
python main.py AAPL
```

**Notebook — one step at a time:**
```bash
jupyter notebook walkthrough.ipynb
```
This calls the MCP server's tools and resources directly first (no agents
involved), then runs each LangGraph node manually so you can inspect `state`
after every step, then finally runs the whole compiled graph in one call for
comparison. Best starting point if you want to see what each layer actually
does rather than just the end result.

Either way you'll see the price data, the analyst's summary, the compliance
notes with which policy docs got retrieved, the decision, and the final
status (published or flagged for review).

## Things to try (in order of least to most changes)

1. **See the conditional edge branch the other way.**
   In mock mode, run:
   ```bash
   python main.py BADNEWS
   ```
   The mock news resource returns bearish headlines for this ticker
   specifically, so `decision_node` should route to `human_review` instead
   of `publish` — watch the `status` field flip.

2. **Turn on live data.** Add a free Alpha Vantage key to `.env` and re-run
   with a real ticker. Compare the mock output to live output for the same
   symbol.

3. **Add a fifth policy document.** Drop a new `.txt` file into
   `knowledge_base/` (e.g. `insider_trading_window_policy.txt`) — no code
   change needed, `mcp_server.py` re-indexes everything in that folder at
   startup. Run a ticker whose mock news wording overlaps with your new
   doc's vocabulary and watch `retrieved_docs` in the output pick it up.

4. **Watch retrieval quality degrade, then improve it.** TF-IDF is pure
   keyword overlap — it has no notion of synonyms. Try a summary that means
   the same thing as a policy but uses none of its words, and see the
   retrieval score drop. Then either add matching keywords to the doc, or
   (bigger change) swap `TfidfVectorizer` for real embeddings — e.g.
   `sentence-transformers` locally, or an embeddings API — to see semantic
   retrieval pick it up anyway.

5. **Add a third resource.** e.g. `stock://{ticker}/financials` — pick any
   free endpoint, add a new `@mcp.resource(...)` function in
   `mcp_server.py`, then read it in `context_node` and fold it into the
   analyst's prompt.

6. **Add a second action tool** — e.g. `get_price_history(ticker, days)`
   for a trend rather than a single price. Add it to `mcp_server.py` with
   `@mcp.tool()`, then call it from `research_node` the same way
   `get_stock_price` is called.

7. **Tighten the decision rule.** Right now `decision_node` asks the LLM to
   classify. Try replacing it with deterministic logic (e.g. `if "error" in
   price_data: return "review"`) and compare reliability vs. an LLM-based
   classifier — this is a real design choice you'll hit in the Amazon→Shopify
   fleet project too (rule-based guardrails vs. LLM judgment at approval
   checkpoints).

8. **Inspect the raw MCP protocol.** Run `mcp_server.py` directly:
   ```bash
   python mcp_server.py
   ```
   It'll sit waiting on stdio — that's the same handshake LangGraph's
   `MultiServerMCPClient` performs under the hood. (Ctrl+C to exit.)

## Where this maps to the Amazon → Shopify fleet

| Here | In the fleet |
|---|---|
| `get_stock_price` tool | `create_shopify_product`, `update_inventory` |
| `profile` / `news` resources | `amazon://{sku}/listing`, `shopify://store/theme-schema` |
| `retrieve_policy_context` tool + `knowledge_base/` | Retrieval over the BeYours theme's field constraints / your Shopify style guide, so the Mapping agent grounds its output in your actual schema instead of guessing |
| `compliance` node | A "style/schema compliance" agent checking a mapped listing against theme rules before it reaches the orchestrator |
| `decision` node | Master/Orchestrator's approval gate |
| `publish` / `human_review` | Auto-commit vs. pause for your sign-off |

Same shape, different tools and knowledge base behind the MCP server.
