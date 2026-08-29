"""Evaluation metrics for RAG system"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class EvaluationMetrics:
    """Compute RAG evaluation metrics"""

    def __init__(self):
        self.results = []

    def compute_mrr(self, rankings: List[int], k: int = 10) -> float:
        """
        Compute Mean Reciprocal Rank

        Args:
            rankings: List of relevance rankings (0=not relevant, 1=relevant)
            k: Cutoff for MRR

        Returns:
            MRR score
        """
        for i, rank in enumerate(rankings[:k]):
            if rank > 0:
                return 1.0 / (i + 1)
        return 0.0

    def compute_mrr_batch(self, all_rankings: List[List[int]], k: int = 10) -> float:
        """
        Compute MRR for batch of queries

        Args:
            all_rankings: List of ranking lists
            k: Cutoff

        Returns:
            Average MRR
        """
        mrrs = [self.compute_mrr(rankings, k) for rankings in all_rankings]
        return sum(mrrs) / len(mrrs) if mrrs else 0.0

    def compute_ndcg(
        self,
        relevance_scores: List[float],
        k: int = 10,
    ) -> float:
        """
        Compute Normalized Discounted Cumulative Gain

        Args:
            relevance_scores: List of relevance scores (0-5)
            k: Cutoff

        Returns:
            NDCG score
        """
        # DCG@k
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k]):
            dcg += score / (i + 1 if i == 0 else i + 1)

        # IDCG@k (ideal: all perfect scores)
        ideal_scores = sorted(relevance_scores, reverse=True)[:k]
        idcg = 0.0
        for i, score in enumerate(ideal_scores):
            idcg += score / (i + 1 if i == 0 else i + 1)

        return dcg / idcg if idcg > 0 else 0.0

    def compute_precision_at_k(
        self,
        relevant_count: int,
        k: int = 5,
    ) -> float:
        """
        Compute Precision@k

        Args:
            relevant_count: Number of relevant items in top-k
            k: Cutoff

        Returns:
            Precision@k score
        """
        return relevant_count / k if k > 0 else 0.0

    def compute_faithfulness(
        self,
        answer: str,
        context: str,
        threshold: float = 0.5,
    ) -> float:
        """
        Estimate faithfulness (simple keyword matching)
        In production, use LLM-based fact verification

        Args:
            answer: Generated answer
            context: Source context
            threshold: Confidence threshold

        Returns:
            Faithfulness score (0-1)
        """
        # Simple implementation: check if key phrases from answer appear in context
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())

        if not answer_words:
            return 0.0

        overlap = len(answer_words & context_words)
        return min(overlap / len(answer_words), 1.0)

    def compute_answer_relevance(
        self,
        query: str,
        answer: str,
        manual_score: Optional[float] = None,
    ) -> float:
        """
        Compute answer relevance

        Args:
            query: Original query
            answer: Generated answer
            manual_score: Manual relevance score (1-5)

        Returns:
            Relevance score (0-1)
        """
        if manual_score is not None:
            return manual_score / 5.0

        # Simple keyword overlap as fallback
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())

        if not query_words:
            return 0.0

        overlap = len(query_words & answer_words)
        return min(overlap / len(query_words), 1.0)

    def compute_latency(self, start_time: float, end_time: float) -> float:
        """Compute inference latency in seconds"""
        return end_time - start_time

    def add_evaluation_result(
        self,
        query: str,
        answer: str,
        context: str,
        retrieved_docs: List[Dict[str, Any]],
        latency: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add evaluation result

        Args:
            query: User query
            answer: Generated answer
            context: Source context
            retrieved_docs: Retrieved documents
            latency: Query latency
            metadata: Additional metadata
        """
        result = {
            "query": query,
            "answer": answer,
            "context": context,
            "num_retrieved": len(retrieved_docs),
            "latency": latency,
            "faithfulness": self.compute_faithfulness(answer, context),
            "answer_relevance": self.compute_answer_relevance(query, answer),
            "metadata": metadata or {},
        }
        self.results.append(result)

    def save_results(self, output_file: str) -> None:
        """Save evaluation results"""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Saved {len(self.results)} evaluation results to {output_file}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report"""
        if not self.results:
            return {}

        faithfulness_scores = [r["faithfulness"] for r in self.results]
        relevance_scores = [r["answer_relevance"] for r in self.results]
        latencies = [r["latency"] for r in self.results]

        return {
            "total_queries": len(self.results),
            "avg_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
            "avg_answer_relevance": sum(relevance_scores) / len(relevance_scores),
            "avg_latency": sum(latencies) / len(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "avg_docs_retrieved": sum(r["num_retrieved"] for r in self.results) / len(self.results),
        }
