"""Reviewed SSI half-year PDF, checked against annual balances and income quarters."""
from datetime import date,datetime
import json,re,subprocess
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.data.providers import DataSourceError,VN_TIME
from src.data.reference_miner import cached_file
from src.data.ssi_issuer import LISTING,AMOUNT,extract_pages
from src.data.shs_issuer import folded
from src.analysis.valuation import number


def parse_ssi_interim(pages,year,source_id,annual,quarters,as_of):
    full=folded(' '.join(p['text'] for p in pages))
    if 'chung khoan ssi' not in full or 'soat xet' not in full or not re.search(rf'sau thang.*30\s+thang\s+6\s+nam\s+{year}',full):
        raise DataSourceError('Chưa xác nhận SSI hợp nhất soát xét sáu tháng đúng năm.')
    match=re.search(r'vao ngay\s+(\d{1,2})/(\d{1,2})/(\d{4})',full)
    if not match:raise DataSourceError('PDF SSI thiếu ngày công bố được xác nhận.')
    published=date(int(match[3]),int(match[2]),int(match[1]));end=date(year,6,30)
    if not end<published<=as_of:raise DataSourceError('Bán niên SSI chưa được công bố tại ngày chốt.')
    mappings={'balance':{'300':('liabilities','no phai tra'),'400':('equity','von chu so huu'),'418':('non_controlling_equity','loi ich')},
              'income':{'20':('revenue','cong doanh thu hoat dong'),'200':('net_profit','loi nhuan ke toan sau thue'),
                        '201':('parent_profit','loi nhuan sau thue phan bo cho chu'),
                        '90':('pretax_profit','tong loi nhuan ke toan'),'91':('realized_pretax_profit','loi nhuan da thuc hien'),
                        '92':('unrealized_pretax_profit','loi nhuan chua thuc hien')},
              'cashflow':{'60':('cfo','luu chuyen tien thuan')}}
    fields={}
    def add(key,text,page):
        amounts=AMOUNT.findall(text)
        if len(amounts)!=2:raise DataSourceError(f'Hàng bán niên SSI {key} chưa có đúng hai số tiền.')
        values=[(-1 if a.startswith(('(','-')) else 1)*int(re.sub(r'\D','',a)) for a in amounts]
        if key in fields and (fields[key]['value'],fields[key]['previous'])!=tuple(values):
            raise DataSourceError('Hàng bán niên SSI trùng mâu thuẫn.')
        fields[key]=dict(value=values[0],previous=values[1],unit='VND',source_id=source_id,
                         source_field='PDF '+key,period=end.isoformat(),period_begin=f'{year}-01-01',
                         published_at=published.isoformat(),available_at=published.isoformat(),
                         statement_scope='consolidated',page=page,ocr_row=text)
    for page in pages:
        text=page['text'];norm=folded(text)
        if 'vnd' not in norm or 'hop nhat' not in norm or 'cac chi tieu ngoai' in norm:continue
        kind='balance' if 'b01a-ctck/hn' in norm else 'income' if 'b02a-ctck/hn' in norm else 'cashflow' if 'b03b-ctck/hn' in norm else None
        if not kind:continue
        if not re.search(rf'30\s*thang\s*6\s*nam\s*{year}',norm):continue
        # Prior income and cash flow are same six months; balance is year-end.
        if not re.search(rf'nam\s+{year-1}',norm):raise DataSourceError('Cột so sánh bán niên SSI thiếu năm gốc.')
        lines=text.splitlines()
        for index,line in enumerate(lines):
            if kind=='balance' and 'tong cong tai san' in folded(line):add('assets',line,page['page'])
            match=re.match(r'^\s*(\d{2,3})\s*(?:\||\s)',line)
            if not match or match[1] not in mappings[kind]:continue
            key,label=mappings[kind][match[1]];chunk=[line]
            for following in lines[index+1:index+5]:
                if len(AMOUNT.findall(' '.join(chunk)))>=2:break
                if re.match(r'^\s*\d{2,3}\s*(?:\||\s)',following):break
                chunk.append(following)
            combined=' '.join(chunk)
            if label in folded(combined):add(key,combined,page['page'])
    required={'assets','liabilities','equity','revenue','net_profit','parent_profit','cfo'}
    if not required<=fields.keys():raise DataSourceError('Bán niên SSI chưa đủ hàng bắt buộc: '+', '.join(sorted(required-fields.keys())))
    for column in ('value','previous'):
        if abs(fields['assets'][column]-fields['liabilities'][column]-fields['equity'][column])>1:
            raise DataSourceError('Bảng cân đối bán niên SSI không cân bằng.')
    prior=next((p for p in annual.get('periods',[]) if p['period_end']==f'{year-1}-12-31' and p['scope']=='consolidated'),None)
    if not prior:raise DataSourceError('SSI thiếu BCTC năm hợp nhất làm đối chiếu số dư đầu năm.')
    checks=[]
    for key in ('assets','liabilities','equity'):
        value=prior['fields'].get(key,{}).get('value')
        matched=number(value) and abs(value-fields[key]['previous'])<=1e6
        checks.append(dict(metric=key,period=str(year-1),match=matched))
    current=[q for q in quarters if q['year']==year and q['quarter'] in (1,2)]
    if {q['quarter'] for q in current}!={1,2}:raise DataSourceError('SSI thiếu hai quý độc lập đối chiếu OCR bán niên.')
    for key in ('revenue','net_profit','parent_profit'):
        values=[q['fields'].get(key,{}).get('value') for q in current]
        matched=all(number(v) for v in values) and abs(sum(values)-fields[key]['value'])<=1e6
        checks.append(dict(metric=key,period=end.isoformat(),match=matched))
    if not all(c['match'] for c in checks):raise DataSourceError('Bán niên SSI lệch số dư năm hoặc tổng Q1+Q2; không dùng OCR.')
    return dict(valid=True,ticker='SSI',period_type='half_year',period_begin=f'{year}-01-01',period_end=end.isoformat(),
                published_at=published.isoformat(),fields=fields,checks=checks,source_id=source_id,
                note='PDF hợp nhất soát xét SSI; số dư đầu năm khớp BCTC năm và doanh thu/LNST/mẹ sáu tháng khớp Q1+Q2 Vietcap. Cột cùng kỳ 2025 trình bày lại, gồm cách phân bổ quỹ; không thay bằng cột cùng kỳ cũ. CFO là lũy kế sáu tháng.')


def collect_ssi_interim(as_of,financial,quarterly,root,run_id):
    out=dict(available=False,interim=None,sources=[],errors=[],warnings=[])
    if not financial.get('periods') or not quarterly.get('records'):return out
    try:
        folder=root/'data/raw/documents'
        raw,_=cached_file(LISTING,folder/'SSI_financial_listing.html',as_of.isoformat(),max_size=5_000_000)
        soup=BeautifulSoup(raw,'html.parser');year=as_of.year
        items=[item for item in soup.select('.chart__content__item') if f'bao cao tai chinh hop nhat soat xet ban nien {year}' in folded(item.get_text(' ',strip=True))]
        if len(items)!=1:raise DataSourceError('SSI chưa có một PDF bán niên hợp nhất đúng năm trong danh mục.')
        url=urljoin('https://www.ssi.com.vn',items[0].find('a',href=True)['href'])
        if not url.startswith('https://www.ssi.com.vn/upload/files/IR/') or not url.endswith('.pdf'):raise DataSourceError('PDF bán niên SSI không thuộc nguồn chính thức.')
        path=folder/f'SSI_{year}_reviewed_half_year.pdf'
        content,meta=cached_file(url,path,as_of.isoformat(),max_size=40_000_000)
        pages,checksum=extract_pages(path,root,issuer='ssi_interim')
        sid=f'SSI_INTERIM_{run_id}'
        interim=parse_ssi_interim(pages,year,sid,financial,quarterly['records'],as_of)
        interim['file']=path.relative_to(root).as_posix()
        out.update(available=True,interim=interim)
        out['sources'].append(dict(source_id=sid,url_or_file=url,retrieved_at=meta['retrieved_at'],page_or_table='Reviewed half-year statements, PDF pages '+','.join(str(f['page']) for f in interim['fields'].values()),
                                   notes=f"SSI consolidated; published={interim['published_at']}; sha256={checksum}; file={interim['file']}; selected balances and current YTD cross-checked."))
    except (DataSourceError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        out['errors'].append(dict(stage='ssi_interim',message=str(exc)))
    return out
