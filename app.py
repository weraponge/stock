import random
import time

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


def _fetch_info_with_retry(ticker: str, max_retries: int = 4) -> dict | None:
    """Fetch a single ticker's info, backing off on Yahoo rate limits (429)."""
    for attempt in range(max_retries):
        try:
            info = yf.Ticker(ticker).info
            # A valid response has real fields; empty/garbage means a soft failure.
            if info and info.get("symbol"):
                return info
            return info or None
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            is_rate_limit = "429" in msg or "too many requests" in msg
            if attempt == max_retries - 1:
                return None
            # Exponential backoff with jitter; longer waits for explicit 429s.
            base = 2.0 if is_rate_limit else 0.5
            sleep_s = base * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(sleep_s)
    return None

st.set_page_config(
    page_title="Stock Screener",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Screener")
st.markdown("Screen stocks by market cap, P/E ratio, price, and more.")


@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(tickers: list[str]) -> pd.DataFrame:
    """Fetch stock data for a list of tickers, one at a time with throttling.

    Yahoo Finance rate-limits bursts of requests (HTTP 429). We pace the
    requests with a small delay and retry with exponential backoff.
    """
    records = []
    failed = []
    progress = st.progress(0.0, text="Fetching stock data...")
    total = len(tickers)

    for idx, ticker in enumerate(tickers):
        info = _fetch_info_with_retry(ticker)
        if not info:
            failed.append(ticker)
        else:
            records.append(
                {
                    "Ticker": ticker,
                    "Name": info.get("shortName", "N/A"),
                    "Sector": info.get("sector", "N/A"),
                    "Industry": info.get("industry", "N/A"),
                    "Market Cap": info.get("marketCap", 0),
                    "Price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                    "P/E Ratio": info.get("trailingPE", 0),
                    "Forward P/E": info.get("forwardPE", 0),
                    "PEG Ratio": info.get("pegRatio", 0),
                    "Dividend Yield (%)": round(
                        (info.get("dividendYield") or 0) * 100, 2
                    ),
                    "EPS": info.get("trailingEps", 0),
                    "Revenue": info.get("totalRevenue", 0),
                    "Profit Margin (%)": round(
                        (info.get("profitMargins") or 0) * 100, 2
                    ),
                    "52W High": info.get("fiftyTwoWeekHigh", 0),
                    "52W Low": info.get("fiftyTwoWeekLow", 0),
                    "50D MA": info.get("fiftyDayAverage", 0),
                    "200D MA": info.get("twoHundredDayAverage", 0),
                    "Beta": info.get("beta", 0),
                    "Volume": info.get("averageVolume", 0),
                }
            )

        progress.progress((idx + 1) / total, text=f"Fetched {idx + 1}/{total}")
        # Small pause between requests to stay under Yahoo's rate limit.
        if idx < total - 1:
            time.sleep(0.4 + random.uniform(0, 0.3))

    progress.empty()

    if failed:
        st.warning(
            f"Could not fetch {len(failed)} ticker(s) after retries "
            f"(likely rate-limited by Yahoo): {', '.join(failed)}. "
            "Try again in a minute or screen a smaller universe."
        )
    return pd.DataFrame(records)


@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch price history for a single ticker with retry on rate limits."""
    for attempt in range(4):
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                return hist
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if attempt == 3 or not ("429" in msg or "too many requests" in msg):
                break
            time.sleep(2.0 * (2 ** attempt) + random.uniform(0, 0.5))
    return pd.DataFrame()


# --- Predefined ticker lists ---
SP500_SAMPLE = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "JPM", "V", "PG", "XOM", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO",
    "ACN", "TMO", "ABT", "DHR", "NEE", "LIN", "PM", "TXN", "NKE",
    "UNP", "RTX", "LOW", "ORCL", "AMD", "INTC", "CRM", "QCOM", "AMAT",
    "NFLX", "ADBE", "PYPL", "DIS", "BA",
]

TECH_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA", "AMD",
    "INTC", "CRM", "ORCL", "ADBE", "NFLX", "PYPL", "QCOM", "AVGO",
    "AMAT", "MU", "NOW", "SNOW",
]

DIVIDEND_STOCKS = [
    "JNJ", "PG", "KO", "PEP", "MCD", "WMT", "ABT", "XOM", "CVX",
    "PM", "MO", "T", "VZ", "SO", "DUK", "NEE", "D", "O", "ABBV", "MMM",
]

# --- Sidebar: Stock Selection ---
st.sidebar.header("🔍 Stock Universe")

universe_option = st.sidebar.selectbox(
    "Choose stock universe",
    ["S&P 500 Sample (50)", "Tech Stocks (20)", "Dividend Stocks (20)", "Custom Tickers"],
)

if universe_option == "S&P 500 Sample (50)":
    selected_tickers = SP500_SAMPLE
elif universe_option == "Tech Stocks (20)":
    selected_tickers = TECH_STOCKS
elif universe_option == "Dividend Stocks (20)":
    selected_tickers = DIVIDEND_STOCKS
else:
    custom_input = st.sidebar.text_area(
        "Enter tickers (comma-separated)",
        value="AAPL, MSFT, GOOGL, AMZN, TSLA",
    )
    selected_tickers = [t.strip().upper() for t in custom_input.split(",") if t.strip()]

# --- Sidebar: Screening Filters ---
st.sidebar.header("⚙️ Screening Filters")

# Market Cap filter
market_cap_options = {
    "All": (0, float("inf")),
    "Mega Cap (>$200B)": (200_000_000_000, float("inf")),
    "Large Cap ($10B-$200B)": (10_000_000_000, 200_000_000_000),
    "Mid Cap ($2B-$10B)": (2_000_000_000, 10_000_000_000),
    "Small Cap (<$2B)": (0, 2_000_000_000),
}
market_cap_filter = st.sidebar.selectbox("Market Cap", list(market_cap_options.keys()))

# P/E Ratio filter
pe_min, pe_max = st.sidebar.slider(
    "P/E Ratio Range", 0.0, 100.0, (0.0, 50.0), step=1.0
)

# Dividend Yield filter
div_min = st.sidebar.slider("Min Dividend Yield (%)", 0.0, 15.0, 0.0, step=0.5)

# Price range filter
price_min, price_max = st.sidebar.slider(
    "Price Range ($)", 0, 2000, (0, 2000), step=10
)

# Sector filter
sector_filter = st.sidebar.multiselect(
    "Sector (leave empty for all)",
    [
        "Technology", "Healthcare", "Financial Services", "Consumer Cyclical",
        "Communication Services", "Industrials", "Consumer Defensive",
        "Energy", "Utilities", "Real Estate", "Basic Materials",
    ],
)

# --- Fetch Data ---
st.sidebar.markdown("---")
fetch_button = st.sidebar.button("🚀 Screen Stocks", type="primary", use_container_width=True)

if fetch_button or "stock_data" in st.session_state:
    if fetch_button:
        with st.spinner(f"Fetching data for {len(selected_tickers)} stocks..."):
            df = get_stock_data(selected_tickers)
            st.session_state["stock_data"] = df
    else:
        df = st.session_state["stock_data"]

    if df.empty:
        st.warning("No data returned. Please check your tickers.")
    else:
        # Apply filters
        cap_min, cap_max = market_cap_options[market_cap_filter]
        filtered = df[
            (df["Market Cap"] >= cap_min)
            & (df["Market Cap"] <= cap_max)
            & (df["P/E Ratio"] >= pe_min)
            & (df["P/E Ratio"] <= pe_max)
            & (df["Dividend Yield (%)"] >= div_min)
            & (df["Price"] >= price_min)
            & (df["Price"] <= price_max)
        ]

        if sector_filter:
            filtered = filtered[filtered["Sector"].isin(sector_filter)]

        # --- Display Results ---
        st.subheader(f"📊 Results: {len(filtered)} stocks found")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Stocks Found", len(filtered))
        with col2:
            avg_pe = filtered["P/E Ratio"].mean()
            st.metric("Avg P/E", f"{avg_pe:.1f}" if pd.notna(avg_pe) else "N/A")
        with col3:
            avg_div = filtered["Dividend Yield (%)"].mean()
            st.metric("Avg Div Yield", f"{avg_div:.2f}%")
        with col4:
            total_cap = filtered["Market Cap"].sum()
            st.metric("Total Mkt Cap", f"${total_cap / 1e12:.2f}T")

        # Data table
        st.dataframe(
            filtered.style.format(
                {
                    "Market Cap": "${:,.0f}",
                    "Price": "${:.2f}",
                    "P/E Ratio": "{:.2f}",
                    "Forward P/E": "{:.2f}",
                    "PEG Ratio": "{:.2f}",
                    "Dividend Yield (%)": "{:.2f}%",
                    "EPS": "${:.2f}",
                    "Revenue": "${:,.0f}",
                    "Profit Margin (%)": "{:.2f}%",
                    "52W High": "${:.2f}",
                    "52W Low": "${:.2f}",
                    "50D MA": "${:.2f}",
                    "200D MA": "${:.2f}",
                    "Beta": "{:.2f}",
                    "Volume": "{:,.0f}",
                }
            ),
            use_container_width=True,
            height=400,
        )

        # --- Stock Detail Section ---
        st.markdown("---")
        st.subheader("📉 Stock Detail")

        if not filtered.empty:
            detail_ticker = st.selectbox(
                "Select a stock to view details",
                filtered["Ticker"].tolist(),
            )

            if detail_ticker:
                col_chart, col_info = st.columns([2, 1])

                with col_chart:
                    period = st.selectbox(
                        "Chart Period",
                        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                        index=2,
                    )
                    hist = get_price_history(detail_ticker, period)

                    if not hist.empty:
                        fig = go.Figure(
                            data=[
                                go.Candlestick(
                                    x=hist.index,
                                    open=hist["Open"],
                                    high=hist["High"],
                                    low=hist["Low"],
                                    close=hist["Close"],
                                    name=detail_ticker,
                                )
                            ]
                        )
                        fig.update_layout(
                            title=f"{detail_ticker} - Price Chart",
                            yaxis_title="Price ($)",
                            xaxis_rangeslider_visible=False,
                            height=450,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                with col_info:
                    stock_row = filtered[filtered["Ticker"] == detail_ticker].iloc[0]
                    st.markdown(f"### {stock_row['Name']}")
                    st.markdown(f"**Sector:** {stock_row['Sector']}")
                    st.markdown(f"**Industry:** {stock_row['Industry']}")
                    st.markdown("---")
                    st.markdown(f"**Price:** ${stock_row['Price']:.2f}")
                    st.markdown(f"**P/E Ratio:** {stock_row['P/E Ratio']:.2f}")
                    st.markdown(f"**EPS:** ${stock_row['EPS']:.2f}")
                    st.markdown(f"**Dividend Yield:** {stock_row['Dividend Yield (%)']:.2f}%")
                    st.markdown(f"**Beta:** {stock_row['Beta']:.2f}")
                    st.markdown("---")
                    st.markdown(f"**52W High:** ${stock_row['52W High']:.2f}")
                    st.markdown(f"**52W Low:** ${stock_row['52W Low']:.2f}")
                    st.markdown(f"**50D MA:** ${stock_row['50D MA']:.2f}")
                    st.markdown(f"**200D MA:** ${stock_row['200D MA']:.2f}")

        # --- Export ---
        st.markdown("---")
        csv = filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="stock_screener_results.csv",
            mime="text/csv",
        )

else:
    st.info("👈 Configure your screening criteria in the sidebar and click **Screen Stocks** to begin.")
    st.markdown(
        """
        ### How to use this screener:
        1. **Choose a stock universe** — pick a predefined list or enter custom tickers
        2. **Set your filters** — market cap, P/E ratio, dividend yield, price range, sector
        3. **Click Screen Stocks** — results will appear with detailed metrics
        4. **Explore individual stocks** — select a stock to see its price chart and details
        5. **Export results** — download filtered results as CSV
        """
    )
