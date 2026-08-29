"""Streamlit chatbot interface"""
import logging
import time
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_rag_pipeline():
    """Initialize RAG pipeline components"""
    # This will be called with actual components in main.py
    pass


def display_product_card(product: dict, col) -> None:
    """Display a product card"""
    with col:
        st.subheader(product.get("product_name", "Unknown"))

        # Price and category
        price = product.get("price", "N/A")
        category = product.get("category", "N/A")
        st.write(f"**Price:** ${price} | **Category:** {category}")

        # Image if available
        image_url = product.get("image_url", "")
        if image_url:
            try:
                st.image(image_url, use_column_width=True)
            except Exception as e:
                st.write(f"Image unavailable: {e}")

        # Relevance score
        score = product.get("combined_score", 0)
        st.write(f"**Relevance Score:** {score:.2f}")

        # Product details
        with st.expander("Details"):
            st.write(f"**Product ID:** {product.get('product_id', 'N/A')}")
            if product.get("description"):
                st.write(f"**Description:** {product.get('description')}")


def display_sources(sources: list) -> None:
    """Display source documents"""
    st.subheader("📚 Sources Used")

    if not sources:
        st.info("No sources found for this query.")
        return

    # Display in columns
    cols = st.columns(min(3, len(sources)))

    for idx, source in enumerate(sources):
        col_idx = idx % len(cols)
        display_product_card(source, cols[col_idx])


def display_retrieval_stats(output: dict) -> None:
    """Display retrieval statistics"""
    with st.expander("🔍 Retrieval Statistics"):
        col1, col2, col3 = st.columns(3)

        retrieval_stats = output.get("retrieval_stats", {})

        with col1:
            st.metric(
                "Documents Retrieved",
                retrieval_stats.get("num_retrieved", 0),
            )

        with col2:
            st.metric(
                "Documents Used",
                retrieval_stats.get("num_ranked", 0),
            )

        with col3:
            st.metric(
                "Total Sources",
                output.get("num_sources", 0),
            )


def run_chatbot(rag_pipeline) -> None:
    """Run Streamlit chatbot"""
    st.set_page_config(
        page_title="IKEA Product Search RAG",
        page_icon="🛋️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛋️ IKEA Product Search Assistant")
    st.markdown(
        """
        Find the perfect IKEA furniture and home decor for your needs!
        Ask questions about products, prices, availability, and more.
        """
    )

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        top_k = st.slider(
            "Number of documents to retrieve",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
        )

        top_k_final = st.slider(
            "Number of sources to display",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )

        st.markdown("---")
        st.markdown("### About")
        st.write("RAG system for IKEA product search using LangChain and LangGraph")

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant" and "output" in message:
                display_retrieval_stats(message["output"])

    # Chat input
    if query := st.chat_input("Ask about IKEA products..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})

        with st.chat_message("user"):
            st.write(query)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching IKEA catalog..."):
                try:
                    start_time = time.time()

                    # Run RAG pipeline
                    output = rag_pipeline.invoke(
                        query=query,
                        top_k=top_k,
                        top_k_final=top_k_final,
                    )

                    latency = time.time() - start_time

                    # Display answer
                    answer = output.get("answer", "No answer generated.")
                    st.write(answer)

                    # Display sources
                    sources = output.get("sources", [])
                    display_sources(sources)

                    # Display stats
                    display_retrieval_stats(output)

                    # Latency
                    st.caption(f"⏱️ Response time: {latency:.2f}s")

                    # Store in chat history
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "output": output,
                        }
                    )

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    logger.error(f"Error in RAG pipeline: {e}")


if __name__ == "__main__":
    # This is a template - actual initialization happens in main.py
    st.error("Please run this through the main.py entry point")
