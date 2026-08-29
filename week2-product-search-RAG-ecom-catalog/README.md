# IKEA Product Search RAG System

A Retrieval-Augmented Generation (RAG) system for IKEA furniture product search using LangChain, LangGraph, and local vector embeddings.

## Quick Start

```bash
# Setup
python main.py setup

# Run chatbot
python main.py chatbot
```

## Project Structure

```
data/
  raw/            # Downloaded IKEA dataset
  processed/      # Cleaned products & chunks
  vector_db/      # ChromaDB (embeddings)

src/
  ingestion/      # Download & clean data
  chunking/       # Split into chunks
  embedding/      # Generate embeddings
  retrieval/      # Hybrid search + ranking
  rag/            # LangGraph pipeline
  evaluation/     # Metrics & evaluation
  ui/             # Streamlit chatbot

config/
  settings.yaml   # Configuration
  prompts.yaml    # LLM prompts
```

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set API Keys

```bash
# .env file
ANTHROPIC_API_KEY=your_key_here
```

### 3. Run Setup

```bash
python main.py setup
```

This will:
- Download IKEA dataset from HuggingFace
- Clean and chunk products
- Generate embeddings
- Create vector database

**Time:** ~15-20 minutes

## Usage

### Chatbot

```bash
python main.py chatbot
```

Opens Streamlit UI at `http://localhost:8501`

### Python API

```python
from main import load_config, setup_rag_pipeline, setup_embedding_pipeline, setup_chunking_pipeline, setup_data_pipeline

config = load_config()
products = setup_data_pipeline(config)
chunks = setup_chunking_pipeline(config, products)
embedder = setup_embedding_pipeline(config, chunks)
rag = setup_rag_pipeline(config, embedder)

result = rag.invoke("Show me affordable couches")
print(result["answer"])
print(result["sources"])
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| LLM | Claude 3.5 Sonnet (Anthropic) |
| Framework | LangChain + LangGraph |
| Embeddings | all-MiniLM-L6-v2 (384-dim) |
| Vector DB | ChromaDB (local) |
| UI | Streamlit |
| Data | IKEA Dataset (HuggingFace Hub) |

## Evaluation Targets

- **Retrieval Relevance:** >80% (MRR/NDCG)
- **Faithfulness:** >90% (facts in context)
- **Answer Relevance:** >75% (manual scoring)
- **Latency:** <5s (end-to-end)

## Configuration

Edit `config/settings.yaml`:

```yaml
embedding:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size: 512
  chunk_overlap: 100

llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.7

retrieval:
  top_k: 10
  top_k_final: 5
  dense_weight: 0.7
  bm25_weight: 0.3
```

## Key Features

✅ **Hybrid Retrieval** - Dense (vector) + BM25 (keyword) search
✅ **Smart Ranking** - Re-rank results by relevance (optional cross-encoder)
✅ **Local Storage** - All data stored locally (no external APIs)
✅ **Streaming UI** - Real-time chatbot with product cards
✅ **Evaluation Framework** - Measure relevance, faithfulness, latency
✅ **Production Ready** - Persistent vector DB, error handling, logging

## Pipeline Phases

1. **Ingestion** - Download & clean IKEA dataset
2. **Chunking** - Split products into 512-token chunks
3. **Embedding** - Generate vector embeddings (ChromaDB)
4. **Retrieval** - Hybrid search (dense + BM25)
5. **Ranking** - Re-rank by relevance (optional cross-encoder)
6. **Generation** - LLM synthesizes answer with context
7. **UI** - Streamlit chatbot for user interaction
8. **Evaluation** - Measure system quality metrics

## Examples

### Query: "I need a comfortable couch under $500"

**Retrieved Products:**
1. KIVIK Sofa (2-seat) - $299
2. NORSBORG Sofa - $449
3. EKTORP Sofa - $379

**Answer:** "For your budget, I recommend the KIVIK 2-seat sofa at $299. It has excellent reviews and comfortable seating. If you prefer more space, the NORSBORG at $449 offers a larger footprint with similar comfort..."

### Query: "Standing desk options for small spaces"

**Retrieved Products:**
1. BEKANT Desk (140cm) - $149
2. MÖRBYLÅNGA Desk - $199
3. IDÅSEN Adjustable Desk - $279

## Troubleshooting

**Issue:** ANTHROPIC_API_KEY not found
```bash
export ANTHROPIC_API_KEY=your_key_here
```

**Issue:** ChromaDB not found
```bash
rm -rf data/vector_db/
python main.py setup
```

**Issue:** Out of memory
- Reduce `embedding.batch_size` in config (e.g., 16)
- Decrease `top_k` in retrieval

## Development

### Add Custom Evaluation Queries

```python
from src.evaluation import EvaluationDataset

dataset = EvaluationDataset()
dataset.add_query(
    "What desks are available?",
    relevant_product_ids=["desk_1", "desk_2"],
    category="furniture"
)
dataset.save_dataset("data/eval_queries.json")
```

### Run Tests

```bash
pytest tests/ -v
```

## Course Context

**Agentic AI Course - Week 2**

Demonstrates:
- LangChain retrieval patterns
- LangGraph for agentic workflows
- Hybrid retrieval (dense + keyword)
- LLM integration & prompting
- Evaluation metrics for RAG
- Local persistence & data handling

## License & Dataset Attribution

**Project Code License**: MIT License (see [LICENSE](LICENSE))

**Dataset License**: This project uses the [IKEA Home Decor & Furniture Product Dataset](https://huggingface.co/datasets/crawlfeeds/IKEA-Home-Decor-Furniture-Dataset) which is made available under **CC BY-NC 4.0**. The dataset is intended for research and non-commercial use only. For commercial licensing, please contact [crawlfeeds.com/contact](https://crawlfeeds.com/contact).

**Citation**: If you use this dataset in your research, please cite:

```bibtex
@dataset{crawlfeeds_ikea_homedecor_2025,
  author    = {Crawl Feeds},
  title     = {IKEA Home Decor & Furniture Product Dataset},
  year      = {2025},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/crawlfeeds/IKEA-Home-Decor-Furniture-Dataset}
}
```

## References

- [LangChain Docs](https://python.langchain.com/)
- [LangGraph](https://python.langchain.com/docs/langgraph)
- [ChromaDB](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [Anthropic Claude](https://docs.anthropic.com/)
