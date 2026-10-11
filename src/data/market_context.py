"""Dated market index and Brent futures context, with explicit instrument units."""
from datetime import datetime,timedelta
import json,math
from urllib.parse import urlencode
from src.data.providers import fetch_vietcap_prices,download,completed_day_cutoff,VN_TIME,DataSourceError
from src.data.acquisition import write_json


def series_summary(rows,as_of):
    rows=sorted([r for r in rows if r["date"]<=completed_day_cutoff(as_of).isoformat()],key=lambda r:r["date"])
    if len({r["date"] for r in rows})!=len(rows):raise DataSourceError("Duplicate context dates")
    if not rows or any(isinstance(r["close"],bool) or not isinstance(r["close"],(int,float)) or not math.isfinite(r["close"]) or r["close"]<=0 for r in rows):raise DataSourceError("Invalid context prices")
    last=rows[-1];c=[r["close"] for r in rows]
    if (as_of-datetime.fromisoformat(last["date"]).date()).days>7:raise DataSourceError("Stale market context")
    ma20=sum(c[-20:])/20 if len(c)>=20 else None;ma50=sum(c[-50:])/50 if len(c)>=50 else None
    change=(c[-1]/c[-21]-1)*100 if len(c)>=21 else None
    trend="Chưa đủ chuỗi để phân loại"
    if change is not None and ma50 is not None:
        trend="Giảm theo quy tắc" if c[-1]<min(ma20,ma50) and change<0 else "Tăng theo quy tắc" if c[-1]>max(ma20,ma50) and change>0 else "Tín hiệu chưa đồng thuận"
    return dict(latest_date=last["date"],latest_close=last["close"],change_20_pct=change,ma20=ma20,ma50=ma50,trend=trend,
                trend_rule="Giảm/tăng khi giá cùng dưới/trên MA20 và MA50, biến động 20 phiên cùng dấu; không phải dự báo.",rows=rows)


def collect_market_context(as_of,root,run_id):
    out={"available":False,"series":[],"sources":[],"errors":[]};folder=root/"data/raw/market_context";folder.mkdir(parents=True,exist_ok=True)
    start=as_of-timedelta(days=150)
    for symbol,label,unit in [("VNINDEX","VN-Index","điểm"),("BZ=F","Brent futures (hợp đồng gần)","USD/thùng")]:
        try:
            if symbol=="VNINDEX":response=fetch_vietcap_prices(symbol,start,as_of);rows=response["rows"]
            else:
                cutoff=completed_day_cutoff(as_of)
                params={"period1":int(datetime.combine(start,datetime.min.time(),VN_TIME).timestamp()),
                        "period2":int(datetime.combine(cutoff+timedelta(days=1),datetime.min.time(),VN_TIME).timestamp()),"interval":"1d"}
                url="https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?"+urlencode(params)
                raw=download(url,timeout=15);p=json.loads(raw)["chart"]["result"][0]
                if p["meta"]["symbol"]!=symbol or p["meta"].get("currency")!="USD":raise DataSourceError("Wrong oil instrument/currency")
                timestamps=p["timestamp"];closes=p["indicators"]["quote"][0]["close"]
                if len(timestamps)!=len(closes):raise DataSourceError("Mismatched oil arrays")
                rows=[dict(date=datetime.fromtimestamp(t,VN_TIME).date().isoformat(),close=c) for t,c in zip(timestamps,closes) if c is not None and start<=datetime.fromtimestamp(t,VN_TIME).date()<=cutoff]
                response={"url":url,"raw":raw,"retrieved_at":datetime.now(VN_TIME).isoformat()}
            summary=series_summary(rows,as_of);sid=f"CTX_{'VNINDEX' if symbol=='VNINDEX' else 'BRENT'}_{run_id}"
            (folder/f"{sid}.json").write_bytes(response["raw"])
            out["series"].append({**summary,"symbol":symbol,"label":label,"unit":unit,"source_id":sid,
                                  "limitation":"Một nguồn chỉ số; chưa chứng nhận xu hướng mọi cổ phiếu hoặc độ rộng thị trường." if symbol=="VNINDEX" else "Hợp đồng gần có chuyển kỳ; không phải giá dầu giao ngay hoặc chi phí đầu vào của riêng doanh nghiệp."})
            out["sources"].append(dict(source_id=sid,url_or_file=response["url"],retrieved_at=response["retrieved_at"],page_or_table=label,notes="Completed sessions; source observations, not independent verification of all history."))
        except Exception as exc:out["errors"].append({"stage":"market_context","message":label+": "+type(exc).__name__})
    run_folder=root/"outputs/runs"/run_id;run_folder.mkdir(parents=True,exist_ok=True)
    out["available"]=bool(out["series"]);write_json(run_folder/"market_context.json",out)
    return out
