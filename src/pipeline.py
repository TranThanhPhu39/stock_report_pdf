"""Application pipeline: always acquire source data before displaying a new result."""

import csv
from datetime import date
from pathlib import Path
import re
import subprocess

from src.data.acquisition import acquire, write_json
from src.data.providers import completed_day_cutoff
from src.data.research import collect_research, collect_peer_news
from src.data.issuer_pdf import extract_hpg_interim
from src.data.quality import verify_financials
from src.models import AnalysisRequest
from src.analysis.market import analyze_market
from src.analysis.financial import analyze_financials
from src.analysis.valuation import analyze_valuation
from src.analysis.conclusion import build_conclusion
from src.data.context import collect_context
from src.data.reference_miner import collect_reference
from src.analysis.context import integrated_thesis
from src.data.valuation_peers import collect_valuation_peers
from src.analysis.ai_commentary import generate_commentary


def run_analysis(ticker: str, start: date, as_of: date, root: Path | None = None, *, mode="full", sections=None, target_pb=1.5,
                 target_pe=12.0,cost_of_equity=.115,terminal_growth=.035,forecast_growth=.07,wacc=.10,tax_rate=.20,use_ai=False,ai_key=None,ai_model=None) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    if start > completed_day_cutoff(as_of):
        raise ValueError("Ngày bắt đầu phải nằm trước hoặc trong ngày giá đã hoàn tất.")
    root = root or Path(__file__).resolve().parents[1]
    request = AnalysisRequest(ticker, start, as_of, mode=mode, target_pb=target_pb,target_pe=target_pe,cost_of_equity=cost_of_equity,
                              terminal_growth=terminal_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate,use_ai=use_ai,
                              **({"sections":sections} if sections is not None else {}))
    # No pre-existing CSV and no manual fetch step required. This calls the network providers.
    acquisition = acquire(ticker, start, as_of, root)
    rows = []
    if acquisition["prices"]:
        with (root / acquisition["prices"]["csv"]).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append({**row, **{key: float(row[key]) for key in ("open", "high", "low", "close")},
                             "adjusted_close":float(row["adjusted_close"]) if row.get("adjusted_close") else None,
                             "volume": int(float(row["volume"]))})
    research = collect_research(ticker, as_of, rows, root, acquisition["run_id"])
    interim=None
    if ticker=="HPG":
        reviewed=next((d for d in acquisition["financial_documents"] if "soát xét" in d["title"].lower()),None)
        if reviewed:
            try:
                interim=extract_hpg_interim(reviewed,root)
                if not interim.get("valid"):
                    research["errors"].append({"stage":"issuer_ocr","message":"OCR chưa đủ kiểm tra; không dùng để kết luận"})
            except (RuntimeError,OSError,ValueError,ImportError,subprocess.SubprocessError) as exc:
                research["errors"].append({"stage":"issuer_ocr","message":str(exc)})
    financial=analyze_financials(research["financial_records"])
    financial_check=verify_financials(ticker,financial,interim,root)
    if financial_check["status"]=="mismatch":
        research["errors"].append({"stage":"financial_check","message":"Chỉ tiêu không khớp tài liệu gốc; chặn phân tích tài chính và định giá."})
        financial={**financial,"periods":[],"metrics":[]}
    market=analyze_market(rows,research["quote_check"])
    company={**research["company"],"name":acquisition["prices"].get("company_name") if acquisition["prices"] else ticker}
    reference=collect_reference(ticker,as_of,financial,company,root,acquisition["run_id"])
    research["sources"].extend(reference["sources"])
    research["warnings"].extend(reference["warnings"])
    context=collect_context(ticker,as_of,financial,root,acquisition["run_id"])
    benchmark=collect_valuation_peers(context["industry"],as_of,market.get("latest_date") if market else None,root,acquisition["run_id"])
    research["sources"].extend(benchmark["sources"])
    valuation=analyze_valuation(financial,market,company,research["quote_check"],as_of,target_pb,target_pe=target_pe,
                                discount_rate=cost_of_equity,perpetual_growth=terminal_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate,industry_benchmark=benchmark)
    conclusion=build_conclusion(financial,market,valuation,research["quote_check"],interim)
    research["sources"].extend(context["sources"])
    research["errors"].extend(context["errors"])
    research["warnings"].extend(context["warnings"])
    peer_tickers=[peer.get("ticker") for peer in context["industry"].get("peers",[])]
    if "news" in request.sections:
        peer_news,peer_sources,peer_errors=collect_peer_news(peer_tickers,as_of,root,acquisition["run_id"])
        research["news"].extend(peer_news)
        research["sources"].extend(peer_sources)
        research["errors"].extend(peer_errors)
        research["news"].sort(key=lambda item:(item["published_at"],item.get("ticker",ticker)),reverse=True)
    conclusion["integrated_thesis"]=integrated_thesis(context["macro"],context["industry"],financial)
    conclusion["summary"]="Đánh giá kết hợp dữ liệu vĩ mô đã công bố, vị trí trong mẫu doanh nghiệp cùng ngành, kết quả kinh doanh và rủi ro giá. Các kênh truyền dẫn là nhận định có điều kiện, không phải quan hệ nhân quả đã định lượng."
    result = {"request": request.to_dict(),
              "acquisition": acquisition, "market": market, "price_rows": rows,
              "company":company,"financial":financial,"interim":interim,"valuation":valuation,"conclusion":conclusion,"news":research["news"],"macro":context["macro"],"industry":context["industry"],
              "reference":reference,"quality":{"price_check":research["quote_check"],"financial_check":financial_check,"warnings":acquisition.get("warnings",[])+research["warnings"]+financial["errors"]},
              "errors":acquisition["errors"]+research["errors"],"financial_metrics_status":"analyzed" if financial["metrics"] else "unavailable",
              "sources":research["sources"],"status":"partial" if acquisition["errors"] or research["errors"] or (acquisition["prices"] and acquisition["prices"].get("coverage",{}).get("start_gap_days",0)>7) or research["quote_check"]["status"]!="matched" or not financial["metrics"] or not context["macro"].get("available") or not context["industry"].get("comparisons") or (financial["periods"] and financial["periods"][0]["year"]<as_of.year-1) else "analyzed"}
    import json
    existing_sources = root / "outputs/runs" / acquisition["run_id"] / "sources.json"
    result["sources"] = json.loads(existing_sources.read_text(encoding="utf-8")) + research["sources"]
    result["ai_commentary"]=generate_commentary(result,key=ai_key,model=ai_model)
    if interim and interim.get("valid"):
        pages_by_source={}
        for field in interim["fields"].values():
            pages_by_source.setdefault(field["source_id"],set()).add(field["page"])
        for source in result["sources"]:
            if source["source_id"] in pages_by_source:
                source["page_or_table"]="OCR statement pages "+", ".join(map(str,sorted(pages_by_source[source["source_id"]])))
    registry=root/"data/metadata/source_registry.csv"
    with registry.open("a",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["source_id","url_or_file","retrieved_at","page_or_table","notes"])
        writer.writerows(research["sources"])
    write_json(existing_sources,result["sources"])
    write_json(root / "outputs/runs" / acquisition["run_id"] / "request.json",request.to_dict())
    write_json(root / "outputs/runs" / acquisition["run_id"] / "analysis.json", result)
    return result
