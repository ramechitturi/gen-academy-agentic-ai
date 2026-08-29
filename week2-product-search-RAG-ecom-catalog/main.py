"""Main entry point for RAG pipeline setup and execution"""
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load configuration"""
    logger.info(f"Loading configuration from {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def setup_data_pipeline(config: dict) -> None:
    """Phase 1-2: Download and clean data"""
    logger.info("=== PHASE 1-2: Data Ingestion & Cleaning ===")

    from ingestion import IKEADatasetDownloader, DataCleaner

    # Download dataset
    downloader = IKEADatasetDownloader(
        repo_id=config["dataset"]["repo_id"],
        cache_dir=config["data"]["raw_dir"],
        images_dir=config["data"]["images_dir"],
    )

    dataset = downloader.download_dataset(split=config["dataset"]["split"])

    # Save raw products
    raw_output = Path(config["data"]["raw_dir"]) / "ikea_products.json"
    downloader.process_and_save(dataset, str(raw_output))

    # Clean data
    cleaner = DataCleaner()
    products = cleaner.load_products(str(raw_output))
    cleaned_products = cleaner.clean_products(products)

    cleaned_output = Path(config["data"]["processed_dir"]) / "products_clean.json"
    cleaner.save_cleaned_products(cleaned_products, str(cleaned_output))

    # Generate quality report
    report = cleaner.generate_quality_report(cleaned_products)
    report_output = Path(config["data"]["processed_dir"]) / "quality_report.json"
    with open(report_output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Data quality report saved to {report_output}")
    return cleaned_products


def setup_chunking_pipeline(config: dict, products: list) -> None:
    """Phase 3: Chunking"""
    logger.info("=== PHASE 3: Chunking ===")

    from chunking import TextChunker

    chunker = TextChunker(
        chunk_size=config["chunking"]["chunk_size"],
        chunk_overlap=config["chunking"]["chunk_overlap"],
    )

    chunks = chunker.chunk_products(products)

    chunks_output = Path(config["data"]["processed_dir"]) / "chunks.json"
    chunker.save_chunks(chunks, str(chunks_output))

    stats = chunker.get_chunk_statistics(chunks)
    logger.info(f"Chunking statistics: {stats}")

    return chunks


def setup_embedding_pipeline(config: dict, chunks: list) -> None:
    """Phase 4: Embedding"""
    logger.info("=== PHASE 4: Embedding & Vector Database ===")

    from embedding import EmbeddingManager

    embedder = EmbeddingManager(
        model_name=config["embedding"]["model_name"],
        db_path=config["data"]["vector_db_dir"],
        collection_name=config["vector_db"]["collection_name"],
        device=config["embedding"]["device"],
    )

    embedder.add_chunks_to_db(chunks, batch_size=config["embedding"]["batch_size"])

    stats = embedder.get_collection_stats()
    logger.info(f"Vector DB stats: {stats}")

    metadata_output = Path(config["data"]["processed_dir"]) / "embeddings_metadata.json"
    embedder.save_embeddings_metadata(str(metadata_output))

    return embedder


def setup_rag_pipeline(config: dict, embedder) -> object:
    """Phase 5-6: Retrieval & RAG Pipeline"""
    logger.info("=== PHASE 5-6: Retrieval & RAG Pipeline ===")

    from retrieval import RAGRetriever, ResultRanker
    from rag import RAGGraph, AnswerGenerator

    # Initialize retriever
    retriever = RAGRetriever(
        embedding_model=config["embedding"]["model_name"],
        db_path=config["data"]["vector_db_dir"],
        collection_name=config["vector_db"]["collection_name"],
        dense_weight=config["retrieval"]["dense_weight"],
        bm25_weight=config["retrieval"]["bm25_weight"],
    )

    # Initialize ranker
    ranker = ResultRanker(
        use_cross_encoder=config["retrieval"]["use_cross_encoder"],
        model_name=config["retrieval"].get("cross_encoder_model"),
    )

    # Initialize generator
    generator = AnswerGenerator(
        llm_provider=config["llm"]["provider"],
        model=config["llm"]["model"],
        temperature=config["llm"]["temperature"],
        max_tokens=config["llm"]["max_tokens"],
    )

    # Initialize RAG graph
    rag_graph = RAGGraph(
        retriever=retriever,
        ranker=ranker,
        generator=generator,
        config_path="config/prompts.yaml",
    )

    logger.info("RAG pipeline initialized successfully")
    return rag_graph


def run_chatbot(rag_pipeline) -> None:
    """Launch Streamlit chatbot"""
    logger.info("=== Launching Chatbot ===")

    import streamlit as st
    from ui.chatbot import run_chatbot as streamlit_app

    # Store pipeline in session state
    if "rag_pipeline" not in st.session_state:
        st.session_state.rag_pipeline = rag_pipeline

    streamlit_app(st.session_state.rag_pipeline)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="IKEA RAG System")
    parser.add_argument(
        "command",
        choices=["setup", "chatbot", "evaluate"],
        help="Command to run",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--query",
        help="Test query (for testing without chatbot)",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    if args.command == "setup":
        logger.info("Starting RAG system setup...")

        # Setup pipeline
        products = setup_data_pipeline(config)
        chunks = setup_chunking_pipeline(config, products)
        embedder = setup_embedding_pipeline(config, chunks)
        rag_pipeline = setup_rag_pipeline(config, embedder)

        logger.info("✅ RAG system setup complete!")
        logger.info("Run 'python main.py chatbot' to start the chatbot")

    elif args.command == "chatbot":
        logger.info("Starting chatbot...")

        # Setup pipeline
        products = setup_data_pipeline(config)
        chunks = setup_chunking_pipeline(config, products)
        embedder = setup_embedding_pipeline(config, chunks)
        rag_pipeline = setup_rag_pipeline(config, embedder)

        # Run chatbot
        run_chatbot(rag_pipeline)

    elif args.command == "evaluate":
        logger.info("Starting evaluation...")

        # Setup pipeline
        products = setup_data_pipeline(config)
        chunks = setup_chunking_pipeline(config, products)
        embedder = setup_embedding_pipeline(config, chunks)
        rag_pipeline = setup_rag_pipeline(config, embedder)

        # Run evaluation (placeholder)
        logger.info("Evaluation pipeline - to be implemented")


if __name__ == "__main__":
    main()
