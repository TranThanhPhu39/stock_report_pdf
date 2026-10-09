"""Compute peer P/B from dated financials and independently matched daily quotes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import statistics
from src.analysis.valuation import number
from src.data.providers import download, fetch_daily_prices, fetch_kbs_prices, VN_TIME, DataSourceError
from src.data.research import KBS_BASE


def collect_valuation_peers(industry, as_of, price_date, root, run_id):
    result={"available":False,"peers":[],"excluded":[],"sources":[],"median_pb":None,
            "sector_name":industry.get("name"),"reason":"Chưa đủ hai P/B đồng kỳ có giá đối chiếu và số CP snapshot."}
    if as_of!=datetime.now(VN_TIME).date() or not price_date:return result
    folder=root/"data/raw/valuation_peers";folder.mkdir(parents=True,exist_ok=True)
    def collect(peer):
        ticker=peer["ticker"];sources=[];quote_inputs=[]
        period=peer["financial"]["periods"][0]
        if period["period_end"]!=industry.get("period_end") or period["scope"]!=industry.get("scope"):
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
        for provider,fetch in [("Yahoo",fetch_daily_prices),("KBS",fetch_kbs_prices)]:
            response=fetch(ticker,start,as_of);q=next((r for r in response["rows"] if r["date"]==price_date),None)
            if not q or not number(q["close"],True):raise DataSourceError("Peer closing price missing on target date")
            quotes.append(q["close"])
            qs=f"VAL_{provider.upper()}_{ticker}_{run_id}";(folder/f"{qs}.json").write_bytes(response["raw"])
            quote_inputs.append({"source_id":qs,"value":q["close"],"unit":"VND/share","period":price_date,"provider":provider})
            sources.append({"source_id":qs,"url_or_file":response["url"],"retrieved_at":response["retrieved_at"],"page_or_table":price_date,"notes":"Only closing price on this date cross-checked; not full adjustment history"})
        if abs(quotes[0]/quotes[1]-1)>.001:raise DataSourceError("Peer close mismatch between Yahoo and KBS")
        fields=period["fields"]
        e=fields.get("equity",{}).get("value");n=fields.get("non_controlling_equity",{}).get("value")
        capital=e if period["scope"] in {"parent","separate"} else e-n if number(e) and number(n) else None
        profit=fields.get("parent_profit",{}).get("value")
        return {"ticker":ticker,"price_date":price_date,"shares_snapshot":as_of.isoformat(),"equity_period":period["period_end"],
                "pb":quotes[0]/(capital/shares) if number(capital,True) else None,
                "pe":quotes[0]/(profit/shares) if number(profit,True) else None,
                "roe":next((m["value"] for m in peer["financial"]["metrics"] if m["key"]=="roe"),None),
                "inputs":[fields[k] for k in ["equity","non_controlling_equity","parent_profit"] if k in fields]+[{"source_id":sid,"value":shares,"unit":"shares","period":as_of.isoformat()}]+quote_inputs,"sources":sources}
    def safe(peer):
        try:return collect(peer),None
        except (DataSourceError,ValueError,KeyError,TypeError,OSError) as exc:return None,{"ticker":peer["ticker"],"reason":str(exc)}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row,error in pool.map(safe,industry.get("peers",[])):
            if row:
                result["sources"].extend(row.pop("sources"));result["peers"].append(row)
            if error:result["excluded"].append(error)
    values=[p["pb"] for p in result["peers"] if p["pb"] is not None]
    if len(values)>=2:
        result.update(available=True,reason="",median_pb=statistics.median(values),sample_size=len(values),price_date=price_date,
                      explanation=f"Trung vị {len(values)} mã khác trong mẫu {industry.get('name')}, giá {price_date}; vốn năm quy đổi trên CP snapshot. Không phải chỉ số P/B toàn ngành.")
    return result
