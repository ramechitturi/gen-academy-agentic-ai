import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis import (
    enrich_transactions,
    calculate_holdings,
    calculate_portfolio_allocation,
    calculate_portfolio_summary,
    calculate_realized_gains,
)


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    return pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL", "AAPL"],
        "shares": [10, 5, 8, 5],
        "purchase_price": [150.0, 280.0, 95.0, 165.0],
        "purchase_date": [
            pd.Timestamp("2023-01-15"),
            pd.Timestamp("2023-02-20"),
            pd.Timestamp("2023-03-10"),
            pd.Timestamp("2023-06-01"),
        ],
        "sold_price": [np.nan, 350.0, np.nan, 295.0],
        "sold_date": [
            pd.NaT,
            pd.Timestamp("2024-06-15"),
            pd.NaT,
            pd.Timestamp("2024-11-20"),
        ],
    })


@pytest.fixture
def current_prices():
    """Create sample current prices."""
    return {"AAPL": 305.93, "MSFT": 495.4, "GOOGL": 345.9}


class TestEnrichTransactions:
    """Tests for enrich_transactions function."""

    def test_enriched_has_all_columns(self, sample_portfolio, current_prices):
        """Test that enriched transactions has all required columns."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        expected_columns = [
            "transaction_type",
            "purchase_value",
            "sale_value",
            "realized_gain_loss",
            "realized_gain_loss_pct",
            "current_price",
            "current_value",
            "unrealized_gain_loss",
            "unrealized_gain_loss_pct",
        ]
        for col in expected_columns:
            assert col in enriched.columns

    def test_transaction_type_classification(self, sample_portfolio, current_prices):
        """Test that transaction types are correctly classified."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # Rows with sold_date should be "Sell", others should be "Buy"
        assert enriched.loc[1, "transaction_type"] == "Sell"
        assert enriched.loc[3, "transaction_type"] == "Sell"
        assert enriched.loc[0, "transaction_type"] == "Buy"
        assert enriched.loc[2, "transaction_type"] == "Buy"

    def test_realized_gain_loss_calculation(self, sample_portfolio, current_prices):
        """Test realized gain/loss calculation for sold transactions."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # MSFT: 5 shares, bought at $280, sold at $350
        # Expected: (5 * 350) - (5 * 280) = 1750 - 1400 = 350
        msft_gain = enriched.loc[1, "realized_gain_loss"]
        assert msft_gain == pytest.approx(350.0)

        # AAPL (2nd): 5 shares, bought at $165, sold at $295
        # Expected: (5 * 295) - (5 * 165) = 1475 - 825 = 650
        aapl_gain = enriched.loc[3, "realized_gain_loss"]
        assert aapl_gain == pytest.approx(650.0)

    def test_realized_gain_loss_pct_calculation(self, sample_portfolio, current_prices):
        """Test realized gain/loss percentage calculation."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # MSFT: gain 350, invested 1400, return 25%
        msft_return = enriched.loc[1, "realized_gain_loss_pct"]
        assert msft_return == pytest.approx(25.0)

        # AAPL (2nd): gain 650, invested 825, return 78.79%
        aapl_return = enriched.loc[3, "realized_gain_loss_pct"]
        assert aapl_return == pytest.approx(78.787878, rel=1e-4)

    def test_unrealized_gain_loss_for_held_positions(self, sample_portfolio, current_prices):
        """Test unrealized gain/loss calculation for held positions."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # AAPL (1st, held): 10 shares, bought at $150, current $305.93
        # Expected: (10 * 305.93) - (10 * 150) = 3059.3 - 1500 = 1559.3
        aapl_unrealized = enriched.loc[0, "unrealized_gain_loss"]
        assert aapl_unrealized == pytest.approx(1559.3)

        # GOOGL (held): 8 shares, bought at $95, current $345.9
        # Expected: (8 * 345.9) - (8 * 95) = 2767.2 - 760 = 2007.2
        googl_unrealized = enriched.loc[2, "unrealized_gain_loss"]
        assert googl_unrealized == pytest.approx(2007.2)

    def test_unrealized_gain_loss_pct_for_held_positions(self, sample_portfolio, current_prices):
        """Test unrealized gain/loss percentage for held positions."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # AAPL (1st): unrealized 1559.3, invested 1500, return 103.95%
        aapl_return = enriched.loc[0, "unrealized_gain_loss_pct"]
        assert aapl_return == pytest.approx(103.953333, rel=1e-4)

    def test_sold_positions_have_no_unrealized_values(self, sample_portfolio, current_prices):
        """Test that sold positions don't have unrealized gain/loss values."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # Sold positions should have NaN for unrealized values
        assert pd.isna(enriched.loc[1, "unrealized_gain_loss"])
        assert pd.isna(enriched.loc[3, "unrealized_gain_loss"])

    def test_held_positions_have_no_realized_values(self, sample_portfolio, current_prices):
        """Test that held positions don't have realized gain/loss values."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        # Held positions should have NaN for realized values
        assert pd.isna(enriched.loc[0, "realized_gain_loss"])
        assert pd.isna(enriched.loc[2, "realized_gain_loss"])


class TestCalculateHoldings:
    """Tests for calculate_holdings function."""

    def test_only_held_positions_returned(self, sample_portfolio, current_prices):
        """Test that only held (not sold) positions are returned."""
        holdings = calculate_holdings(sample_portfolio, current_prices)

        assert len(holdings) == 2
        assert "AAPL" in holdings["ticker"].values
        assert "GOOGL" in holdings["ticker"].values
        assert "MSFT" not in holdings["ticker"].values

    def test_holdings_contain_unrealized_gains(self, sample_portfolio, current_prices):
        """Test that holdings include unrealized gain/loss calculations."""
        holdings = calculate_holdings(sample_portfolio, current_prices)

        assert "unrealized_gain_loss" in holdings.columns
        assert "unrealized_gain_loss_pct" in holdings.columns
        assert holdings["unrealized_gain_loss"].notna().all()

    def test_current_value_calculation(self, sample_portfolio, current_prices):
        """Test that current value is correctly calculated."""
        holdings = calculate_holdings(sample_portfolio, current_prices)

        aapl_holdings = holdings[holdings["ticker"] == "AAPL"]
        # 10 shares at $305.93 = 3059.3
        assert aapl_holdings["current_value"].values[0] == pytest.approx(3059.3)


class TestCalculatePortfolioAllocation:
    """Tests for calculate_portfolio_allocation function."""

    def test_allocation_pct_sum_to_100(self, sample_portfolio, current_prices):
        """Test that allocation percentages sum to 100."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        allocation = calculate_portfolio_allocation(holdings)

        total_allocation = allocation["allocation_pct"].sum()
        assert total_allocation == pytest.approx(100.0)

    def test_allocation_sorted_by_percentage(self, sample_portfolio, current_prices):
        """Test that allocation is sorted in descending order."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        allocation = calculate_portfolio_allocation(holdings)

        percentages = allocation["allocation_pct"].values
        assert all(percentages[i] >= percentages[i + 1] for i in range(len(percentages) - 1))

    def test_allocation_values_positive(self, sample_portfolio, current_prices):
        """Test that all allocation percentages are positive."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        allocation = calculate_portfolio_allocation(holdings)

        assert (allocation["allocation_pct"] > 0).all()
        assert (allocation["allocation_pct"] < 100).all()


class TestCalculatePortfolioSummary:
    """Tests for calculate_portfolio_summary function."""

    def test_summary_includes_required_keys(self, sample_portfolio, current_prices):
        """Test that summary includes all required keys."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        required_keys = [
            "total_invested",
            "total_current_value",
            "total_gain_loss",
            "total_return_pct",
            "num_holdings",
        ]
        for key in required_keys:
            assert key in summary

    def test_total_gain_loss_calculation(self, sample_portfolio, current_prices):
        """Test total gain/loss calculation."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        # Only AAPL (1st) and GOOGL are held
        # AAPL: 1559.3, GOOGL: 2007.2
        expected_gain = 1559.3 + 2007.2
        assert summary["total_gain_loss"] == pytest.approx(expected_gain)

    def test_total_return_pct_calculation(self, sample_portfolio, current_prices):
        """Test total return percentage calculation."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        # Total invested: 1500 + 760 = 2260
        # Total current: 3059.3 + 2767.2 = 5826.5
        # Total gain: 3566.5
        # Return: 3566.5 / 2260 * 100 = 157.81%
        expected_return = (3566.5 / 2260.0) * 100
        assert summary["total_return_pct"] == pytest.approx(expected_return, rel=1e-3)

    def test_num_holdings_count(self, sample_portfolio, current_prices):
        """Test that number of holdings is correct."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        assert summary["num_holdings"] == 2

    def test_total_current_value_calculation(self, sample_portfolio, current_prices):
        """Test total current value calculation."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        # 3059.3 + 2767.2 = 5826.5
        expected_total = 3059.3 + 2767.2
        assert summary["total_current_value"] == pytest.approx(expected_total)


class TestCalculateRealizedGains:
    """Tests for calculate_realized_gains function."""

    def test_realized_gains_all_transactions(self, sample_portfolio, current_prices):
        """Test realized gains calculation for all transactions."""
        enriched = enrich_transactions(sample_portfolio, current_prices)
        gains = calculate_realized_gains(enriched)

        # MSFT: 350, AAPL: 650
        expected_total = 350.0 + 650.0
        assert gains["total_realized_gain"] == pytest.approx(expected_total)
        assert gains["num_sold_transactions"] == 2

    def test_realized_gains_date_range_filter_start(self, sample_portfolio, current_prices):
        """Test realized gains with start date filter."""
        enriched = enrich_transactions(sample_portfolio, current_prices)
        start_date = pd.Timestamp("2024-11-01")
        gains = calculate_realized_gains(enriched, start_date=start_date)

        # Only AAPL (sold 2024-11-20) should be included
        assert gains["total_realized_gain"] == pytest.approx(650.0)
        assert gains["num_sold_transactions"] == 1

    def test_realized_gains_date_range_filter_end(self, sample_portfolio, current_prices):
        """Test realized gains with end date filter."""
        enriched = enrich_transactions(sample_portfolio, current_prices)
        end_date = pd.Timestamp("2024-09-30")
        gains = calculate_realized_gains(enriched, end_date=end_date)

        # Only MSFT (sold 2024-06-15) should be included
        assert gains["total_realized_gain"] == pytest.approx(350.0)
        assert gains["num_sold_transactions"] == 1

    def test_realized_gains_date_range_both_filters(self, sample_portfolio, current_prices):
        """Test realized gains with both start and end date filters."""
        enriched = enrich_transactions(sample_portfolio, current_prices)
        start_date = pd.Timestamp("2024-06-01")
        end_date = pd.Timestamp("2024-08-31")
        gains = calculate_realized_gains(enriched, start_date=start_date, end_date=end_date)

        # Only MSFT (sold 2024-06-15) should be included
        assert gains["total_realized_gain"] == pytest.approx(350.0)
        assert gains["num_sold_transactions"] == 1

    def test_realized_gains_no_transactions_in_range(self, sample_portfolio, current_prices):
        """Test realized gains when no transactions in date range."""
        enriched = enrich_transactions(sample_portfolio, current_prices)
        start_date = pd.Timestamp("2025-01-01")
        end_date = pd.Timestamp("2025-12-31")
        gains = calculate_realized_gains(enriched, start_date=start_date, end_date=end_date)

        assert gains["total_realized_gain"] == 0
        assert gains["num_sold_transactions"] == 0


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_all_losses_portfolio(self, current_prices):
        """Test portfolio where all positions have losses."""
        portfolio = pd.DataFrame({
            "ticker": ["AAPL", "MSFT"],
            "shares": [10, 5],
            "purchase_price": [400.0, 600.0],
            "purchase_date": [
                pd.Timestamp("2023-01-15"),
                pd.Timestamp("2023-02-20"),
            ],
            "sold_price": [np.nan, np.nan],
            "sold_date": [pd.NaT, pd.NaT],
        })

        enriched = enrich_transactions(portfolio, current_prices)
        holdings = calculate_holdings(portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        # Both should have negative unrealized gains
        assert enriched["unrealized_gain_loss"].sum() < 0
        assert summary["total_return_pct"] < 0

    def test_single_holding_portfolio(self, current_prices):
        """Test portfolio with single holding."""
        portfolio = pd.DataFrame({
            "ticker": ["AAPL"],
            "shares": [10],
            "purchase_price": [150.0],
            "purchase_date": [pd.Timestamp("2023-01-15")],
            "sold_price": [np.nan],
            "sold_date": [pd.NaT],
        })

        holdings = calculate_holdings(portfolio, current_prices)
        allocation = calculate_portfolio_allocation(holdings)

        assert len(holdings) == 1
        assert allocation["allocation_pct"].values[0] == pytest.approx(100.0)

    def test_fractional_shares(self, current_prices):
        """Test portfolio with fractional shares."""
        portfolio = pd.DataFrame({
            "ticker": ["AAPL"],
            "shares": [1.5],
            "purchase_price": [150.0],
            "purchase_date": [pd.Timestamp("2023-01-15")],
            "sold_price": [np.nan],
            "sold_date": [pd.NaT],
        })

        holdings = calculate_holdings(portfolio, current_prices)
        expected_value = 1.5 * current_prices["AAPL"]
        assert holdings["current_value"].values[0] == pytest.approx(expected_value)

    def test_zero_purchase_value_handling(self, current_prices):
        """Test that portfolio handles edge cases gracefully."""
        portfolio = pd.DataFrame({
            "ticker": ["AAPL"],
            "shares": [10],
            "purchase_price": [150.0],
            "purchase_date": [pd.Timestamp("2023-01-15")],
            "sold_price": [np.nan],
            "sold_date": [pd.NaT],
        })

        holdings = calculate_holdings(portfolio, current_prices)
        summary = calculate_portfolio_summary(holdings)

        # Should not raise division by zero
        assert summary["total_return_pct"] != np.inf
        assert summary["total_return_pct"] != -np.inf


class TestDataConsistency:
    """Tests for data consistency and integrity."""

    def test_enriched_preserves_original_data(self, sample_portfolio, current_prices):
        """Test that enrich_transactions preserves original data."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        assert len(enriched) == len(sample_portfolio)
        assert (enriched["ticker"] == sample_portfolio["ticker"]).all()
        assert (enriched["shares"] == sample_portfolio["shares"]).all()

    def test_no_nan_in_purchase_values(self, sample_portfolio, current_prices):
        """Test that purchase values never have NaN."""
        enriched = enrich_transactions(sample_portfolio, current_prices)

        assert enriched["purchase_value"].notna().all()

    def test_allocation_consistency_with_holdings(self, sample_portfolio, current_prices):
        """Test that allocation values match holdings values."""
        holdings = calculate_holdings(sample_portfolio, current_prices)
        allocation = calculate_portfolio_allocation(holdings)

        total_from_allocation = allocation["current_value"].sum()
        total_from_holdings = holdings["current_value"].sum()

        assert total_from_allocation == pytest.approx(total_from_holdings)
