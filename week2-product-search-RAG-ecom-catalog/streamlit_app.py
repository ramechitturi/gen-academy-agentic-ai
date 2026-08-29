"""Streamlit app for IKEA product search with RAG"""
import sys
import os
from pathlib import Path
import yaml
import json
from dotenv import load_dotenv

import streamlit as st
from PIL import Image
import requests
from io import BytesIO
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

# Load environment
load_dotenv(project_root / '.env')

# Load config
@st.cache_resource
def load_config():
    with open(project_root / 'config' / 'settings.yaml', 'r') as f:
        return yaml.safe_load(f)

@st.cache_resource
def initialize_rag_pipeline():
    """Initialize RAG pipeline once"""
    from embedding import EmbeddingManager
    from retrieval import RAGRetriever, ResultRanker
    from rag import RAGGraph, AnswerGenerator

    config = load_config()

    embedder = EmbeddingManager(
        model_name=config['embedding']['model_name'],
        db_path=str(project_root / config['data']['vector_db_dir']),
        collection_name=config['vector_db']['collection_name'],
        device=config['embedding']['device']
    )

    retriever = RAGRetriever(
        embedding_model=config['embedding']['model_name'],
        db_path=str(project_root / config['data']['vector_db_dir']),
        collection_name=config['vector_db']['collection_name'],
        dense_weight=config['retrieval']['dense_weight'],
        bm25_weight=config['retrieval']['bm25_weight']
    )

    ranker = ResultRanker(
        use_cross_encoder=config['retrieval']['use_cross_encoder'],
        model_name=config['retrieval'].get('cross_encoder_model')
    )

    generator = AnswerGenerator(
        llm_provider=config['llm']['provider'],
        model=config['llm']['model'],
        temperature=config['llm']['temperature'],
        max_tokens=config['llm']['max_tokens']
    )

    rag_graph = RAGGraph(
        retriever=retriever,
        ranker=ranker,
        generator=generator,
        config_path=str(project_root / 'config' / 'prompts.yaml')
    )

    return rag_graph, config


def display_product_card(source: dict, col):
    """Display a product card with image"""
    with col:
        st.markdown("---")

        # Product name and price
        st.markdown(f"### {source['product_name']}")
        st.markdown(f"**Price:** ${source['price']}")

        # Product URL
        if source.get('product_url'):
            st.markdown(f"[View on IKEA →]({source['product_url']})")

        # Image - prefer local path over URL
        image_displayed = False

        # Try local image first
        if source.get('image_path'):
            try:
                img_path = Path(source['image_path'])
                if img_path.exists():
                    img = Image.open(img_path)
                    st.image(img, use_container_width=True)
                    image_displayed = True
                    st.caption("✅ Local image")
            except Exception as e:
                st.warning(f"Could not load local image: {e}")

        # Fallback to URL if local not available
        if not image_displayed and source.get('primary_image'):
            try:
                response = requests.get(source['primary_image'], timeout=5)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    st.image(img, use_container_width=True)
                    image_displayed = True
                    st.caption("📡 From URL")
            except Exception as e:
                st.warning("Could not load image from URL")

        if not image_displayed:
            st.info("📷 No image available")

        # Relevance score
        if source.get('combined_score'):
            st.caption(f"Relevance: {source['combined_score']:.1%}")


def main():
    st.set_page_config(
        page_title="IKEA Product Search",
        page_icon="🛋️",
        layout="wide"
    )

    st.title("🛋️ IKEA Product Search with RAG")
    st.markdown("Find IKEA products with AI-powered semantic search")

    # Initialize pipeline
    with st.spinner("Loading RAG pipeline..."):
        rag_graph, config = initialize_rag_pipeline()

    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Settings")
        top_k = st.slider(
            "Number of results to retrieve",
            min_value=5,
            max_value=30,
            value=config['retrieval']['top_k'],
            step=5
        )
        top_k_final = st.slider(
            "Number of results to display",
            min_value=1,
            max_value=10,
            value=5,
            step=1
        )

    # Main search area
    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "What are you looking for?",
            placeholder="e.g., 'comfortable couch under $500' or 'standing desk for home office'",
            help="Try including budget constraints like 'under $200' for filtering"
        )

    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)

    # Process search
    if search_button and query:
        with st.spinner(f"Searching for: {query}"):
            try:
                output = rag_graph.invoke(
                    query=query,
                    top_k=top_k,
                    top_k_final=top_k_final
                )

                # Display answer
                st.markdown("### 💡 AI Answer")
                st.markdown(output['answer'])

                # Display stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Retrieved", output['retrieval_stats']['num_retrieved'])
                with col2:
                    st.metric("Ranked", output['retrieval_stats']['num_ranked'])
                with col3:
                    st.metric("Displayed", output['num_sources'])

                # Display sources
                if output['sources']:
                    st.markdown("### 🏪 Recommended Products")

                    # Display products in a grid
                    cols = st.columns(min(3, len(output['sources'])))
                    for idx, source in enumerate(output['sources']):
                        col_idx = idx % len(cols)
                        display_product_card(source, cols[col_idx])
                else:
                    st.warning("No products found matching your criteria")

            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                st.error(f"Details: {repr(e)}")

    # Example queries
    with st.expander("💡 Example Queries"):
        st.markdown("""
        Try these example searches:
        - "comfortable couch under $500"
        - "standing desk for home office"
        - "bedroom storage solutions"
        - "dining table for small spaces under $1000"
        - "bathroom shelves and organizers"
        """)

    # Footer
    st.markdown("---")
    st.caption("IKEA Product Search powered by RAG + Claude AI")


if __name__ == "__main__":
    main()
