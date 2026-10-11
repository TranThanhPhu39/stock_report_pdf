"""Automatic, fail-closed adapter for a public SSI REE segment valuation table."""
from datetime import datetime
import hashlib,re
import pymupdf
from src.data.providers import download,VN_TIME,DataSourceError
from src.analysis.sotp import analyze_sotp
from src.data.acquisition import write_json

REE_URL="https://ftp2.ssi.com.vn/Customers/GDDT/Analyst_Report/OnWeb_Project/Company_Notes/REE_SSIResearch.pdf"


def parse_ree_ssi(raw,source_id):
    with pymupdf.open(stream=raw,filetype="pdf") as doc:
        first=doc[0].get_text();pages=[p.get_text() for p in doc]
    if "SSI" not in first or "REE" not in first:raise DataSourceError("SOTP issuer/provider mismatch")
    m=re.search(r"Ngày báo cáo:\s*(\d{2})/(\d{2})/(\d{4})",first)
    if not m:raise DataSourceError("SOTP publication date missing")
    published=f"{m[3]}-{m[2]}-{m[1]}"
    starts=[i for i,t in enumerate(pages) if "Bảng 12: Tóm tắt định giá" in t]
    if len(starts)!=1:raise DataSourceError("SOTP table missing or ambiguous")
    index=starts[0];text="\n".join(pages[index:index+2]).split("Bảng 12: Tóm tắt định giá",1)[1]
    lines=[" ".join(t.split()) for t in text.splitlines() if t.strip()]
    def value_after(label):
        positions=[i for i,t in enumerate(lines) if t==label]
        if len(positions)!=1:raise DataSourceError("SOTP row ambiguous: "+label)
        for line in lines[positions[0]+1:positions[0]+5]:
            if re.fullmatch(r"-?\d+(?:\.\d{3})*(?:,\d+)?%?",line):return float(line.replace(".","").replace(",",".").replace("%",""))
        raise DataSourceError("SOTP numeric row missing: "+label)
    labels=[("property","BẤT ĐỘNG SẢN","Bất động sản"),("power","ĐIỆN","Năng lượng"),
            ("water","Nước & Môi trường","Nước và môi trường"),("engineering","Cơ điện lạnh & Thương mại","Cơ điện và thương mại")]
    parts=[dict(id=key,label=display,value_vnd=value_after(label)*1e9,method="Mô hình từng mảng của SSI Research",source_id=source_id,page=index+1+(key=="engineering")) for key,label,display in labels]
    return dict(provider="SSI Research",published_at=published,components=parts,non_overlapping=True,bridge_basis="broker_report_declared",scope_verified=False,
                reported_enterprise_value=value_after("Tổng giá trị doanh nghiệp")*1e9,
                adjustments=[dict(id="parent_net_cash",label="Tiền ròng công ty mẹ theo bảng nguồn",value_vnd=value_after("Tiền mặt ròng tại công ty mẹ")*1e9,source_id=source_id)],
                reported_equity_value=value_after("Giá trị hợp lý của VCSH")*1e9,discount=value_after("Chiết khấu")/100,
                shares=value_after("SLCP lưu hành (triệu)")*1e6,reported_target=value_after("Giá mục tiêu (Đồng/share)"),pages=[index+1,index+2])


def collect_sotp(ticker,as_of,company,root,run_id):
    out=analyze_sotp(None,as_of);out.update(sources=[],errors=[])
    if ticker!="REE":return out
    try:
        raw=download(REE_URL,timeout=20)
        if len(raw)>15_000_000:raise DataSourceError("SOTP report size limit")
        sid=f"SOTP_SSI_REE_{run_id}";snapshot=parse_ree_ssi(raw,sid)
        out={**analyze_sotp(snapshot,as_of,company.get("outstanding_shares")),"sources":[],"errors":[]}
        if snapshot["published_at"]>as_of.isoformat():return out
        folder=root/"data/raw/sotp";folder.mkdir(parents=True,exist_ok=True);path=folder/f"{sid}.pdf";path.write_bytes(raw)
        out.update(raw_file=path.relative_to(root).as_posix(),snapshot=snapshot,sha256=hashlib.sha256(raw).hexdigest())
        out["sources"].append(dict(source_id=sid,url_or_file=REE_URL,retrieved_at=datetime.now(VN_TIME).isoformat(),page_or_table="SOTP table pages "+", ".join(map(str,snapshot["pages"])),notes="Published "+snapshot["published_at"]+"; historical broker model, not current independently verified valuation; SHA256 "+out["sha256"]))
    except Exception as exc:out["errors"].append(dict(stage="sotp",message=type(exc).__name__));out["reason"]="Bảng SOTP nguồn không qua kiểm tra cấu trúc/ngày/tổng; không nhập số thay thế."
    run_folder=root/"outputs/runs"/run_id;run_folder.mkdir(parents=True,exist_ok=True)
    write_json(run_folder/"sotp.json",out)
    return out
