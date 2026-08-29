"""Result re-ranking and post-processing"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResultRanker:
    """Re-rank and filter retrieval results"""

    def __init__(self, use_cross_encoder: bool = False, model_name: Optional[str] = None):
        """
        Args:
            use_cross_encoder: Whether to use cross-encoder for re-ranking
            model_name: Cross-encoder model name
        """
        self.use_cross_encoder = use_cross_encoder
        self.model_name = model_name
        self.cross_encoder = None

        if use_cross_encoder and model_name:
            logger.info(f"Loading cross-encoder: {model_name}")
            try:
                from sentence_transformers import CrossEncoder

                self.cross_encoder = CrossEncoder(model_name)
            except ImportError:
                logger.warning("sentence-transformers not available for cross-encoder")

    def rank_by_relevance(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using cross-encoder if available

        Args:
            query: Original query
            results: List of retrieved results
            top_k: Number of top results to return

        Returns:
            Re-ranked results
        """
        if not results:
            return []

        if self.use_cross_encoder and self.cross_encoder:
            logger.debug("Re-ranking with cross-encoder...")
            return self._rank_with_cross_encoder(query, results, top_k)
        else:
            logger.debug("Using hybrid scores for ranking...")
            return sorted(
                results,
                key=lambda x: x.get("combined_score", 0),
                reverse=True,
            )[:top_k]

    def _rank_with_cross_encoder(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank using cross-encoder

        Args:
            query: Query text
            results: Retrieval results
            top_k: Number of top results

        Returns:
            Re-ranked results
        """
        # Prepare query-document pairs
        query_doc_pairs = [
            [query, result["text"]] for result in results
        ]

        # Score with cross-encoder
        scores = self.cross_encoder.predict(query_doc_pairs)

        # Add cross-encoder scores
        for result, score in zip(results, scores):
            result["cross_encoder_score"] = float(score)

        # Sort by cross-encoder score
        ranked = sorted(results, key=lambda x: x.get("cross_encoder_score", 0), reverse=True)

        return ranked[:top_k]

    def deduplicate_results(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate products (keep highest score)

        Args:
            results: List of results

        Returns:
            Deduplicated results
        """
        seen_products = {}
        for result in results:
            product_id = result.get("metadata", {}).get("product_id", "")
            if product_id not in seen_products:
                seen_products[product_id] = result
            else:
                # Keep result with higher combined score
                current_score = result.get("combined_score", 0)
                existing_score = seen_products[product_id].get("combined_score", 0)
                if current_score > existing_score:
                    seen_products[product_id] = result

        return list(seen_products.values())

    def filter_by_confidence(
        self,
        results: List[Dict[str, Any]],
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Filter results by confidence threshold

        Args:
            results: List of results
            threshold: Minimum confidence score

        Returns:
            Filtered results
        """
        return [
            result for result in results
            if result.get("combined_score", 0) >= threshold
        ]

    def post_process(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 5,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Full post-processing pipeline

        Args:
            query: Original query
            results: Retrieval results
            top_k: Number of final results
            min_confidence: Minimum confidence threshold

        Returns:
            Final processed results
        """
        # Deduplicate
        results = self.deduplicate_results(results)

        # Filter by confidence
        results = self.filter_by_confidence(results, threshold=min_confidence)

        # Re-rank
        results = self.rank_by_relevance(query, results, top_k=top_k)

        return results
