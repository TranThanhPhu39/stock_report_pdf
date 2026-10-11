"""Pinned vnfinancialdata statements, full-table export and scoped comparisons."""
from __future__ import annotations

from datetime import date, datetime
from importlib.metadata import version
import io
import json
import math
from pathlib import Path
from threading import Lock
import unicodedata

import pandas as pd

from src.data.acquisition import write_json
from src.data.providers import DataSourceError, VN_TIME
from src.data.reference_miner import cached_file, sha256

SDK_LOCK = Lock()
STATEMENTS = {"balance": "balance_sheet", "income": "income_statement", "cashflow": "cash_flow"}
NAMES = {
    "balance": {
        "assets": ["TỔNG TÀI SẢN", "TỔNG CỘNG TÀI SẢN"], "liabilities": ["NỢ PHẢI TRẢ", "Tổng nợ phải trả"],
        "equity": ["VỐN CHỦ SỞ HỮU", "Vốn chủ sở hữu", "Vốn và các quỹ"],
        "cash": ["Tiền và tương đương tiền"], "short_debt": ["Vay ngắn hạn"],
        "long_debt": ["Vay dài hạn"], "non_controlling_equity": ["Lợi ích của cổ đông thiểu số", "Lợi ích cổ đông không kiểm soát"],
        "financial_loans": ["Các khoản cho vay"],
    },
    "income": {
        "revenue": ["Doanh số thuần", "Doanh thu thuần"],
        "net_profit": ["Lãi/(lỗ) thuần sau thuế"],
        "parent_profit": ["Lợi nhuận của Cổ đông của Công ty mẹ"],
        "gross_profit": ["Lãi gộp"], "pretax_profit": ["Lãi/(lỗ) ròng trước thuế"],
        "interest_expense": ["Trong đó: Chi phí lãi vay"],
    },
    "cashflow": {
        "cfo": ["Lưu chuyển tiền thuần từ các hoạt động sản xuất kinh doanh", "Lưu chuyển tiền thuần từ hoạt động kinh doanh"],
        "capex_cash": ["Tiền mua tài sản cố định và các tài sản dài hạn khác"],
        "interest_paid": ["Chi phí lãi vay đã trả"],
    },
}


def folded(text):
    return " ".join(unicodedata.normalize("NFKC", str(text)).casefold().split())


def validate_frame(frame, ticker, exchange, statement):
    required = {"ticker", "year", "exchange", "statement", "item_code", "item_name", "value", "source_file", "source_sheet"}
    if not isinstance(frame, pd.DataFrame) or not required.issubset(frame.columns):
        raise DataSourceError("vnfinancialdata schema mismatch")
    if not frame.empty and (not frame.ticker.eq(ticker).all() or not frame.exchange.eq(exchange).all() or not frame.statement.eq(statement).all()):
        raise DataSourceError("vnfinancialdata identity/exchange/statement mismatch")
    if frame.duplicated(["ticker", "year", "statement", "item_code"]).any():
        raise DataSourceError("vnfinancialdata duplicate company/year/item")
    years=pd.to_numeric(frame.year, errors="coerce")
    if years.isna().any() or (years % 1 != 0).any():
        raise DataSourceError("vnfinancialdata invalid reporting year")


def mapped_records(frame, dictionary, kind, group, as_of, source_id):
    """Map exact accounting names through the actual dictionary, never positions."""
    expected=STATEMENTS[kind]
    d=dictionary[dictionary.statement.eq(expected)]
    if d.item_code.duplicated().any():raise DataSourceError("vnfinancialdata dictionary duplicate item")
    contract=d.set_index("item_code").to_dict("index")
    names={key:list(aliases) for key,aliases in NAMES[kind].items()}
    if kind=="income" and group=="securities":
        names.update(revenue=["Doanh thu hoạt động"],net_profit=["Lợi nhuận kế toán sau thuế"],
                     pretax_profit=["Tổng lợi nhuận kế toán trước thuế"],
                     brokerage_revenue=["Doanh thu hoạt động môi giới chứng khoán"],
                     lending_revenue=["Lãi từ các khoản cho vay và phải thu"])
    elif kind=="income" and group=="bank":
        names.pop("revenue",None)
        names.update(net_profit=["Lợi nhuận sau thuế"],net_interest_income=["Thu nhập lãi thuần"],
                     pretax_profit=["Tổng lợi nhuận trước thuế"])
    if kind=="cashflow" and group=="securities":
        names["cfo"]=["Lưu chuyển thuần từ hoạt động kinh doanh chứng khoán"]
    results=[];issues=[]
    for year,part in frame.groupby("year"):
        if int(year)>=as_of.year:continue
        fields={}
        for key,aliases in names.items():
            selected=part[part.item_name.map(folded).isin({folded(a) for a in aliases})]
            values=[]
            for row in selected.to_dict("records"):
                info=contract.get(row["item_code"])
                if not info or folded(info["item_name"])!=folded(row["item_name"]) or info.get("unit")!="VND":
                    issues.append(f"{year}/{row['item_code']}: chưa khớp tên hoặc đơn vị VND trong từ điển")
                    continue
                value=row["value"]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):continue
                values.append((float(value),row))
            if not values:continue
            if any(abs(v[0]-values[0][0])>max(1,abs(values[0][0])*1e-10) for v in values):
                issues.append(f"{year}/{key}: nhiều dòng cùng khái niệm có giá trị khác nhau; không gộp")
                continue
            value,row=values[0]
            fields[key]={"value":value,"unit":"VND","unit_status":"dataset_dictionary_declared",
                         "unit_multiplier":1,"source_id":source_id,"source_field":row["item_code"],
                         "source_label":row["item_name"],"source_file":row["source_file"],"source_sheet":row["source_sheet"],
                         "period":str(int(year)),"published_at":None,"statement_scope":"unknown"}
        if fields:results.append({"year":int(year),"kind":kind,"fields":fields,"scope":"unknown","published_at":None})
    return sorted(results,key=lambda r:r["year"],reverse=True),issues


def compare_statements(records, financial):
    primary={p["year"]:p for p in financial.get("periods",[])};checks=[]
    for record in records:
        current=primary.get(record["year"])
        if not current:continue
        for key,field in record["fields"].items():
            target=current["fields"].get(key)
            if not target or target.get("unit")!="VND" or target.get("value") is None:continue
            deviation=abs(target["value"]-field["value"])/max(abs(target["value"]),1)
            sign_difference=key in {"interest_expense","interest_paid","capex_cash"} and target["value"]*field["value"]<0 and abs(abs(target["value"])-abs(field["value"]))/max(abs(target["value"]),1)<=.001
            checks.append({"year":record["year"],"metric":key,"label":field["source_label"],
                           "primary_vnd":target["value"],"reference_vnd":field["value"],
                           "relative_difference":deviation,"match":deviation<=.001,
                           "status":"different_sign_convention" if sign_difference else "matched" if deviation<=.001 else "mismatch",
                           "note":"Cùng độ lớn nhưng trái dấu ở dòng chi phí/chi tiền; giữ giá trị gốc, cần đối chiếu quy ước trình bày trước khi chuẩn hóa." if sign_difference else "",
                           "source_id":field["source_id"],"primary_source_id":target.get("source_id"),
                           "scope_certified":False,"publication_certified":False})
    return checks


def load_statement(ticker, exchange, statement, as_of, root, cfg):
    """Use the package's load API with a verified immutable downloader boundary."""
    if version("vnfinancialdata")!=cfg["package_version"]:
        raise DataSourceError("vnfinancialdata version outside the tested contract")
    import vnfinancialdata as vnf
    import vnfinancialdata.loader as loader
    from huggingface_hub import hf_hub_download
    captured={}

    def pinned_download(**kwargs):
        filename=f"data/{statement}/{exchange}.parquet"
        if kwargs.get("filename")!=filename or kwargs.get("repo_id")!=cfg["repository"] or kwargs.get("revision")!=cfg["commit"]:
            raise DataSourceError("vnfinancialdata unexpected SDK download target")
        path=Path(hf_hub_download(**kwargs,cache_dir=str(root/"data/raw/vnfinancialdata/hub"),token=False,etag_timeout=10))
        raw=path.read_bytes();expected=cfg["files"][f"{statement}/{exchange}"]
        if len(raw)!=expected["size"] or sha256(raw)!=expected["sha256"]:
            raise DataSourceError("vnfinancialdata Parquet size/checksum mismatch")
        captured.update(file=path.relative_to(root.resolve()).as_posix(),sha256=sha256(raw),size=len(raw))
        return str(path)

    # The public API has no revision/cache arguments. Serialize the scoped
    # adapter override and always restore the SDK's own settings afterwards.
    with SDK_LOCK:
        old_revision,old_download=loader.DATASET_REVISION,loader.hf_hub_download
        try:
            loader.DATASET_REVISION=cfg["commit"];loader.hf_hub_download=pinned_download
            frame=vnf.load(exchange=exchange,statement=statement,ticker=ticker,end_year=as_of.year-1)
        finally:
            loader.DATASET_REVISION=old_revision;loader.hf_hub_download=old_download
    return frame,captured


def collect_vnfinancialdata(ticker, as_of, company, financial, root, run_id):
    result={"available":False,"status":"unavailable","records":[],"statements":[],"checks":[],
            "sources":[],"warnings":[],"errors":[],"used_in_primary_analysis":False,
            "reason":"Chưa tải được vnfinancialdata."}
    config_path=root/"config/vnfinancialdata.json"
    if not config_path.exists():return result
    cfg=json.loads(config_path.read_text(encoding="utf-8"));result["dataset"]={k:cfg[k] for k in ["repository","revision","commit","available_at","schema_version","package_version"]}
    exchange={"HOSE":"HSX","HSX":"HSX","HNX":"HNX"}.get(str(company.get("exchange","")).upper())
    if not exchange:
        result.update(status="unsupported_exchange",reason="vnfinancialdata v1.0.0 hỗ trợ HSX/HNX; chưa có bảng UPCoM hoặc chưa xác nhận sàn của mã.")
        return result
    if datetime.fromisoformat(cfg["available_at"].replace("Z","+00:00")).date()>as_of:
        result.update(status="future_snapshot",reason="Phiên bản vnfinancialdata công bố sau ngày chốt; không dùng dữ liệu nhìn trước.")
        return result
    base=f"https://huggingface.co/datasets/{cfg['repository']}/resolve/{cfg['commit']}/"
    folder=root/"data/raw/vnfinancialdata";folder.mkdir(parents=True,exist_ok=True)
    try:
        raw,meta=cached_file(base+"metadata/item_dictionary.csv",folder/"item_dictionary.csv",cfg["available_at"])
        if sha256(raw)!=cfg["dictionary_sha256"]:raise DataSourceError("vnfinancialdata dictionary checksum mismatch")
        dictionary=pd.read_csv(io.BytesIO(raw))
        if not {"statement","item_code","item_name","unit"}.issubset(dictionary.columns):raise DataSourceError("vnfinancialdata dictionary schema mismatch")
        result["sources"].append({"source_id":f"VNF_DICTIONARY_{run_id}","url_or_file":base+"metadata/item_dictionary.csv",
                                  "retrieved_at":meta["retrieved_at"],"page_or_table":"item dictionary","notes":"Pinned SHA256; monetary item units declared VND; EPS/ratios are not imported using that unit declaration."})
    except Exception as exc:
        result["errors"].append({"stage":"vnfinancialdata","message":str(exc)});return result
    all_frames=[]
    for kind,statement in STATEMENTS.items():
        try:
            frame,snapshot=load_statement(ticker,exchange,statement,as_of,root,cfg)
            validate_frame(frame,ticker,exchange,statement)
            frame=frame[frame.year.le(as_of.year-1)].copy()
            sid=f"VNF_{exchange}_{kind}_{run_id}"
            records,issues=mapped_records(frame,dictionary,kind,financial.get("industry_group"),as_of,sid)
            result["records"].extend(records);result["warnings"].extend(issues)
            years=sorted(int(y) for y in frame.year.unique())
            result["statements"].append({"kind":kind,"statement":statement,"years":years,"row_count":len(frame),
                                         "latest_year":max(years) if years else None,"source_id":sid,**snapshot})
            result["sources"].append({"source_id":sid,"url_or_file":base+f"data/{statement}/{exchange}.parquet",
                                      "retrieved_at":datetime.now(VN_TIME).isoformat(),"page_or_table":f"{ticker} {statement}",
                                      "notes":f"vnfinancialdata {cfg['package_version']}; dataset {cfg['revision']}; pinned checksum {snapshot.get('sha256')}; scope/publication of individual statements unknown; not an independent-origin certification."})
            if not frame.empty:all_frames.append(frame)
        except Exception as exc:result["errors"].append({"stage":"vnfinancialdata","message":f"{statement}: {type(exc).__name__}: {exc}"})
    if all_frames:
        combined=pd.concat(all_frames,ignore_index=True).sort_values(["year","statement","item_code"],ascending=[False,True,True])
        path=root/"data/processed"/f"{run_id}_vnfinancialdata.csv";path.parent.mkdir(parents=True,exist_ok=True)
        combined.to_csv(path,index=False,encoding="utf-8-sig")
        result.update(available=True,status="partial_reference" if result["errors"] else "reference_only",csv=path.relative_to(root).as_posix(),row_count=len(combined),
                      years=sorted(int(y) for y in combined.year.unique()),
                      reason="Đã tải các bảng có dữ liệu; các dòng tiền ánh xạ dùng VND theo từ điển nguồn. Chưa đủ metadata ngày công bố/phạm vi từng kỳ để tự thay đầu vào định giá.")
    else:result["reason"]="Không có dòng tài chính cho mã trong snapshot vnfinancialdata hoặc kết nối thất bại."
    result["checks"]=compare_statements(result["records"],financial)
    run_folder=root/"outputs/runs"/run_id;run_folder.mkdir(parents=True,exist_ok=True)
    write_json(run_folder/"vnfinancialdata.json",result)
    return result
