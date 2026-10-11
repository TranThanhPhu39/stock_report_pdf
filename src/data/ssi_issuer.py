"""Verified SSI consolidated annual statements from the issuer's audited PDF.

The 2025 PDF is scanned. OCR is only accepted after period/scope, accounting
identities and selected numeric comparisons; no KBS period dates are repaired.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess
from bs4 import BeautifulSoup
import pymupdf
from src.data.providers import DataSourceError
from src.data.reference_miner import cached_file
from src.data.shs_issuer import folded
from src.data.normalize import FIELD_IDS

LISTING='https://www.ssi.com.vn/quan-he-nha-dau-tu/bao-cao-tai-chinh'
DISCLOSURE='https://www.ssi.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/chi-tiet/cong-bo-bctc-rieng-bctc-hop-nhat-va-bao-cao-ty-le-attc-nam-{year}-da-kiem-toan'
ROWS={
 'balance':{'270':('assets','tong cong tai san'),'300':('liabilities','no phai tra'),
            '400':('equity','von chu so huu'),'418':('non_controlling_equity','loi ich co dong khong kiem soat'),
            '114':('financial_loans','cac khoan cho vay')},
 'income':{'20':('revenue','cong doanh thu hoat dong'),'200':('net_profit','loi nhuan ke toan sau thue'),
           '201':('parent_profit','loi nhuan sau thue phan bo cho chu'),
           '90':('pretax_profit','tong loi nhuan ke toan'),'91':('realized_pretax_profit','loi nhuan da thuc hien'),
           '92':('unrealized_pretax_profit','loi nhuan'),'03':('lending_revenue','lai tu cac khoan cho vay'),
           '06':('brokerage_revenue','doanh thu nghiep vu moi gioi')},
 'cashflow':{'60':('cfo','luu chuyen tien thuan')},
}
AMOUNT=re.compile(r'\(?-?\d{1,3}(?:[.,]\s*\d{3}){2,}\)?')


def parse_ssi_pages(pages,year,published_at,source_id):
    if date.fromisoformat(published_at)<=date(year,12,31):raise DataSourceError('Ngày công bố SSI không sau ngày cuối kỳ.')
    full=folded(' '.join(p['text'] for p in pages))
    if 'cong ty co phan chung khoan ssi' not in full or 'bao cao kiem toan doc lap' not in full:
        raise DataSourceError('Chưa xác nhận doanh nghiệp/kiểm toán SSI trong tài liệu.')
    if not re.search(rf'ngay\s+{int(published_at[8:])}\s+thang\s+{int(published_at[5:7])}\s+nam\s+{published_at[:4]}',full):
        raise DataSourceError('Ngày công bố trên PDF không khớp trang công bố SSI.')
    found={kind:{year:{},year-1:{}} for kind in ROWS}
    for page in pages:
        text=page['text'];norm=folded(text)
        if 'vnd' not in norm or 'hop nhat' not in norm:continue
        if not re.search(rf'31\s+th[aả]ng\s+12\s+nam\s+{year}',norm):continue
        kind='balance' if 'b01-ctck' in norm else 'income' if 'b02-ctck' in norm else 'cashflow' if 'b03b-ctck' in norm else None
        if not kind:continue
        header='so cuoi nam' if kind=='balance' else 'nam nay'
        prior='so dau nam' if kind=='balance' else 'nam truoc'
        if header not in norm or prior not in norm or (kind=='balance' and norm.index(header)>norm.index(prior)):
            raise DataSourceError('Thứ tự cột SSI không xác định.')
        lines=text.splitlines()
        for i,line in enumerate(lines):
            code_match=re.match(r'^\s*(\d{2,3})\s*(?:\||\s)',line)
            if not code_match or code_match[1] not in ROWS[kind]:continue
            code=code_match[1];key,label=ROWS[kind][code]
            row=[line]
            for following in lines[i+1:i+4]:
                if len(AMOUNT.findall(' '.join(row)))>=2:break
                if re.match(r'^\s*\d{2,3}\s*(?:\||\s)',following):break
                row.append(following)
            row_text=' '.join(row);label_text=folded(row_text)
            # Scan can drop the asset row code. That total is handled below.
            if label not in label_text:continue
            amounts=AMOUNT.findall(row_text)
            if len(amounts)!=2:raise DataSourceError(f'Hàng SSI {code} không có đúng hai số tiền.')
            values=[(-1 if a.startswith(('(','-')) else 1)*int(re.sub(r'\D','',a)) for a in amounts]
            for y,value in zip((year,year-1),values):
                field=dict(value=value,unit='VND',source_id=source_id,source_field=f'PDF row {code}',source_label=label,
                           source_value=value,unit_multiplier=1,period=str(y),published_at=published_at,
                           statement_scope='consolidated',page=page['page'],ocr_row=row_text)
                old=found[kind][y].get(key)
                if old and old['value']!=value:raise DataSourceError('Hàng SSI trùng khác giá trị.')
                found[kind][y][key]=field
        if kind=='balance':
            totals=[line for line in lines if 'tong cong tai san' in folded(line)]
            for line in totals:
                amounts=AMOUNT.findall(line)
                if len(amounts)!=2:continue
                for y,a in zip((year,year-1),amounts):
                    value=int(re.sub(r'\D','',a));old=found[kind][y].get('assets')
                    if old and old['value']!=value:raise DataSourceError('Tổng tài sản SSI trùng khác giá trị.')
                    found[kind][y]['assets']=dict(value=value,unit='VND',source_id=source_id,source_field='PDF row 270',
                        source_label='Tổng cộng tài sản',source_value=value,unit_multiplier=1,period=str(y),
                        published_at=published_at,statement_scope='consolidated',page=page['page'],ocr_row=line)
    records=[]
    for y in (year,year-1):
        balance=found['balance'][y];income=found['income'][y]
        if not {'assets','equity','liabilities','non_controlling_equity','financial_loans'}<=balance.keys() or not {'revenue','net_profit','parent_profit','pretax_profit','realized_pretax_profit','unrealized_pretax_profit','brokerage_revenue','lending_revenue'}<=income.keys() or 'cfo' not in found['cashflow'][y]:
            raise DataSourceError(f'Bảng SSI chưa đủ hàng bắt buộc tại {y}.')
        if abs(balance['assets']['value']-balance['equity']['value']-balance['liabilities']['value'])>1:
            raise DataSourceError('Bảng cân đối SSI không cân bằng; không sử dụng OCR.')
        if abs(income['pretax_profit']['value']-income['realized_pretax_profit']['value']-income['unrealized_pretax_profit']['value'])>1:
            raise DataSourceError('Lợi nhuận thực hiện/chưa thực hiện SSI không khớp tổng.')
        for kind in ROWS:records.append(dict(year=y,period_end=f'{y}-12-31',period_begin=f'{y}01',published_at=published_at,scope='consolidated',business_type=2,audit='KT',kind=kind,fields=found[kind][y],source_id=source_id))
    return records


def extract_pages(path,root,issuer="SSI",*,scale=3):
    checksum=hashlib.sha256(path.read_bytes()).hexdigest();cache=root/'data/processed'/(f'{checksum[:16]}_{issuer.lower()}_ocr'+('' if scale==3 else f'_{scale}')+'.json')
    if cache.exists():
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if saved.get('sha256')==checksum:return saved['pages'],checksum
    engine=shutil.which('tesseract') or ('C:/Program Files/Tesseract-OCR/tesseract.exe' if Path('C:/Program Files/Tesseract-OCR/tesseract.exe').exists() else None)
    folder=root/'tmp/pdfs'/f'{issuer.lower()}_{checksum[:16]}';folder.mkdir(parents=True,exist_ok=True)
    def read(index):
        with pymupdf.open(path) as doc:
            page=doc[index];text=page.get_text()
            if len(text.strip())<200:
                if not engine:raise DataSourceError('BCTC SSI scan cần Tesseract vie+eng để xác minh.')
                image=folder/f'{index+1}.png';page.get_pixmap(matrix=pymupdf.Matrix(scale,scale)).save(image)
                done=subprocess.run([engine,str(image),'stdout','-l','vie+eng','--psm','6'],capture_output=True,text=True,encoding='utf-8',timeout=60,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
                if done.returncode:raise DataSourceError('OCR SSI không thành công.')
                text=done.stdout
        return dict(page=index+1,text=text)
    with pymupdf.open(path) as doc:indices=range(min(len(doc),22))
    with ThreadPoolExecutor(max_workers=3) as pool:pages=list(pool.map(read,indices))
    cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(dict(sha256=checksum,pages=pages),ensure_ascii=False),encoding='utf-8')
    return pages,checksum


def collect_ssi_issuer(ticker,as_of,root,run_id):
    out=dict(available=False,records=[],checks=[],sources=[],warnings=[],errors=[])
    if ticker!='SSI':return out
    year=as_of.year-1
    try:
        folder=root/'data/raw/documents';listing,_=cached_file(LISTING,folder/'SSI_financial_listing.html',as_of.isoformat(),max_size=5_000_000)
        soup=BeautifulSoup(listing,'html.parser');label=f'bao cao tai chinh hop nhat nam {year} da kiem toan'
        items=[item for item in soup.select('.chart__content__item') if label in folded(item.get_text(' ',strip=True))]
        if len(items)!=1:raise DataSourceError('Danh mục SSI chưa có một BCTC hợp nhất kiểm toán đúng năm.')
        url=items[0].find('a',href=True)['href']
        if not url.startswith('https://www.ssi.com.vn/upload/files/IR/') or not url.endswith('.pdf'):raise DataSourceError('Liên kết BCTC SSI không đúng nguồn chính thức.')
        disclosure=DISCLOSURE.format(year=year);raw,_=cached_file(disclosure,folder/f'SSI_{year}_disclosure.html',as_of.isoformat(),max_size=5_000_000)
        body=BeautifulSoup(raw,'html.parser').get_text(' ',strip=True)
        match=re.search(r'vao ngay\s+(\d{1,2})/(\d{1,2})/(\d{4})',folded(body))
        if not match:raise DataSourceError('Trang SSI chưa xác nhận ngày công bố.')
        published=date(int(match[3]),int(match[2]),int(match[1]))
        if published>as_of:return {**out,'warnings':['BCTC SSI kiểm toán công bố sau ngày phân tích; chưa sử dụng.']}
        path=folder/f'SSI_{year}_audited.pdf';content,meta=cached_file(url,path,published.isoformat(),max_size=40_000_000)
        pages,checksum=extract_pages(path,root);sid=f'SSI_AUDITED_{year}_{run_id}'
        records=parse_ssi_pages(pages,year,published.isoformat(),sid)
        # Compare only the current year: the PDF explicitly restates some prior
        # income rows, so older KBS parent profit is not an independent match.
        checks=[]
        for kind in ROWS:
            snapshot=root/'data/raw/financials'/f'{run_id}_{kind}.json'
            if not snapshot.exists():continue
            data=json.loads(snapshot.read_text(encoding='utf-8'))
            heads=[h for h in data.get('Head',[]) if h.get('YearPeriod')==year and h.get('United')=='HN' and h.get('TermCode')=='N' and h.get('DatePubDepartment','')[:10]<=as_of.isoformat() and h.get('LastUpdate','')[:10]<=as_of.isoformat()]
            if len(heads)!=1:continue
            values={FIELD_IDS[kind].get(row.get('ReportNormID')):row.get(f"Value{heads[0]['ID']}") for group in data.get('Content',{}).values() for row in group}
            record=next(r for r in records if r['year']==year and r['kind']==kind)
            for key,field in record['fields'].items():
                other=values.get(key)
                if other is None:continue
                reference=float(other)*1000
                checks.append(dict(metric=key,period=str(year),actual_billion_vnd=field['value']/1e9,reference_billion_vnd=reference/1e9,match=abs(field['value']-reference)<=1000,source_id=sid,reference_source_id=f'KBS_{kind}_{run_id}',locator=f"SSI kiểm toán {year}, trang PDF {field['page']}, {field['source_field']}",note='Đối chiếu giá trị; metadata kỳ KBS vẫn bị loại. Kỳ/phạm vi chính xác lấy từ PDF.'))
        if not {'assets','equity','liabilities','revenue','net_profit','cfo'}<={check['metric'] for check in checks}:
            raise DataSourceError('Chưa đủ sáu chỉ tiêu đối chiếu cột năm SSI để xác minh OCR.')
        if any(not check['match'] for check in checks):raise DataSourceError('OCR SSI lệch chỉ tiêu đối chiếu KBS; chưa sử dụng.')
        out.update(available=True,year=year,records=records,checks=checks,file=path.relative_to(root).as_posix(),published_at=published.isoformat(),sha256=checksum)
        out['sources']=[dict(source_id=sid,url_or_file=url,retrieved_at=meta['retrieved_at'],page_or_table='Audited consolidated statements, OCR verified rows; '+','.join(str(p['page']) for p in pages),notes=f'Published {published}; SHA256 {checksum}; period/scope/balance/profit identities verified; selected values cross-checked.'),dict(source_id=f'SSI_DISCLOSURE_{year}_{run_id}',url_or_file=disclosure,retrieved_at=meta['retrieved_at'],page_or_table='Publication date',notes='Official issuer disclosure confirms publication date; source HTML cached.')]
        out['warnings']=[f'SSI dùng BCTC hợp nhất kiểm toán {year} từ PDF chính thức; năm {year-1} lấy cột so sánh đã trình bày lại. Không sửa metadata KBS.']
    except (DataSourceError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        out['errors'].append(dict(stage='ssi_issuer',message=str(exc)))
    return out
