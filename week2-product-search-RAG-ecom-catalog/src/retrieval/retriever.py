"""Multi-stage retrieval pipeline"""
import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Hybrid retriever combining dense and keyword-based search"""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        db_path: str = "data/vector_db",
        collection_name: str = "ikea_products",
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ):
        """
        Args:
            embedding_model: Embedding model name
            db_path: Path to ChromaDB
            collection_name: Collection name
            dense_weight: Weight for dense retrieval
            bm25_weight: Weight for BM25 retrieval
        """
        self.embedding_model = embedding_model
        self.db_path = db_path
        self.collection_name = collection_name
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

        # Initialize Chroma vector store
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=db_path,
        )

        # Initialize BM25 retriever (placeholder)
        self.bm25_retriever = None

    def retrieve_dense(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Retrieve using dense similarity search

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of relevant documents
        """
        logger.debug(f"Dense retrieval for: {query}")
        return self.vector_store.similarity_search(query, k=top_k)

    def retrieve_bm25(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Retrieve using BM25 (keyword-based)

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of relevant documents
        """
        logger.debug(f"BM25 retrieval for: {query}")
        # Placeholder - implement BM25 if needed
        if self.bm25_retriever:
            return self.bm25_retriever.get_relevant_documents(query)
        return []

    def retrieve_hybrid(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining dense and BM25

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of ranked documents with scores
        """
        logger.info(f"Hybrid retrieval for: {query}")

        # Dense retrieval
        dense_docs = self.retrieve_dense(query, top_k=top_k)

        # Convert to dict format with scores
        results = {}
        for idx, doc in enumerate(dense_docs):
            doc_id = doc.metadata.get("product_id", "")
            score = 1.0 / (idx + 1)  # Reciprocal rank scoring
            results[doc_id] = {
                "document": doc,
                "dense_score": score * self.dense_weight,
                "bm25_score": 0.0,
                "combined_score": score * self.dense_weight,
            }

        # BM25 retrieval (optional)
        bm25_docs = self.retrieve_bm25(query, top_k=top_k)
        for idx, doc in enumerate(bm25_docs):
            doc_id = doc.metadata.get("product_id", "")
            score = 1.0 / (idx + 1)
            if doc_id in results:
                results[doc_id]["bm25_score"] = score * self.bm25_weight
                results[doc_id]["combined_score"] = (
                    results[doc_id]["dense_score"] + score * self.bm25_weight
                )
            else:
                results[doc_id] = {
                    "document": doc,
                    "dense_score": 0.0,
                    "bm25_score": score * self.bm25_weight,
                    "combined_score": score * self.bm25_weight,
                }

        # Sort by combined score
        sorted_results = sorted(results.items(), key=lambda x: x[1]["combined_score"], reverse=True)

        return [
            {
                "product_id": doc_id,
                "text": result["document"].page_content,
                "metadata": result["document"].metadata,
                "dense_score": result["dense_score"],
                "bm25_score": result["bm25_score"],
                "combined_score": result["combined_score"],
            }
            for doc_id, result in sorted_results[:top_k]
        ]

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get retriever statistics"""
        return {
            "embedding_model": self.embedding_model,
            "collection_name": self.collection_name,
            "dense_weight": self.dense_weight,
            "bm25_weight": self.bm25_weight,
        }
