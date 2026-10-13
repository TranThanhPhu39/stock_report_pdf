"""Checksum-bound transcription of TCH's reviewed official fiscal-year PDF.

The source has poor OCR and ambiguous KBS columns. The versioned transcription
is accepted only after downloading the identical issuer document. Never repair
KBS dates or apply this transcription to another PDF/year.
"""
from datetime import date
import hashlib,json
from bs4 import BeautifulSoup
from src.data.providers import DataSourceError
from src.data.reference_miner import cached_file
from src.data.shs_issuer import folded


def snapshot_records(snapshot,content,as_of,source_id):
    if snapshot['ticker']!='TCH' or snapshot['scope']!='consolidated' or snapshot['unit']!='VND':
        raise DataSourceError('Snapshot TCH sai doanh nghiệp/phạm vi/đơn vị.')
    if hashlib.sha256(content).hexdigest()!=snapshot['sha256'] or not content.startswith(b'%PDF-'):
        raise DataSourceError('PDF TCH khác bản đã kiểm tra; không dùng số liệu snapshot.')
    year=snapshot['year']
    if snapshot['period_begin']!=f'{year}-04-01' or snapshot['period_end']!=f'{year+1}-03-31':
        raise DataSourceError('Snapshot TCH sai niên độ 01/04–31/03.')
    published=date.fromisoformat(snapshot['published_at'])
    if published<=date.fromisoformat(snapshot['period_end']) or published>as_of:
        raise DataSourceError('BCTC TCH chưa được công bố tại ngày phân tích.')
    records=[]
    for y,column in [(year,'value'),(year-1,'previous')]:
        fields=snapshot['fields']
        values={key:f[column] for key,f in fields.items()}
        if any(isinstance(v,bool) or not isinstance(v,int) for v in values.values()):
            raise DataSourceError('Snapshot TCH có giá trị tiền không hợp lệ.')
        if values['assets']!=values['liabilities']+values['equity']:
            raise DataSourceError('Snapshot TCH không cân đối tài sản/nợ/vốn.')
        if values['net_profit']!=values['parent_profit']+values['non_controlling_profit']:
            raise DataSourceError('Snapshot TCH không khớp phân bổ lợi nhuận.')
        for kind in ('income','balance','cashflow'):
            normalized={key:dict(value=f[column],unit='VND',source_id=source_id,
                                source_field='PDF row '+f['row'],page=f['page'],
                                source_label=key,source_value=f[column],unit_multiplier=1,
                                period=str(y),period_begin=f'{y}-04-01',period_end=f'{y+1}-03-31',
                                published_at=published.isoformat(),statement_scope='consolidated',
                                extraction_method='checksum_bound_reviewed_transcription')
                        for key,f in fields.items() if f['kind']==kind}
            records.append(dict(year=y,period_begin=f'{y}04',period_end=f'{y+1}-03-31',
                                scope='consolidated',business_type=1,audit='KT',kind=kind,
                                published_at=published.isoformat(),source_id=source_id,fields=normalized))
    return records


def collect_tch_issuer(ticker,as_of,root,run_id):
    out=dict(available=False,records=[],checks=[],sources=[],warnings=[],errors=[])
    if ticker!='TCH':return out
    try:
        snapshot=json.loads((root/'config/issuer_snapshots/TCH_2025.json').read_text(encoding='utf-8'))
        if date.fromisoformat(snapshot['published_at'])>as_of:
            out['warnings'].append('BCTC TCH đã kiểm tra công bố sau ngày phân tích; không dùng.')
            return out
        folder=root/'data/raw/documents';folder.mkdir(parents=True,exist_ok=True)
        html,_=cached_file(snapshot['disclosure_url'],folder/'TCH_2025_disclosure.html',as_of.isoformat(),max_size=5_000_000)
        body=folded(BeautifulSoup(html,'html.parser').get_text(' ',strip=True))
        if '26/6/2026' not in body or '01/04/2025' not in body or '31/03/2026' not in body:
            raise DataSourceError('Trang công bố TCH không khớp ngày/niên độ đã kiểm tra.')
        path=folder/'TCH_2025_audited.pdf'
        content,meta=cached_file(snapshot['url'],path,snapshot['published_at'],max_size=40_000_000)
        sid='TCH_AUDITED_2025_'+run_id
        records=snapshot_records(snapshot,content,as_of,sid)
        out.update(available=True,records=records,year=snapshot['year'],file=path.relative_to(root).as_posix(),
                   name=snapshot['name'],scope=snapshot['scope'],sha256=snapshot['sha256'],published_at=snapshot['published_at'])
        out['sources']=[dict(source_id=sid,url_or_file=snapshot['url'],retrieved_at=meta['retrieved_at'],
                             page_or_table='Audited consolidated FY 2025, PDF pages 7–11; current and comparative columns',
                             notes=snapshot['review_method']+' SHA256 '+snapshot['sha256']),
                        dict(source_id='TCH_DISCLOSURE_'+run_id,url_or_file=snapshot['disclosure_url'],
                             retrieved_at=meta['retrieved_at'],page_or_table='Publication date and fiscal period',
                             notes='Official issuer disclosure; fiscal year starts 1 April.')]
        out['warnings']=['TCH dùng bản chép số liệu đã kiểm tra trực quan từ PDF kiểm toán chính thức, chỉ nhận đúng SHA256. Năm tài chính 2025 là 01/04/2025–31/03/2026; cột so sánh là 2024. Không sửa hoặc dùng các cột KBS bị trùng. Chưa xác minh độc lập mọi chỉ tiêu.']
        if as_of>=date(2027,4,1):out['warnings'].append('Nguồn TCH đã xác minh hiện dừng ở niên độ kết thúc 31/03/2026; cần kiểm tra BCTC mới trước khi sử dụng.')
    except (DataSourceError,OSError,ValueError,KeyError,TypeError) as exc:
        out['errors'].append(dict(stage='tch_issuer',message=str(exc)))
    return out
