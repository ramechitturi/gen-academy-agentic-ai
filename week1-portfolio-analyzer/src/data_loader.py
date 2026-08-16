import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DataLoaderError(Exception):
    """Base exception for data loading errors."""
    pass


class MissingColumnError(DataLoaderError):
    """Raised when required columns are missing."""
    pass


class MalformedRowError(DataLoaderError):
    """Raised when a row has invalid data."""
    pass


def load_portfolio(csv_path: str = "data/sample_portfolio.csv") -> pd.DataFrame:
    """
    Load and validate portfolio data from CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        Validated DataFrame with cleaned data

    Raises:
        MissingColumnError: If required columns are missing
        MalformedRowError: If critical rows have invalid data
        FileNotFoundError: If CSV file doesn't exist
    """
    # Check file exists
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as e:
        raise DataLoaderError(f"CSV file is empty: {str(e)}")
    except pd.errors.ParserError as e:
        raise DataLoaderError(f"Failed to parse CSV file: {str(e)}")
    except Exception as e:
        raise DataLoaderError(f"Failed to read CSV file: {str(e)}")

    # Validate required columns exist
    _validate_required_columns(df)

    # Clean and validate data
    df = _clean_data(df)

    # Validate row integrity
    _validate_rows(df)

    return df


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Validate that all required columns are present."""
    required_columns = {"ticker", "shares", "purchase_price", "purchase_date"}
    missing = required_columns - set(df.columns)

    if missing:
        raise MissingColumnError(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Available columns: {', '.join(df.columns)}"
        )


def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize data types."""
    df = df.copy()

    # Strip whitespace from all string columns
    string_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()

    # Clean ticker - uppercase
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    # Convert numeric columns
    try:
        df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
        df["purchase_price"] = pd.to_numeric(df["purchase_price"], errors="coerce")
        if "sold_price" in df.columns:
            df["sold_price"] = pd.to_numeric(df["sold_price"], errors="coerce")
    except Exception as e:
        raise MalformedRowError(f"Failed to convert numeric columns: {str(e)}")

    # Convert date columns
    try:
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
        if "sold_date" in df.columns:
            df["sold_date"] = pd.to_datetime(df["sold_date"], errors="coerce")
    except Exception as e:
        raise MalformedRowError(f"Failed to convert date columns: {str(e)}")

    return df


def _validate_rows(df: pd.DataFrame) -> None:
    """Validate individual rows for data integrity."""
    errors = []

    for idx, row in df.iterrows():
        row_errors = _validate_row(row, idx)
        errors.extend(row_errors)

    if errors:
        error_summary = "\n".join(errors)
        raise MalformedRowError(
            f"Data validation failed for {len(errors)} row(s):\n{error_summary}"
        )


def _validate_row(row: pd.Series, row_idx: int) -> list[str]:
    """
    Validate a single row.

    Returns list of error messages for the row.
    """
    errors = []
    row_num = row_idx + 2  # +2 because row_idx is 0-based and header is row 1

    # Validate ticker
    ticker = str(row["ticker"]).strip() if pd.notna(row["ticker"]) else ""
    if not ticker or ticker == "nan":
        errors.append(f"Row {row_num}: Missing ticker")
    elif not ticker.replace(".", "").replace("-", "").isalnum():
        errors.append(f"Row {row_num}: Invalid ticker format: '{ticker}'")

    # Validate shares
    if pd.isna(row["shares"]):
        errors.append(f"Row {row_num}: Missing shares")
    elif row["shares"] <= 0:
        errors.append(f"Row {row_num}: Shares must be positive, got {row['shares']}")

    # Validate purchase_price
    if pd.isna(row["purchase_price"]):
        errors.append(f"Row {row_num}: Missing purchase_price")
    elif row["purchase_price"] <= 0:
        errors.append(f"Row {row_num}: Purchase price must be positive, got {row['purchase_price']}")

    # Validate purchase_date
    if pd.isna(row["purchase_date"]):
        errors.append(f"Row {row_num}: Missing purchase_date")

    # Validate sold_price and sold_date consistency
    has_sold_price = pd.notna(row.get("sold_price")) and row.get("sold_price") > 0
    has_sold_date = pd.notna(row.get("sold_date"))

    if has_sold_price and not has_sold_date:
        errors.append(f"Row {row_num}: Has sold_price but missing sold_date")
    elif has_sold_date and not has_sold_price:
        errors.append(f"Row {row_num}: Has sold_date but missing sold_price")

    # Validate sold_price is positive (only if it has a value and is not NaN)
    sold_price = row.get("sold_price")
    if pd.notna(sold_price) and sold_price != 0 and sold_price < 0:
        errors.append(f"Row {row_num}: Sold price must be positive, got {sold_price}")

    # Validate sold_date is after purchase_date
    if has_sold_date and pd.notna(row["purchase_date"]):
        if row["sold_date"] < row["purchase_date"]:
            errors.append(
                f"Row {row_num}: Sold date ({row['sold_date'].date()}) "
                f"is before purchase date ({row['purchase_date'].date()})"
            )

    return errors


def validate_portfolio_data(df: pd.DataFrame) -> bool:
    """
    Validate that the portfolio DataFrame has required columns.

    Args:
        df: DataFrame to validate

    Returns:
        True if valid, False otherwise
    """
    required_columns = {"ticker", "shares", "purchase_price", "purchase_date"}
    return required_columns.issubset(df.columns)
