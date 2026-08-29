"""Download IKEA dataset from Hugging Face Hub"""
import json
import logging
from pathlib import Path
from typing import Optional

from datasets import load_dataset
from tqdm import tqdm
from .image_downloader import ImageDownloader

logger = logging.getLogger(__name__)


class IKEADatasetDownloader:
    """Download and organize IKEA dataset locally"""

    def __init__(self, repo_id: str, cache_dir: str, images_dir: str):
        """
        Args:
            repo_id: Hugging Face dataset repository ID
            cache_dir: Directory to cache downloaded data
            images_dir: Directory to store images
        """
        self.repo_id = repo_id
        self.cache_dir = Path(cache_dir)
        self.images_dir = Path(images_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def download_dataset(self, split: str = "train") -> dict:
        """
        Download dataset from Hugging Face Hub

        Args:
            split: Dataset split (default: train)

        Returns:
            Dataset dictionary with metadata
        """
        logger.info(f"Loading dataset {self.repo_id} from Hugging Face Hub...")

        try:
            dataset = load_dataset(self.repo_id, split=split, cache_dir=str(self.cache_dir))
            logger.info(f"Dataset loaded successfully: {len(dataset)} products")
            return dataset
        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            raise

    def process_and_save(self, dataset, output_file: str) -> None:
        """
        Process and save dataset as JSON

        Args:
            dataset: Loaded dataset
            output_file: Path to save JSON
        """
        logger.info("Processing dataset...")
        products = []

        for idx, item in enumerate(tqdm(dataset, desc="Processing products")):
            product = {
                "product_id": str(item.get("product_id", idx)),
                "name": item.get("product_name", ""),
                "category": item.get("category_1", ""),
                "price": item.get("price", None),
                "description": item.get("description", ""),
                "materials": item.get("material_and_care", ""),
                "dimensions": item.get("measurements", ""),
                "primary_image": item.get("primary_image", ""),
                "additional_images": item.get("additional_images", []),
                "availability": item.get("availability", ""),
                "rating": item.get("average_rating", None),
                "product_url": item.get("product_url", ""),
            }
            products.append(product)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(products)} products to {output_file}")

        # Save manifest
        manifest = {
            "total_products": len(products),
            "dataset_repo": self.repo_id,
            "output_file": str(output_file),
        }

        manifest_path = output_path.parent / "data_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Saved manifest to {manifest_path}")

    def download_images(self, products: list, skip_existing: bool = True) -> dict:
        """
        Download product images from URLs and store locally

        Args:
            products: List of products with primary_image URLs
            skip_existing: Skip if image already downloaded

        Returns:
            Dict with products updated with image_path and download stats
        """
        logger.info(f"Starting image download for {len(products)} products...")

        img_downloader = ImageDownloader(str(self.images_dir))
        result = img_downloader.download_product_images(products)

        # Save stats
        img_downloader.save_download_log(result["stats"])

        logger.info(
            f"Image download complete: {result['stats']['downloaded']} "
            f"downloaded, {result['stats']['failed']} failed"
        )

        return result
