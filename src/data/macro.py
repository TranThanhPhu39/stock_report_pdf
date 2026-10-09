"""Automatically discover dated NSO releases and retrieve World Bank annual context."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
import json, math, re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.data.providers import download, DataSourceError, VN_TIME
from src.data.issuer_pdf import fold

NSO_URL="https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/"
WB_INDICATORS={"gdp_annual":("NY.GDP.MKTP.KD.ZG","GDP thực tăng trưởng năm","%"),
               "cpi_annual":("FP.CPI.TOTL.ZG","CPI bình quân năm","%"),
               "lending_annual":("FR.INR.LEND","Lãi suất cho vay bình quân năm (lịch sử)","%"),
               "fx_annual":("PA.NUS.FCRF","Tỷ giá chính thức bình quân năm (lịch sử)","VND/USD")}

def discover_releases(raw,as_of):
    soup=BeautifulSoup(raw,"html.parser");found=[]
    for item in soup.select("section.item"):
        stamp=item.select_one(".archive-issue-date");title=item.find("h3")
        if not stamp or not title:continue
        match=re.search(r"(\d{2})/(\d{2})/(\d{4})",stamp.get_text())
        if not match:continue
        published=date(int(match[3]),int(match[2]),int(match[1]))
        link=item.select_one("a[href]")
        if not link:
            before=item.find_previous_sibling("p")
            link=before.select_one("a[href]") if before else None
        if not link or published>as_of:continue
        url=urljoin(NSO_URL,link["href"])
        if not url.startswith("https://www.nso.gov.vn/"):continue
        ref=item.select_one(".archive-reference-period")
        found.append({"title":title.get_text(" ",strip=True),"url":url,"published_at":published.isoformat(),
                      "period":ref.get_text(" ",strip=True).split(":",1)[-1].strip() if ref else title.get_text(" ",strip=True)})
    return sorted(found,key=lambda r:r["published_at"],reverse=True)

def parse_nso(raw,release,source_id):
    soup=BeautifulSoup(raw,"html.parser");body=soup.select_one(".post-content") or soup.find("article")
    if body is None:raise DataSourceError("NSO không có nội dung báo cáo")
    text=body.get_text(" ",strip=True);normalized=re.sub(r"\s+"," ",re.sub(r"[\u00ad\u200b-\u200f]","",fold(text)))
    # Match specific comparative statements; never take the first percentage in a paragraph.
    num=r"([0-9]+(?:[,.][0-9]+)?)"
    patterns={
        "gdp_ytd":("GDP thực tăng trưởng lũy kế",r"\bgdp (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4} (?:uoc |uoc tinh )?(?:tang|giam) "+num+r"%"),
        "gdp_year":("GDP thực tăng trưởng năm",r"\bgdp nam \d{4} (?:uoc |uoc tinh )?(?:tang|giam) "+num+r"%"),
        "cpi_ytd":("CPI bình quân lũy kế",r"binh quan (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4},? cpi (?:tang|giam) "+num+r"%"),
        "industrial_growth":("IIP tăng trưởng lũy kế",r"tinh chung (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4},? iip (?:uoc )?(?:tang|giam) "+num+r"%"),
        "construction_growth":("Giá trị tăng thêm xây dựng",r"nganh xay dung (?:tang|giam) "+num+r"%"),
        "real_retail_growth":("Bán lẻ và dịch vụ, loại trừ giá",r"neu loai tru yeu to gia (?:tang|giam) "+num+r"%"),
        "credit_growth":("Tín dụng so với cuối năm trước",r"tang truong tin dung cua nen kinh te (?:dat|tang) "+num+r"%"),
        "investment_growth":("Đầu tư toàn xã hội, giá hiện hành",r"tinh chung (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4} uoc dat [0-9.,]+ nghin ty dong, (?:tang|giam) "+num+r"%"),
        "exports_growth":("Xuất khẩu hàng hóa, giá trị USD",r"tinh chung (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4},? kim ngach xuat khau hang hoa (?:dat|uoc dat) [0-9.,]+ ty usd, (?:tang|giam) "+num+r"%"),
        "telecom_growth":("Doanh thu viễn thông, giá hiện hành",r"tinh chung (?:chin|sau|[0-9]+) thang(?: dau)? nam \d{4},? doanh thu hoat dong vien thong (?:uoc )?dat [0-9.,]+ nghin ty dong, (?:tang|giam) "+num+r"%"),
    }
    fields=[]
    for key,(label,pattern) in patterns.items():
        match=re.search(pattern,normalized)
        if not match:continue
        value=float(match[1].replace(",","."))
        if "giam" in match[0]:value=-value
        if not math.isfinite(value) or abs(value)>100:continue
        period=release["period"]
        if key=="credit_growth":
            time=re.search(r"tinh den (?:thoi diem |ngay )?(\d{1,2}/\d{1,2}/\d{4})[^.]{0,200}?tang truong tin dung",normalized)
            period=time[1]+" / so với cuối năm trước" if time else period+" / so với cuối năm trước"
        fields.append({"key":key,"label":label,"value":value,"unit":"%","period":period,"published_at":release["published_at"],
                       "source_id":source_id,"url":release["url"],"evidence":match[0],"basis":"NSO estimated/reported; yoy except credit vs year end"})
    # USD price index is not a spot exchange rate. Take the explicit same-month YoY comparison.
    line=re.search(r"chi so gia do la my thang [^.]{0,350}",normalized)
    if line:
        match=re.search(r"(tang|giam) "+num+r"% so voi cung ky nam truoc",line[0])
        if match:fields.append({"key":"usd_index_yoy","label":"Chỉ số giá USD so với cùng tháng năm trước","value":float(match[2].replace(",","."))*(-1 if match[1]=="giam" else 1),"unit":"%","period":release["period"],"published_at":release["published_at"],"source_id":source_id,"url":release["url"],"evidence":match[0],"basis":"USD price index YoY, not a spot USD/VND quote"})
    return fields

def parse_world_bank(payload,key,as_of,source_id):
    if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[0],dict):raise DataSourceError("World Bank schema không hợp lệ")
    updated=payload[0].get("lastupdated")
    if not updated or date.fromisoformat(updated)>as_of:return []
    code,label,unit=WB_INDICATORS[key];rows=[]
    for row in payload[1] or []:
        if row.get("countryiso3code")!="VNM" or row.get("indicator",{}).get("id")!=code:raise DataSourceError("Sai quốc gia/chỉ tiêu World Bank")
        value=row.get("value");year=int(row["date"])
        if value is None or year>=as_of.year:continue
        value=float(value)
        if not math.isfinite(value):continue
        rows.append({"key":key,"label":label,"value":value,"unit":unit,"period":str(year),"published_at":None,"source_updated_at":updated,
                     "source_id":source_id,"stale":as_of.year-year>2,"basis":"Annual WDI; update date is not first publication date"})
    return sorted(rows,key=lambda r:r["period"],reverse=True)[:5]

def collect_macro(as_of,root,run_id):
    result={"available":False,"indicators":[],"annual_history":[],"sources":[],"errors":[],"warnings":[],"releases":[]}
    folder=root/"data/raw/macro";folder.mkdir(parents=True,exist_ok=True)
    cutoff=min(as_of,datetime.now(VN_TIME).date())
    try:
        releases=[]
        for page in range(1,7):
            url=NSO_URL if page==1 else NSO_URL+f"page/{page}/"
            raw=download(url,timeout=20);(folder/f"{run_id}_nso_listing_{page}.html").write_bytes(raw)
            releases.extend(discover_releases(raw,cutoff))
            if len(releases)>=3:break
        for index,release in enumerate(releases[:3]):
            raw=download(release["url"],timeout=20);sid=f"NSO_{run_id}_{index}"
            (folder/f"{sid}.html").write_bytes(raw)
            parsed=parse_nso(raw,release,sid)
            existing={r["key"] for r in result["indicators"]}
            result["indicators"].extend(r for r in parsed if r["key"] not in existing)
            result["releases"].append(release)
            result["sources"].append({"source_id":sid,"url_or_file":release["url"],"retrieved_at":datetime.now(VN_TIME).isoformat(),"page_or_table":release["title"],"notes":f"NSO; published {release['published_at']}; reference {release['period']}; raw {sid}.html"})
            if {"gdp_ytd","cpi_ytd","credit_growth"}<={r["key"] for r in result["indicators"]}:break
    except (DataSourceError,ValueError,KeyError,TypeError) as exc:result["errors"].append({"stage":"macro_nso","message":str(exc)})
    def wb(key):
        code=WB_INDICATORS[key][0];url=f"https://api.worldbank.org/v2/country/VNM/indicator/{code}?format=json&per_page=20"
        raw=download(url,timeout=20);sid=f"WDI_{key}_{run_id}";(folder/f"{sid}.json").write_bytes(raw)
        return key,url,sid,parse_world_bank(json.loads(raw),key,cutoff,sid)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(wb,key):key for key in WB_INDICATORS}
        for future in as_completed(futures):
            try:
                key,url,sid,rows=future.result();result["annual_history"].extend(rows)
                if rows:result["indicators"].append(rows[0])
                result["sources"].append({"source_id":sid,"url_or_file":url,"retrieved_at":datetime.now(VN_TIME).isoformat(),"page_or_table":key,"notes":"World Bank WDI annual; lastupdated not first release; historical/stale observations labeled"})
            except (DataSourceError,ValueError,KeyError,TypeError) as exc:result["errors"].append({"stage":"macro_wdi","message":str(exc)})
    result["indicators"].sort(key=lambda r:r["key"]);result["sources"].sort(key=lambda r:r["source_id"])
    result["available"]=bool(result["indicators"])
    result["warnings"].append("NSO: kỳ và ngày công bố riêng cho từng chỉ tiêu; số liệu ước tính có thể được điều chỉnh. WDI là nền năm, không thay số liệu tháng hoặc lãi suất/tỷ giá hiện tại.")
    if any(r.get("stale") for r in result["indicators"]):result["warnings"].append("Có chỉ tiêu WDI cũ hơn hai năm; chỉ dùng tham khảo lịch sử, không suy luận điều kiện hiện tại.")
    if not any(r["key"] in {"gdp_ytd","gdp_year"} for r in result["indicators"]):result["warnings"].append("Chưa trích được GDP lũy kế/năm từ bản tin NSO; dùng nền năm WDI nếu có.")
    if cutoff<datetime.now(VN_TIME).date():result["warnings"].append("Phân tích quá khứ đã lọc ngày công bố; chưa có kho vintage để xác nhận bài NSO không bị điều chỉnh sau ngày đó.")
    return result
