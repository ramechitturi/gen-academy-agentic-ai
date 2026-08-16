import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from src.data_loader import load_portfolio, validate_portfolio_data
from src.analysis import (
    fetch_current_prices,
    calculate_holdings,
    calculate_portfolio_allocation,
    calculate_portfolio_summary,
    enrich_transactions,
    calculate_realized_gains,
)

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

st.title("📊 Portfolio Analyzer")

# Initialize session state
if "portfolio" not in st.session_state:
    st.session_state.portfolio = None
if "transactions" not in st.session_state:
    st.session_state.transactions = None
if "holdings" not in st.session_state:
    st.session_state.holdings = None
if "summary" not in st.session_state:
    st.session_state.summary = None


def load_and_process_portfolio(portfolio_df):
    """Load, validate, and process portfolio data."""
    if not validate_portfolio_data(portfolio_df):
        st.error("Invalid portfolio data. Missing required columns: ticker, shares, purchase_price, purchase_date")
        return False

    with st.spinner("Fetching current prices... This may take a moment."):
        tickers = portfolio_df["ticker"].unique().tolist()
        current_prices = fetch_current_prices(tickers)

    if any(price is None for price in current_prices.values()):
        st.warning("Some prices could not be fetched. Results may be incomplete.")

    transactions = enrich_transactions(portfolio_df, current_prices)
    holdings = calculate_holdings(portfolio_df, current_prices)
    summary = calculate_portfolio_summary(holdings)

    st.session_state.portfolio = portfolio_df
    st.session_state.transactions = transactions
    st.session_state.holdings = holdings
    st.session_state.summary = summary
    return True


# Create tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload", "📊 Allocations", "📈 Transaction History"])

# ==================== TAB 1: UPLOAD ====================
with tab1:
    st.subheader("Upload Portfolio Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Option 1: Upload CSV File**")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type="csv",
            help="File should have columns: ticker, shares, purchase_price, purchase_date",
        )

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                df["purchase_date"] = pd.to_datetime(df["purchase_date"])
                if load_and_process_portfolio(df):
                    st.success("✅ Portfolio loaded successfully!")
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    with col2:
        st.markdown("**Option 2: Load Sample Portfolio**")
        if st.button("Load Sample Data", use_container_width=True):
            try:
                portfolio = load_portfolio()
                if load_and_process_portfolio(portfolio):
                    st.success("✅ Sample portfolio loaded successfully!")
            except Exception as e:
                st.error(f"Error loading sample data: {str(e)}")

    st.divider()

    st.markdown("### CSV Format Requirements")
    st.markdown("""
    Your CSV file should contain these columns:
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    - **shares**: Number of shares purchased
    - **purchase_price**: Price per share at purchase
    - **purchase_date**: Date of purchase (YYYY-MM-DD format)

    Example:
    ```
    ticker,shares,purchase_price,purchase_date
    AAPL,10,150.00,2023-01-15
    MSFT,5,280.00,2023-02-20
    ```
    """)


# ==================== TAB 2: ALLOCATIONS ====================
with tab2:
    if st.session_state.holdings is None:
        st.info("👈 Please upload or load a portfolio in the **Upload** tab first.")
    else:
        holdings = st.session_state.holdings
        summary = st.session_state.summary

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Invested", f"${summary['total_invested']:,.2f}")
        with col2:
            st.metric("Current Value", f"${summary['total_current_value']:,.2f}")
        with col3:
            gain_loss = summary["total_gain_loss"]
            st.metric(
                "Gain/Loss",
                f"${gain_loss:,.2f}",
                delta=f"{summary['total_return_pct']:.2f}%",
            )
        with col4:
            st.metric("Holdings", summary["num_holdings"])

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Holdings Summary")
            display_holdings = holdings[
                [
                    "ticker",
                    "shares",
                    "purchase_price",
                    "current_price",
                    "purchase_value",
                    "current_value",
                    "unrealized_gain_loss",
                    "unrealized_gain_loss_pct",
                ]
            ].copy()
            display_holdings.columns = [
                "Ticker",
                "Shares",
                "Purchase Price",
                "Current Price",
                "Purchase Value",
                "Current Value",
                "Gain/Loss",
                "Return %",
            ]
            st.dataframe(
                display_holdings.style.format(
                    {
                        "Purchase Price": "${:.2f}",
                        "Current Price": "${:.2f}",
                        "Purchase Value": "${:,.2f}",
                        "Current Value": "${:,.2f}",
                        "Gain/Loss": "${:,.2f}",
                        "Return %": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            st.subheader("Portfolio Allocation")
            allocation = calculate_portfolio_allocation(holdings)

            # Create pie chart
            pie_fig = px.pie(
                allocation,
                values="current_value",
                names="ticker",
                title="Allocation by Ticker",
                hover_data={"current_value": ":.2f", "allocation_pct": ":.2f%"},
            )
            pie_fig.update_traces(
                textposition="inside",
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Value: $%{value:,.2f}<br>Allocation: %{customdata[1]:.2f}%<extra></extra>",
            )
            st.plotly_chart(pie_fig, use_container_width=True)

            st.subheader("Allocation Details")
            allocation_display = allocation[["ticker", "current_value", "allocation_pct"]].copy()
            allocation_display.columns = ["Ticker", "Value", "Allocation %"]
            st.dataframe(
                allocation_display.style.format(
                    {
                        "Value": "${:,.2f}",
                        "Allocation %": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


# ==================== TAB 3: TRANSACTION HISTORY ====================
with tab3:
    if st.session_state.transactions is None:
        st.info("👈 Please upload or load a portfolio in the **Upload** tab first.")
    else:
        transactions = st.session_state.transactions

        st.subheader("Transaction History")

        # Date range filter
        col1, col2, col3 = st.columns(3)
        with col1:
            min_date = transactions[
                ["purchase_date", "sold_date"]
            ].min().min().date()
            start_date = st.date_input(
                "Start Date",
                value=min_date,
                max_value=datetime.now().date(),
            )
        with col2:
            max_date = transactions[
                ["purchase_date", "sold_date"]
            ].max().max().date()
            end_date = st.date_input(
                "End Date",
                value=max_date,
                max_value=datetime.now().date(),
            )
        with col3:
            st.empty()  # Spacer for alignment

        # Filter transactions by date range (both buy and sell dates)
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date) + timedelta(days=1)

        # Filter by purchase date for buys and sold date for sells
        filtered_buys = transactions[
            (transactions["transaction_type"] == "Buy") &
            (transactions["purchase_date"] >= start_dt) &
            (transactions["purchase_date"] < end_dt)
        ].copy()

        filtered_sells = transactions[
            (transactions["transaction_type"] == "Sell") &
            (transactions["sold_date"] >= start_dt) &
            (transactions["sold_date"] < end_dt)
        ].copy()

        filtered_transactions = pd.concat([filtered_buys, filtered_sells], ignore_index=True)

        if len(filtered_transactions) == 0:
            st.warning("No transactions found in the selected date range.")
        else:
            # Calculate metrics for period
            total_invested_period = filtered_buys["purchase_value"].sum()
            realized_gains_period = filtered_sells["realized_gain_loss"].sum()

            # Summary stats for filtered period
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Amount Invested", f"${total_invested_period:,.2f}")
            with col2:
                st.metric("Realized Gains", f"${realized_gains_period:,.2f}")
            with col3:
                num_transactions = len(filtered_transactions)
                st.metric("Transactions", num_transactions)
            with col4:
                unique_tickers = filtered_transactions["ticker"].nunique()
                st.metric("Unique Tickers", unique_tickers)

            st.divider()

            # Detailed transaction table
            st.subheader("All Transactions")
            display_trans = filtered_transactions[
                [
                    "ticker",
                    "shares",
                    "purchase_price",
                    "purchase_date",
                    "sold_price",
                    "sold_date",
                    "transaction_type",
                    "purchase_value",
                    "sale_value",
                    "realized_gain_loss",
                    "realized_gain_loss_pct",
                ]
            ].copy()

            # Format for display
            display_trans = display_trans.sort_values("purchase_date", ascending=False)
            display_trans_display = pd.DataFrame({
                "Ticker": display_trans["ticker"],
                "Type": display_trans["transaction_type"],
                "Shares": display_trans["shares"],
                "Buy Price": display_trans["purchase_price"],
                "Buy Date": display_trans["purchase_date"].dt.strftime("%Y-%m-%d"),
                "Buy Value": display_trans["purchase_value"],
                "Sell Price": display_trans["sold_price"],
                "Sell Date": display_trans["sold_date"].dt.strftime("%Y-%m-%d"),
                "Realized Gain/Loss": display_trans["realized_gain_loss"],
                "Return %": display_trans["realized_gain_loss_pct"],
            })

            st.dataframe(
                display_trans_display.style.format(
                    {
                        "Shares": "{:.2f}",
                        "Buy Price": "${:.2f}",
                        "Buy Value": "${:,.2f}",
                        "Sell Price": "${:.2f}",
                        "Realized Gain/Loss": "${:,.2f}",
                        "Return %": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            # Transaction breakdown by ticker
            st.subheader("Transactions by Ticker")
            ticker_stats = filtered_transactions.groupby("ticker").agg({
                "shares": "sum",
                "purchase_price": "mean",
                "purchase_date": ["min", "max"],
                "transaction_type": lambda x: (x == "Buy").sum(),
            }).round(2)
            ticker_stats.columns = ["Total Shares", "Avg Buy Price", "First Date", "Last Date", "Buys"]

            # Add sell count
            sell_counts = filtered_transactions[filtered_transactions["transaction_type"] == "Sell"].groupby("ticker").size()
            ticker_stats["Sells"] = sell_counts

            ticker_stats = ticker_stats.reset_index().fillna(0)
            st.dataframe(
                ticker_stats.style.format(
                    {
                        "Total Shares": "{:.2f}",
                        "Avg Buy Price": "${:.2f}",
                        "Buys": "{:.0f}",
                        "Sells": "{:.0f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
