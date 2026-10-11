"""Read SHS's audited standalone statements from a dated annual-report PDF.

This is a layout-specific adapter, not a general PDF/Parquet promotion rule.
Amounts are extracted on every run; no financial values are hard-coded.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
import hashlib
import json
import re
import unicodedata

from bs4 import BeautifulSoup
import pymupdf

from src.data.providers import DataSourceError, VN_TIME, download
from src.data.normalize import FIELD_IDS
from src.data.reference_miner import cached_file


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ','d'))
                   if unicodedata.category(c) != 'Mn')


ROWS = {
    'balance': {'270':('assets','tong cong tai san'), '300':('liabilities','no phai tra'),
                '400':('equity','von chu so huu'), '114':('financial_loans','cac khoan cho vay')},
    'income': {'20':('revenue','cong doanh thu hoat dong'),
               '200':('net_profit','loi nhuan ke toan sau thue'),
               '90':('pretax_profit','tong loi nhuan ke toan truoc thue'),
               '03':('lending_revenue','lai tu cac khoan cho vay va phai thu'),
               '06':('brokerage_revenue','doanh thu nghiep vu moi gioi'),
               '91':('realized_pretax_profit','loi nhuan da thuc hien'),
               '92':('unrealized_pretax_profit','loi nhuan chua thuc hien')},
    'cashflow': {'60':('cfo','luu chuyen tien thuan tu hoat dong kinh doanh')},
}
AMOUNT = re.compile(r'^\(?-?\d{1,3}(?:\.\d{3})+\)?$')


def row_amounts(text, code, label):
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    found=[]
    for i,line in enumerate(lines):
        if line != code: continue
        tail=lines[i+1:i+16]
        for n in range(len(tail)-1):
            if AMOUNT.fullmatch(tail[n]) and AMOUNT.fullmatch(tail[n+1]):
                if label not in folded(' '.join(tail[:n])): break
                values=[int(v.strip('()').replace('.',''))*(-1 if v.startswith('(') else 1) for v in tail[n:n+2]]
                found.append(values);break
    if len(found)>1: raise DataSourceError(f'Hàng PDF {code} không duy nhất.')
    return found[0] if found else None


def parse_shs_pdf(raw, year, published_at, as_of, source_id):
    published=date.fromisoformat(published_at)
    if published>as_of or date(year,12,31)>=published:
        raise DataSourceError('PDF SHS chưa công bố hoặc năm tài chính chưa kết thúc.')
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        texts=[p.get_text() for p in doc]
        whole=folded('\n'.join(texts))
        intro=f'cho nam tai chinh ket thuc ngay 31/12/{year}'
        section=next((folded(t) for t in texts if intro in folded(t)),None)
        if not section or 'da duoc kiem toan' not in section or 'chung khoan sai gon - ha noi' not in section:
            raise DataSourceError('Không xác nhận được doanh nghiệp, năm và kiểm toán trong PDF SHS.')
        if 'hop nhat' in section or 'bao cao tai chinh cua cong ty' not in whole:
            raise DataSourceError('Phạm vi BCTC SHS không khớp bộ đọc riêng lẻ.')
        # A mirrored filing can contain a later disclosure cover than the web listing.
        covers=folded('\n'.join(texts[:2]))
        dates=re.findall(r'(?:ngay)\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+(?:nam|nem)\s+(20\d{2})',covers)
        for day,month,y in dates:
            published=max(published,date(int(y),int(month),int(day)))
        if published>as_of:raise DataSourceError('Ngày trên văn bản công bố PDF sau ngày phân tích.')
        output={k:{year:{},year-1:{}} for k in ROWS}
        for page_index,page in enumerate(doc):
            text=texts[page_index];normalized=folded(text)
            kind='balance' if 'bao cao tinh hinh tai chinh' in normalized else 'cashflow' if 'bao cao luu chuyen tien te' in normalized else 'income' if 'bao cao ket qua hoat dong' in normalized else None
            if not kind:continue
            # Printed spreads have two independent table columns. Never cross them.
            clips=[pymupdf.Rect(0,0,page.rect.width/2,page.rect.height),pymupdf.Rect(page.rect.width/2,0,page.rect.width,page.rect.height)] if page.rect.width>page.rect.height else [page.rect]
            for clip in clips:
                table=page.get_text(clip=clip);norm=folded(table)
                if 'vnd' not in norm:continue
                if kind=='balance':
                    if f'31/12/{year}' not in norm or f'01/01/{year}' not in norm:continue
                    if norm.index(f'31/12/{year}')>norm.index(f'01/01/{year}'):raise DataSourceError('Thứ tự cột năm PDF SHS không phù hợp.')
                elif f'nam {year}' not in norm or f'nam {year-1}' not in norm:continue
                elif norm.index(f'nam {year}')>norm.index(f'nam {year-1}'):raise DataSourceError('Thứ tự cột năm PDF SHS không phù hợp.')
                table_kind='income' if 'bao cao ket qua hoat dong' in norm else 'cashflow' if 'bao cao luu chuyen tien te' in norm else kind
                for code,(key,label) in ROWS[table_kind].items():
                    values=row_amounts(table,code,label)
                    if values is None:continue
                    for y,value in zip((year,year-1),values):
                        field=dict(value=value,unit='VND',source_id=source_id,source_field=f'PDF row {code}',
                                   source_label=label,source_value=value,unit_multiplier=1,period=str(y),
                                   published_at=published.isoformat(),statement_scope='separate',page=page_index+1)
                        old=output[table_kind][y].get(key)
                        if old and old['value']!=value:raise DataSourceError(f'Số liệu PDF {key} bị trùng khác giá trị.')
                        output[table_kind][y][key]=field
        records=[]
        for y in (year,year-1):
            balance=output['balance'][y];income=output['income'][y]
            if not all(k in balance for k in ('assets','equity','liabilities')) or not all(k in income for k in ('revenue','net_profit')) or 'cfo' not in output['cashflow'][y]:
                raise DataSourceError(f'PDF SHS thiếu hàng/cột bắt buộc tại {y}; không tự điền số.')
            if abs(balance['assets']['value']-balance['equity']['value']-balance['liabilities']['value'])>1:
                raise DataSourceError('Bảng cân đối PDF SHS không cân bằng.')
            income['parent_profit']={**income['net_profit'],'derivation':'BCTC riêng lẻ: LNST của chính công ty, không phân bổ NCI.'}
            for kind in ROWS:
                records.append(dict(year=y,period_end=f'{y}-12-31',period_begin=f'{y}01',published_at=published.isoformat(),
                                    scope='separate',business_type=2,audit='KT',kind=kind,fields=output[kind][y],source_id=source_id))
    return records


def compare_kbs_pdf(records, root, run_id, as_of):
    """Numeric cross-check only. Invalid KBS period metadata is never repaired."""
    checks=[]
    for kind in ROWS:
        path=root/'data/raw/financials'/f'{run_id}_{kind}.json'
        if not path.exists():continue
        data=json.loads(path.read_text(encoding='utf8'))
        for record in [r for r in records if r['kind']==kind]:
            heads=[h for h in data.get('Head',[]) if h.get('YearPeriod')==record['year'] and h.get('United')=='ĐL' and h.get('TermCode')=='N']
            if len(heads)!=1:continue
            head=heads[0]
            if any(not head.get(k) or head[k][:10]>as_of.isoformat() for k in ('DatePubDepartment','LastUpdate')):continue
            values={FIELD_IDS[kind].get(row.get('ReportNormID')):row.get(f"Value{head['ID']}") for group in data.get('Content',{}).values() for row in group}
            for key in ('assets','equity','liabilities','revenue','net_profit','cfo'):
                if key not in record['fields'] or values.get(key) is None:continue
                field=record['fields'][key];other=float(values[key])*1000
                checks.append(dict(metric=key,period=str(record['year']),actual_billion_vnd=field['value']/1e9,
                                   reference_billion_vnd=other/1e9,match=abs(field['value']-other)<=1000,
                                   source_id=field['source_id'],reference_source_id=f'KBS_{kind}_{run_id}',
                                   locator=f"BCTN SHS, trang PDF {field['page']}, {field['source_field']}; cột {record['year']}",
                                   note='Đối chiếu giá trị KBS gắn nhãn năm; kỳ chính xác lấy từ PDF, không sửa metadata KBS.'))
    return checks


def collect_shs_issuer(ticker, as_of, reference, root, run_id):
    result=dict(available=False,records=[],checks=[],sources=[],warnings=[],errors=[])
    if ticker!='SHS':return result
    year=as_of.year-1
    url=f'https://www.shs.com.vn/cong-bo-thong-tin/shs-cbtt-bao-cao-thuong-nien-nam-{year}'
    try:
        folder=root/'data/raw/documents';folder.mkdir(parents=True,exist_ok=True)
        raw,listing_meta=cached_file(url,folder/f'SHS_{year}_issuer_listing.html',as_of.isoformat(),max_size=5_000_000)
        soup=BeautifulSoup(raw,'html.parser')
        title=soup.find('h1');text=soup.get_text(' ',strip=True)
        if not title or f'bao cao thuong nien nam {year}' not in folded(title.get_text(' ',strip=True)):
            raise DataSourceError('Trang công bố SHS không đúng tài liệu/năm yêu cầu.')
        match=re.search(r'Ngày đăng:\s*(\d{2})/(\d{2})/(\d{4})',text)
        if not match:raise DataSourceError('Trang SHS thiếu ngày công bố.')
        day,month,y=map(int,match.groups());published=date(y,month,day)
        if published>as_of:raise DataSourceError('BCTN SHS công bố sau ngày phân tích.')
        (folder/f'{run_id}_issuer_listing.html').write_bytes(raw)
        reports=[r for r in reference.get('reports',[]) if r.get('year')==year and r.get('file')]
        content=None;document_url=None
        links=[a['href'] for a in soup.find_all('a',href=True) if a['href'].startswith('https://s3-storage.shs.com.vn/') and '.pdf' in a['href'] and 'VI_SHS' in a['href']]
        official_cache=folder/f'SHS_{year}_issuer_annual.pdf'
        cache_meta=official_cache.with_suffix('.pdf.json')
        if len(links)==1 and official_cache.exists() and cache_meta.exists():
            try:
                meta=json.loads(cache_meta.read_text(encoding='utf8'));candidate=official_cache.read_bytes()
                age=datetime.now(VN_TIME)-datetime.fromisoformat(meta['retrieved_at'])
                if meta['url']==links[0] and timedelta(0)<=age<timedelta(hours=24) and hashlib.sha256(candidate).hexdigest()==meta['sha256']:
                    content=candidate;document_url=links[0];file=official_cache.relative_to(root).as_posix()
            except (OSError,ValueError,KeyError,TypeError):pass
        for report in reports:
            if content is not None:break
            p=(root/report['file']).resolve()
            if not p.is_relative_to(root.resolve()) or not p.exists():continue
            candidate=p.read_bytes()
            if hashlib.sha256(candidate).hexdigest()==report['sha256']:
                content=candidate;document_url=report.get('download_url');file=report['file'];break
        if content is None:
            if len(links)!=1:raise DataSourceError('Link PDF tiếng Việt SHS không duy nhất.')
            document_url=links[0];content=download(document_url,timeout=25)
            official_cache.write_bytes(content);file=official_cache.relative_to(root).as_posix()
            cache_meta.write_text(json.dumps(dict(url=document_url,sha256=hashlib.sha256(content).hexdigest(),retrieved_at=datetime.now(VN_TIME).isoformat())),encoding='utf8')
        digest=hashlib.sha256(content).hexdigest();sid=f'SHS_ISSUER_{digest[:16]}';listing_sid=f'SHS_DISCLOSURE_{run_id}'
        records=parse_shs_pdf(content,year,published.isoformat(),as_of,sid)
        checks=compare_kbs_pdf(records,root,run_id,as_of)
        pages=sorted({field['page'] for r in records for field in r['fields'].values()})
        now=datetime.now(VN_TIME).isoformat()
        result.update(available=True,records=records,checks=checks,year=year,file=file,sha256=digest,
                      published_at=max(r['published_at'] for r in records),sources=[
            dict(source_id=listing_sid,url_or_file=url,retrieved_at=listing_meta['retrieved_at'],page_or_table='Công bố BCTN, ngày đăng',notes=f"Official issuer disclosure; published={published}; PDF cover may be later; listing checksum={listing_meta['sha256']}; cache under 24h checked on each reuse."),
            dict(source_id=sid,url_or_file=document_url,retrieved_at=now,page_or_table='BCTC kiểm toán, trang PDF '+', '.join(map(str,pages)),
                 notes=f'SHS standalone; year {year}; VND; PDF row/column extraction; checksum={digest}; file={file}; disclosure={url}; copy origin disclosed, not a separate audit.')])
        result['warnings'].append(f'Tài chính SHS {year} lấy từ bảng kiểm toán trong BCTN, kèm trang và mã hàng. Kỳ lỗi metadata KBS vẫn bị loại; đối chiếu KBS chỉ kiểm tra các giá trị được liệt kê.')
    except (DataSourceError,OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        result['errors'].append(dict(stage='issuer_financials',message=str(exc)))
    return result
