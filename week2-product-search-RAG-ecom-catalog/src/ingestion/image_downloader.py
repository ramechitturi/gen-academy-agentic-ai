"""Download and cache product images locally"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Download product images from URLs and cache locally"""

    def __init__(self, images_dir: str, timeout: int = 10, max_retries: int = 3):
        """
        Args:
            images_dir: Directory to store images
            timeout: Request timeout in seconds
            max_retries: Max retry attempts per image
        """
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_retries = max_retries

        self.download_log = self.images_dir / "download_log.json"

    def download_image(self, url: str, filename: str) -> Optional[Path]:
        """
        Download a single image from URL

        Args:
            url: Image URL
            filename: Local filename to save as

        Returns:
            Path to saved image or None if failed
        """
        if not url:
            return None

        file_path = self.images_dir / filename

        # Skip if already downloaded
        if file_path.exists():
            return file_path

        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    logger.debug(f"Downloaded: {filename}")
                    return file_path
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.warning(f"Failed to download {url}: {e}")
                continue

        return None

    def download_product_images(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Download images for all products

        Args:
            products: List of products with image URLs

        Returns:
            Dict with download stats and updated products
        """
        logger.info(f"Downloading images for {len(products)} products...")

        stats = {
            "total": len(products),
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
        }

        for product in tqdm(products, desc="Downloading images"):
            product_id = product.get("product_id")
            primary_image_url = product.get("primary_image", "")

            if not primary_image_url:
                stats["skipped"] += 1
                product["image_path"] = None
                continue

            # Download primary image
            filename = f"{product_id}.jpg"
            image_path = self.download_image(primary_image_url, filename)

            if image_path:
                product["image_path"] = str(image_path)
                stats["downloaded"] += 1
            else:
                stats["failed"] += 1
                product["image_path"] = None

        logger.info(
            f"Download complete: {stats['downloaded']} downloaded, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )

        return {"products": products, "stats": stats}

    def save_download_log(self, stats: Dict[str, Any]) -> None:
        """Save download statistics"""
        with open(self.download_log, "w") as f:
            json.dump(stats, f, indent=2)

        logger.info(f"Saved download log to {self.download_log}")

    def get_local_image_path(self, product_id: str) -> Optional[Path]:
        """Get local image path if it exists"""
        image_path = self.images_dir / f"{product_id}.jpg"
        return image_path if image_path.exists() else None
