"""Verified annual + reviewed YTD - comparative YTD for all industries."""
from datetime import date
from src.analysis.valuation import number


def trailing_from_interim(financial,interim,as_of):
    out=dict(available=False,fields={},reason='Thiếu năm và bán niên đã kiểm tra cùng kỳ/phạm vi.')
    if not interim or not interim.get('valid') or interim.get('period_type')!='half_year':return out
    try:
        end=date.fromisoformat(interim['period_end'])
    except (ValueError,TypeError,KeyError):return out
    if (end.month,end.day)!=(6,30) or end>as_of:return out
    if interim.get('period_begin',f'{end.year}-01-01')!=f'{end.year}-01-01':return out
    annual=next((p for p in financial.get('periods',[]) if p.get('period_end')==f'{end.year-1}-12-31' and p['scope']=='consolidated'),None)
    if not annual:return out
    for key in ('revenue','net_profit','parent_profit','net_interest_income','cfo'):
        a=annual['fields'].get(key,{});b=interim.get('fields',{}).get(key,{})
        inputs=(a.get('value'),b.get('value'),b.get('previous'))
        if not all(number(v) for v in inputs):continue
        if any(f.get('statement_scope')!='consolidated' or f.get('unit')!='VND' or not f.get('source_id') for f in (a,b)):continue
        try:
            dates=[date.fromisoformat(f.get('available_at') or f.get('published_at') or '') for f in (a,b)]
        except (ValueError,TypeError):continue
        if any(d>as_of for d in dates):continue
        if a.get('period') not in {str(end.year-1),f'{end.year-1}-12-31'} or b.get('period')!=end.isoformat():continue
        out['fields'][key]=dict(value=inputs[0]+inputs[1]-inputs[2],unit='VND',
                               annual_value=inputs[0],current_ytd=inputs[1],prior_ytd=inputs[2],
                               formula='Năm trước + bán niên hiện tại - bán niên cùng kỳ',
                               inputs=[dict(a,role='annual'),dict(b,role='current_ytd'),
                                       dict(b,value=inputs[2],period=f'{end.year-1}-06-30',role='prior_ytd')])
    if 'net_profit' not in out['fields']:return out
    out.update(available=True,scope='consolidated',period_begin=f'{end.year-1}-07-01',period_end=end.isoformat(),
               usable_for_valuation=True,
               note='TTM từ BCTC năm và bán niên hợp nhất đã kiểm tra; giữ từng đầu vào và ngày công bố. Không nhân đôi bán niên. P/E TTM tham khảo riêng, chưa dùng mẫu P/E năm để định giá TTM.')
    return out
