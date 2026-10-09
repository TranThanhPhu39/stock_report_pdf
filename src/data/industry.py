"""Discover source classifications; compare a dated sample selected by assets."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
import json
import re
from pathlib import Path
from src.data.providers import download,DataSourceError,VN_TIME
from src.data.research import KBS_BASE,financial_url
from src.data.normalize import parse_annual_financials
from src.analysis.financial import analyze_financials

VCI_URL="https://iq.vietcap.com.vn/api/iq-insight-service/v2/company/search-bar?language=1"

def parse_vci_universe(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get("data"),list):raise DataSourceError("Schema phân ngành Vietcap không hợp lệ")
    groups={}
    for company in payload["data"]:
        symbol=company.get("code","")
        if company.get("isIndex") or company.get("floor") not in {"HOSE","HNX","UPCOM"} or not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}",symbol):continue
        for level in [4,3,2]:
            classification=company.get(f"icbLv{level}") or {}
            if not classification.get("code"):continue
            code=str(classification["code"])
            group=groups.setdefault(code,{"code":code,"name":classification["name"],"symbols":set(),"url":VCI_URL,"level":level})
            group["symbols"].add(symbol)
    return [{**group,"symbols":sorted(group["symbols"])} for group in sorted(groups.values(),key=lambda g:g["code"])]

def collect_universe(root,run_id):
    cache=root/"data/processed/icb_universe.json"
    if cache.exists():
        saved=json.loads(cache.read_text(encoding="utf-8"))
        age=(datetime.now(VN_TIME)-datetime.fromisoformat(saved["retrieved_at"])).total_seconds()
        if 0<=age<3600 and saved.get("complete") and saved.get("schema_version")==2:return {**saved,"retrieval_mode":"cache_under_1h"}
    try:
        raw=download(VCI_URL,timeout=20);groups=parse_vci_universe(json.loads(raw))
        if not groups:raise DataSourceError("Phân ngành Vietcap rỗng")
        folder=root/"data/raw/industry";folder.mkdir(parents=True,exist_ok=True);(folder/f"{run_id}_vci_icb.json").write_bytes(raw)
        result={"schema_version":2,"taxonomy":"Vietcap ICB","retrieved_at":datetime.now(VN_TIME).isoformat(),"complete":True,"groups":groups,"errors":[],"retrieval_mode":"downloaded","source_url":VCI_URL}
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        return result
    except (DataSourceError,ValueError,KeyError,TypeError):
        result=collect_kbs_universe(root,run_id);result["taxonomy"]="KBS";return result

def collect_kbs_universe(root,run_id):
    cache=root/"data/processed/industry_universe.json"
    if cache.exists():
        saved=json.loads(cache.read_text(encoding="utf-8"))
        age=(datetime.now(VN_TIME)-datetime.fromisoformat(saved["retrieved_at"])).total_seconds()
        if 0<=age<3600 and saved.get("complete"):return {**saved,"retrieval_mode":"cache_under_1h"}
    folder=root/"data/raw/industry";folder.mkdir(parents=True,exist_ok=True)
    url=f"{KBS_BASE}/sector/all";raw=download(url,timeout=20)
    (folder/f"{run_id}_sectors.json").write_bytes(raw);sectors=json.loads(raw)
    if not isinstance(sectors,list) or not sectors:raise DataSourceError("Không có danh sách ngành")
    groups=[];errors=[]
    def get(sector):
        code=str(sector["code"]);url=f"{KBS_BASE}/sector/stock?code={code}&l=1"
        raw=download(url,timeout=20);(folder/f"{run_id}_sector_{code}.json").write_bytes(raw)
        data=json.loads(raw)
        if not isinstance(data,dict) or not isinstance(data.get("stocks"),list):raise DataSourceError("Schema ngành không hợp lệ")
        return {"code":code,"name":data.get("name") or sector["name"],"symbols":sorted({r["sb"] for r in data["stocks"] if r.get("sb")}),"url":url}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(get,s):s for s in sectors}
        for future in as_completed(futures):
            try:groups.append(future.result())
            except (DataSourceError,ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    result={"retrieved_at":datetime.now(VN_TIME).isoformat(),"complete":not errors,"groups":sorted(groups,key=lambda r:r["code"]),"errors":errors,"retrieval_mode":"downloaded","source_url":url}
    cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def collect_industry(ticker,as_of,financial,root,run_id,max_peers=4):
    result={"available":False,"name":None,"code":None,"members":[],"peers":[],"sources":[],"errors":[],"warnings":[],"excluded":[],"selection":"Tối đa 4 doanh nghiệp khác cùng nhóm nguồn, lớn nhất theo tài sản trong đúng kỳ/phạm vi của mã phân tích; không dùng giá/volume trong phiên."}
    try:universe=collect_universe(root,run_id)
    except (DataSourceError,ValueError,OSError,KeyError,TypeError) as exc:
        result["errors"].append({"stage":"industry_classification","message":str(exc)});return result
    groups=[g for g in universe["groups"] if ticker in g["symbols"]]
    result["coverage"]={"groups":len(universe["groups"]),"symbols":len({s for g in universe["groups"] for s in g["symbols"]}),"classification_complete":universe["complete"]}
    groups.sort(key=lambda g:-(g.get("level") or 4))
    if any(sum((g.get("level") or 4)==level for g in groups)>1 for level in {g.get("level") or 4 for g in groups}):
        result["errors"].append({"stage":"industry_classification","message":"Nguồn có nhiều phân ngành cùng cấp cho một mã; chặn lựa chọn mẫu mơ hồ."});return result
    if not groups:
        result["errors"].append({"stage":"industry_classification","message":"Mã chưa có một phân ngành duy nhất trong nguồn; không tự gán ngành từ tên doanh nghiệp."});return result
    group=groups[0];taxonomy=universe.get("taxonomy","KBS");sid=f"SECTOR_{group['code']}_{run_id}"
    result.update({"available":True,"name":group["name"],"code":group["code"],"taxonomy":taxonomy,"level":group.get("level"),"subsector_name":group["name"],"members":group["symbols"],"classification_snapshot":universe["retrieved_at"],"classification_source_id":sid})
    result["sources"].append({"source_id":sid,"url_or_file":group["url"],"retrieved_at":universe["retrieved_at"],"page_or_table":"sector membership","notes":f"{taxonomy}; {universe['retrieval_mode']}; current classification; ratings/targets/intraday quote fields excluded"})
    result["warnings"].append(f"Phân ngành theo {taxonomy}; khác biệt mô hình kinh doanh/chu kỳ vẫn có thể lớn. Trung vị mẫu không phải chỉ số của toàn ngành.")
    if as_of.isoformat()!=universe["retrieved_at"][:10]:result["warnings"].append("Danh sách ngành hiện tại được dùng cho phân tích quá khứ; có rủi ro thay đổi thành viên/survivorship, không dùng làm backtest.")
    if not financial["periods"]:
        result["errors"].append({"stage":"industry_peers","message":"Mã phân tích chưa có kỳ tài chính hợp lệ để so sánh đồng kỳ."});return result
    target=financial["periods"][0];result["period_end"]=target["period_end"];result["scope"]=target["scope"]
    folder=root/"data/raw/industry";folder.mkdir(parents=True,exist_ok=True)
    def fetch(symbol,kind):
        url=financial_url(symbol,kind);raw=download(url,timeout=15);source_id=f"PEER_{symbol}_{kind}_{run_id}"
        (folder/f"{source_id}.json").write_bytes(raw);issues=[]
        records=parse_annual_financials(json.loads(raw),kind,as_of,source_id,issues)
        source={"source_id":source_id,"url_or_file":url,"retrieved_at":datetime.now(VN_TIME).isoformat(),"page_or_table":f"{symbol} {kind}","notes":"KBS annual peer snapshot; period and scope checked; not independently verified"}
        return records,source,issues
    candidates=[];balance_cache={}
    for comparison_group in groups:
        candidates=[];result["excluded"]=[]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures={pool.submit(fetch,s,"balance"):s for s in comparison_group["symbols"] if s!=ticker and s not in balance_cache}
            for future in as_completed(futures):
                symbol=futures[future]
                try:balance_cache[symbol]=future.result()
                except (DataSourceError,ValueError,KeyError,TypeError) as exc:balance_cache[symbol]=str(exc)
        for symbol in comparison_group["symbols"]:
            if symbol==ticker:continue
            data=balance_cache[symbol]
            if isinstance(data,str):result["excluded"].append({"ticker":symbol,"reason":data});continue
            records,source,issues=data;valid=analyze_financials(records)
            period=next((p for p in valid["periods"] if p["period_end"]==target["period_end"] and p["scope"]==target["scope"] and p["business_type"]==target["business_type"]),None)
            if period and all(period["fields"].get(k,{}).get("value") is not None for k in ["assets","equity","liabilities"]) and period["fields"]["assets"]["value"]>0:
                candidates.append({"ticker":symbol,"assets":period["fields"]["assets"]["value"],"records":list(records),"sources":[source],"warnings":list(issues)})
            else:result["excluded"].append({"ticker":symbol,"reason":"Thiếu tài sản/bảng cân đối hợp lệ cùng ngày cuối kỳ, phạm vi hoặc loại hình"})
        group=comparison_group
        if len(candidates)>=2:break
    if group["code"]!=result["code"]:
        result["warnings"].append(f"Không đủ mẫu cùng kỳ trong {result['subsector_name']}; mở rộng mẫu lên ICB cấp {group.get('level')}: {group['name']}. So sánh nhóm rộng hơn, không coi là các đối thủ có sản phẩm giống nhau.")
        result.update({"name":group["name"],"code":group["code"],"level":group.get("level"),"members":group["symbols"]})
    result["sources"][0]["page_or_table"]=f"{taxonomy}; level {group.get('level')}; code {group['code']}; {group['name']}"
    candidates.sort(key=lambda c:(-c["assets"],c["ticker"]))
    chosen=candidates[:max_peers];result["eligible_candidates"]=len(candidates)
    result["selection_candidates"]=[{"ticker":c["ticker"],"assets":c["assets"]} for c in candidates]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(fetch,c["ticker"],kind):(c,kind) for c in chosen for kind in ["income","cashflow"]}
        for future in as_completed(futures):
            candidate,kind=futures[future]
            try:
                records,source,issues=future.result();candidate["records"].extend(records);candidate["sources"].append(source);candidate["warnings"].extend(issues)
            except (DataSourceError,ValueError,KeyError,TypeError) as exc:candidate["warnings"].append(f"{kind}: {exc}")
    for candidate in chosen:
        comparable=[r for r in candidate["records"] if r["scope"]==target["scope"] and r["period_end"]<=target["period_end"]]
        analysis=analyze_financials(comparable)
        if not analysis["periods"] or analysis["periods"][0]["period_end"]!=target["period_end"]:continue
        result["peers"].append({"ticker":candidate["ticker"],"financial":analysis,"warnings":candidate["warnings"]})
        result["sources"].extend(candidate["sources"])
    result["excluded"].sort(key=lambda r:r["ticker"])
    if len(result["peers"])<2:result["errors"].append({"stage":"industry_peers","message":"Chưa đủ hai doanh nghiệp so sánh có kỳ phù hợp; không tính trung vị mẫu."})
    result["warnings"].append("Số liệu mẫu so sánh lấy một nguồn KBS và kiểm tra cấu trúc/kỳ/bảng cân đối; chưa đối chiếu độc lập tất cả tài liệu gốc của từng doanh nghiệp.")
    return result
