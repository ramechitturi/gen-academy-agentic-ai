"""Extract and apply query constraints (budget, price range, etc.)"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_price_constraint(query: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """
    Extract price constraints from query.

    Returns:
        Tuple of (min_price, max_price) or None if no constraint found
    """
    query_lower = query.lower()

    # Pattern: "under $X", "less than $X", "below $X"
    under_match = re.search(r'(under|less than|below|max|maximum)[\s$]*(\d+(?:\.\d{2})?)', query_lower)
    if under_match:
        max_price = float(under_match.group(2))
        return (None, max_price)

    # Pattern: "over $X", "more than $X", "above $X"
    over_match = re.search(r'(over|more than|above|min|minimum|at least)[\s$]*(\d+(?:\.\d{2})?)', query_lower)
    if over_match:
        min_price = float(over_match.group(2))
        return (min_price, None)

    # Pattern: "$X-$Y", "$X to $Y"
    range_match = re.search(r'\$?(\d+(?:\.\d{2})?)\s*(?:to|-)\s*\$?(\d+(?:\.\d{2})?)', query_lower)
    if range_match:
        min_price = float(range_match.group(1))
        max_price = float(range_match.group(2))
        return (min_price, max_price)

    return None


def apply_price_filter(
    docs: List[Dict[str, Any]],
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filter documents by price range.

    Returns:
        Tuple of (matching_docs, filtered_out_docs)
    """
    matching = []
    filtered_out = []

    for doc in docs:
        price = doc.get("metadata", {}).get("price")
        if price is None:
            matching.append(doc)
            continue

        price_float = float(price)

        if min_price is not None and price_float < min_price:
            filtered_out.append(doc)
            continue

        if max_price is not None and price_float > max_price:
            filtered_out.append(doc)
            continue

        matching.append(doc)

    return matching, filtered_out


def extract_and_filter_constraints(query: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract constraints from query and apply to documents.

    Returns:
        Dict with filtered_docs, constraints, and stats
    """
    price_constraint = extract_price_constraint(query)

    if price_constraint:
        min_price, max_price = price_constraint
        matching, filtered = apply_price_filter(docs, min_price, max_price)

        constraint_str = ""
        if min_price and max_price:
            constraint_str = f"${min_price:.0f}-${max_price:.0f}"
        elif max_price:
            constraint_str = f"under ${max_price:.0f}"
        elif min_price:
            constraint_str = f"over ${min_price:.0f}"

        logger.info(f"Extracted price constraint: {constraint_str}")
        logger.info(f"Filtered {len(filtered)} docs outside price range")

        return {
            "docs": matching,
            "constraints": {"price": constraint_str, "min": min_price, "max": max_price},
            "num_filtered": len(filtered),
        }

    return {
        "docs": docs,
        "constraints": {},
        "num_filtered": 0,
    }
