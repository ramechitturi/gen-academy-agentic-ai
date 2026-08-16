import pytest
import pandas as pd
import tempfile
from pathlib import Path
from src.data_loader import (
    load_portfolio,
    validate_portfolio_data,
    MissingColumnError,
    MalformedRowError,
    DataLoaderError,
)


@pytest.fixture
def temp_csv_dir():
    """Create a temporary directory for test CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def create_csv(path, content):
    """Helper to create a CSV file with given content."""
    with open(path, "w") as f:
        f.write(content)


class TestValidCSVLoading:
    """Tests for loading valid CSV files."""

    def test_load_valid_portfolio(self, temp_csv_dir):
        """Test loading a valid portfolio CSV."""
        csv_path = Path(temp_csv_dir) / "valid.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,,
MSFT,5,280.00,2023-02-20,350.00,2024-06-15""",
        )

        df = load_portfolio(str(csv_path))

        assert len(df) == 2
        assert df["ticker"].tolist() == ["AAPL", "MSFT"]
        assert (df["shares"] == [10, 5]).all()

    def test_load_whitespace_trimmed(self, temp_csv_dir):
        """Test that whitespace is properly trimmed."""
        csv_path = Path(temp_csv_dir) / "whitespace.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
 AAPL ,10,150.00,2023-01-15, , """,
        )

        df = load_portfolio(str(csv_path))

        assert df["ticker"].iloc[0] == "AAPL"
        assert pd.isna(df["sold_price"].iloc[0])
        assert pd.isna(df["sold_date"].iloc[0])

    def test_ticker_uppercase_conversion(self, temp_csv_dir):
        """Test that tickers are converted to uppercase."""
        csv_path = Path(temp_csv_dir) / "lowercase.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
aapl,10,150.00,2023-01-15,,""",
        )

        df = load_portfolio(str(csv_path))

        assert df["ticker"].iloc[0] == "AAPL"

    def test_fractional_shares(self, temp_csv_dir):
        """Test handling of fractional shares."""
        csv_path = Path(temp_csv_dir) / "fractional.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,2.5,150.00,2023-01-15,,""",
        )

        df = load_portfolio(str(csv_path))

        assert df["shares"].iloc[0] == 2.5

    def test_multiple_rows_same_ticker(self, temp_csv_dir):
        """Test loading multiple rows with same ticker."""
        csv_path = Path(temp_csv_dir) / "multi_aapl.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,,
AAPL,5,165.00,2023-06-01,295.00,2024-11-20""",
        )

        df = load_portfolio(str(csv_path))

        assert len(df) == 2
        assert (df["ticker"] == "AAPL").all()


class TestMissingColumns:
    """Tests for missing required columns."""

    def test_missing_ticker_column(self, temp_csv_dir):
        """Test error when ticker column is missing."""
        csv_path = Path(temp_csv_dir) / "no_ticker.csv"
        create_csv(
            csv_path,
            """shares,purchase_price,purchase_date
10,150.00,2023-01-15""",
        )

        with pytest.raises(MissingColumnError) as exc_info:
            load_portfolio(str(csv_path))

        assert "ticker" in str(exc_info.value)

    def test_missing_shares_column(self, temp_csv_dir):
        """Test error when shares column is missing."""
        csv_path = Path(temp_csv_dir) / "no_shares.csv"
        create_csv(
            csv_path,
            """ticker,purchase_price,purchase_date
AAPL,150.00,2023-01-15""",
        )

        with pytest.raises(MissingColumnError) as exc_info:
            load_portfolio(str(csv_path))

        assert "shares" in str(exc_info.value)

    def test_missing_purchase_price_column(self, temp_csv_dir):
        """Test error when purchase_price column is missing."""
        csv_path = Path(temp_csv_dir) / "no_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_date
AAPL,10,2023-01-15""",
        )

        with pytest.raises(MissingColumnError) as exc_info:
            load_portfolio(str(csv_path))

        assert "purchase_price" in str(exc_info.value)

    def test_missing_purchase_date_column(self, temp_csv_dir):
        """Test error when purchase_date column is missing."""
        csv_path = Path(temp_csv_dir) / "no_date.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price
AAPL,10,150.00""",
        )

        with pytest.raises(MissingColumnError) as exc_info:
            load_portfolio(str(csv_path))

        assert "purchase_date" in str(exc_info.value)


class TestMissingValues:
    """Tests for missing values in rows."""

    def test_missing_ticker_value(self, temp_csv_dir):
        """Test error when ticker value is missing."""
        csv_path = Path(temp_csv_dir) / "missing_ticker.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
,10,150.00,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Missing ticker" in str(exc_info.value)

    def test_missing_shares_value(self, temp_csv_dir):
        """Test error when shares value is missing."""
        csv_path = Path(temp_csv_dir) / "missing_shares.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,,150.00,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Missing shares" in str(exc_info.value)

    def test_missing_purchase_price_value(self, temp_csv_dir):
        """Test error when purchase_price value is missing."""
        csv_path = Path(temp_csv_dir) / "missing_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Missing purchase_price" in str(exc_info.value)

    def test_missing_purchase_date_value(self, temp_csv_dir):
        """Test error when purchase_date value is missing."""
        csv_path = Path(temp_csv_dir) / "missing_date.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Missing purchase_date" in str(exc_info.value)


class TestInvalidDataTypes:
    """Tests for invalid data types."""

    def test_non_numeric_shares(self, temp_csv_dir):
        """Test error when shares is non-numeric."""
        csv_path = Path(temp_csv_dir) / "non_numeric_shares.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,abc,150.00,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Shares must be positive" in str(exc_info.value) or "shares" in str(exc_info.value).lower()

    def test_non_numeric_purchase_price(self, temp_csv_dir):
        """Test error when purchase_price is non-numeric."""
        csv_path = Path(temp_csv_dir) / "non_numeric_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,abc,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "purchase_price" in str(exc_info.value).lower() or "positive" in str(exc_info.value).lower()

    def test_invalid_purchase_date_format(self, temp_csv_dir):
        """Test error when purchase_date has invalid format."""
        csv_path = Path(temp_csv_dir) / "invalid_date.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,invalid-date,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Missing purchase_date" in str(exc_info.value)


class TestNegativeValues:
    """Tests for negative values where they shouldn't be."""

    def test_negative_shares(self, temp_csv_dir):
        """Test error when shares is negative."""
        csv_path = Path(temp_csv_dir) / "negative_shares.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,-10,150.00,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Shares must be positive" in str(exc_info.value)

    def test_negative_purchase_price(self, temp_csv_dir):
        """Test error when purchase_price is negative."""
        csv_path = Path(temp_csv_dir) / "negative_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,-150.00,2023-01-15,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Purchase price must be positive" in str(exc_info.value)

    def test_negative_sold_price(self, temp_csv_dir):
        """Test error when sold_price is negative."""
        csv_path = Path(temp_csv_dir) / "negative_sold_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,-200.00,2024-06-15""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "Sold price must be positive" in str(exc_info.value)


class TestSoldTransactionValidation:
    """Tests for validation of buy/sell transaction consistency."""

    def test_sold_price_without_sold_date(self, temp_csv_dir):
        """Test error when sold_price exists but sold_date doesn't."""
        csv_path = Path(temp_csv_dir) / "price_no_date.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,200.00,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "sold_date" in str(exc_info.value).lower()

    def test_sold_date_without_sold_price(self, temp_csv_dir):
        """Test error when sold_date exists but sold_price doesn't."""
        csv_path = Path(temp_csv_dir) / "date_no_price.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-01-15,,2024-06-15""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "sold_price" in str(exc_info.value).lower()

    def test_sold_date_before_purchase_date(self, temp_csv_dir):
        """Test error when sold_date is before purchase_date."""
        csv_path = Path(temp_csv_dir) / "date_order.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,10,150.00,2023-06-15,200.00,2023-01-15""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        assert "before" in str(exc_info.value).lower()


class TestFileHandling:
    """Tests for file handling errors."""

    def test_file_not_found(self):
        """Test error when CSV file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_portfolio("nonexistent_file.csv")

    def test_empty_csv(self, temp_csv_dir):
        """Test handling of empty CSV file."""
        csv_path = Path(temp_csv_dir) / "empty.csv"
        create_csv(csv_path, "")

        with pytest.raises(DataLoaderError):
            load_portfolio(str(csv_path))

    def test_csv_with_only_headers(self, temp_csv_dir):
        """Test CSV with headers but no data rows."""
        csv_path = Path(temp_csv_dir) / "headers_only.csv"
        create_csv(
            csv_path,
            "ticker,shares,purchase_price,purchase_date,sold_price,sold_date\n",
        )

        df = load_portfolio(str(csv_path))

        assert len(df) == 0
        assert validate_portfolio_data(df)


class TestMultipleErrors:
    """Tests for detecting multiple errors in one file."""

    def test_multiple_invalid_rows(self, temp_csv_dir):
        """Test error reporting for multiple invalid rows."""
        csv_path = Path(temp_csv_dir) / "multiple_errors.csv"
        create_csv(
            csv_path,
            """ticker,shares,purchase_price,purchase_date,sold_price,sold_date
AAPL,-10,150.00,2023-01-15,,
,5,280.00,2023-02-20,,""",
        )

        with pytest.raises(MalformedRowError) as exc_info:
            load_portfolio(str(csv_path))

        error_msg = str(exc_info.value)
        # Should report multiple row errors
        assert "Row" in error_msg
