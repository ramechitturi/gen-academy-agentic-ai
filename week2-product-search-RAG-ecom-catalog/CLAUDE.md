# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a production-ready **Retrieval-Augmented Generation (RAG) system** for semantic product search on the IKEA catalog. It uses LangGraph to orchestrate a 6-phase pipeline that downloads data, embeds it, retrieves relevant products, and generates AI-powered answers.

### High-Level Data Flow

```
User Query
    ↓
[1. Ingestion] Download dataset & images from HuggingFace
    ↓
[2. Cleaning] Remove HTML, normalize text, preserve metadata
    ↓
[3. Chunking] Split products into 512-token chunks with overlap
    ↓
[4. Embedding] Generate vectors using sentence-transformers, store in ChromaDB
    ↓
[5. Retrieval] Hybrid search: dense (70%) + BM25 keyword (30%) → top 20 results
    ↓
[6. Ranking & Filtering] Re-rank with optional cross-encoder, apply price/budget constraints
    ↓
[7. Generation] Claude LLM synthesizes answer from top 5 results
    ↓
[8. Display] Streamlit UI shows answer + images + links + relevance scores
```

### Key Design Decisions

- **Hybrid Retrieval**: Combines semantic (dense embeddings) and keyword (BM25) search for robustness. Dense search handles conceptual queries ("cozy furniture"), while BM25 handles specific terms ("KIVIK sofa").
- **Constraint Filtering**: Automatically extracts budget constraints from queries (e.g., "under $500") and filters results BEFORE ranking for efficiency.
- **Confidence Threshold**: Results must exceed 10% relevance or the system returns "I don't have that information" instead of guessing.
- **Local-Only Storage**: All data (products, embeddings, images) stored locally—no external APIs for persistence.
- **LLM-Based Evaluation**: Replaced word-overlap metrics with Claude-based semantic evaluation of faithfulness and relevance.

### Component Structure

```
src/
├── ingestion/        Download & clean raw data
│   ├── downloader.py    → HuggingFace dataset download + image fetching
│   ├── cleaner.py       → HTML removal, normalization, validation
│   └── image_downloader.py → Fetch product images from URLs
├── chunking/         Split text into semantic chunks
│   └── chunker.py    → Fixed-size chunks (512 tokens, 100 overlap) with metadata preservation
├── embedding/        Vector embeddings & database
│   └── embedder.py   → Sentence-transformers → ChromaDB (384-dim vectors)
├── retrieval/        Hybrid search & ranking
│   ├── retriever.py  → Dense + BM25 hybrid retrieval
│   └── ranker.py     → Cross-encoder ranking (optional)
├── rag/              LangGraph orchestration
│   ├── graph.py      → StateGraph workflow (retrieve → rank → generate → format)
│   ├── generator.py  → Claude LLM integration
│   └── constraints.py → Budget/price constraint extraction & filtering
└── evaluation/       Quality metrics
    ├── llm_evaluator.py → Claude-based faithfulness & relevance scoring
    └── eval_dataset.py  → Test set management
```

## Development Commands

### Initial Setup

```bash
# 1. Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
```

### Running the Full Pipeline

```bash
# Full setup: download data, clean, chunk, embed, build vector DB (~15-20 min)
python main.py setup

# Launch Streamlit chatbot UI (requires data already set up)
python main.py chatbot

# Direct Streamlit launch (alternative)
streamlit run streamlit_app.py
```

### Development Workflow

```bash
# Run a quick evaluation test
python main.py evaluate

# Run Jupyter notebooks for experimentation
jupyter notebook notebooks/rag_pipeline_phases.ipynb

# Modify configuration and test (all config in config/settings.yaml)
# Edit config/prompts.yaml to change LLM system prompt
```

## Configuration

All settings are in `config/settings.yaml`. Key parameters:

- **embedding.model_name**: Embedding model (default: all-MiniLM-L6-v2 for fast CPU inference)
- **embedding.batch_size**: Reduce from 32 to 16 if memory-constrained
- **retrieval.top_k**: Number of candidates to retrieve (default: 20)
- **retrieval.dense_weight / bm25_weight**: Balance between semantic & keyword search
- **llm.model**: Claude model (currently claude-sonnet-5; don't use temperature—newer Claude models ignore it)
- **data paths**: All data directories (raw, processed, vector_db) for local storage

### Environment Variables

- **ANTHROPIC_API_KEY**: Required for Claude LLM integration

## Critical Code Paths

### When Adding a New Retrieval Feature

1. **Modify `src/retrieval/retriever.py`**: Add new retrieval method to `RAGRetriever` class
2. **Update `src/rag/graph.py`**: Modify the `node_retrieve` or `node_rank` methods to use new logic
3. **Test in notebook**: Validate with sample queries before running full pipeline

### When Changing the LLM Prompt

1. Edit `config/prompts.yaml` directly (controls system prompt)
2. Modify `src/rag/generator.py::AnswerGenerator._get_default_system_prompt()` for hardcoded defaults
3. Re-run evaluation to check faithfulness impact

### When Debugging Retrieval Quality

1. Check `retrieved_docs` in `src/rag/graph.py::node_retrieve` to see what's being fetched
2. Inspect `src/rag/constraints.py` to verify price filtering is working
3. Look at vector DB stats: `EmbeddingManager.get_collection_stats()` shows collection size
4. Evaluate with: `python main.py evaluate` (outputs to `notebooks/evaluation_results_llm.json`)

## Data Pipeline Details

### Phase 1-2: Ingestion & Cleaning
- Downloads 464 IKEA products from HuggingFace Hub + product images (464 JPGs)
- Cleans HTML, normalizes prices, preserves image paths as metadata
- Output: `data/processed/products_clean.json`

### Phase 3: Chunking
- Splits each product into semantic chunks (512 tokens, 100-token overlap)
- Preserves metadata: product_id, name, price, image_path, category
- Output: `data/processed/chunks.json` (464 chunks, one per product)

### Phase 4: Embedding
- Uses `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU-optimized)
- Stores in ChromaDB at `data/vector_db/ikea_products` for persistence
- Fast on CPU (~1min for 464 products), 384-dim is good balance of speed/quality

### Phase 5-6: Retrieval & Ranking
- **Dense retrieval** (vector similarity): Returns top 20 by cosine distance
- **BM25 retrieval** (keyword): Sparse term matching
- **Hybrid merge**: Weighted score (0.7 × dense + 0.3 × BM25)
- **Constraint filtering**: Removes products outside budget before ranking
- **Cross-encoder ranking** (optional): Re-ranks top 5 using cross-encoder if enabled
- **Confidence check**: Discards results below 10% relevance threshold

### Phase 7: Generation
- Sends top 5 results + system prompt to Claude LLM
- System prompt enforces using ONLY provided context (no hallucinations)
- Extracts text from response (handles Claude's thinking blocks)
- Returns: answer, retrieved products, relevance scores

### Phase 8: Evaluation
- Uses Claude to evaluate faithfulness (is answer grounded in context?)
- Uses Claude to evaluate relevance (does answer address query?)
- Better than word-overlap metrics because accounts for paraphrasing

## Known Constraints & Limitations

1. **Sparse Product Data**: IKEA dataset has minimal descriptions (~23 words avg). Affects semantic search accuracy. Solution: Better embedding model (all-mpnet-base-v2) or enriched descriptions.

2. **Single Collection**: All 464 products in one ChromaDB collection. If dataset grows beyond 10k+, consider sharding by category.

3. **No Caching**: Every query re-generates embeddings and retrieves. Could add caching layer for repeated queries.

4. **Image Fallback**: Falls back to URLs if local images unavailable—ensure image paths in metadata stay synchronized.

5. **LLM Temperature**: Claude models don't support temperature parameter; it's in config but ignored. Remove if upgrading to non-Claude LLMs.

## Testing & Validation

**No automated test suite exists.** Validation is done via:
- Jupyter notebooks (`notebooks/rag_pipeline_phases.ipynb`)
- Streamlit UI manual testing
- LLM-based evaluation metrics

To validate a change:
1. Run the full pipeline: `python main.py setup`
2. Test queries in Streamlit: `python main.py chatbot`
3. Run evaluation: `python main.py evaluate` → check `notebooks/evaluation_results_llm.json`

## Performance Targets

- **Latency**: 5-8 seconds end-to-end (retrieval + LLM generation)
- **Retrieval**: 20 candidates → 5 ranked results
- **Faithfulness**: ~30% (LLM-evaluated, accounts for paraphrasing—higher than word-overlap)
- **Relevance**: ~60% when results exist
- **Constraint Accuracy**: 100% (price filters work correctly)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ANTHROPIC_API_KEY not found` | Set in `.env` file: `ANTHROPIC_API_KEY=sk-...` |
| `ChromaDB not found` | Delete `data/vector_db/` and re-run `python main.py setup` |
| Out of memory | Reduce `embedding.batch_size` from 32 → 16 in settings.yaml |
| Slow embedding | Switch to GPU: set `embedding.device: "cuda"` if NVIDIA available |
| Poor retrieval results | Check if product data is loaded: `ls data/processed/chunks.json` should exist |
| Streamlit app won't load | Ensure vector DB exists: `ls data/vector_db/ikea_products/` should have ChromaDB files |

## Related Files

- [README.md](README.md) — User-facing overview, quick start, examples
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) — Detailed improvements, learnings, performance metrics
- [LICENSE](LICENSE) — Dataset and project licensing information
- `config/settings.yaml` — All tunable parameters
- `config/prompts.yaml` — LLM system prompt and other prompt templates

## Licensing

- **Project Code** (MIT): All source code in `src/`, configuration, and notebooks are MIT licensed (permissive, can be used commercially)
- **Dataset** (CC BY-NC 4.0): The IKEA product data is licensed for research/non-commercial use only (see [LICENSE](LICENSE) for commercial licensing contact)

See [LICENSE](LICENSE) for full details and dataset citation information.
