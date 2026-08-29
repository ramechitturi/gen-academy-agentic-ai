"""LLM-based evaluation using Claude"""
import logging
import os
import json
from typing import Dict, Any

from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """Evaluate RAG outputs using Claude"""

    def __init__(self, model: str = "claude-opus-5"):
        """
        Args:
            model: Claude model to use for evaluation
        """
        self.model = model
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.llm = ChatAnthropic(api_key=api_key, model=model)
        self.results = []

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        """
        Evaluate how faithful the answer is to the context (0-1 scale)

        Args:
            answer: Generated answer
            context: Source context

        Returns:
            Faithfulness score 0-1
        """
        prompt = f"""Evaluate the faithfulness of this answer to the provided context.

Context:
{context}

Answer:
{answer}

On a scale of 0-1, how faithfully does the answer reflect the context?
- 1.0: Answer is entirely grounded in context, no hallucinations
- 0.7-0.9: Answer mostly grounded with minor additions
- 0.4-0.6: Answer partially grounded, some unsupported claims
- 0.1-0.3: Answer has significant unsupported content
- 0.0: Answer is entirely hallucinated or wrong

Respond with ONLY a single number between 0 and 1 (e.g., 0.85)"""

        try:
            response = self.llm.invoke(prompt)
            # Extract text from content blocks
            score_text = "0"
            if isinstance(response.content, list):
                # Find text block (skip thinking blocks)
                for block in response.content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        score_text = block.get('text', '0')
                        break
            else:
                score_text = response.content
            score = float(score_text.strip())
            return max(0.0, min(1.0, score))  # Clamp to 0-1
        except Exception as e:
            logger.error(f"Error evaluating faithfulness: {e}")
            return 0.0

    def evaluate_relevance(self, query: str, answer: str) -> float:
        """
        Evaluate how relevant the answer is to the query (0-1 scale)

        Args:
            query: User query
            answer: Generated answer

        Returns:
            Relevance score 0-1
        """
        prompt = f"""Evaluate how well the answer addresses the user's query.

Query:
{query}

Answer:
{answer}

On a scale of 0-1, how relevant is the answer to the query?
- 1.0: Answer directly and completely addresses the query
- 0.7-0.9: Answer mostly addresses the query with minor gaps
- 0.4-0.6: Answer partially addresses the query
- 0.1-0.3: Answer barely addresses the query
- 0.0: Answer is completely off-topic

Respond with ONLY a single number between 0 and 1 (e.g., 0.92)"""

        try:
            response = self.llm.invoke(prompt)
            # Extract text from content blocks
            score_text = "0"
            if isinstance(response.content, list):
                # Find text block (skip thinking blocks)
                for block in response.content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        score_text = block.get('text', '0')
                        break
            else:
                score_text = response.content
            score = float(score_text.strip())
            return max(0.0, min(1.0, score))  # Clamp to 0-1
        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return 0.0

    def evaluate(self, query: str, answer: str, context: str) -> Dict[str, Any]:
        """
        Evaluate both faithfulness and relevance

        Args:
            query: User query
            answer: Generated answer
            context: Source context

        Returns:
            Dict with faithfulness and relevance scores
        """
        logger.info("Evaluating with LLM...")

        faithfulness = self.evaluate_faithfulness(answer, context)
        relevance = self.evaluate_relevance(query, answer)

        result = {
            "query": query,
            "faithfulness": faithfulness,
            "relevance": relevance,
            "avg_score": (faithfulness + relevance) / 2,
        }

        self.results.append(result)
        return result

    def evaluate_batch(self, queries: list, answers: list, contexts: list) -> Dict[str, Any]:
        """
        Evaluate multiple results

        Args:
            queries: List of queries
            answers: List of answers
            contexts: List of contexts

        Returns:
            Aggregated scores
        """
        logger.info(f"Evaluating {len(queries)} results...")

        for query, answer, context in zip(queries, answers, contexts):
            self.evaluate(query, answer, context)

        # Aggregate
        faithfulness_scores = [r["faithfulness"] for r in self.results]
        relevance_scores = [r["relevance"] for r in self.results]

        return {
            "num_evaluated": len(self.results),
            "avg_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores)
            if faithfulness_scores
            else 0.0,
            "avg_relevance": sum(relevance_scores) / len(relevance_scores)
            if relevance_scores
            else 0.0,
            "results": self.results,
        }

    def save_results(self, output_file: str) -> None:
        """Save evaluation results"""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Saved {len(self.results)} evaluation results to {output_file}")
