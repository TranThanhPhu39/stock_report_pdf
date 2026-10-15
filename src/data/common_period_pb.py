"""Use actual same-date balances for P/B without relabeling interim earnings."""
from datetime import date
import json
from src.analysis.financial import analyze_financials
from src.analysis.valuation import number
from src.analysis.price_quality import latest_price_matches
from src.data.normalize import parse_annual_financials
from src.data.providers import DataSourceError
from src.data.research import financial_url
from src.data.valuation_peers import collect_valuation_peers


def valid_balance(period, scope, business_type):
    if scope not in {'consolidated','parent','separate'}:return False
    if period.get('scope')!=scope or period.get('business_type')!=business_type:return False
    fields=period.get('fields',{})
    values={k:fields.get(k,{}).get('value') for k in ('assets','liabilities','equity','non_controlling_equity')}
    if not all(number(values[k]) and fields[k].get('unit')=='VND' for k in ('assets','liabilities','equity')):return False
    if not number(values['assets'],True) or abs(values['assets']-values['liabilities']-values['equity'])>max(1000,values['assets']*.001):return False
    capital=values['equity']
    if scope=='consolidated':
        if not number(values['non_controlling_equity']) or fields['non_controlling_equity'].get('unit')!='VND' or not fields['non_controlling_equity'].get('source_id'):return False
        capital-=values['non_controlling_equity']
    return number(capital,True) and all(fields[k].get('source_id') for k in ('assets','liabilities','equity'))


def collect_common_period_pb(ticker,as_of,financial,balance_snapshots,industry,valuation,market,quote_check,root,run_id):
    out=dict(available=False,benchmark={},sources=[],attempts=[],
             reason='Chưa có ít nhất hai doanh nghiệp với số dư vốn cùng ngày/phạm vi và giá đối chiếu.')
    if not financial.get('periods') or not industry.get('available') or not market or not number(valuation.get('shares'),True) or not latest_price_matches(quote_check,market):return out
    latest=financial['periods'][0];scope=latest['scope'];business_type=latest['business_type']
    # Bounded fallback: no more than 90 days behind the latest annual statement,
    # and never a balance older than one year at the analysis date.
    own={}
    for p in financial['periods']+balance_snapshots:
        try:end=date.fromisoformat(p['period_end']);published=date.fromisoformat(p.get('published_at') or max(f.get('published_at','9999-12-31') for f in p['fields'].values()))
        except (ValueError,KeyError,TypeError):continue
        if end>as_of or published>as_of or published<end:continue
        if (as_of-end).days>365 or (date.fromisoformat(latest['period_end'])-end).days>90:continue
        if valid_balance(p,scope,business_type):own.setdefault(p['period_end'],p)
    peers={};sources={}
    for symbol in sorted(set(industry.get('members',[]))-{ticker}):
        sid=f'PEER_{symbol}_balance_{run_id}';path=root/'data/raw/industry'/f'{sid}.json'
        if not path.exists():continue
        try:
            records=parse_annual_financials(json.loads(path.read_text(encoding='utf-8')),'balance',as_of,sid)
            peers[symbol]=[p for p in analyze_financials(records)['periods'] if valid_balance(p,scope,business_type)]
            sources[symbol]=dict(source_id=sid,url_or_file=financial_url(symbol,'balance'),retrieved_at=as_of.isoformat(),page_or_table='Balance sheet',notes=f'Current-run raw snapshot {path.relative_to(root).as_posix()}; VND; exact end/scope; balances checked, not independently verified.')
        except (DataSourceError,ValueError,KeyError,TypeError,OSError):continue
    for end,p in sorted(own.items(),reverse=True):
        candidates=[dict(ticker=s,financial=dict(periods=[r],metrics=[])) for s,rows in peers.items() for r in rows if r['period_end']==end]
        candidates.sort(key=lambda c:(-c['financial']['periods'][0]['fields']['assets']['value'],c['ticker']))
        out['attempts'].append(dict(period_end=end,candidate_count=len(candidates)))
        if len(candidates)<2:continue
        prepared=dict(name=industry['name'],period_end=end,scope=scope,peers=candidates[:4])
        benchmark=collect_valuation_peers(prepared,as_of,market['latest_date'],root,run_id,period_policy='exact_balance')
        out['sources'].extend(benchmark['sources'])
        out['sources'].extend(sources[c['ticker']] for c in candidates[:4])
        if not benchmark['available']:continue
        capital=p['fields']['equity']['value']-(p['fields']['non_controlling_equity']['value'] if scope=='consolidated' else 0)
        out.update(available=True,period=p,benchmark=benchmark,book_value_per_share=capital/valuation['shares'],
                   shares=valuation['shares'],shares_snapshot=valuation.get('shares_snapshot'),reason='P/B dùng số dư vốn thực tế cùng ngày; không dùng lợi nhuận lũy kế để tính P/E.')
        break
    return out
