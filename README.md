# yfinance-fetcher

Lightweight CLI wrapper around [yfinance](https://github.com/ranaroussi/yfinance) that downloads historical price data for any Yahoo Finance instrument and saves it as clean JSON.

Supports equities, ETFs, indices, crypto, futures, and options.

## Install

```bash
pip install yfinance
```

## Usage

### Defaults (GEV + NVDA)

```bash
python fetch_stock_data.py
```

Outputs `gev_prices.json` and `nvda_prices.json` next to the script.

### Custom ticker

```bash
# Any equity or ETF
python fetch_stock_data.py -t AAPL -s 2020-01-01
python fetch_stock_data.py -t SPY  -s 2010-01-01 -e 2023-12-31

# Crypto
python fetch_stock_data.py -t BTC-USD -s 2020-01-01
python fetch_stock_data.py -t ETH-USD -s 2020-01-01

# Futures
python fetch_stock_data.py -t ES=F -s 2022-01-01   # S&P 500 futures
python fetch_stock_data.py -t CL=F -s 2022-01-01   # crude oil
python fetch_stock_data.py -t GC=F -s 2020-01-01   # gold
python fetch_stock_data.py -t NQ=F -s 2022-01-01   # Nasdaq 100 futures

# Volatility index
python fetch_stock_data.py -t ^VIX -s 2020-01-01

# Weekly bars
python fetch_stock_data.py -t SPY -s 2010-01-01 -i 1wk

# Full OHLCV output (open, high, low, close, volume)
python fetch_stock_data.py -t NVDA -s 2019-01-01 -f all
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `-t / --ticker` | — | Ticker symbol |
| `-s / --start` | — | Start date `YYYY-MM-DD` (required with `-t`) |
| `-e / --end` | today | End date `YYYY-MM-DD` |
| `-i / --interval` | `1d` | Bar size: `1m 5m 15m 1h 1d 1wk 1mo` etc. |
| `-f / --fields` | `close` | `close` → `{date,close}` · `all` → full OHLCV |
| `-o / --output` | `<ticker>_prices.json` | Custom output path |
| `--no-adjust` | off | Disable split/dividend adjustment |

## Output format

```json
[
  {"date": "2024-04-02", "close": 139.48},
  {"date": "2024-04-03", "close": 141.20}
]
```

With `-f all`:

```json
[
  {"date": "2024-04-02", "open": 138.10, "high": 140.50, "low": 137.80, "close": 139.48, "volume": 1234567}
]
```

## Notes

- `auto_adjust=True` by default — all historical prices are adjusted for splits and dividends (essential for NVDA which had a 10-for-1 split in June 2024).
- Intraday intervals (`1m`, `5m`, etc.) are limited by Yahoo Finance to the last 60 days.
- Futures use the continuous front-month contract (e.g. `ES=F`).
