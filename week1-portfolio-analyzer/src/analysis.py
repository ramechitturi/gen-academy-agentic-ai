import pandas as pd
import yfinance as yf
from typing import Dict, Tuple


def fetch_current_prices(tickers: list[str]) -> Dict[str, float]:
    """Fetch current prices for given tickers using yfinance."""
    prices = {}
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker)
            price = data.info.get("currentPrice")
            if price is None:
                price = data.history(period="1d")["Close"].iloc[-1]
            prices[ticker] = price
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            prices[ticker] = None
    return prices


def enrich_transactions(portfolio: pd.DataFrame, current_prices: Dict[str, float]) -> pd.DataFrame:
    """Add transaction type and gain/loss information to portfolio."""
    portfolio = portfolio.copy()

    # Determine transaction type (buy or sell)
    portfolio["transaction_type"] = portfolio["sold_date"].isna().apply(
        lambda x: "Buy" if x else "Sell"
    )

    # Calculate purchase value
    portfolio["purchase_value"] = portfolio["shares"] * portfolio["purchase_price"]

    # For sold transactions, calculate realized gain
    portfolio["sale_value"] = portfolio.apply(
        lambda row: row["shares"] * row["sold_price"] if pd.notna(row["sold_price"]) else None,
        axis=1
    )

    portfolio["realized_gain_loss"] = portfolio.apply(
        lambda row: row["sale_value"] - row["purchase_value"] if pd.notna(row["sale_value"]) else None,
        axis=1
    )

    portfolio["realized_gain_loss_pct"] = portfolio.apply(
        lambda row: (row["realized_gain_loss"] / row["purchase_value"] * 100)
                    if pd.notna(row["realized_gain_loss"]) else None,
        axis=1
    )

    # For held transactions, calculate unrealized gain
    portfolio["current_price"] = portfolio["ticker"].map(current_prices)
    portfolio["current_value"] = portfolio.apply(
        lambda row: row["shares"] * row["current_price"] if pd.notna(row["current_price"]) else None,
        axis=1
    )

    portfolio["unrealized_gain_loss"] = portfolio.apply(
        lambda row: row["current_value"] - row["purchase_value"]
                    if pd.notna(row["current_value"]) and pd.isna(row["sold_date"]) else None,
        axis=1
    )

    portfolio["unrealized_gain_loss_pct"] = portfolio.apply(
        lambda row: (row["unrealized_gain_loss"] / row["purchase_value"] * 100)
                    if pd.notna(row["unrealized_gain_loss"]) else None,
        axis=1
    )

    return portfolio


def calculate_holdings(portfolio: pd.DataFrame, current_prices: Dict[str, float]) -> pd.DataFrame:
    """Calculate current value and gain/loss for each holding (only held positions)."""
    enriched = enrich_transactions(portfolio, current_prices)
    # Filter only held positions (not sold)
    held = enriched[enriched["sold_date"].isna()].copy()
    return held


def calculate_portfolio_allocation(holdings: pd.DataFrame) -> pd.DataFrame:
    """Calculate allocation percentages for each holding."""
    allocation = holdings[["ticker", "current_value"]].copy()
    total_value = holdings["current_value"].sum()
    allocation["allocation_pct"] = (allocation["current_value"] / total_value) * 100
    return allocation.sort_values("allocation_pct", ascending=False)


def calculate_portfolio_summary(holdings: pd.DataFrame) -> Dict:
    """Calculate total portfolio metrics."""
    total_current_value = holdings["current_value"].sum()
    total_purchase_value = holdings["purchase_value"].sum()
    total_gain_loss = total_current_value - total_purchase_value
    total_return_pct = (total_gain_loss / total_purchase_value) * 100 if total_purchase_value > 0 else 0

    return {
        "total_invested": total_purchase_value,
        "total_current_value": total_current_value,
        "total_gain_loss": total_gain_loss,
        "total_return_pct": total_return_pct,
        "num_holdings": len(holdings),
    }


def calculate_realized_gains(transactions: pd.DataFrame, start_date=None, end_date=None) -> Dict:
    """Calculate realized gains for sold transactions in a given period."""
    sold = transactions[transactions["sold_date"].notna()].copy()

    if start_date is not None:
        sold = sold[sold["sold_date"] >= start_date]
    if end_date is not None:
        sold = sold[sold["sold_date"] <= end_date]

    if len(sold) == 0:
        return {
            "total_realized_gain": 0,
            "num_sold_transactions": 0,
            "sold_transactions": pd.DataFrame(),
        }

    total_realized_gain = sold["realized_gain_loss"].sum()

    return {
        "total_realized_gain": total_realized_gain,
        "num_sold_transactions": len(sold),
        "sold_transactions": sold,
    }
