"""Dated TVS audited consolidated PDF adapter for comparable financials.

OCR amounts are accepted only with accounting identities and independent
numeric column checks. KBS's invalid period metadata is never repaired.
"""
from datetime import date
import json,re
from bs4 import BeautifulSoup
from src.data.providers import DataSourceError
from src.data.reference_miner import cached_file
from src.data.shs_issuer import folded
from src.data.ssi_issuer import AMOUNT, ROWS, extract_pages
from src.data.normalize import FIELD_IDS

LISTING='https://www.tvs.vn/vi/quan-he-nha-dau-tu/bao-cao-tai-chinh-kiem-toan-hop-nhat-nam-{year}'


def parse_tvs_pages(pages,year,published_at,source_id):
    full=folded(' '.join(p['text'] for p in pages))
    if 'cong ty co phan chung khoan thien viet' not in full or 'bao cao kiem toan doc lap' not in full:
        raise DataSourceError('Chưa xác nhận doanh nghiệp và kiểm toán TVS trong PDF.')
    published=date.fromisoformat(published_at)
    if published<=date(year,12,31) or not re.search(rf'ngay\s+{published.day}\s+thang\s+0?{published.month}\s+nam\s+{published.year}',full):
        raise DataSourceError('Ngày PDF TVS không khớp ngày công bố sau cuối kỳ.')
    found={kind:{year:{},year-1:{}} for kind in ROWS}
    for page in pages:
        text=page['text'];norm=folded(text)
        if 'vnd' not in norm or 'hop nhat' not in norm or not re.search(rf'31\s+thang\s+12\s+nam\s+{year}',norm):continue
        kind='balance' if 'b01-ctck/hn' in norm else 'income' if 'b02-ctck/hn' in norm else 'cashflow' if 'b03b-ctck/hn' in norm else None
        if not kind:continue
        # TVS prints the explicit years above the two columns rather than
        # "current/prior". Numeric year-column checks below are mandatory.
        if f'nam {year-1}' not in norm:raise DataSourceError('Chưa xác định hai cột năm TVS.')
        lines=text.splitlines()
        for i,line in enumerate(lines):
            match=re.match(r'^\s*\|?\s*(\d{2,3})\s*(?:\||\s)',line)
            if match and match[1] in ROWS[kind]:
                code=match[1];key,label=ROWS[kind][code]
                if key=='revenue':label='doanh thu hoat dong'
                if key=='parent_profit':label='phan bo cho chu so huu'
            elif kind=='balance' and 'tong cong tai san' in folded(line):code='270';key='assets';label='tong cong tai san'
            else:continue
            row=[line]
            for following in lines[i+1:i+5]:
                if len(AMOUNT.findall(' '.join(row)))>=2:break
                if re.match(r'^\s*\|?\s*\d{2,3}\s*(?:\||\s)',following):break
                row.append(following)
            row_text=' '.join(row)
            if label not in folded(row_text):continue
            amounts=AMOUNT.findall(row_text)
            if len(amounts)!=2:raise DataSourceError(f'Hàng TVS {code} chưa có đúng hai số tiền.')
            for y,amount in zip((year,year-1),amounts):
                value=(-1 if amount.startswith(('(','-')) else 1)*int(re.sub(r'\D','',amount))
                old=found[kind][y].get(key)
                if old and old['value']!=value:raise DataSourceError('Hàng TVS trùng khác giá trị.')
                found[kind][y][key]=dict(value=value,unit='VND',source_id=source_id,source_field=f'PDF row {code}',
                    source_label=label,source_value=value,unit_multiplier=1,period=str(y),published_at=published_at,
                    statement_scope='consolidated',page=page['page'],ocr_row=row_text)
    records=[]
    for y in (year,year-1):
        for kind in ROWS:
            required={entry[0] for entry in ROWS[kind].values()}
            if not required<=found[kind][y].keys():raise DataSourceError(f'TVS thiếu hàng bắt buộc {kind} {y}: '+', '.join(sorted(required-found[kind][y].keys())))
        b=found['balance'][y];i=found['income'][y]
        if b['assets']['value']!=b['liabilities']['value']+b['equity']['value']:raise DataSourceError('Bảng cân đối TVS không cân bằng.')
        if i['pretax_profit']['value']!=i['realized_pretax_profit']['value']+i['unrealized_pretax_profit']['value']:raise DataSourceError('Lợi nhuận thực hiện/chưa thực hiện TVS không khớp tổng.')
        for kind in ROWS:records.append(dict(year=y,period_end=f'{y}-12-31',period_begin=f'{y}01',published_at=published_at,
            scope='consolidated',business_type=2,audit='KT',kind=kind,fields=found[kind][y],source_id=source_id))
    return records


def collect_tvs_peer(as_of,root,run_id,snapshots):
    year=as_of.year-1;folder=root/'data/raw/documents';listing=LISTING.format(year=year)
    raw,_=cached_file(listing,folder/f'TVS_{year}_disclosure.html',as_of.isoformat(),max_size=5_000_000)
    soup=BeautifulSoup(raw,'html.parser')
    if f'bao cao tai chinh kiem toan hop nhat nam {year}' not in folded(soup.get_text(' ',strip=True)):
        raise DataSourceError('Trang TVS không xác nhận báo cáo đúng năm/phạm vi.')
    days=[m for span in soup.find_all('span') if (m:=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})',span.get_text(strip=True)))]
    if not days:raise DataSourceError('Chưa đọc được ngày công bố TVS.')
    # Official TVS page renders its leading publication date in US format.
    published=date(int(days[0][3]),int(days[0][1]),int(days[0][2]))
    if published>as_of:raise DataSourceError('BCTC TVS công bố sau ngày phân tích.')
    links=set(re.findall(r'https://www\.tvs\.vn/api/files/TVS_-_31\.12\.'+str(year)+r'_-_FS_Consol_V[^\\"<>]*\.pdf',raw.decode('utf8')))
    if len(links)!=1:raise DataSourceError('Link BCTC hợp nhất TVS không duy nhất.')
    url=links.pop();path=folder/f'TVS_{year}_audited.pdf'
    _,meta=cached_file(url,path,published.isoformat(),max_size=40_000_000)
    pages,sha=extract_pages(path,root,'TVS',scale=4);sid=f'TVS_AUDITED_{year}_{run_id}'
    records=parse_tvs_pages(pages,year,published.isoformat(),sid);checks=[]
    for kind,data in snapshots.items():
        heads=[h for h in data.get('Head',[]) if h.get('YearPeriod')==year and h.get('United')=='HN' and h.get('TermCode')=='N' and h.get('DatePubDepartment','')[:10]<=as_of.isoformat() and h.get('LastUpdate','')[:10]<=as_of.isoformat()]
        if len(heads)!=1:continue
        values={FIELD_IDS[kind].get(row.get('ReportNormID')):row.get(f"Value{heads[0]['ID']}") for group in data.get('Content',{}).values() for row in group}
        record=next(r for r in records if r['year']==year and r['kind']==kind)
        for key,field in record['fields'].items():
            other=values.get(key)
            if other is not None:checks.append(dict(metric=key,match=abs(field['value']-float(other)*1000)<=1000))
    if not {'assets','equity','liabilities','revenue','net_profit','cfo'}<={c['metric'] for c in checks} or any(not c['match'] for c in checks):
        raise DataSourceError('TVS chưa qua đối chiếu số liệu/cột năm PDF với nguồn tổng hợp.')
    source=dict(source_id=sid,url_or_file=url,retrieved_at=meta['retrieved_at'],page_or_table='TVS audited consolidated PDF; rows and years verified',
        notes=f'Published {published}; SHA256 {sha}; official disclosure {listing}; {len(checks)} selected numeric checks matched KBS (invalid period metadata remains excluded).')
    return dict(records=records,source=source,checks=checks)
