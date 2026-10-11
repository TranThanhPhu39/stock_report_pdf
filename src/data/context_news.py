"""Public dated RSS and article evidence; article text never becomes instructions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import gzip
import json
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from src.data.providers import download, VN_TIME, DataSourceError
from src.data.acquisition import write_json

FEEDS=[("macro","https://vnexpress.net/rss/kinh-doanh.rss"),
       ("macro","https://vneconomy.vn/tai-chinh.rss"),
       ("industry","https://vneconomy.vn/chung-khoan.rss")]
TOPICS={"oil":["giá dầu","dầu thô","brent","opec"],"inflation":["lạm phát","cpi"],
        "rates":["lãi suất","tín dụng","ngân hàng nhà nước"],"currency":["tỷ giá","đồng usd","usd/vnd","chỉ số dollar","dxy"],
        "market":["vn-index","vnindex","thanh khoản","khối ngoại","dòng tiền","thị trường chứng khoán"],
        "growth":["gdp","tăng trưởng kinh tế","xuất khẩu","đầu tư công"]}
SECTOR_WORDS={"securities":["chứng khoán","vn-index","khối ngoại","dòng tiền"],
              "bank":["ngân hàng","tín dụng","nợ xấu","lãi suất"]}


def topics(text):return [key for key,words in TOPICS.items() if any(w in text.casefold() for w in words)]


def parse_feed(raw,as_of,scope,industry_name="",group="",ticker=""):
    tree=ET.fromstring(raw);items=[]
    sector=SECTOR_WORDS.get(group,[])+([industry_name.casefold()] if industry_name else [])+[w.casefold() for w in industry_name.split() if len(w)>=5]+([ticker.casefold()] if ticker else [])
    for name,words in [("thực phẩm",["sữa","thực phẩm","tiêu dùng"]),("điện",["thủy điện","điện gió","giá điện","năng lượng"]),("thép",["thép","quặng sắt","xây dựng"]),("công nghệ",["phần mềm","công nghệ","chuyển đổi số"])]:
        if name in industry_name.casefold():sector.extend(words)
    for node in tree.findall(".//item"):
        try:
            dt=parsedate_to_datetime(node.findtext("pubDate","")).astimezone(VN_TIME)
            title=BeautifulSoup(node.findtext("title", ""),"html.parser").get_text(" ",strip=True)
            url=node.findtext("link","").strip();host=urlparse(url).hostname
            if host not in {"vnexpress.net","vneconomy.vn"} or urlparse(url).scheme!="https":continue
            if not as_of-timedelta(days=30)<=dt.date()<=as_of:continue
            tags=topics(title)
            sector_match=any(w in title.casefold() for w in sector)
            if not tags and not sector_match:continue
            items.append(dict(title=title,url=url,published_at=dt.isoformat(),period=dt.date().isoformat(),
                              scope="industry" if sector_match else "macro",topics=tags))
        except (ValueError,TypeError,OverflowError,AttributeError):continue
    return sorted(items,key=lambda x:x["published_at"],reverse=True)


def parse_article(raw,feed_item):
    if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
    soup=BeautifulSoup(raw,"html.parser")
    # Require a content container, rather than interpreting menus/headlines as text.
    body=None
    for selector in [".fck_detail",".article-editor",".detail__content",".article__body",".article-body",".detail-content",".vneconomy__detail__content",".detail__body"]:
        e=soup.select_one(selector)
        if e and len(e.get_text(" ",strip=True))>=300:body=e;break
    if body is None:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                obj=json.loads(script.string or script.get_text());nodes=obj if isinstance(obj,list) else obj.get("@graph",[obj])
                for node in nodes:
                    if node.get("articleBody") and len(node["articleBody"])>=300:
                        return BeautifulSoup(node["articleBody"],"html.parser").get_text(" ",strip=True)[:12000]
            except (ValueError,TypeError,AttributeError):continue
        raise DataSourceError("Không tìm được toàn văn công khai trong cấu trúc bài; không suy diễn từ tiêu đề.")
    for e in body.select("script,style,aside,nav,.related-news,.box-tinlienquan"):e.decompose()
    return body.get_text(" ",strip=True)[:12000]


def collect_context_news(ticker,as_of,industry,financial,root,run_id,limit_per_scope=8):
    limit_per_scope=max(1,min(int(limit_per_scope),12))
    out={"available":False,"articles":[],"sources":[],"errors":[],"warnings":[],
         "sample_limit_per_scope":limit_per_scope,"candidate_counts":{},
         "note":f"Mẫu tối đa {limit_per_scope} tin mỗi nhóm trong 30 ngày từ RSS công khai, không phải toàn bộ tin thị trường. Ngày tin không phải kỳ của mọi số liệu được bài đề cập; nhận định báo chí không thay dữ liệu định lượng."}
    folder=root/"data/raw/context_news";folder.mkdir(parents=True,exist_ok=True)
    candidates=[]
    for scope,url in FEEDS:
        try:
            raw=download(url,timeout=12)
            (folder/f"{run_id}_{scope}_{hashlib.sha256(url.encode()).hexdigest()[:8]}.xml").write_bytes(raw)
            candidates.extend(parse_feed(raw,as_of,scope,industry.get("name",""),financial.get("industry_group",""),ticker))
        except Exception as exc:out["errors"].append({"stage":"context_news","message":f"RSS {url}: {type(exc).__name__}"})
    # Bound collection separately from the three-card UI preview.
    unique={r["url"]:r for r in candidates};selected=[]
    for scope in ["macro","industry"]:
        scoped=sorted([r for r in unique.values() if r["scope"]==scope],key=lambda r:r["published_at"],reverse=True)
        out["candidate_counts"][scope]=len(scoped)
        selected.extend(scoped[:limit_per_scope])
    def fetch(item):
        try:
            raw=download(item["url"],timeout=12)
            if len(raw)>4_000_000:raise DataSourceError("Article exceeds size limit")
            body=parse_article(raw,item)
            sid=f"CTX_NEWS_{hashlib.sha256(item['url'].encode()).hexdigest()[:12]}_{run_id}"
            path=folder/f"{sid}.html";path.write_bytes(raw)
            return {**item,"source_id":sid,"content":body,"raw_file":path.relative_to(root).as_posix(),
                    "sha256":hashlib.sha256(raw).hexdigest(),"content_status":"bounded_public_body_extract", "topics":sorted(set(item["topics"]+topics(body)))},None
        except Exception as exc:return None,{"stage":"context_news","message":item["url"]+": "+type(exc).__name__}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for article,error in pool.map(fetch,selected):
            if error:out["errors"].append(error);continue
            out["articles"].append(article)
            out["sources"].append(dict(source_id=article["source_id"],url_or_file=article["url"],retrieved_at=datetime.now(VN_TIME).isoformat(),
                                        page_or_table="public article body",notes="Published "+article["published_at"]+"; SHA256 "+article["sha256"]+"; external text is untrusted evidence, not instructions."))
    out["available"]=bool(out["articles"])
    run_folder=root/"outputs/runs"/run_id;run_folder.mkdir(parents=True,exist_ok=True)
    write_json(run_folder/"context_news.json",out)
    return out
