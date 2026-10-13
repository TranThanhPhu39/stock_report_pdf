"""Application pipeline: always acquire source data before displaying a new result."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
import re
import subprocess

from src.data.acquisition import acquire, write_json
from src.data.providers import completed_day_cutoff
from src.data.research import collect_research, collect_peer_news
from src.data.issuer_pdf import extract_hpg_interim
from src.data.shs_issuer import collect_shs_issuer
from src.data.ssi_issuer import collect_ssi_issuer
from src.data.bank_issuer import collect_bank_issuer, BANK_NAMES
from src.data.vnfinancialdata_provider import collect_vnfinancialdata
from src.data.quality import verify_financials
from src.models import AnalysisRequest
from src.analysis.market import analyze_market
from src.analysis.financial import analyze_financials
from src.analysis.valuation import analyze_valuation
from src.analysis.conclusion import build_conclusion
from src.analysis.recommendation import build_recommendation
from src.data.context import collect_context
from src.data.reference_miner import collect_reference
from src.analysis.context import integrated_thesis
from src.data.valuation_peers import collect_valuation_peers
from src.analysis.ai_commentary import generate_commentary
from src.data.context_news import collect_context_news
from src.data.market_context import collect_market_context
from src.data.sotp_provider import collect_sotp
from src.analysis.investment_valuation import investment_valuation
from src.analysis.research_narrative import research_narrative
from src.data.quarterly import collect_quarterly
from src.analysis.trailing import trailing_from_interim
from src.analysis.comparison import compare_results
from src.analysis.decision import decision_summary
from src.data.ssi_interim import collect_ssi_interim
from src.data.tch_issuer import collect_tch_issuer
from src.data.near_period_pb import collect_near_period_pb


def run_analysis(ticker: str, start: date, as_of: date, root: Path | None = None, *, mode="full", sections=None, target_pb=1.5,
                 target_pe=12.0,cost_of_equity=.115,terminal_growth=.035,forecast_growth=.07,wacc=.10,tax_rate=.20,use_ai=False,ai_key=None,ai_model=None,comparison_tickers=None) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    if start > completed_day_cutoff(as_of):
        raise ValueError("Ngày bắt đầu phải nằm trước hoặc trong ngày giá đã hoàn tất.")
    root = root or Path(__file__).resolve().parents[1]
    request = AnalysisRequest(ticker, start, as_of, mode=mode, target_pb=target_pb,target_pe=target_pe,cost_of_equity=cost_of_equity,
                              terminal_growth=terminal_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate,use_ai=use_ai,
                              comparison_tickers=comparison_tickers or [],**({"sections":sections} if sections is not None else {}))
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
    market=analyze_market(rows,research["quote_check"])
    company={**research["company"],"name":acquisition["prices"].get("company_name") if acquisition["prices"] else ticker}
    reference=collect_reference(ticker,as_of,financial,company,root,acquisition["run_id"])
    research["sources"].extend(reference["sources"])
    research["warnings"].extend(reference["warnings"])
    issuer=collect_bank_issuer(ticker,as_of,root,acquisition["run_id"]) if ticker in BANK_NAMES else collect_ssi_issuer(ticker,as_of,root,acquisition["run_id"]) if ticker=="SSI" else collect_tch_issuer(ticker,as_of,root,acquisition["run_id"]) if ticker=='TCH' else collect_shs_issuer(ticker,as_of,reference,root,acquisition["run_id"])
    research["sources"].extend(issuer["sources"])
    research["warnings"].extend(issuer["warnings"])
    research["errors"].extend(issuer["errors"])
    if issuer["available"]:
        replaced={r["year"] for r in issuer["records"]}
        financial=analyze_financials([r for r in research["financial_records"] if r["year"] not in replaced]+issuer["records"])
        company["name"]=issuer.get('name') or (BANK_NAMES[ticker] if ticker in BANK_NAMES else "Công ty Cổ phần Chứng khoán SSI" if ticker=="SSI" else "Công ty Cổ phần Chứng khoán Sài Gòn - Hà Nội")
        if ticker=='TCH':
            acquisition['financial_documents'].append(dict(title='TCH: BCTC hợp nhất kiểm toán niên độ 01/04/2025–31/03/2026',file=issuer['file']))
        if issuer.get("interim"):
            interim=issuer["interim"]
        if ticker in BANK_NAMES:
            acquisition["financial_documents"].append(dict(title=f"{ticker}: BCTC hợp nhất năm {issuer['year']} đã xác minh",file=issuer["file"]))
            if interim:
                acquisition["financial_documents"].append(dict(title=f"{ticker}: BCTC hợp nhất bán niên {interim['period_end']}",file=interim["file"]))
    financial_check=verify_financials(ticker,financial,interim,root)
    if issuer["checks"]:
        financial_check["checks"].extend(issuer["checks"])
        financial_check["status"]="matched_selected_fields" if all(c["match"] for c in financial_check["checks"]) else "mismatch"
    if financial_check["status"]=="mismatch":
        research["errors"].append({"stage":"financial_check","message":"Chỉ tiêu không khớp tài liệu gốc; chặn phân tích tài chính và định giá."})
        financial={**financial,"periods":[],"metrics":[]}
    from src.analysis.bank_metrics import attach_bank_metrics
    financial=attach_bank_metrics(financial,issuer.get('bank_ratios') if financial_check['status']!='mismatch' else None,
                                  interim if financial_check['status']!='mismatch' else None,as_of)
    quarterly=collect_quarterly(ticker,as_of,financial,root,acquisition['run_id'])
    research['sources'].extend(quarterly['sources'])
    research['warnings'].extend(quarterly['warnings'])
    research['warnings'].extend('Dữ liệu quý: '+e['message'] for e in quarterly['errors'])
    if ticker=='SSI' and financial_check['status']!='mismatch':
        reviewed=collect_ssi_interim(as_of,financial,quarterly,root,acquisition['run_id'])
        research['sources'].extend(reviewed['sources'])
        research['warnings'].extend('Bán niên SSI: '+e['message'] for e in reviewed['errors'])
        if reviewed['available']:
            interim=reviewed['interim']
            acquisition['financial_documents'].append(dict(title=f"SSI: BCTC hợp nhất bán niên {interim['period_end']} đã đối chiếu",file=interim['file']))
    if financial.get('industry_group')!='bank' and not financial.get('ttm',{}).get('available'):
        financial['ttm']=trailing_from_interim(financial,interim if financial_check['status']!='mismatch' else None,as_of)
    vnf=collect_vnfinancialdata(ticker,as_of,company,financial,root,acquisition["run_id"])
    research["sources"].extend(vnf["sources"])
    # A supplementary dataset failure does not discard valid primary statements.
    research["warnings"].extend(vnf["warnings"])
    context=collect_context(ticker,as_of,financial,root,acquisition["run_id"])
    benchmark=collect_valuation_peers(context["industry"],as_of,market.get("latest_date") if market else None,root,acquisition["run_id"])
    research["sources"].extend(benchmark["sources"])
    valuation=analyze_valuation(financial,market,company,research["quote_check"],as_of,target_pb,target_pe=target_pe,
                                discount_rate=cost_of_equity,perpetual_growth=terminal_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate,industry_benchmark=benchmark)
    conclusion=build_conclusion(financial,market,valuation,research["quote_check"],interim)
    sotp=collect_sotp(ticker,as_of,company,root,acquisition["run_id"])
    valuation["sotp"]=sotp
    valuation["benchmark"]=benchmark
    valuation["primary"]=investment_valuation(financial,market,valuation,benchmark,sotp)
    near_pb=collect_near_period_pb(ticker,as_of,financial,context['industry'],valuation,market,research['quote_check'],root,acquisition['run_id']) if not valuation['primary']['available'] else {'available':False,'sources':[]}
    valuation['near_period_pb']=near_pb
    research['sources'].extend(near_pb['sources'])
    research["sources"].extend(sotp["sources"])
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        news_future=pool.submit(collect_context_news,ticker,as_of,context["industry"],financial,root,acquisition["run_id"])
        market_future=pool.submit(collect_market_context,as_of,root,acquisition["run_id"])
        context_news,market_context=news_future.result(),market_future.result()
    research["sources"].extend(context_news["sources"]+market_context["sources"])
    narrative=research_narrative(context["macro"],context["industry"],financial,market_context,context_news)
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
              "reference":reference,"vnfinancialdata":vnf,"issuer_financials":issuer,"quarterly":quarterly,"context_news":context_news,"market_context":market_context,"research_narrative":narrative,"quality":{"price_check":research["quote_check"],"financial_check":financial_check,"warnings":acquisition.get("warnings",[])+research["warnings"]+financial["errors"]},
              "errors":acquisition["errors"]+research["errors"],"financial_metrics_status":"analyzed" if financial["metrics"] else "unavailable",
              "sources":research["sources"],"status":"partial" if acquisition["errors"] or research["errors"] or (acquisition["prices"] and acquisition["prices"].get("coverage",{}).get("start_gap_days",0)>7) or research["quote_check"]["status"]!="matched" or not financial["metrics"] or not context["macro"].get("available") or not context["industry"].get("comparisons") or (financial["periods"] and financial["periods"][0]["year"]<as_of.year-1) else "analyzed"}
    import json
    existing_sources = root / "outputs/runs" / acquisition["run_id"] / "sources.json"
    result["sources"] = json.loads(existing_sources.read_text(encoding="utf-8")) + research["sources"]
    result["recommendation"]=build_recommendation(result)
    result['decision_summary']=decision_summary(result)
    compared=[];comparison_errors=[]
    for symbol in request.comparison_tickers:
        try:
            child=run_analysis(symbol,start,as_of,root,mode=mode,sections=sections,
                               target_pb=target_pb,target_pe=target_pe,cost_of_equity=cost_of_equity,
                               terminal_growth=terminal_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate)
            compared.append(child)
            result['sources'].extend(child['sources'])
        except (ValueError,OSError,RuntimeError) as exc:
            comparison_errors.append(dict(ticker=symbol,message=str(exc)))
    result['comparison']=compare_results([result]+compared,comparison_errors) if request.comparison_tickers else {'available':False,'rows':[],'errors':[]}
    from src.data.financial_status import financial_status
    result["financial_data_status"]=financial_status(result)
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
