"""LangGraph RAG pipeline"""
import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from .constraints import extract_and_filter_constraints

logger = logging.getLogger(__name__)


class RAGGraph:
    """LangGraph-based RAG pipeline"""

    def __init__(
        self,
        retriever,
        ranker,
        generator,
        config_path: str = "config/prompts.yaml",
    ):
        """
        Args:
            retriever: RAG retriever instance
            ranker: Result ranker instance
            generator: Answer generator instance
            config_path: Path to prompts config
        """
        self.retriever = retriever
        self.ranker = ranker
        self.generator = generator
        self.config_path = config_path

        # Load prompts
        self._load_prompts()

        # Build graph
        self.graph = self._build_graph()

    def _load_prompts(self) -> None:
        """Load prompts from config"""
        import yaml

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        self.prompts = config

    def _build_graph(self):
        """Build LangGraph workflow"""
        workflow = StateGraph(dict)

        # Define nodes
        workflow.add_node("retrieve", self.node_retrieve)
        workflow.add_node("rank", self.node_rank)
        workflow.add_node("generate", self.node_generate)
        workflow.add_node("format", self.node_format)

        # Define edges
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "rank")
        workflow.add_edge("rank", "generate")
        workflow.add_edge("generate", "format")
        workflow.add_edge("format", END)

        return workflow.compile()

    def node_retrieve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant documents"""
        logger.info(f"Retrieving for query: {state['query']}")

        query = state.get("query", "")
        top_k = state.get("top_k", 10)

        results = self.retriever.retrieve_hybrid(query, top_k=top_k)

        state["retrieved_docs"] = results
        state["num_retrieved"] = len(results)

        return state

    def node_rank(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Re-rank retrieved documents and apply constraints"""
        logger.info("Re-ranking results...")

        query = state.get("query", "")
        retrieved_docs = state.get("retrieved_docs", [])
        top_k = state.get("top_k_final", 5)

        # Extract and apply price/budget constraints
        constraint_result = extract_and_filter_constraints(query, retrieved_docs)
        filtered_docs = constraint_result["docs"]
        constraints = constraint_result["constraints"]

        print(f"\n[CONSTRAINT FILTER] {len(retrieved_docs)} docs -> {len(filtered_docs)} docs")
        if constraints:
            print(f"[CONSTRAINT FILTER] Applied: {constraints}")

        # Re-rank filtered documents
        ranked_results = self.ranker.post_process(
            query,
            filtered_docs,
            top_k=top_k,
            min_confidence=0.0,
        )

        state["ranked_docs"] = ranked_results
        state["num_ranked"] = len(ranked_results)
        state["constraints"] = constraints
        state["num_filtered_by_constraint"] = constraint_result["num_filtered"]

        return state

    def node_generate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answer using LLM"""
        logger.info("Generating answer...")

        query = state.get("query", "")
        ranked_docs = state.get("ranked_docs", [])

        # Check if we have relevant results (minimum confidence threshold)
        min_confidence = 0.1  # Only accept results with 10%+ relevance
        relevant_docs = [
            doc for doc in ranked_docs
            if doc.get("combined_score", 0) >= min_confidence
        ]

        if not relevant_docs:
            logger.warning(f"No relevant documents found (confidence < {min_confidence})")
            answer = "I don't have that information in the catalog."
            context = ""
        else:
            # Build context from relevant documents
            context = self._build_context(relevant_docs)

            # Generate answer
            answer = self.generator.generate(query, context)

        state["answer"] = answer
        state["context"] = context

        return state

    def node_format(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format final response"""
        logger.info("Formatting response...")

        answer = state.get("answer", "")
        ranked_docs = state.get("ranked_docs", [])

        # Format output
        output = {
            "answer": answer,
            "sources": self._extract_sources(ranked_docs),
            "num_sources": len(ranked_docs),
            "retrieval_stats": {
                "num_retrieved": state.get("num_retrieved", 0),
                "num_ranked": state.get("num_ranked", 0),
            },
        }

        state["output"] = output

        return state

    def _build_context(self, docs: List[Dict[str, Any]]) -> str:
        """Build context string from documents"""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = f"[Source {i}] {doc.get('metadata', {}).get('product_name', 'Unknown')}"
            text = doc.get("text", "")
            context_parts.append(f"{source}\n{text}")

        return "\n\n".join(context_parts)

    def _extract_sources(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from documents"""
        sources = []
        for doc in docs:
            source = {
                "product_id": doc.get("metadata", {}).get("product_id", ""),
                "product_name": doc.get("metadata", {}).get("product_name", ""),
                "category": doc.get("metadata", {}).get("category", ""),
                "price": doc.get("metadata", {}).get("price", ""),
                "image_path": doc.get("metadata", {}).get("image_path", ""),
                "primary_image": doc.get("metadata", {}).get("primary_image", ""),
                "product_url": doc.get("metadata", {}).get("product_url", ""),
                "combined_score": doc.get("combined_score", 0),
            }
            sources.append(source)

        return sources

    def invoke(self, query: str, top_k: int = 10, top_k_final: int = 5) -> Dict[str, Any]:
        """
        Run the RAG pipeline

        Args:
            query: User query
            top_k: Number of documents to retrieve
            top_k_final: Number of documents for answer generation

        Returns:
            RAG output with answer and sources
        """
        logger.info(f"Running RAG pipeline for query: {query}")

        state = {
            "query": query,
            "top_k": top_k,
            "top_k_final": top_k_final,
        }

        result = self.graph.invoke(state)

        return result.get("output", {})
