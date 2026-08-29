"""Evaluation dataset for benchmarking RAG"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class EvaluationDataset:
    """Build and manage evaluation dataset"""

    def __init__(self):
        self.queries = []

    def add_query(
        self,
        query: str,
        relevant_product_ids: List[str],
        category: Optional[str] = None,
        query_type: str = "general",
        expected_answer: Optional[str] = None,
    ) -> None:
        """
        Add evaluation query

        Args:
            query: Query text
            relevant_product_ids: List of relevant product IDs
            category: Query category
            query_type: Type of query
            expected_answer: Expected answer for validation
        """
        self.queries.append(
            {
                "query": query,
                "relevant_product_ids": relevant_product_ids,
                "category": category,
                "query_type": query_type,
                "expected_answer": expected_answer,
            }
        )

    def create_default_dataset(self) -> None:
        """Create default evaluation dataset"""
        default_queries = [
            {
                "query": "I need a comfortable couch for my living room under $500",
                "relevant_product_ids": ["product_1", "product_2"],
                "category": "furniture",
                "query_type": "budget_search",
            },
            {
                "query": "What are good desk options for a home office?",
                "relevant_product_ids": ["product_3", "product_4"],
                "category": "furniture",
                "query_type": "category_search",
            },
            {
                "query": "Show me bedroom storage solutions",
                "relevant_product_ids": ["product_5", "product_6"],
                "category": "storage",
                "query_type": "category_search",
            },
            {
                "query": "I'm looking for a white bookshelf",
                "relevant_product_ids": ["product_7"],
                "category": "storage",
                "query_type": "attribute_search",
            },
            {
                "query": "What small furniture fits in a studio apartment?",
                "relevant_product_ids": ["product_8", "product_9"],
                "category": "space_planning",
                "query_type": "constraint_search",
            },
        ]

        for q in default_queries:
            self.add_query(**q)

    def save_dataset(self, output_file: str) -> None:
        """Save evaluation dataset"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.queries, f, indent=2)

        logger.info(f"Saved {len(self.queries)} queries to {output_file}")

    def load_dataset(self, input_file: str) -> None:
        """Load evaluation dataset"""
        with open(input_file, "r") as f:
            self.queries = json.load(f)

        logger.info(f"Loaded {len(self.queries)} queries from {input_file}")

    def get_queries_by_type(self, query_type: str) -> List[Dict[str, Any]]:
        """Get queries by type"""
        return [q for q in self.queries if q.get("query_type") == query_type]

    def get_queries_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get queries by category"""
        return [q for q in self.queries if q.get("category") == category]

    def filter_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """
        Filter queries by difficulty level

        Args:
            difficulty: "easy", "medium", or "hard"

        Returns:
            Filtered queries
        """
        # Simple heuristic: number of relevant products indicates difficulty
        if difficulty == "easy":
            return [q for q in self.queries if len(q["relevant_product_ids"]) >= 2]
        elif difficulty == "medium":
            return [q for q in self.queries if len(q["relevant_product_ids"]) == 1]
        elif difficulty == "hard":
            return [q for q in self.queries if len(q["relevant_product_ids"]) <= 1]
        return self.queries

    def get_stats(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        query_types = {}
        categories = {}

        for q in self.queries:
            qtype = q.get("query_type", "unknown")
            category = q.get("category", "unknown")

            query_types[qtype] = query_types.get(qtype, 0) + 1
            categories[category] = categories.get(category, 0) + 1

        return {
            "total_queries": len(self.queries),
            "query_types": query_types,
            "categories": categories,
            "avg_relevant_products": (
                sum(len(q["relevant_product_ids"]) for q in self.queries) / len(self.queries)
                if self.queries
                else 0
            ),
        }

    def __len__(self) -> int:
        return len(self.queries)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.queries[idx]

    def __iter__(self):
        return iter(self.queries)
