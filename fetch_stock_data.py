#!/usr/bin/env python3
"""
fetch_stock_data.py

Download historical OHLCV data from Yahoo Finance via yfinance and save as JSON.

Default behaviour (no args): fetches GEV (2024-04-02→today) and NVDA (2019-01-01→today).
Pass --ticker / --start to query any equity, ETF, crypto, futures contract, or option.

Usage
-----
  python fetch_stock_data.py                                 # GEV + NVDA defaults
  python fetch_stock_data.py -t AAPL -s 2020-01-01
  python fetch_stock_data.py -t BTC-USD -s 2020-01-01       # crypto
  python fetch_stock_data.py -t ES=F  -s 2022-01-01         # S&P 500 futures
  python fetch_stock_data.py -t CL=F  -s 2022-01-01         # crude oil futures
  python fetch_stock_data.py -t AAPL240119C00150000 -s 2023-10-01   # option chain
  python fetch_stock_data.py -t SPY   -s 2010-01-01 -i 1wk  # weekly bars
  python fetch_stock_data.py -t NVDA  -s 2019-01-01 -f all  # full OHLCV + volume
"""

import argparse
import json
import os
import sys
from datetime import date, datetime

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. Run: pip install yfinance")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── default queries ────────────────────────────────────────────────────────────
DEFAULTS = [
    {"ticker": "GEV",  "start": "2024-04-02", "auto_adjust": True},
    {"ticker": "NVDA", "start": "2019-01-01", "auto_adjust": True},
]

VALID_INTERVALS = {
    "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h",
    "1d", "5d", "1wk", "1mo", "3mo",
}


# ── core fetch ────────────────────────────────────────────────────────────────
def fetch_ticker(
    ticker: str,
    start: str,
    end: str,
    interval: str = "1d",
    auto_adjust: bool = True,
    fields: str = "close",
) -> list[dict]:
    """
    Download data for *ticker* and return a list of record dicts.

    fields='close'  → [{date, close}, ...]
    fields='all'    → [{date, open, high, low, close, volume}, ...]
    """
    t = yf.Ticker(ticker)
    df = t.history(
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
    )

    if df.empty:
        raise ValueError(
            f"No data returned for {ticker} ({start} → {end}).\n"
            "  • Verify the ticker symbol at finance.yahoo.com\n"
            "  • Check the date range is valid for this instrument\n"
            "  • Intraday intervals (<1d) are limited to the last 60 days"
        )

    records = []
    for idx, row in df.iterrows():
        dt_str = (
            idx.date().strftime("%Y-%m-%d")
            if hasattr(idx, "date")
            else str(idx)[:10]
        )
        if fields == "all":
            record = {
                "date":   dt_str,
                "open":   round(float(row["Open"]),   2),
                "high":   round(float(row["High"]),   2),
                "low":    round(float(row["Low"]),    2),
                "close":  round(float(row["Close"]),  2),
                "volume": int(row["Volume"]) if "Volume" in row else None,
            }
        else:
            record = {
                "date":  dt_str,
                "close": round(float(row["Close"]), 2),
            }
        records.append(record)

    return records


def save_json(records: list[dict], path: str) -> None:
    with open(path, "w") as f:
        json.dump(records, f, indent=2)


def print_summary(ticker: str, records: list[dict], path: str) -> None:
    first, last = records[0], records[-1]
    print(
        f"  {ticker:<12} {len(records):>5} records | "
        f"{first['date']} → {last['date']} | "
        f"close {first['close']:.2f} → {last['close']:.2f} | "
        f"→ {os.path.relpath(path)}"
    )


# ── default run ───────────────────────────────────────────────────────────────
def run_defaults(fields: str = "close") -> None:
    today = date.today().strftime("%Y-%m-%d")
    print(f"Fetching defaults (end date: {today})\n")
    for cfg in DEFAULTS:
        ticker = cfg["ticker"]
        records = fetch_ticker(
            ticker, cfg["start"], today,
            auto_adjust=cfg["auto_adjust"],
            fields=fields,
        )
        path = os.path.join(SCRIPT_DIR, f"{ticker.lower()}_prices.json")
        save_json(records, path)
        print_summary(ticker, records, path)


# ── CLI run ───────────────────────────────────────────────────────────────────
def run_cli(args: argparse.Namespace) -> None:
    end = args.end or date.today().strftime("%Y-%m-%d")
    safe_name = args.ticker.lower().replace("=", "_").replace("-", "_")
    output = args.output or os.path.join(SCRIPT_DIR, f"{safe_name}_prices.json")

    print(f"Fetching {args.ticker}  {args.start} → {end}  interval={args.interval}\n")
    records = fetch_ticker(
        args.ticker, args.start, end,
        interval=args.interval,
        auto_adjust=not args.no_adjust,
        fields=args.fields,
    )
    save_json(records, output)
    print_summary(args.ticker, records, output)


# ── entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fetch_stock_data",
        description="Fetch historical price data from Yahoo Finance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python fetch_stock_data.py                              # GEV + NVDA defaults
  python fetch_stock_data.py -t AAPL -s 2020-01-01
  python fetch_stock_data.py -t BTC-USD  -s 2020-01-01   # crypto
  python fetch_stock_data.py -t ES=F     -s 2022-01-01   # S&P 500 futures
  python fetch_stock_data.py -t CL=F     -s 2022-01-01   # crude oil futures
  python fetch_stock_data.py -t GC=F     -s 2020-01-01   # gold futures
  python fetch_stock_data.py -t ^VIX     -s 2020-01-01   # VIX index
  python fetch_stock_data.py -t AAPL -s 2024-01-01 -i 1h # hourly bars
  python fetch_stock_data.py -t SPY  -s 2010-01-01 -i 1wk -f all  # full OHLCV
        """,
    )
    parser.add_argument("-t", "--ticker",
                        help="Ticker symbol (equity, ETF, crypto, futures, index)")
    parser.add_argument("-s", "--start",
                        help="Start date YYYY-MM-DD  (required with --ticker)")
    parser.add_argument("-e", "--end",
                        help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("-i", "--interval", default="1d",
                        choices=sorted(VALID_INTERVALS),
                        help="Bar interval (default: 1d)")
    parser.add_argument("-f", "--fields", default="close",
                        choices=["close", "all"],
                        help="'close' → {date,close}  |  'all' → full OHLCV (default: close)")
    parser.add_argument("-o", "--output",
                        help="Output file path (default: <ticker>_prices.json next to script)")
    parser.add_argument("--no-adjust", action="store_true",
                        help="Disable split/dividend adjustment (auto_adjust=False)")

    args = parser.parse_args()

    if args.ticker:
        if not args.start:
            parser.error("--start is required when --ticker is specified")
        run_cli(args)
    else:
        run_defaults(fields=args.fields)


if __name__ == "__main__":
    main()
