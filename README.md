# 📈 Stock Screener

A Streamlit-based stock screener that lets you filter and analyze stocks by fundamental metrics.

## Features

- **Predefined stock universes** — S&P 500 sample, tech stocks, dividend stocks, or custom tickers
- **Multiple filters** — Market cap, P/E ratio, dividend yield, price range, sector
- **Interactive charts** — Candlestick price charts via Plotly
- **Stock detail panel** — Key metrics at a glance
- **CSV export** — Download filtered results

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Select your repository, branch (`main`), and main file (`app.py`)
5. Click **Deploy**

The app will be live in about a minute.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
stock/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── .streamlit/
│   └── config.toml        # Theme & server config
└── README.md
```

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [Plotly](https://plotly.com/python/) — Interactive charts
- [Pandas](https://pandas.pydata.org/) — Data manipulation
