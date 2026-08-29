"""Answer generation with LLM"""
import logging
import os
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generate answers using LLM with retrieved context"""

    def __init__(
        self,
        llm_provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: str = None,
    ):
        """
        Args:
            llm_provider: LLM provider (anthropic or openai)
            model: Model name
            temperature: Generation temperature
            max_tokens: Max tokens to generate
            system_prompt: System prompt for the LLM
        """
        self.llm_provider = llm_provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM based on provider"""
        logger.info(f"Initializing {self.llm_provider} LLM: {self.model}")

        if self.llm_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")

            return ChatAnthropic(
                api_key=api_key,
                model=self.model,
                max_tokens=self.max_tokens,
            )

        elif self.llm_provider == "openai":
            from langchain_openai import ChatOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")

            return ChatOpenAI(
                api_key=api_key,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return """You are an IKEA product search assistant. Your PRIMARY job is to answer questions based ONLY on the provided product information.

CRITICAL RULES - FOLLOW THESE STRICTLY:
1. ONLY use information from the provided product context
2. NEVER add information, assumptions, or general knowledge
3. NEVER make up product details or specifications
4. If the context doesn't answer the question, say "I don't have that information in the catalog"
5. Always cite product names and prices from the context
6. Strictly respect budget constraints - ONLY recommend items within price ranges
7. Be concise and factual

ANSWER FORMAT:
- Start with direct answer based on context
- List recommended products with name and price
- Reference the specific products provided, nothing else"""

    def generate(self, query: str, context: str) -> str:
        """
        Generate answer based on query and context

        Args:
            query: User query
            context: Retrieved context/documents

        Returns:
            Generated answer
        """
        logger.info(f"Generating answer for query: {query}")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                (
                    "human",
                    """Based on the following product information from the IKEA catalog, please answer the user's question.

Context:
{context}

User Question: {query}

Please provide a helpful, specific recommendation based on the products shown above.""",
                ),
            ]
        )

        chain = prompt | self.llm

        try:
            result = chain.invoke({"context": context, "query": query})

            # Extract text from content blocks (handle thinking blocks)
            if hasattr(result, "content"):
                if isinstance(result.content, list):
                    # Find text block (skip thinking blocks)
                    answer = ""
                    for block in result.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            answer = block.get("text", "")
                            break
                    if not answer:
                        # Fallback if no text block found
                        answer = str(result.content)
                else:
                    answer = result.content
            else:
                answer = str(result)

            logger.info("Answer generated successfully")
            return answer
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"I encountered an error while processing your request: {str(e)}"

    def generate_with_fallback(self, query: str, context: str, fallback_text: str = None) -> str:
        """
        Generate answer with fallback text

        Args:
            query: User query
            context: Retrieved context
            fallback_text: Text to return if generation fails

        Returns:
            Generated answer or fallback text
        """
        try:
            return self.generate(query, context)
        except Exception as e:
            logger.error(f"Generation failed, using fallback: {e}")
            if fallback_text:
                return fallback_text
            return "I don't have enough information to answer that question. Please try rephrasing your query."

    def format_answer_with_sources(self, answer: str, sources: list) -> str:
        """
        Format answer with source citations

        Args:
            answer: Generated answer
            sources: List of source documents

        Returns:
            Formatted answer with citations
        """
        formatted = answer + "\n\n---\n**Sources:**\n"

        for i, source in enumerate(sources, 1):
            product_name = source.get("product_name", "Unknown")
            product_id = source.get("product_id", "")
            price = source.get("price", "")
            category = source.get("category", "")

            source_text = f"{i}. {product_name}"
            if price:
                source_text += f" - ${price}"
            if category:
                source_text += f" (Category: {category})"

            formatted += f"\n{source_text}"

        return formatted
