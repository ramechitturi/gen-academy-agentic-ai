"""Smart text chunking for product data"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunk product text while preserving metadata"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100):
        """
        Args:
            chunk_size: Target chunk size in tokens (approx)
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def create_product_text(self, product: Dict[str, Any]) -> str:
        """Create rich text representation of a product"""
        parts = []

        if product.get("name"):
            parts.append(f"Product: {product['name']}")
        if product.get("category"):
            parts.append(f"Category: {product['category']}")
        if product.get("description"):
            parts.append(f"Description: {product['description']}")
        if product.get("materials"):
            parts.append(f"Materials: {product['materials']}")
        if product.get("dimensions"):
            parts.append(f"Dimensions: {product['dimensions']}")
        if product.get("price"):
            parts.append(f"Price: ${product['price']}")
        if product.get("availability"):
            parts.append(f"Availability: {product['availability']}")
        if product.get("rating"):
            parts.append(f"Rating: {product['rating']}/5")

        return "\n".join(parts)

    def chunk_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk all products into retrieval-friendly chunks

        Args:
            products: List of cleaned product dictionaries

        Returns:
            List of chunks with metadata
        """
        logger.info(f"Chunking {len(products)} products...")
        chunks = []
        chunk_id = 0

        for product in tqdm(products, desc="Creating chunks"):
            product_text = self.create_product_text(product)

            # Split product text
            text_chunks = self.splitter.split_text(product_text)

            for text_chunk in text_chunks:
                chunk_dict = {
                    "chunk_id": f"chunk_{chunk_id}",
                    "product_id": product["product_id"],
                    "product_name": product.get("name", ""),
                    "category": product.get("category", ""),
                    "price": product.get("price"),
                    "image_path": product.get("image_path", ""),
                    "primary_image": product.get("primary_image", ""),
                    "product_url": product.get("product_url", ""),
                    "text": text_chunk,
                }
                chunks.append(chunk_dict)
                chunk_id += 1

        logger.info(f"Created {len(chunks)} chunks from {len(products)} products")
        return chunks

    def save_chunks(self, chunks: List[Dict[str, Any]], output_file: str) -> None:
        """Save chunks to JSON"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(chunks)} chunks to {output_file}")

    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute chunk statistics"""
        from statistics import mean, stdev

        chunk_lengths = [len(chunk["text"].split()) for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_length": mean(chunk_lengths),
            "min_chunk_length": min(chunk_lengths),
            "max_chunk_length": max(chunk_lengths),
            "std_chunk_length": stdev(chunk_lengths) if len(chunk_lengths) > 1 else 0,
        }
