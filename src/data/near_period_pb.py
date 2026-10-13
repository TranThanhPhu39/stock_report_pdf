"""Separate P/B research reference for companies with a non-calendar year.

The 90-day limit is an application research policy, not an accounting standard.
These observations never enter the primary valuation or investment stance.
"""
from datetime import date
import json
from src.analysis.financial import analyze_financials
from src.analysis.valuation import number
from src.analysis.price_quality import latest_price_matches
from src.data.normalize import parse_annual_financials
from src.data.providers import DataSourceError
from src.data.research import financial_url
from src.data.valuation_peers import collect_valuation_peers


def select_balance_period(records,target,as_of):
    suitable=[]
    for period in analyze_financials(records)['periods']:
        end=date.fromisoformat(period['period_end'])
        gap=(date.fromisoformat(target['period_end'])-end).days
        if not 0<=gap<=90 or end>as_of or period['scope']!=target['scope'] or period['business_type']!=target['business_type']:continue
        fields=period['fields'];equity=fields.get('equity',{}).get('value')
        nci=fields.get('non_controlling_equity',{}).get('value')
        capital=equity if period['scope'] in {'parent','separate'} else equity-nci if number(equity) and number(nci) else None
        assets=fields.get('assets',{}).get('value');liabilities=fields.get('liabilities',{}).get('value')
        if not number(assets,True) or not number(capital,True) or not number(liabilities) or not number(equity):continue
        if abs(assets-equity-liabilities)>max(1000,assets*.001):continue
        suitable.append(period)
    return max(suitable,key=lambda p:p['period_end']) if suitable else None


def collect_near_period_pb(ticker,as_of,financial,industry,valuation,market,quote_check,root,run_id):
    out=dict(available=False,usable_in_primary=False,peers=[],sources=[],excluded=[],
             reference_price_vnd=None,difference_pct=None,reason='Chưa đủ mẫu P/B gần kỳ có số dư vốn mẹ và giá đối chiếu.')
    periods=financial.get('periods',[])
    if not periods or financial.get('industry_group')!='nonfinancial' or periods[0]['period_end'].endswith('-12-31'):
        return {**out,'reason':'Mẫu gần kỳ chỉ áp dụng tham khảo cho doanh nghiệp phi tài chính có niên độ riêng.'}
    if not industry.get('available') or not number(valuation.get('book_value_per_share'),True) or not latest_price_matches(quote_check,market):return out
    target=periods[0];folder=root/'data/raw/industry';candidates=[];sources=[]
    # Only use the current run's sector-member snapshots. No old cached run or
    # unsourced ticker list can silently become a comparable.
    for symbol in sorted(set(industry.get('members',[]))-{ticker}):
        sid=f'PEER_{symbol}_balance_{run_id}';path=folder/f'{sid}.json'
        if not path.exists():continue
        try:
            records=parse_annual_financials(json.loads(path.read_text(encoding='utf-8')),'balance',as_of,sid)
            period=select_balance_period(records,target,as_of)
            if not period:continue
            candidates.append(dict(ticker=symbol,financial=analyze_financials([dict(period,business_type=target['business_type'])])))
            sources.append(dict(source_id=sid,url_or_file=financial_url(symbol,'balance'),
                                retrieved_at=as_of.isoformat(),page_or_table='Annual balance sheet; period '+period['period_end'],
                                notes=f'Current-run raw snapshot {path.relative_to(root).as_posix()}; thousand VND converted to VND; scope and balance checked, not fully independently verified.'))
        except (DataSourceError,OSError,ValueError,TypeError,KeyError):continue
    candidates.sort(key=lambda p:(-p['financial']['periods'][0]['fields']['assets']['value'],p['ticker']))
    selected=candidates[:4];ids={p['ticker'] for p in selected}
    prepared=dict(name=industry['name'],period_end=target['period_end'],scope=target['scope'],peers=selected)
    benchmark=collect_valuation_peers(prepared,as_of,market['latest_date'],root,run_id,period_policy='prior_balance_90_days')
    out.update(benchmark)
    chosen_sources=[s for s in sources if any(s['source_id']==f'PEER_{symbol}_balance_{run_id}' for symbol in ids)]
    out['sources'].extend(chosen_sources)
    out.update(anchor_period_end=target['period_end'],selection='Tối đa bốn mã cùng nhóm nguồn, lớn nhất theo tài sản trong các kỳ đạt; số dư trước kỳ mã phân tích tối đa 90 ngày.',
               candidate_count=len(candidates),book_value_per_share=valuation['book_value_per_share'])
    if benchmark['available'] and number(benchmark['median_pb'],True):
        price=valuation['book_value_per_share']*benchmark['median_pb']
        out.update(reference_price_vnd=price,difference_pct=(price/market['latest_close_vnd']-1)*100,
                   reason=benchmark['explanation'])
    return out
