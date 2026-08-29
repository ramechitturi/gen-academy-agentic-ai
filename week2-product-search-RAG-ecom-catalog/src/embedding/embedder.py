"""Embedding generation and vector database management"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manage embeddings and ChromaDB vector store"""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        db_path: str = "data/vector_db",
        collection_name: str = "ikea_products",
        device: str = "cpu",
    ):
        """
        Args:
            model_name: Sentence transformer model name
            db_path: Path to ChromaDB persistent storage
            collection_name: Name of ChromaDB collection
            device: Device to use (cpu or cuda)
        """
        self.model_name = model_name
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self.device = device

        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)

        logger.info(f"Initializing ChromaDB at {db_path}")
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for texts

        Args:
            texts: List of texts to embed
            batch_size: Batch size for embedding

        Returns:
            List of embedding vectors
        """
        logger.info(f"Embedding {len(texts)} texts...")
        embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=True)
        return embeddings.tolist()

    def add_chunks_to_db(self, chunks: List[Dict[str, Any]], batch_size: int = 32) -> None:
        """
        Embed chunks and add to vector database

        Args:
            chunks: List of chunk dictionaries
            batch_size: Batch size for embedding
        """
        logger.info(f"Adding {len(chunks)} chunks to ChromaDB...")

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embed_texts(texts, batch_size=batch_size)

        # Prepare documents and metadata
        ids = [chunk["chunk_id"] for chunk in chunks]
        metadatas = [
            {
                "product_id": chunk["product_id"],
                "product_name": chunk["product_name"],
                "category": chunk["category"],
                "price": str(chunk.get("price", "")) if chunk.get("price") else "",
                "image_path": chunk.get("image_path", ""),
                "primary_image": chunk.get("primary_image", ""),
                "product_url": chunk.get("product_url", ""),
            }
            for chunk in chunks
        ]

        # Add to collection in batches
        for i in tqdm(range(0, len(chunks), batch_size), desc="Adding to ChromaDB"):
            batch_end = min(i + batch_size, len(chunks))
            self.collection.upsert(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                metadatas=metadatas[i:batch_end],
                documents=texts[i:batch_end],
            )

        logger.info(f"Successfully added {len(chunks)} chunks to ChromaDB")

    def query(self, query_text: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Query the vector database

        Args:
            query_text: Query text
            top_k: Number of results to return

        Returns:
            Query results with documents, metadatas, and distances
        """
        logger.debug(f"Querying: {query_text}")

        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "embedding_model": self.model_name,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
        }

    def save_embeddings_metadata(self, output_file: str) -> None:
        """Save embeddings metadata"""
        metadata = {
            "model": self.model_name,
            "dimension": self.model.get_sentence_embedding_dimension(),
            "collection_stats": self.get_collection_stats(),
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved embeddings metadata to {output_file}")
