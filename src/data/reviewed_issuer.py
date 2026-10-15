"""Verified-document fallback for scanned issuer annual statements.

Only versioned, visually reviewed transcriptions are supported. This is not
general OCR and never corrects ambiguous provider metadata in place.
"""
from datetime import date
import hashlib,json
from src.data.providers import DataSourceError
from src.data.reference_miner import cached_file
from src.data.normalize import FIELD_IDS

SUPPORTED={'VIC': 'VIC_2025.json'}


def reviewed_records(snapshot,content,ticker,as_of,source_id):
    if snapshot['ticker']!=ticker or snapshot['scope']!='consolidated' or snapshot['business_type']!=1 or snapshot['audit']!='KT':
        raise DataSourceError('Bản chép BCTC sai mã/phạm vi/loại báo cáo/kiểm toán.')
    if not content.startswith(b'%PDF-') or hashlib.sha256(content).hexdigest()!=snapshot['sha256']:
        raise DataSourceError('PDF khác bản BCTC đã kiểm tra; không dùng bản chép.')
    year=snapshot['year']
    if isinstance(year,bool) or not isinstance(year,int) or snapshot['period_begin']!=f'{year}-01-01' or snapshot['period_end']!=f'{year}-12-31':
        raise DataSourceError('Bản chép BCTC sai kỳ năm.')
    published=date.fromisoformat(snapshot['published_at'])
    if published<=date(year,12,31) or published>as_of:raise DataSourceError('BCTC chưa công bố tại ngày phân tích.')
    multiplier={'VND':1,'VND_million':1_000_000}.get(snapshot['unit'])
    if multiplier is None:raise DataSourceError('Đơn vị BCTC không được hỗ trợ.')
    records=[]
    for y,column in [(year,'value'),(year-1,'previous')]:
        values={k:f[column] for k,f in snapshot['fields'].items()}
        if any(isinstance(v,bool) or not isinstance(v,int) for v in values.values()):raise DataSourceError('Số tiền bản chép không hợp lệ.')
        if values['assets']!=values['liabilities']+values['equity']:raise DataSourceError('Bản chép không cân đối tài sản/nợ/vốn.')
        if values['net_profit']!=values['parent_profit']+values['non_controlling_profit']:raise DataSourceError('Phân bổ lợi nhuận bản chép không khớp.')
        if values.get('interest_paid',0)>0 or values.get('capex_cash',0)>0:raise DataSourceError('Dòng chi tiền có dấu sai.')
        for kind in ('balance','income','cashflow'):
            fields={k:dict(value=f[column]*multiplier,unit='VND',source_id=source_id,page=f['page'],source_field='PDF row '+f['row'],
                           source_value=f[column],source_unit=snapshot['unit'],unit_multiplier=multiplier,
                           period=str(y),period_begin=f'{y}-01-01',period_end=f'{y}-12-31',published_at=published.isoformat(),
                           statement_scope='consolidated',extraction_method='checksum_bound_reviewed_transcription',formula=f.get('formula'))
                    for k,f in snapshot['fields'].items() if f['kind']==kind}
            records.append(dict(year=y,period_begin=f'{y}01',period_end=f'{y}-12-31',scope='consolidated',business_type=1,
                                audit='KT',kind=kind,source_id=source_id,published_at=published.isoformat(),fields=fields))
    return records


def provider_value_checks(records,snapshots,source_ids):
    """Numeric comparison only; invalid KBS dates remain rejected, not repaired."""
    checks=[]
    for record in records:
        kind=record['kind'];payload=snapshots.get(kind,{})
        heads=payload.get('Head',[])
        if [h.get('ID') for h in heads]!=[1,2,3,4]:continue
        selected=[h for h in heads if h.get('YearPeriod')==record['year'] and h.get('TermCode')=='N' and h.get('United')=='HN']
        if len(selected)!=1:continue
        rows=[r for group in payload.get('Content',{}).values() for r in group]
        for key,field in record['fields'].items():
            values=[r.get('Value'+str(selected[0]['ID'])) for r in rows if FIELD_IDS[kind].get(r.get('ReportNormID'))==key]
            if len(values)!=1 or values[0] is None or isinstance(values[0],bool):continue
            try:reference=float(values[0])*1000
            except (ValueError,TypeError):continue
            import math
            if not math.isfinite(reference):continue
            checks.append(dict(metric=key,period=str(record['year']),match=abs(field['value']-reference)<=max(1_000_000,abs(field['value'])*.001),
                               primary_vnd=field['value'],reference_vnd=reference,source_id=field['source_id'],
                               reference_source_id=source_ids.get(kind),locator=f"Official PDF page {field['page']}, {field['source_field']}; KBS numeric column only, metadata not accepted."))
    return checks


def collect_reviewed_issuer(ticker,as_of,root,run_id):
    out=dict(available=False,records=[],checks=[],sources=[],warnings=[],errors=[])
    if ticker not in SUPPORTED:return out
    try:
        snapshot=json.loads((root/'config/issuer_snapshots'/SUPPORTED[ticker]).read_text(encoding='utf-8'))
        if date.fromisoformat(snapshot['published_at'])>as_of:return out
        path=root/f"data/raw/documents/{ticker}_{snapshot['year']}_audited.pdf"
        content,meta=cached_file(snapshot['url'],path,snapshot['published_at'],max_size=50_000_000)
        sid=f"{ticker}_AUDITED_{snapshot['year']}_{run_id}"
        records=reviewed_records(snapshot,content,ticker,as_of,sid)
        inputs={};ids={}
        for kind in ('balance','income','cashflow'):
            raw=root/'data/raw/financials'/f'{run_id}_{kind}.json'
            if raw.exists():
                try:inputs[kind]=json.loads(raw.read_text(encoding='utf-8'));ids[kind]=f'KBS_{kind}_{run_id}'
                except (ValueError,OSError):continue
        out.update(available=True,records=records,checks=provider_value_checks(records,inputs,ids),
                   year=snapshot['year'],scope=snapshot['scope'],name=snapshot['name'],file=path.relative_to(root).as_posix(),sha256=snapshot['sha256'])
        out['sources']=[dict(source_id=sid,url_or_file=snapshot['url'],retrieved_at=meta['retrieved_at'],page_or_table='PDF pages 9–16; current/comparative annual columns',notes=snapshot['review_method']+' SHA256 '+snapshot['sha256'])]
        out['warnings']=['BCTC '+ticker+' dùng bản chép đã kiểm tra trực quan, chỉ nhận đúng PDF chính thức khớp SHA256. Không sửa ngày hoặc ánh xạ cột KBS sai. Đối chiếu chỉ xác nhận các chỉ tiêu được liệt kê, không toàn bộ BCTC.']
        if as_of>=date(snapshot['year']+2,4,1):out['warnings'].append('Bộ đọc BCTC đã kiểm tra chưa có năm mới; cần cập nhật tài liệu có nguồn.')
    except (DataSourceError,KeyError,TypeError,ValueError,OSError) as exc:
        out['errors'].append(dict(stage='reviewed_issuer',message=str(exc)))
    return out
