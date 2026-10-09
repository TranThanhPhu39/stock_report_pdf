"""Application pipeline: always acquire source data before displaying a new result."""

import csv
from datetime import date
from pathlib import Path
import re

from src.data.acquisition import acquire, write_json
from src.data.providers import completed_day_cutoff


def run_analysis(ticker: str, start: date, as_of: date, root: Path | None = None) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    if start > completed_day_cutoff(as_of):
        raise ValueError("Ngày bắt đầu phải nằm trước hoặc trong ngày giá đã hoàn tất.")
    root = root or Path(__file__).resolve().parents[1]
    # No pre-existing CSV and no manual fetch step required. This calls the network providers.
    acquisition = acquire(ticker, start, as_of, root)
    rows = []
    if acquisition["prices"]:
        with (root / acquisition["prices"]["csv"]).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append({**row, **{key: float(row[key]) for key in ("open", "high", "low", "close")},
                             "volume": int(float(row["volume"]))})
    market = None
    if rows:
        closes = [row["close"] for row in rows]
        market = {"latest_close_vnd": closes[-1], "latest_date": rows[-1]["date"],
                  "latest_volume": rows[-1]["volume"],
                  "ma20_vnd": sum(closes[-20:]) / 20 if len(closes) >= 20 else None,
                  "ma50_vnd": sum(closes[-50:]) / 50 if len(closes) >= 50 else None}
    result = {"request": {"ticker": ticker, "start": start.isoformat(), "as_of": as_of.isoformat()},
              "acquisition": acquisition, "market": market, "price_rows": rows,
              "financial_metrics_status": acquisition["financial_metrics_status"],
              "status": "partial" if acquisition["errors"] else "acquired"}
    write_json(root / "outputs/runs" / acquisition["run_id"] / "analysis.json", result)
    return result
