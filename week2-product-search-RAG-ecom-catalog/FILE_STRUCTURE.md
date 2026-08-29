# File Structure Guide

A comprehensive guide to the IKEA Product Search RAG system project organization.

## Directory Tree

```
week2-product-search-RAG-ecom-catalog/
│
├── 📄 Root Configuration Files
│   ├── main.py                    # Entry point: orchestrates setup, chatbot, evaluation
│   ├── streamlit_app.py           # Direct Streamlit launcher
│   ├── requirements.txt           # Python package dependencies
│   ├── pyproject.toml             # Project metadata & build configuration
│   ├── uv.lock                    # Locked dependency versions
│   ├── .env.example               # Environment variables template (copy to .env)
│   ├── .gitignore                 # Git ignore patterns
│   ├── .python-version            # Python 3.12 specification
│   └── pyproject.toml             # uv project configuration
│
├── 📚 Documentation
│   ├── README.md                  # User-facing overview, quick start, examples
│   ├── CLAUDE.md                  # Developer documentation for Claude Code instances
│   ├── IMPLEMENTATION_SUMMARY.md  # Detailed implementation, improvements, learnings
│   ├── LICENSE                    # MIT (code) + CC BY-NC 4.0 (dataset)
│   └── FILE_STRUCTURE.md          # This file
│
├── ⚙️  Configuration Directory
│   └── config/
│       ├── settings.yaml          # All system configuration parameters
│       │                          #   - Embedding model & dimensions
│       │                          #   - Chunking strategy (size, overlap)
│       │                          #   - Retrieval weights (dense vs BM25)
│       │                          #   - LLM model & parameters
│       │                          #   - Data paths
│       └── prompts.yaml           # LLM system prompts & message templates
│
├── 📊 Data Directory (Generated - Not Committed)
│   └── data/
│       ├── raw/                   # Phase 1-2 output: Raw downloaded data
│       │   ├── ikea_products.json          # 464 raw IKEA products + image URLs
│       │   ├── images/                     # 464 downloaded product JPEGs
│       │   ├── data_manifest.json          # Dataset metadata (source, size, etc.)
│       │   └── [huggingface cache files]   # HuggingFace Hub cache
│       │
│       ├── processed/             # Phase 2-3 output: Cleaned & chunked data
│       │   ├── products_clean.json         # Cleaned products (no HTML, normalized)
│       │   ├── chunks.json                 # 464 semantic chunks (512 tokens each)
│       │   ├── quality_report.json         # Data quality metrics & stats
│       │   └── embeddings_metadata.json    # Embedding metadata
│       │
│       └── vector_db/             # Phase 4 output: Vector database
│           ├── chroma.sqlite3              # ChromaDB embedded SQLite DB
│           └── [collection folders]        # ChromaDB collection storage
│
├── 🔧 Core Implementation (src/)
│   └── src/
│       ├── __init__.py
│       │
│       ├── ingestion/             # Phase 1-2: Data Download & Cleaning
│       │   ├── __init__.py
│       │   ├── downloader.py           # Download IKEA dataset from HuggingFace Hub
│       │   │                           #   - IKEADatasetDownloader class
│       │   │                           #   - Processes & extracts fields
│       │   ├── image_downloader.py     # Fetch product images from URLs
│       │   │                           #   - Downloads 464 images locally
│       │   │                           #   - Fallback to URLs if local unavailable
│       │   └── cleaner.py              # Clean & validate data
│       │                               #   - Remove HTML tags & URLs
│       │                               #   - Normalize prices (string → float)
│       │                               #   - Preserve metadata (images, URLs)
│       │
│       ├── chunking/              # Phase 3: Semantic Chunking
│       │   ├── __init__.py
│       │   └── chunker.py              # Split text into semantic chunks
│       │                               #   - Fixed size: 512 tokens
│       │                               #   - Overlap: 100 tokens
│       │                               #   - Preserves all metadata
│       │
│       ├── embedding/             # Phase 4: Vector Embeddings
│       │   ├── __init__.py
│       │   └── embedder.py             # Generate embeddings & store in ChromaDB
│       │                               #   - Model: all-MiniLM-L6-v2 (384-dim)
│       │                               #   - EmbeddingManager class
│       │                               #   - Persistent ChromaDB storage
│       │
│       ├── retrieval/             # Phase 5: Search & Ranking
│       │   ├── __init__.py
│       │   ├── retriever.py            # Hybrid retrieval implementation
│       │   │                           #   - Dense: vector similarity search
│       │   │                           #   - BM25: keyword-based search
│       │   │                           #   - RAGRetriever class
│       │   │                           #   - Weighted combination
│       │   └── ranker.py               # Re-ranking with cross-encoder
│       │                               #   - Optional ranking refinement
│       │                               #   - ResultRanker class
│       │
│       ├── rag/                   # Phase 6-7: RAG Orchestration & Generation
│       │   ├── __init__.py
│       │   ├── graph.py                # LangGraph workflow orchestration
│       │   │                           #   - RAGGraph class
│       │   │                           #   - StateGraph pipeline
│       │   │                           #   - Nodes: retrieve → rank → generate → format
│       │   ├── generator.py            # LLM integration & answer generation
│       │   │                           #   - AnswerGenerator class
│       │   │                           #   - Claude LLM (via Anthropic SDK)
│       │   │                           #   - System prompt management
│       │   └── constraints.py          # Budget & price filtering
│       │                               #   - Extract constraints from queries
│       │                               #   - Filter products by budget
│       │                               #   - Regex-based price extraction
│       │
│       ├── evaluation/            # Phase 8: Quality Evaluation
│       │   ├── __init__.py
│       │   ├── llm_evaluator.py        # Claude-based semantic evaluation
│       │   │                           #   - Faithfulness scoring
│       │   │                           #   - Relevance scoring
│       │   │                           #   - Accounts for paraphrasing
│       │   ├── eval_dataset.py         # Test set management
│       │   │                           #   - Query templates
│       │   │                           #   - Expected answers
│       │   └── metrics.py              # Traditional evaluation metrics
│       │                               #   - MRR, NDCG, etc. (optional)
│       │
│       ├── ui/                    # Frontend Interface
│       │   ├── __init__.py
│       │   └── chatbot.py              # Streamlit chatbot UI
│       │                               #   - Query input
│       │                               #   - Product cards with images
│       │                               #   - Source citations
│       │                               #   - Relevance scores
│       │
│       └── week2_product_search_rag_ecom_catalog/  # Package entry point
│           └── __init__.py
│
├── 📓 Notebooks & Analysis
│   └── notebooks/
│       ├── 01_rag_pipeline_phases.ipynb   # End-to-end pipeline demonstration
│       │                                  # - Runs all 8 phases
│       │                                  # - Includes debugging checkpoints
│       │                                  # - Outputs evaluation results
│       └── evaluation_results_llm.json    # Sample evaluation results
│
└── 🧪 Tests (Empty)
    └── tests/                      # Placeholder for unit tests
```

## Component Interaction Flow

### 1. **Ingestion Phase** (`src/ingestion/`)
```
HuggingFace Hub
    ↓
downloader.py: Download 464 IKEA products
    ↓
image_downloader.py: Fetch product images
    ↓
Output: data/raw/ikea_products.json + data/raw/images/
    ↓
cleaner.py: Clean HTML, normalize prices
    ↓
Output: data/processed/products_clean.json
```

### 2. **Chunking Phase** (`src/chunking/`)
```
products_clean.json
    ↓
chunker.py: Split into 512-token chunks
    ↓
Output: data/processed/chunks.json
```

### 3. **Embedding Phase** (`src/embedding/`)
```
chunks.json
    ↓
embedder.py: Generate all-MiniLM-L6-v2 vectors (384-dim)
    ↓
Output: data/vector_db/chroma.sqlite3 (ChromaDB)
```

### 4. **Retrieval & Generation** (`src/retrieval/`, `src/rag/`)
```
User Query
    ↓
constraints.py: Extract price/budget constraints
    ↓
retriever.py: Hybrid search (dense 70% + BM25 30%)
    ↓
ranker.py: Re-rank top results
    ↓
generator.py: Claude LLM + system prompt
    ↓
Output: Answer + sources + images + scores
```

### 5. **Evaluation** (`src/evaluation/`)
```
Query + Retrieved Results + Generated Answer
    ↓
llm_evaluator.py: Claude judges faithfulness & relevance
    ↓
Output: Scores + metrics (data/processed/quality_report.json)
```

## Configuration Details

### `config/settings.yaml`
Controls all system parameters:

```yaml
embedding:
  model_name: sentence-transformers/all-MiniLM-L6-v2
  dimension: 384
  batch_size: 32
  device: cpu  # or cuda

retrieval:
  top_k: 20
  dense_weight: 0.7
  bm25_weight: 0.3

llm:
  provider: anthropic
  model: claude-sonnet-5
  max_tokens: 1024
```

### `config/prompts.yaml`
Contains all LLM prompts:
- System prompt (enforces grounding in context)
- User message templates
- Evaluation prompts

## Key Files by Purpose

### Setup & Execution
- `main.py` — Entry point for all commands
- `streamlit_app.py` — Direct Streamlit launcher
- `requirements.txt` — Dependencies

### Configuration
- `config/settings.yaml` — All tunable parameters
- `config/prompts.yaml` — LLM prompts
- `.env.example` → `.env` — API keys

### Core Logic (by pipeline phase)
- **Phase 1-2**: `src/ingestion/downloader.py`, `cleaner.py`
- **Phase 3**: `src/chunking/chunker.py`
- **Phase 4**: `src/embedding/embedder.py`
- **Phase 5-6**: `src/retrieval/retriever.py`, `src/rag/graph.py`
- **Phase 7**: `src/rag/generator.py`
- **Phase 8**: `src/evaluation/llm_evaluator.py`

### UI & Frontend
- `src/ui/chatbot.py` — Streamlit interface
- `streamlit_app.py` — Entry point

### Documentation
- `README.md` — Quick start & overview
- `CLAUDE.md` — Developer guide
- `IMPLEMENTATION_SUMMARY.md` — Learnings & improvements
- `LICENSE` — Licensing info
- `FILE_STRUCTURE.md` — This guide

## Data Flow Summary

```
User Input
    ↓
main.py or streamlit_app.py
    ↓
RAG Pipeline (LangGraph in src/rag/graph.py)
    ├─→ src/retrieval/retriever.py (search)
    ├─→ src/rag/constraints.py (filter)
    ├─→ src/retrieval/ranker.py (rank)
    ├─→ src/rag/generator.py (LLM)
    └─→ src/ui/chatbot.py (display)
    ↓
Streamlit UI / Command Line Output
```

## Git Ignore Strategy

Large files that are **NOT committed**:
- `data/raw/` — Downloaded datasets (regenerable)
- `data/processed/` — Cleaned data (regenerable)
- `data/vector_db/` — Vector DB (regenerable)
- `venv/` `.venv/` — Virtual environments
- `*.pyc` `__pycache__/` — Python cache

**Why**: These can be regenerated by `python main.py setup` and would bloat the repository. Only source code and configuration are committed.

## Development Workflow

1. **Edit configuration** → `config/settings.yaml` or `config/prompts.yaml`
2. **Modify logic** → Edit files in `src/`
3. **Run pipeline** → `python main.py setup` then `python main.py chatbot`
4. **Test in notebook** → `notebooks/01_rag_pipeline_phases.ipynb`
5. **Commit changes** → Git commit with description
6. **Push to GitHub** → `git push origin main`

## Adding New Features

### To add a new retrieval strategy:
1. Create method in `src/retrieval/retriever.py`
2. Update `src/rag/graph.py::node_retrieve()` to use it
3. Test in notebook

### To add a new evaluation metric:
1. Add method to `src/evaluation/llm_evaluator.py`
2. Call from `python main.py evaluate`

### To modify the RAG pipeline:
1. Edit `src/rag/graph.py` (the LangGraph workflow)
2. Add/remove nodes or edges as needed

## File Size References

| Directory | Size | Notes |
|-----------|------|-------|
| `src/` | ~50 KB | Source code (not git-ignored) |
| `config/` | ~5 KB | Configuration files |
| `notebooks/` | ~2 MB | Jupyter notebook (git-ignored usually) |
| `data/raw/` | ~500 MB | 464 images + dataset (git-ignored) |
| `data/processed/` | ~50 MB | JSON chunks (git-ignored) |
| `data/vector_db/` | ~100 MB | ChromaDB (git-ignored) |

Total committed size: ~100 KB (source + config + docs)
Total on disk after setup: ~700 MB (includes generated data)
