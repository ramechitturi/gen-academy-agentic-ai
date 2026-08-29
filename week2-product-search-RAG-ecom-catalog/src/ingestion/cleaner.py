"""Data cleaning and preprocessing"""
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)


class DataCleaner:
    """Clean and preprocess IKEA product data"""

    def __init__(self):
        self.cleaning_stats = {}

    def load_products(self, input_file: str) -> List[Dict[str, Any]]:
        """Load products from JSON file"""
        logger.info(f"Loading products from {input_file}")
        with open(input_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        logger.info(f"Loaded {len(products)} products")
        return products

    def clean_text(self, text: str) -> str:
        """Clean text: remove HTML tags, special chars, extra whitespace"""
        if not isinstance(text, str):
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove URLs
        text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def clean_price(self, price: Any) -> Optional[float]:
        """Extract numeric price from string"""
        if price is None:
            return None
        if isinstance(price, (int, float)):
            return float(price)
        if isinstance(price, str):
            match = re.search(r"[\d.]+", price)
            return float(match.group()) if match else None
        return None

    def normalize_availability(self, availability: Any) -> str:
        """Normalize availability status"""
        if not availability:
            return "unknown"
        avail_str = str(availability).lower()
        if "available" in avail_str or "stock" in avail_str or "yes" in avail_str:
            return "available"
        elif "out" in avail_str or "unavailable" in avail_str or "no" in avail_str:
            return "unavailable"
        return "unknown"

    def clean_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply cleaning pipeline to all products"""
        logger.info("Cleaning products...")
        cleaned = []
        duplicates = 0

        seen_ids = set()

        for product in tqdm(products, desc="Cleaning"):
            # Skip duplicates
            product_id = str(product.get("product_id", ""))
            if product_id in seen_ids:
                duplicates += 1
                continue
            seen_ids.add(product_id)

            # Clean fields
            name = self.clean_text(product.get("name", ""))
            description = self.clean_text(product.get("description", ""))

            # Use description as name if name is empty
            if not name and description:
                name = description[:100]  # Use first 100 chars of description as name

            cleaned_product = {
                "product_id": product_id,
                "name": name,
                "category": self.clean_text(product.get("category", "")),
                "price": self.clean_price(product.get("price")),
                "description": description,
                "materials": self.clean_text(product.get("materials", "")),
                "dimensions": self.clean_text(product.get("dimensions", "")),
                "primary_image": product.get("primary_image", ""),
                "image_path": product.get("image_path", ""),
                "product_url": product.get("product_url", ""),
                "availability": self.normalize_availability(product.get("availability")),
                "rating": float(product.get("rating", 0)) if product.get("rating") else None,
            }

            # Skip if name is still empty after cleaning
            if cleaned_product["name"]:
                cleaned.append(cleaned_product)

        self.cleaning_stats = {
            "total_input": len(products),
            "duplicates_removed": duplicates,
            "empty_names_removed": len(products) - duplicates - len(cleaned),
            "total_output": len(cleaned),
        }

        logger.info(f"Cleaning stats: {self.cleaning_stats}")
        return cleaned

    def save_cleaned_products(self, products: List[Dict[str, Any]], output_file: str) -> None:
        """Save cleaned products to JSON"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(products)} cleaned products to {output_file}")

    def generate_quality_report(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate data quality report"""
        df = pd.DataFrame(products)

        report = {
            "total_products": len(products),
            "columns": list(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "price_stats": {
                "min": float(df["price"].min()) if df["price"].notna().any() else None,
                "max": float(df["price"].max()) if df["price"].notna().any() else None,
                "mean": float(df["price"].mean()) if df["price"].notna().any() else None,
            },
            "availability_distribution": df["availability"].value_counts().to_dict(),
            "categories": df["category"].nunique(),
            "avg_description_length": int(df["description"].str.len().mean()),
        }

        return report
