"""Versioned vnstock connectors; KBS/VCI remain the upstream providers."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from importlib.metadata import version
import json
import math
import os
import re

from src.data.providers import DataSourceError, VN_TIME, completed_day_cutoff
from src.data.validate import validate_prices

VNSTOCK_VERSION = "4.0.8"
ENDPOINTS = {
    "KBS": "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{ticker}/data_day",
    "VCI": "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
}


def load_quote(source="KBS"):
    # The dependency can write assistant rules on import; this app only needs data.
    os.environ["VNSTOCK_DISABLE_AGENT_SETUP"] = "1"
    os.environ["VNSTOCK_DISABLE_GLOBAL_AGENT"] = "1"
    os.environ["VNSTOCK_AGENT_TARGETS"] = "none"
    try:
        installed = version("vnstock")
        if installed != VNSTOCK_VERSION:
            raise DataSourceError(f"vnstock {installed} has no verified unit contract; install vnstock=={VNSTOCK_VERSION}")
        # Direct component preserves VCI symbol/source metadata; the unified
        # Quote adapter drops these custom DataFrame attributes when slicing.
        if source == "KBS":
            from vnstock.explorer.kbs.quote import Quote
        else:
            from vnstock.explorer.vci.quote import Quote
        return Quote
    except ImportError as exc:
        raise DataSourceError("vnstock unavailable; install requirements.txt") from exc


def normalize_history(frame, ticker: str, source: str, start: date, cutoff: date) -> list[dict]:
    """4.0.8 stock OHLC is thousand VND, volumes are shares; never infer units."""
    import pandas as pd

    required = {"time", "open", "high", "low", "close", "volume"}
    if not isinstance(frame, pd.DataFrame) or not required.issubset(frame.columns):
        raise DataSourceError("vnstock history has missing OHLCV columns")
    symbol = frame.attrs.get("symbol", getattr(frame, "name", None))
    upstream = frame.attrs.get("source", getattr(frame, "source", None))
    if symbol != ticker or upstream != source:
        raise DataSourceError("vnstock history symbol/source metadata mismatch")
    if getattr(frame, "category", "stock") != "stock":
        raise DataSourceError("vnstock history is not stock data")
    rows = []
    for item in frame.to_dict("records"):
        stamp = pd.Timestamp(item["time"])
        if pd.isna(stamp):
            raise DataSourceError("vnstock history contains invalid dates")
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert(VN_TIME)
        session = stamp.date()
        if not start <= session <= cutoff:
            continue
        values = {}
        for key in ("open", "high", "low", "close", "volume"):
            value = item[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise DataSourceError(f"vnstock history contains invalid {key}")
            values[key] = round(float(value) * 1000, 6) if key != "volume" else value
        rows.append({"ticker": ticker, "date": session.isoformat(), **values,
                     "adjusted_close": None, "unit": "VND_per_share",
                     "price_provider": f"Vnstock-{source}",
                     "upstream_source": "KBS" if source == "KBS" else "Vietcap",
                     "price_basis": f"vnstock_{source.lower()}_ohlc_adjustment_unverified"})
    rows.sort(key=lambda row: row["date"])
    validation = validate_prices(rows, ticker, start, cutoff)
    if not validation["valid"]:
        raise DataSourceError(f"vnstock {source} price validation failed: {validation['errors'][:3]}")
    return rows


def fetch_vnstock_prices(ticker: str, start: date, as_of: date, *, source: str) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker) or source not in ENDPOINTS:
        raise ValueError("Invalid ticker or vnstock source")
    cutoff = completed_day_cutoff(as_of)
    if start > cutoff:
        raise ValueError("start must be on or before cutoff")
    end = cutoff + timedelta(days=2) if source == "KBS" else cutoff
    request = {"symbol": ticker, "source": source, "start": start.isoformat(),
               "end": end.isoformat(), "interval": "1D", "floating": 6,
               "show_log": False}
    try:
        quote = load_quote(source)(symbol=ticker, show_log=False)
        if quote.symbol != ticker or quote.asset_type != "stock":
            raise DataSourceError("vnstock quote identity/asset type mismatch")
        frame = quote.history(**{k: request[k] for k in ("start", "end", "interval", "floating", "show_log")})
        rows = normalize_history(frame, ticker, source, start, cutoff)
        snapshot = {"snapshot_kind": "vnstock_library_output_not_raw_http", "library": "vnstock",
                    "library_version": VNSTOCK_VERSION, "upstream_source": source,
                    "request": request, "library_price_unit": "thousand_VND_per_share",
                    "price_multiplier": 1000, "volume_multiplier": 1,
                    "history": json.loads(frame.to_json(orient="records", date_format="iso"))}
        raw = json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"vnstock {source} failed: {type(exc).__name__}: {exc}") from exc
    except SystemExit as exc:
        # Some SDK rate-limit paths exit; keep a Streamlit request from terminating.
        raise DataSourceError(f"vnstock {source} stopped the request (exit {exc.code})") from exc
    return {"url": ENDPOINTS[source].format(ticker=ticker), "raw": raw, "rows": rows,
            "meta": {}, "cutoff": cutoff.isoformat(), "request_payload": request,
            "upstream_source": "KBS" if source == "KBS" else "Vietcap",
            "snapshot_kind": snapshot["snapshot_kind"], "library_version": VNSTOCK_VERSION,
            "retrieved_at": datetime.now(VN_TIME).isoformat()}


def fetch_vnstock_kbs_prices(ticker: str, start: date, as_of: date) -> dict:
    return fetch_vnstock_prices(ticker, start, as_of, source="KBS")


def fetch_vnstock_vci_prices(ticker: str, start: date, as_of: date) -> dict:
    return fetch_vnstock_prices(ticker, start, as_of, source="VCI")
