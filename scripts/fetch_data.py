"""Fetch daily prices and, for HPG, issuer financial-report PDFs.

Example: python -m scripts.fetch_data --ticker HPG --start 2025-10-09 --as-of 2026-10-09
"""

import argparse
import csv
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from src.data.providers import (DataSourceError, HPG_REPORTS_URL, VN_TIME,
                                discover_hpg_reports, download, fetch_daily_prices)
from src.data.validate import validate_prices


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def acquire(ticker: str, start: date, as_of: date, root: Path, report_limit: int = 2) -> dict:
    ticker = ticker.upper().strip()
    stamp = datetime.now(VN_TIME).strftime("%Y%m%d_%H%M%S_%f")
    run_id = f"{ticker}_{stamp}"
    run_dir = root / "outputs/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "request.json", {"ticker": ticker, "start": start.isoformat(),
                                          "as_of": as_of.isoformat(), "mode": "completed_daily",
                                          "report_limit": report_limit})
    sources, errors = [], []
    summary = {"ticker": ticker, "run_id": run_id, "prices": None, "financial_documents": [],
               "financial_metrics_status": "not_extracted", "errors": errors}
    try:
        prices = fetch_daily_prices(ticker, start, as_of)
        source_id = f"YAHOO_{run_id}"
        raw_path = root / "data/raw/prices" / f"{run_id}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(prices["raw"])
        validation = validate_prices(prices["rows"], ticker, start, date.fromisoformat(prices["cutoff"]))
        write_json(run_dir / "validation.json", validation)
        sources.append({"source_id": source_id, "url_or_file": prices["url"],
                        "retrieved_at": prices["retrieved_at"], "page_or_table": "chart.indicators.quote",
                        "notes": f"Raw snapshot: {raw_path.relative_to(root).as_posix()}; VND; adjustment basis unverified"})
        if not validation["valid"]:
            raise DataSourceError(f"Daily price validation failed: {validation['errors'][:5]}")
        output = root / "data/processed" / f"{run_id}_prices.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(prices["rows"][0]) + ["source_id"])
            writer.writeheader()
            writer.writerows({**row, "source_id": source_id} for row in prices["rows"])
        summary["prices"] = {"row_count": len(prices["rows"]), "first": prices["rows"][0]["date"],
                             "last": prices["rows"][-1]["date"], "last_close_vnd": prices["rows"][-1]["close"],
                             "cutoff": prices["cutoff"], "csv": output.relative_to(root).as_posix(),
                             "company_name": prices["meta"].get("longName"), "validation": validation}
    except (DataSourceError, ValueError) as exc:
        errors.append({"stage": "prices", "message": str(exc)})
    if ticker == "HPG" and report_limit:
        try:
            reports, html = discover_hpg_reports(min(as_of, datetime.now(VN_TIME).date()))
            listing_path = root / "data/raw/documents" / f"{run_id}_listing.html"
            listing_path.parent.mkdir(parents=True, exist_ok=True)
            listing_path.write_bytes(html)
            write_json(run_dir / "financial_document_candidates.json", reports)
            if not reports:
                raise DataSourceError("No eligible consolidated reports discovered on issuer listing page 1")
            for report in reports[:report_limit]:
                try:
                    content = download(report["url"])
                    if not content.startswith(b"%PDF-"):
                        raise DataSourceError("Download is not a PDF")
                    filename = Path(urlparse(report["url"]).path).name
                    target = root / "data/raw/documents" / filename
                    target.write_bytes(content)
                    source_id = f"HPG_{hashlib.sha256(content).hexdigest()[:16]}"
                    summary["financial_documents"].append({**report, "file": target.relative_to(root).as_posix(),
                                                           "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                                                           "source_id": source_id})
                    sources.append({"source_id": source_id, "url_or_file": report["url"],
                                    "retrieved_at": datetime.now(VN_TIME).isoformat(), "page_or_table": "whole PDF; metrics not extracted",
                                    "notes": f"{report['title']}; published_at={report['published_at']}; listing={HPG_REPORTS_URL}"})
                except DataSourceError as exc:
                    errors.append({"stage": "financial_document", "url": report["url"], "message": str(exc)})
        except DataSourceError as exc:
            errors.append({"stage": "financial_listing", "message": str(exc)})
    elif ticker != "HPG":
        summary["financial_metrics_status"] = "issuer_provider_not_implemented_for_this_ticker"
    registry = root / "data/metadata/source_registry.csv"
    registry.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not registry.exists() or not registry.stat().st_size
    with registry.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_id", "url_or_file", "retrieved_at", "page_or_table", "notes"])
        if needs_header:
            writer.writeheader()
        writer.writerows(sources)
    write_json(run_dir / "acquisition.json", summary)
    write_json(run_dir / "sources.json", sources)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", default="HPG")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(VN_TIME).date())
    parser.add_argument("--report-limit", type=int, default=2)
    args = parser.parse_args()
    if args.report_limit < 0:
        parser.error("report-limit must be nonnegative")
    if args.start > args.as_of:
        parser.error("start must be on or before as-of")
    result = acquire(args.ticker, args.start, args.as_of, Path(__file__).resolve().parents[1], args.report_limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
