"""Dated Vietcap income quarters; keep undisclosed scope out of valuation."""
from datetime import date, datetime
import calendar
import json

from src.analysis.valuation import number
from src.data.providers import DataSourceError, VN_TIME, download

BASE = 'https://iq.vietcap.com.vn/api/iq-insight-service/v1/company'
INCOME_FIELDS = {'revenue':'isa3', 'net_profit':'isa20', 'parent_profit':'isa22',
                 'net_interest_income':'isb27'}


def parse_quarters(payload, ticker, as_of, source_id, industry_group):
    data=payload.get('data',{})
    if not isinstance(data,dict) or not isinstance(data.get('quarters'),list):
        raise DataSourceError('Vietcap không có danh sách quý đúng cấu trúc.')
    records={};organ_codes=set()
    for row in data['quarters']:
        if row.get('ticker')!=ticker or not isinstance(row.get('organCode'),str) or not row['organCode']:
            raise DataSourceError('Vietcap trả sai mã doanh nghiệp.')
        # organCode is an internal identifier (e.g. HHSF for ticker TCH).
        organ_codes.add(row['organCode'])
        if len(organ_codes)>1:
            raise DataSourceError('Vietcap có mã định danh doanh nghiệp không nhất quán.')
        year=row.get('yearReport');quarter=row.get('lengthReport')
        if isinstance(year,bool) or not isinstance(year,int) or isinstance(quarter,bool) or quarter not in (1,2,3,4):
            raise DataSourceError('Vietcap có kỳ quý không hợp lệ.')
        end_month=quarter*3
        end=date(year,end_month,calendar.monthrange(year,end_month)[1])
        begin=date(year,end_month-2,1)
        try:
            published=date.fromisoformat(str(row.get('publicDate',''))[:10])
            updated=date.fromisoformat(str(row.get('updateDate',''))[:10])
        except ValueError:
            continue
        if published<end or end>as_of or published>as_of or updated>as_of:
            continue
        fields={}
        for key,code in INCOME_FIELDS.items():
            if (key=='revenue' and industry_group=='bank') or (key=='net_interest_income' and industry_group!='bank'):
                continue
            v=row.get(code)
            if v is not None and not number(v):
                raise DataSourceError('Giá trị quý không hữu hạn hoặc không phải số.')
            if v is not None:
                fields[key]=dict(value=v,unit='VND',source_id=source_id,source_field=code,
                                 period=end.isoformat(),period_begin=begin.isoformat(),period_end=end.isoformat(),
                                 published_at=published.isoformat(),available_at=max(published,updated).isoformat(),
                                 statement_scope='vendor_not_disclosed')
        record=dict(year=year,quarter=quarter,period_begin=begin.isoformat(),period_end=end.isoformat(),
                    published_at=published.isoformat(),updated_at=updated.isoformat(),
                    scope='vendor_not_disclosed',basis='quarter',fields=fields)
        key=(year,quarter)
        if key in records and records[key]!=record:
            raise DataSourceError('Vietcap có các bản quý trùng mâu thuẫn; không tự chọn bản.')
        records[key]=record
    return sorted(records.values(),key=lambda r:r['period_end'],reverse=True)


def quarter_observation(records):
    out=dict(available=False,reason='Chưa đủ bốn quý liên tiếp có cùng nguồn/cơ sở.',fields={},
             usable_for_valuation=False,scope='vendor_not_disclosed')
    if not records:return out
    latest=records[0];index=latest['year']*4+latest['quarter']-1
    lookup={r['year']*4+r['quarter']-1:r for r in records}
    if not all(i in lookup for i in range(index-3,index+1)):return out
    quarters=[lookup[i] for i in range(index-3,index+1)]
    for key in INCOME_FIELDS:
        inputs=[q['fields'].get(key) for q in quarters]
        if all(f and number(f.get('value')) for f in inputs):
            out['fields'][key]=dict(value=sum(f['value'] for f in inputs),unit='VND',inputs=inputs,
                                   formula='Tổng bốn quý riêng liên tiếp')
    if 'net_profit' not in out['fields']:return out
    out.update(available=True,period_begin=quarters[0]['period_begin'],period_end=latest['period_end'],
               quarters=[f"{q['year']}-Q{q['quarter']}" for q in quarters],
               reason='Tổng bốn quý theo Vietcap; phạm vi từng quý chưa được nguồn khai báo.',
               note='Quan sát TTM từ bốn quý riêng của một nhà cung cấp. Chưa đối chiếu độc lập phạm vi và mọi quý; không dùng số này thay TTM đã xác minh, P/E định giá hoặc khuyến nghị. Không cộng CFO do cơ sở riêng quý/lũy kế chưa xác nhận.')
    return out


def collect_quarterly(ticker,as_of,financial,root,run_id):
    out=dict(available=False,records=[],sources=[],errors=[],warnings=[],checks=[],
             reason='Chưa có số liệu quý hợp lệ.',ttm=quarter_observation([]))
    url=f'{BASE}/{ticker}/financial-statement?section=INCOME_STATEMENT'
    try:
        raw=download(url,timeout=15)
        folder=root/'data/raw/quarterly';folder.mkdir(parents=True,exist_ok=True)
        path=folder/f'{run_id}_income.json';path.write_bytes(raw)
        sid=f'VIETCAP_QUARTERLY_{run_id}'
        out['sources'].append(dict(source_id=sid,url_or_file=url,retrieved_at=datetime.now(VN_TIME).isoformat(),
                                  page_or_table='INCOME_STATEMENT.quarters',
                                  notes=f'Raw snapshot {path.relative_to(root).as_posix()}; monetary VND; scope not disclosed; publication and revision dates filtered.'))
        payload=json.loads(raw)
        records=parse_quarters(payload,ticker,as_of,sid,financial.get('industry_group'))
        # Independently check the VND scale against the selected annual inputs.
        primary_year=max((p['year'] for p in financial.get('periods',[])),default=None)
        for annual in payload.get('data',{}).get('years',[]):
            if annual.get('yearReport')!=primary_year:continue
            if annual.get('ticker')!=ticker:continue
            if annual.get('publicDate','9999')[:10]>as_of.isoformat() or annual.get('updateDate','9999')[:10]>as_of.isoformat():continue
            primary=next((p for p in financial.get('periods',[]) if p['year']==annual.get('yearReport') and p.get('period_end')==f"{p['year']}-12-31"),None)
            if not primary:continue
            for key in ('net_profit','parent_profit'):
                a=primary['fields'].get(key,{}).get('value');b=annual.get(INCOME_FIELDS[key])
                if number(a) and number(b):
                    out['checks'].append(dict(metric=key,period=str(primary['year']),match=abs(a-b)<=max(1e6,abs(a)*.001),
                                              primary_vnd=a,reference_vnd=b,source_id=sid))
        scale_ok=bool(out['checks']) and all(c['match'] for c in out['checks'])
        if not scale_ok:
            out['warnings'].append('Dữ liệu quý Vietcap chưa khớp thang VND với tài chính năm chính; không dùng số quý để tính TTM.')
        out.update(available=bool(records),records=records,
                   ttm=quarter_observation(records) if scale_ok else quarter_observation([]),
                   reason='Quý riêng theo Vietcap, tiền theo VND; nguồn chưa khai báo phạm vi từng quý. Tài chính/định giá năm được giữ riêng.')
    except (DataSourceError,ValueError,TypeError,KeyError,OSError) as exc:
        out['errors'].append(dict(stage='quarterly',message=str(exc)))
    return out
