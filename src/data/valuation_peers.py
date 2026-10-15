"""Comparable P/B and annual P/E, with dated, independently matched quotes."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, date
import json
import statistics
from src.analysis.valuation import number
from src.data.providers import download, fetch_daily_prices, fetch_kbs_prices, fetch_vietcap_prices, VN_TIME, DataSourceError
from src.data.research import KBS_BASE


def collect_valuation_peers(industry, as_of, price_date, root, run_id, *, period_policy='exact'):
    if period_policy not in {'exact','exact_balance','prior_balance_90_days'}:raise ValueError('Unknown peer period policy')
    near=period_policy=='prior_balance_90_days'
    balance_only=near or period_policy=='exact_balance'
    result={"available":False,"peers":[],"excluded":[],"sources":[],"median_pb":None,
            "median_pe":None,"pb_sample_size":0,"pe_sample_size":0,"pe_available":False,
            "sector_name":industry.get("name"),"period_end":industry.get("period_end"),"scope":industry.get("scope"),"reason":"Chưa đủ hai P/B đồng kỳ có giá đối chiếu và số CP snapshot."}
    if as_of!=datetime.now(VN_TIME).date() or not price_date:return result
    folder=root/"data/raw/valuation_peers";folder.mkdir(parents=True,exist_ok=True)
    def collect(peer):
        ticker=peer["ticker"];sources=[];quote_inputs=[]
        period=peer["financial"]["periods"][0]
        gap=(date.fromisoformat(industry['period_end'])-date.fromisoformat(period['period_end'])).days
        if (not (0<=gap<=90) if near else gap!=0) or period["scope"]!=industry.get("scope"):
            raise DataSourceError("Peer financial period/scope mismatch")
        url=f"{KBS_BASE}/stockinfo/profile/{ticker}?l=1"
        raw=download(url,timeout=15);profile=json.loads(raw)
        if profile.get("SB")!=ticker:raise DataSourceError("Peer profile symbol mismatch")
        shares=profile.get("KLCPLH")
        if not number(shares,True):raise DataSourceError("Peer shares missing")
        sid=f"VAL_PROFILE_{ticker}_{run_id}"
        (folder/f"{sid}.json").write_bytes(raw)
        sources.append({"source_id":sid,"url_or_file":url,"retrieved_at":datetime.now(VN_TIME).isoformat(),"page_or_table":"profile.KLCPLH","notes":"Current shares; annual equity held constant as an explicit scenario assumption"})
        start=as_of-timedelta(days=45)
        quotes=[]
        for options in [[("Yahoo",fetch_daily_prices),("Vietcap",fetch_vietcap_prices)],[("KBS",fetch_kbs_prices)]]:
            q=None
            for provider,fetch in options:
                try:response=fetch(ticker,start,as_of)
                except DataSourceError:continue
                q=next((r for r in response['rows'] if r['date']==price_date and number(r.get('close'),True)),None)
                if q:break
            if not q:raise DataSourceError("Peer closing price missing on target date")
            quotes.append(q["close"])
            qs=f"VAL_{provider.upper()}_{ticker}_{run_id}";(folder/f"{qs}.json").write_bytes(response["raw"])
            quote_inputs.append({"source_id":qs,"value":q["close"],"unit":"VND/share","period":price_date,"provider":provider})
            sources.append({"source_id":qs,"url_or_file":response["url"],"retrieved_at":response["retrieved_at"],"page_or_table":price_date,"notes":"Only closing price on this date cross-checked; not full adjustment history; request="+str(response.get("request_payload",{}))})
        if abs(quotes[0]/quotes[1]-1)>.001:raise DataSourceError("Peer close mismatch between independent provider and KBS")
        fields=period["fields"]
        e=fields.get("equity",{}).get("value");n=fields.get("non_controlling_equity",{}).get("value")
        capital=e if period["scope"] in {"parent","separate"} else e-n if number(e) and number(n) else None
        profit=fields.get("parent_profit",{}).get("value")
        if profit is None and period["scope"] in {"parent","separate"}:profit=fields.get("net_profit",{}).get("value")
        metrics={m["key"]:m["value"] for m in peer["financial"]["metrics"]}
        return {"ticker":ticker,"price_date":price_date,"shares_snapshot":as_of.isoformat(),"equity_period":period["period_end"],
                "pb":quotes[0]/(capital/shares) if number(capital,True) else None,
                "pe":quotes[0]/(profit/shares) if not balance_only and number(profit,True) else None,
                "period_gap_days":gap,
                "roe":metrics.get("roe"),"profit_growth":metrics.get("net_profit_growth"),"debt_equity":metrics.get("debt_equity"),
                "pe_basis":"LNST cổ đông mẹ năm / CP snapshot; không phải TTM hoặc dự phóng",
                "inputs":[fields[k] for k in ["equity","non_controlling_equity","parent_profit","net_profit"] if k in fields]+[{"source_id":sid,"value":shares,"unit":"shares","period":as_of.isoformat()}]+quote_inputs,"sources":sources}
    def safe(peer):
        try:return collect(peer),None
        except (DataSourceError,ValueError,KeyError,TypeError,OSError) as exc:return None,{"ticker":peer["ticker"],"reason":str(exc)}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row,error in pool.map(safe,industry.get("peers",[])):
            if row:
                result["sources"].extend(row.pop("sources"));result["peers"].append(row)
            if error:result["excluded"].append(error)
    values=[p["pb"] for p in result["peers"] if p["pb"] is not None]
    earnings=[p["pe"] for p in result["peers"] if p["pe"] is not None]
    result.update(pb_sample_size=len(values),pe_sample_size=len(earnings),pe_available=len(earnings)>=2,
                  median_pe=statistics.median(earnings) if len(earnings)>=2 else None,
                  price_date=price_date,
                  pe_reason="" if len(earnings)>=2 else "Chưa đủ hai P/E lợi nhuận mẹ dương, đồng kỳ và có giá đối chiếu.")
    if len(values)>=2:
        result.update(available=True,reason="",median_pb=statistics.median(values),sample_size=len(values),price_date=price_date,
                      explanation=f"Trung vị {len(values)} mã khác trong mẫu {industry.get('name')}, giá {price_date}; vốn năm quy đổi trên CP snapshot. Không phải chỉ số P/B toàn ngành.")
    if period_policy=='exact_balance':
        result.update(period_policy=period_policy,explanation=f"P/B từ số dư vốn cổ đông mẹ cùng ngày {industry.get('period_end')}, cùng phạm vi; giá {price_date}, CP snapshot {as_of}. Không sử dụng lợi nhuận quý/lũy kế để tính P/E.")
    if near:
        result.update(period_policy=period_policy,usable_in_primary=False,
                      explanation='P/B tham khảo từ số dư vốn mẹ trước ngày cuối kỳ mã phân tích tối đa 90 ngày; giá cùng ngày, CP snapshot cùng ngày chốt. Không phải mẫu đồng kỳ, giá mục tiêu, RNAV hay khuyến nghị. Không dùng P/E từ các năm lệch kỳ.')
    return result
