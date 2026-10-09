"""Pinned public reference data and selectively downloaded original annual reports.

Parquet lacks publication, scope and unit metadata. Never promote it into the
primary financial/valuation model merely because its numbers look plausible.
"""
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from src.data.providers import DataSourceError, VN_TIME, download

REPO = "Tumiqa/vn-annual-report-miner"
ZENODO = "https://zenodo.org/records/20949551"
CATALOG_RELEASE = date(2026, 6, 27)
TABLES = {"balance": "balance_sheet", "income": "income_statement", "cashflow": "cash_flow"}
LABELS = {"assets": "Tổng tài sản", "liabilities": "Nợ phải trả", "equity": "Vốn chủ sở hữu",
          "revenue": "Doanh thu thuần", "net_profit": "LNST", "cfo": "Dòng tiền kinh doanh"}
ITEMS = {
    "balance": {"assets": ["bs_tong_tai_san"], "liabilities": ["bs_no_phai_tra", "bs_tong_no_phai_tra"],
                "equity": ["bs_von_chu_so_huu_4d280b22", "bs_von_chu_so_huu_6cda78ae", "bs_von_va_cac_quy"]},
    "income": {"revenue": ["is_doanh_so_thuan", "is_doanh_thu_thuan", "is_doanh_thu_hoat_dong"],
               "net_profit": ["is_lai_lo_thuan_sau_thue", "is_loi_nhuan_sau_thue"]},
    "cashflow": {"cfo": ["cf_luu_chuyen_tien_thuan_tu_cac_hoat_dong_san_xuat_kinh_doanh",
                          "cf_luu_chuyen_tien_thuan_tu_hoat_dong_kinh_doanh",
                          "cf_luu_chuyen_thuan_tu_hoat_dong_kinh_doanh_chung_khoan"]},
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def cached_file(url, path, available_at, max_size=15_000_000):
    """24h cache, bound to a pinned URL, with integrity validation on every reuse."""
    meta_path = path.with_suffix(path.suffix + ".json")
    if path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf8"))
            raw = path.read_bytes()
            age = datetime.now(VN_TIME) - datetime.fromisoformat(meta["retrieved_at"])
            if meta["url"] == url and timedelta(0) <= age < timedelta(hours=24) and len(raw) <= max_size and sha256(raw) == meta["sha256"]:
                return raw, meta
        except (ValueError, KeyError, TypeError, OSError):
            pass
    raw = download(url, timeout=30)
    if len(raw) > max_size:
        raise DataSourceError("Reference file exceeds the size limit")
    meta = {"url": url, "retrieved_at": datetime.now(VN_TIME).isoformat(), "sha256": sha256(raw), "version_available_at": available_at}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(raw)
    temp.replace(path)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf8")
    return raw, meta


def parse_catalog(raw, ticker, as_of):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"record_id", "ticker_folder", "ticker_file", "year_full", "relative_path", "sha256", "archive_period", "file_size_bytes", "status"}
    if not required.issubset(reader.fieldnames or []):
        raise DataSourceError("Annual report catalog schema mismatch")
    reports = []
    for row in reader:
        if row["ticker_file"] != ticker or row["ticker_folder"] != ticker or row["status"] != "ok":
            continue
        try:
            year, size = int(row["year_full"]), int(row["file_size_bytes"])
        except ValueError:
            continue
        if year >= as_of.year or size <= 0 or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            continue
        if row.get("document_type") != "annual_report":
            continue
        reports.append({**row, "year": year, "file_size_bytes": size, "publication_at": None})
    return sorted(reports, key=lambda r: (r["year"], r["record_id"]), reverse=True)


def parse_parquet(frame, ticker, kind, as_of, source_id):
    required = {"ticker", "year", "exchange", "statement", "item_code", "item_name", "value", "source_file", "source_sheet"}
    if not required.issubset(frame.columns):
        raise DataSourceError("Reference financial schema mismatch")
    frame = frame[frame["ticker"] == ticker].copy()
    if frame.duplicated(["ticker", "year", "item_code"]).any():
        raise DataSourceError("Duplicate reference financial keys")
    result = []
    for year, group in frame.groupby("year"):
        if not float(year).is_integer() or int(year) >= as_of.year:
            continue
        fields = {}
        for key, codes in ITEMS[kind].items():
            selected = group[group["item_code"].isin(codes)]
            values = []
            for _, row in selected.iterrows():
                try:
                    value = float(row["value"])
                except (ValueError, TypeError):
                    continue
                if math.isfinite(value):
                    values.append((value, row))
            # Two names for equity sometimes coexist; accept only equal values.
            if values and all(abs(v[0] - values[0][0]) <= max(1, abs(values[0][0])*1e-10) for v in values):
                value, row = values[0]
                fields[key] = {"value": value, "unit": "source_value", "source_id": source_id,
                               "source_field": row["item_code"], "source_label": row["item_name"],
                               "source_file": str(row["source_file"]) if pd.notna(row["source_file"]) else None,
                               "source_sheet": str(row["source_sheet"]) if pd.notna(row["source_sheet"]) else None,
                               "period": str(int(year)), "published_at": None, "statement_scope": "unknown"}
        if fields:
            result.append({"year": int(year), "kind": kind, "fields": fields, "scope": "unknown", "published_at": None})
    return sorted(result, key=lambda r: r["year"], reverse=True)


def compare_reference(records, financial):
    """Value comparisons only: neither independent-origin nor scope certification."""
    primary = {p["year"]: p for p in financial.get("periods", [])}
    checks = []
    for record in records:
        period = primary.get(record["year"])
        if not period:
            continue
        for key, field in record["fields"].items():
            target = period["fields"].get(key)
            if target is None or target.get("value") is None:
                continue
            actual, other = target["value"], field["value"]
            deviation = abs(actual-other)/max(abs(actual), 1)
            checks.append({"year": record["year"], "metric": key, "label": LABELS[key],
                           "primary_vnd": actual, "reference_raw": other, "relative_difference": deviation,
                           "match": deviation <= .001, "source_id": field["source_id"],
                           "reference_item": field["source_field"], "scope_certified": False})
    return checks


class RemoteZip(io.RawIOBase):
    """Seek a remote ZIP with bounded, strictly validated HTTP range requests."""
    BLOCK = 1024*1024

    def __init__(self, url):
        self.url, self.position, self.blocks = url, 0, {}
        raw, header = self._request("bytes=-65536")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", header)
        if not match:
            raise DataSourceError("Server did not disclose archive length")
        self.length = int(match[3])
        self.tail_start, self.tail = int(match[1]), raw

    def _request(self, range_value):
        last_error=None
        for _ in range(3):
            try:
                return self._request_once(range_value)
            except DataSourceError as exc:
                last_error=exc
        raise last_error

    def _request_once(self, range_value):
        request = Request(self.url, headers={"Range": range_value, "Accept-Encoding": "identity", "User-Agent": "StockInsight/0.1"})
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 206:
                    raise DataSourceError("Server ignored Range; refusing whole archive download")
                header = response.headers.get("Content-Range", "")
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", header)
                if not match or int(match[2])-int(match[1])+1 > self.BLOCK:
                    raise DataSourceError("Invalid archive range response")
                raw = response.read(self.BLOCK+1)
                if len(raw) != int(match[2])-int(match[1])+1:
                    raise DataSourceError(f"Truncated archive range: {range_value}; {header}; received {len(raw)} bytes")
                return raw, header
        except OSError as exc:
            raise DataSourceError(f"Cannot read annual-report archive: {exc}") from exc

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position+offset if whence == 1 else self.length+offset
        if self.position < 0:
            raise ValueError("Negative archive offset")
        return self.position

    def read(self, size=-1):
        size = min(self.length-self.position, size if size >= 0 else self.length-self.position)
        if size < 0 or size > 45_000_000:
            raise DataSourceError("Unbounded archive read refused")
        pieces = []
        while size:
            if self.position >= self.tail_start:
                n = min(size, self.length-self.position)
                pieces.append(self.tail[self.position-self.tail_start:self.position-self.tail_start+n])
            else:
                block = self.position//self.BLOCK
                start, end = block*self.BLOCK, min((block+1)*self.BLOCK, self.length)-1
                if block not in self.blocks:
                    raw, header = self._request(f"bytes={start}-{end}")
                    if header != f"bytes {start}-{end}/{self.length}":
                        raise DataSourceError("Archive range offset mismatch")
                    self.blocks[block] = raw
                n = min(size, end-self.position+1)
                pieces.append(self.blocks[block][self.position-start:self.position-start+n])
            self.position += n
            size -= n
        return b"".join(pieces)


def fetch_report(report, root):
    if report["file_size_bytes"] > 40_000_000:
        raise DataSourceError("Report exceeds 40MB selective-download limit")
    path = root/"data/raw/reference_miner/pdfs"/f"{report['ticker_file']}_{report['year']}_{report['sha256'][:12]}.pdf"
    meta_path=path.with_suffix(".json")
    if path.exists():
        raw = path.read_bytes()
        if len(raw) == report["file_size_bytes"] and sha256(raw) == report["sha256"]:
            try:
                meta=json.loads(meta_path.read_text(encoding="utf8")) if meta_path.exists() else {}
                if not isinstance(meta,dict):meta={}
            except (ValueError,OSError):
                meta={}
            report.update({"downloaded_at":meta.get("downloaded_at"),"download_url":meta.get("download_url"),"retrieval_mode":"local_cache_checked_sha256"})
            return path
    if report["archive_period"] not in {"2000_2005", "2006_2010", "2011_2015", "2016_2020", "2021_2025"}:
        raise DataSourceError("Unknown annual-report archive")
    url = f"https://zenodo.org/api/records/20949551/files/vn_bctn_{report['archive_period']}.zip/content"
    raw=None
    mirror=f"https://cafef1.mediacdn.vn/Images/Uploaded/DuLieuDownload/BCTC/{report['file_name']}" if re.fullmatch(r"[A-Za-z0-9_.-]+\.pdf",report.get("file_name","")) else None
    if mirror:
        try:
            request=Request(mirror,headers={"User-Agent":"Mozilla/5.0 StockInsight/0.1"})
            with urlopen(request,timeout=15) as response:candidate=response.read(40_000_001)
            if len(candidate)==report["file_size_bytes"] and candidate.startswith(b"%PDF-") and sha256(candidate)==report["sha256"]:
                raw=candidate
                report["download_url"]=mirror
                report["retrieval_mode"]="catalog_hash_verified_mirror"
        except OSError:
            pass
    if raw is None:
        raw=read_zip_report(report,url)
        report["download_url"]=url
        report["retrieval_mode"]="selective_zip_download"
    if not raw.startswith(b"%PDF-") or sha256(raw) != report["sha256"]:
        raise DataSourceError("Annual-report PDF checksum mismatch")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(raw)
    temp.replace(path)
    report["downloaded_at"]=datetime.now(VN_TIME).isoformat()
    meta_path.write_text(json.dumps({k:report[k] for k in ["downloaded_at","download_url","retrieval_mode"]}),encoding="utf8")
    return path


def read_zip_report(report,url):
    with zipfile.ZipFile(RemoteZip(url)) as archive:
        relative = report["relative_path"].replace("\\", "/")
        entries = [p for p in archive.namelist() if p.replace("\\", "/").endswith("/"+relative) or p.replace("\\", "/") == relative]
        if len(entries) != 1:
            raise DataSourceError("Report ZIP path missing or ambiguous")
        info = archive.getinfo(entries[0])
        if info.file_size != report["file_size_bytes"]:
            raise DataSourceError("Report size disagrees with catalog")
        raw = archive.read(info)
    return raw


def inspect_pdf(path):
    import pymupdf
    with pymupdf.open(path) as doc:
        pages = [page.get_text() for page in doc]
    text_pages=sum(len(p.strip()) >= 80 for p in pages)
    status="scan_requires_ocr" if text_pages/max(len(pages),1)<.1 else "mixed_requires_ocr" if text_pages/max(len(pages),1)<.8 else "text_available"
    return {"pages": len(pages), "text_pages": text_pages, "status":status,
            "scope_certified": False, "publication_at": None}


def collect_reference(ticker, as_of, financial, company, root, run_id):
    result = {"available": False, "records": [], "checks": [], "reports": [], "sources": [], "errors": [], "warnings": [], "used_in_primary_analysis": False}
    config_path = root/"config/reference_sources.json"
    if not config_path.exists():
        return result
    config = json.loads(config_path.read_text(encoding="utf8"))
    commit, available_at = config["commit"], config["available_at"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid pinned reference commit")
    result["commit"] = commit
    result["version_available_at"] = available_at
    result["warnings"] = ["Parquet tham khảo chưa có ngày công bố, đơn vị và phạm vi báo cáo; không tự thay số liệu phân tích/định giá. Khớp giá trị không chứng nhận nguồn độc lập hay phạm vi."]
    if date.fromisoformat(available_at[:10]) > as_of:
        result["warnings"].append("Phiên bản dữ liệu tham khảo được ghi nhận sau ngày phân tích; không sử dụng cho ngày quá khứ.")
        return result
    folder = root/"data/raw/reference_miner"/commit[:12]
    base = f"https://raw.githubusercontent.com/{REPO}/{commit}/"
    def source(source_id, meta, table):
        result["sources"].append({"source_id": source_id, "url_or_file": meta["url"], "retrieved_at": meta["retrieved_at"],
                                  "page_or_table": table, "notes": f"Pinned {commit}; SHA256 {meta['sha256']}; reference only; publication/unit/scope not certified"})
    exchange = {"HOSE": "HSX", "HSX": "HSX", "HNX": "HNX"}.get(company.get("exchange"))
    if exchange:
        for kind, table in TABLES.items():
            try:
                url = base+f"src/arminer/data/bctc_data/{table}/{exchange}.parquet"
                raw, meta = cached_file(url, folder/f"{exchange}_{table}.parquet", available_at)
                sid = f"MINER_{kind}_{run_id}"
                records = parse_parquet(pd.read_parquet(io.BytesIO(raw)), ticker, kind, as_of, sid)
                result["records"].extend(records)
                source(sid, meta, f"{exchange}/{table}: {ticker}")
            except (DataSourceError, ValueError, OSError, ImportError) as exc:
                result["errors"].append({"stage": f"reference_{kind}", "message": str(exc)})
    else:
        result["warnings"].append("Parquet tài chính chỉ có HSX/HNX; không tự gán dữ liệu sàn khác.")
    result["checks"] = compare_reference(result["records"], financial)
    if any(not c["match"] for c in result["checks"]):
        result["warnings"].append("Có chỉ tiêu lệch giữa Parquet và nguồn phân tích; giữ nguyên hai giá trị để kiểm tra, không tự ghi đè.")
    if as_of >= CATALOG_RELEASE:
        try:
            raw, meta = cached_file(base+"data/zenodo_catalog/file_index_full.csv", folder/"file_index_full.csv", available_at)
            reports = parse_catalog(raw, ticker, as_of)
            result["reports"] = reports[:5]
            source(f"MINER_catalog_{run_id}", meta, f"Annual-report catalog: {ticker}; original catalog release 2026-06-27")
            if reports:
                latest = result["reports"][0]
                try:
                    path = fetch_report(latest, root)
                    latest["file"] = path.relative_to(root).as_posix()
                    latest["inspection"] = inspect_pdf(path)
                    result["sources"].append({"source_id": f"ZENODO_PDF_{run_id}", "url_or_file": latest.get("download_url") or ZENODO,
                                              "retrieved_at": datetime.now(VN_TIME).isoformat(), "page_or_table": latest["relative_path"],
                                              "notes": f"{latest['retrieval_mode']}; downloaded_at={latest.get('downloaded_at')}; catalog={ZENODO}; SHA256 verified {latest['sha256']}; report year {latest['year']}; original publication/scope not certified"})
                except (DataSourceError, ValueError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
                    result["errors"].append({"stage": "reference_pdf", "message": str(exc)})
        except (DataSourceError, ValueError, OSError) as exc:
            result["errors"].append({"stage": "reference_catalog", "message": str(exc)})
    result["records"].sort(key=lambda r: (r["year"], r["kind"]), reverse=True)
    result["available"] = bool(result["records"] or result["reports"])
    result["warnings"].append("Năm trong danh mục không phải ngày công bố. PDF kiểm tra checksum và khả năng đọc text; chưa tự chứng nhận số liệu/kỳ/phạm vi. Báo cáo lịch sử chưa bao gồm cập nhật 2026.")
    return result
