"""Read pinned issuer bank statements; never repair a vendor's period metadata."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pymupdf

from src.data.providers import DataSourceError, VN_TIME
from src.data.reference_miner import cached_file
from src.data.shs_issuer import folded
from src.data.normalize import FIELD_IDS

AMOUNT = re.compile(r'(?<![\w\d])\(?-?\d{1,3}(?:[.,]\s?\d{3})+\)?(?!\d)')
BANK_NAMES = {'MBB':'Ngân hàng TMCP Quân đội', 'CTG':'Ngân hàng TMCP Công thương Việt Nam', 'TCB':'Ngân hàng TMCP Kỹ thương Việt Nam'}
LABELS = {
    'balance': {
        'assets': ['tong cong tai san', 'tong tai san', 'tong tai san co', 'total assets'],
        'liabilities': ['tong no phai tra', 'total liabilities'],
        'equity': ['tong von chu so huu', 'von chu so huu', 'tong von', 'total shareholders’ equity'],
        'non_controlling_equity': ['loi ich cua co dong khong kiem soat', 'loi ich co dong khong kiem soat', 'non-controlling interests'],
        'customer_deposits': ['tien gui cua khach hang', 'tien gui khach hang', 'deposits from customers'],
    },
    'income': {
        'net_interest_income': ['thu nhap lai thuan', 'net interest and similar income'],
        'net_profit': ['loi nhuan sau thue', 'profit after tax'],
        'parent_profit': ['loi nhuan sau thue thuoc ve ngan hang me', 'loi nhuan sau thue thuoc ve co dong cua ngan hang', 'loi nhuan thuan cua chu so huu', 'net profit contributed to the bank’s shareholders'],
        'pretax_profit': ['tong loi nhuan truoc thue', 'loi nhuan truoc thue', 'profit before tax'],
        'pre_provision_profit': ['loi nhuan thuan tu hoat dong kinh doanh truoc chi phi du', 'loi nhuan thuan tu hoat dong kinh doanh truoc chi phi du phong rui ro tin dung', 'profit before provision for credit losses'],
        'operating_cost': ['chi phi hoat dong', 'operating expenses'],
        'credit_provision': ['chi phi du phong rui ro tin dung', 'provision expenses for credit losses'],
        'non_controlling_profit': ['loi ich cua co dong khong kiem soat', 'loi ich co dong khong kiem soat', 'non-controlling interests'],
    },
    'cashflow': {'cfo': ['luu chuyen tien thuan tu hoat dong kinh doanh', 'luu chuyen tien thuan su dung tu hoat dong kinh doanh', 'luu chuyen tien thuan su dung tu hoat dong', 'net cash flows from operating activities']},
}
REQUIRED = {'balance': {'assets', 'liabilities', 'equity', 'non_controlling_equity'},
            'income': {'net_profit', 'parent_profit', 'net_interest_income', 'pretax_profit'},
            'cashflow': {'cfo'}}


def label_text(value):
    # Scanner punctuation in labels is harmless; never correct numeric characters.
    return re.sub(r'[^a-z0-9]+', ' ', folded(value)).strip()


def amount_pair(text):
    matches = list(AMOUNT.finditer(text))
    if len(matches) != 2:
        return None
    if any(m[0].startswith('(') != m[0].endswith(')') for m in matches):
        return None
    return tuple((-1 if m[0].startswith(('(', '-')) else 1)*int(re.sub(r'\D', '', m[0])) for m in matches)


def read_bank_pages(path, root, manifest):
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    contract = {'pages': manifest['pages'], 'row_regions': manifest.get('row_regions', [])}
    cache = root/'data/processed'/f'{checksum[:16]}_bank_pages_v3.json'
    if cache.exists():
        saved = json.loads(cache.read_text(encoding='utf-8'))
        if saved.get('sha256') == checksum and saved.get('page_contract') == contract:
            return saved['pages']
    engine = shutil.which('tesseract')
    if not engine and Path('C:/Program Files/Tesseract-OCR/tesseract.exe').exists():
        engine = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
    folder = root/'tmp/pdfs'/f'bank_{checksum[:16]}'
    folder.mkdir(parents=True, exist_ok=True)

    def read(spec):
        with pymupdf.open(path) as doc:
            page = doc[spec['page']-1]
            clip = page.rect
            if 'side' in spec:
                side = spec['side']
                clip = pymupdf.Rect(page.rect.width*side/2, 0, page.rect.width*(side+1)/2, page.rect.height)
            text = page.get_text(sort=True, clip=clip)
            mode = 'embedded_text'
            if len(text.strip()) < 200:
                if not engine:
                    raise DataSourceError('BCTC ngân hàng scan cần Tesseract vie+eng; chưa sử dụng số liệu.')
                image = folder/f"{spec['page']}_{spec.get('side',0)}.png"
                # Exclude scanner binding marks outside the printed table margins.
                clip = pymupdf.Rect(page.rect.width*.09, page.rect.height*.025, page.rect.width*.94, page.rect.height*.95)
                page.get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=clip).save(image)
                done = subprocess.run([engine, str(image), 'stdout', '-l', 'vie+eng', '--psm', '6'],
                    capture_output=True, encoding='utf-8', timeout=60, env={**os.environ, 'OMP_THREAD_LIMIT':'1'})
                if done.returncode:
                    raise DataSourceError('OCR BCTC ngân hàng thất bại.')
                text, mode = done.stdout, 'ocr'
        return {**spec, 'text':text, 'extraction_mode':mode}

    with ThreadPoolExecutor(max_workers=3) as pool:
        pages = list(pool.map(read, manifest['pages']))
    # These regions are reviewed against the pinned original PDF. Read digits at
    # three resolutions; accept a two-out-of-three numeric consensus, not repairs.
    for spec in manifest.get('row_regions', []):
        if not engine:
            raise DataSourceError('Vùng số scan cần Tesseract; chưa sử dụng số liệu.')
        trials = []
        with pymupdf.open(path) as doc:
            page = doc[spec['page']-1]
            clip = pymupdf.Rect(*(n*(page.rect.width if i % 2 == 0 else page.rect.height) for i,n in enumerate(spec['rect'])))
            for scale in (4, 5, 6):
                image = folder/f"{spec['page']}_{spec['key']}_{scale}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip).save(image)
                done = subprocess.run([engine, str(image), 'stdout', '-l', 'eng', '--psm', '7'],
                    capture_output=True, encoding='utf-8', timeout=60, env={**os.environ, 'OMP_THREAD_LIMIT':'1'})
                if done.returncode:
                    raise DataSourceError('OCR vùng số BCTC thất bại.')
                trials.append({'scale':scale, 'text':done.stdout, 'values':amount_pair(done.stdout)})
        counts = Counter(t['values'] for t in trials if t['values'] is not None)
        if not counts or counts.most_common(1)[0][1] < 2:
            raise DataSourceError(f"Vùng số {spec['key']} chưa có đồng thuận OCR.")
        values = counts.most_common(1)[0][0]
        digits = lambda v: f'({abs(v):,})' if v < 0 else f'{v:,}'
        pages.append({**spec, 'text':spec['label']+' '+ ' '.join(digits(v) for v in values),
                      'extraction_mode':'ocr_region_consensus', 'ocr_trials':trials,
                      'label_verification':'visually_reviewed_pinned_manifest'})
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({'sha256':checksum, 'page_contract':contract, 'pages':pages}, ensure_ascii=False), encoding='utf-8')
    return pages


def parse_bank_pages(pages, manifest, source_id):
    if manifest['unit_multiplier'] != 1_000_000 or manifest['period_end'] > manifest['available_at']:
        raise DataSourceError('Đơn vị hoặc thời điểm khả dụng BCTC ngân hàng không hợp lệ.')
    full = folded(' '.join(p['text'] for p in pages))
    if folded(manifest['identity']) not in full:
        raise DataSourceError('PDF chưa xác nhận đúng ngân hàng.')
    if folded(manifest['assurance_label']) not in full:
        raise DataSourceError('PDF chưa xác nhận kiểm toán/soát xét.')
    fields = {kind:{} for kind in REQUIRED}
    regions = {(p['kind'],p['key']) for p in pages if p.get('extraction_mode') == 'ocr_region_consensus'}
    for kind in REQUIRED:
        selected = [p for p in pages if p.get('kind') == kind]
        body = folded(' '.join(p['text'] for p in selected))
        if not selected or not all(folded(s) in body for s in manifest['headers'][kind]):
            raise DataSourceError(f'Chưa xác nhận kỳ, đơn vị và thứ tự cột {kind}.')
        anchor = ' '.join(folded(manifest['column_headers'][kind]).split())
        if any(anchor not in ' '.join(folded(p['text']).split()) for p in selected if p.get('extraction_mode') != 'ocr_region_consensus'):
            raise DataSourceError(f'Thứ tự cột hiện tại/kỳ so sánh {kind} chưa xác nhận.')
        for page in selected:
            lines = [line.strip() for line in page['text'].splitlines() if line.strip()]
            for i, line in enumerate(lines):
                row = line
                for following in lines[i+1:i+3]:
                    if len(AMOUNT.findall(row)) >= 2:break
                    row += ' '+following
                amounts = list(AMOUNT.finditer(row))
                if len(amounts) != 2:continue
                prefix = row[:amounts[0].start()].strip().lstrip('|]‘’ ')
                prefix = re.sub(r'^(?:\d+|[IVX]+)\.?\s+', '', prefix)
                prefix = re.sub(r'[\d.,\s]+$', '', prefix)
                label = label_text(prefix)
                for key, aliases in LABELS[kind].items():
                    if label not in {label_text(a) for a in aliases}:continue
                    if (kind,key) in regions and page.get('extraction_mode') != 'ocr_region_consensus':continue
                    values = amount_pair(row)
                    if values is None:continue
                    multiplier = manifest['unit_multiplier']
                    value, previous = (v*multiplier for v in values)
                    # Expense rows are displayed as positive costs in the bank metrics.
                    if key in {'operating_cost', 'credit_provision'}:
                        value, previous = abs(value), abs(previous)
                    field = dict(value=value, previous=previous, unit='VND', unit_multiplier=multiplier,
                        source_value=values[0], source_id=source_id, source_field='PDF: '+prefix,
                        source_label=prefix, page=page['page'], page_side=page.get('side'),
                        extraction_mode=page.get('extraction_mode','embedded_text'), source_row=row,
                        period=manifest['period_end'], published_at=None, available_at=manifest['available_at'],
                        availability_basis=manifest['availability_basis'], statement_scope='consolidated')
                    if page.get('ocr_trials'):
                        field.update(ocr_trials=page['ocr_trials'], source_region=page['rect'],
                                     label_verification=page['label_verification'])
                    old = fields[kind].get(key)
                    if old and (old['value'],old['previous']) != (value,previous):
                        raise DataSourceError(f'PDF có nhiều dòng {key} khác giá trị; không tự chọn.')
                    fields[kind][key] = field
        missing = REQUIRED[kind]-fields[kind].keys()
        if missing:raise DataSourceError(f'Bảng {kind} thiếu dòng đã xác minh: {sorted(missing)}')
    tolerance = manifest['unit_multiplier']
    for column in ('value','previous'):
        b = fields['balance']; inc = fields['income']
        if abs(b['assets'][column]-b['liabilities'][column]-b['equity'][column]) > tolerance:
            raise DataSourceError('Bảng cân đối ngân hàng không cân bằng.')
        if not 0 <= b['non_controlling_equity'][column] < b['equity'][column]:
            raise DataSourceError('Vốn cổ đông không kiểm soát ngân hàng ngoài miền hợp lệ.')
        if 'non_controlling_profit' in inc and abs(inc['net_profit'][column]-inc['parent_profit'][column]-inc['non_controlling_profit'][column]) > tolerance:
            raise DataSourceError('Phân bổ LNST ngân hàng không khớp tổng.')
    return fields


def compare_bank_values(fields, snapshots, manifest, source_id, run_id, reference_source_ids=None):
    checks = []
    for kind, data in snapshots.items():
        heads = [h for h in data.get('Head',[]) if h.get('YearPeriod') == manifest['year']
                 and h.get('United') == 'HN' and h.get('TermCode') == 'N'
                 and h.get('BusinessType') == 3 and h.get('DatePubDepartment') and h.get('LastUpdate')
                 and h.get('DatePubDepartment','')[:10] <= manifest['available_at']
                 and h.get('LastUpdate','')[:10] <= manifest['available_at']]
        if len(heads) != 1:continue
        values = {FIELD_IDS[kind].get(r.get('ReportNormID')):r.get(f"Value{heads[0]['ID']}")
                  for rows in data.get('Content',{}).values() for r in rows}
        for key in REQUIRED[kind]:
            field, other = fields[kind].get(key), values.get(key)
            if not field or other is None:continue
            reference = float(other)*1000
            checks.append(dict(metric=key,period=str(manifest['year']),actual_billion_vnd=field['value']/1e9,
                reference_billion_vnd=reference/1e9,match=abs(field['value']-reference)<=manifest['unit_multiplier'],
                source_id=source_id,reference_source_id=(reference_source_ids or {}).get(kind,f'KBS_{kind}_{run_id}'),locator=f"PDF trang {field['page']}: {field['source_label']}",
                note='Chỉ đối chiếu giá trị; kỳ/phạm vi/đơn vị lấy từ BCTC gốc, không sửa metadata KBS.'))
    required = set().union(*REQUIRED.values())
    if not required <= {c['metric'] for c in checks} or any(not c['match'] for c in checks):
        raise DataSourceError('BCTC ngân hàng chưa khớp đủ chín chỉ tiêu đối chiếu KBS; chưa dùng số liệu.')
    return checks


def collect_bank_issuer(ticker, as_of, root, run_id, snapshots=None, *, include_interim=True, reference_source_ids=None):
    out = dict(available=False, records=[], checks=[], sources=[], warnings=[], errors=[], interim=None)
    config = root/'config/bank_issuer_sources.json'
    if not config.exists():return out
    entries = json.loads(config.read_text(encoding='utf-8')).get(ticker,[])
    annual = [m for m in entries if m['period_type']=='annual' and date.fromisoformat(m['available_at'])<=as_of]
    if not annual:return out
    manifest = max(annual,key=lambda m:m['period_end'])
    try:
        def load(m):
            path = root/'data/raw/documents'/f"{ticker}_{m['period_end']}_{m['sha256'][:12]}.pdf"
            raw, meta = cached_file(m['url'],path,m['available_at'],max_size=80_000_000)
            if hashlib.sha256(raw).hexdigest()!=m['sha256']:
                raise DataSourceError('BCTC ngân hàng thay đổi checksum; cần kiểm tra bản mới.')
            sid = f"BANK_{ticker}_{m['period_end']}_{run_id}"
            fields = parse_bank_pages(read_bank_pages(path,root,m),m,sid)
            source = dict(source_id=sid,url_or_file=m['url'],retrieved_at=meta['retrieved_at'],
                page_or_table='; '.join(f"{p['page']}:{p.get('kind','identity')}" for p in m['pages']),
                notes=f"Issuer {ticker}; {m['hosting']}; SHA256 {m['sha256']}; availability {m['available_at']} ({m['availability_basis']}); consolidated; million VND")
            return fields, source, path
        fields, source, path = load(manifest)
        if snapshots is None:
            snapshots = {kind:json.loads((root/'data/raw/financials'/f'{run_id}_{kind}.json').read_text(encoding='utf-8')) for kind in REQUIRED}
        checks = compare_bank_values(fields,snapshots,manifest,source['source_id'],run_id,reference_source_ids)
        # Do not promote optional OCR rows to metrics without numeric comparison.
        for kind,values in fields.items():
            for key in list(values):
                if key not in REQUIRED[kind] and key != 'non_controlling_profit':
                    heads = [h for h in snapshots[kind].get('Head',[]) if h.get('YearPeriod') == manifest['year'] and h.get('United') == 'HN']
                    reference = next((r.get(f"Value{heads[0]['ID']}") for rows in snapshots[kind].get('Content',{}).values() for r in rows if FIELD_IDS[kind].get(r.get('ReportNormID')) == key),None) if len(heads)==1 else None
                    if reference is None or abs(values[key]['value']-float(reference)*1000)>manifest['unit_multiplier']:
                        del values[key]
        for year, column in [(manifest['year'],'value'),(manifest['year']-1,'previous')]:
            for kind, values in fields.items():
                mapped = {k:{**v,'value':v[column],'source_value':v[column]/manifest['unit_multiplier'],'period':str(year)} for k,v in values.items()}
                out['records'].append(dict(year=year,period_end=f'{year}-12-31',period_begin=f'{year}01',
                    published_at=None,available_at=manifest['available_at'],scope='consolidated',business_type=3,audit='KT',kind=kind,fields=mapped,source_id=source['source_id']))
        out.update(available=True, year=manifest['year'],checks=checks,file=path.relative_to(root).as_posix(),sha256=manifest['sha256'],
                   available_at=manifest['available_at'],availability_note=manifest['availability_note'],
                   hosting=manifest['hosting'],scope='consolidated',unit_multiplier=manifest['unit_multiplier'])
        out['sources'].append(source)
        if reference_source_ids:
            from src.data.research import financial_url
            out['sources'].extend(dict(source_id=reference_source_ids[kind],url_or_file=financial_url(ticker,kind),
                retrieved_at=datetime.now(VN_TIME).isoformat(),page_or_table=f'{ticker} {kind}',
                notes='KBS peer raw values used for selected numeric checks; invalid annual period metadata remains rejected.') for kind in REQUIRED)
        out['warnings'].append(f"{ticker}: dùng BCTC hợp nhất {manifest['year']} gốc, đã đối chiếu chín chỉ tiêu; số kỳ trước là cột so sánh của cùng PDF. {manifest['availability_note']}")
        if include_interim:
            eligible = [m for m in entries if m['period_type']=='half_year' and date.fromisoformat(m['available_at'])<=as_of]
            if eligible:
                m = max(eligible,key=lambda x:x['period_end'])
                try:
                    current, src, interim_path = load(m)
                    # An interim balance's prior column is the audited year-end balance.
                    for key in REQUIRED['balance']:
                        if abs(current['balance'][key]['previous']-fields['balance'][key]['value'])>m['unit_multiplier']:
                            raise DataSourceError('Cột đầu năm bán niên không khớp BCTC năm đã xác minh.')
                    # Optional OCR rows are not inputs until independently checked.
                    merged = {k:v for kind,group in current.items() for k,v in group.items() if k in REQUIRED[kind] or k == 'non_controlling_profit'}
                    out['interim'] = dict(valid=True,ticker=ticker,period_end=m['period_end'],period_type='half_year',
                        fields=merged,checks=[{'name':'balance_identity_and_audited_opening_balance','valid':True}],
                        file=interim_path.relative_to(root).as_posix(),source_id=src['source_id'],
                        note='Lợi nhuận/thu nhập/dòng tiền là lũy kế sáu tháng; cột so sánh cùng kỳ. Tài sản/vốn/nợ là số dư cuối kỳ và đầu năm. Không nhân đôi thành dự báo năm hoặc ghép vào P/E năm. '+m['availability_note'])
                    out['sources'].append(src)
                except (DataSourceError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
                    out['errors'].append(dict(stage='bank_interim',message=str(exc)))
    except (DataSourceError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        out['errors'].append(dict(stage='bank_issuer',message=str(exc)))
    return out
