"""Attach verified annual bank ratios and trailing profit from annual + YTD."""
import math
from datetime import date


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def trailing_profit(financial, interim, as_of):
    unavailable = dict(available=False, reason='Thiếu BCTC năm và bán niên cùng phạm vi đã kiểm tra.')
    if not financial.get('periods') or not interim or not interim.get('valid') or interim.get('period_type')!='half_year':
        return unavailable
    end = interim.get('period_end','')
    try:
        current_date = date.fromisoformat(end)
    except ValueError:
        return unavailable
    if current_date > as_of or (current_date.month,current_date.day)!=(6,30) or interim.get('period_begin')!=f'{current_date.year}-01-01':
        return dict(unavailable,reason='Kỳ bán niên không hợp lệ hoặc sau ngày chốt.')
    year = current_date.year
    annual = next((p for p in financial['periods'] if p['year']==year-1 and p.get('period_end')==f'{year-1}-12-31' and p['scope']=='consolidated'),None)
    if not annual:
        return unavailable
    results = {}
    # Profit allocation checks must hold on all three input columns; keep NCI signed.
    for origin,col in [(annual['fields'],'value'),(interim['fields'],'value'),(interim['fields'],'previous')]:
        fields = [origin.get(k,{}) for k in ('net_profit','parent_profit','non_controlling_profit')]
        if any(not finite(f.get(col)) or f.get('statement_scope')!='consolidated' or f.get('unit')!='VND' for f in fields) or abs(fields[0][col]-fields[1][col]-fields[2][col]) > 1e6:
            return dict(unavailable,reason='Phân bổ lợi nhuận mẹ/NCI chưa khớp cho cả ba đầu vào TTM.')
    for key in ('net_profit','parent_profit','net_interest_income'):
        annual_field = annual['fields'].get(key,{})
        interim_field = interim['fields'].get(key,{})
        if any(f.get('statement_scope')!='consolidated' or f.get('unit')!='VND'
               or not f.get('source_id') or not f.get('available_at') or f['available_at']>as_of.isoformat()
               for f in (annual_field,interim_field)):
            return dict(unavailable,reason='Đầu vào TTM thiếu hoặc khác đơn vị/phạm vi/thời điểm khả dụng.')
        if annual_field.get('period') not in {str(year-1),f'{year-1}-12-31'} or interim_field.get('period')!=end:
            return dict(unavailable,reason='Đầu vào TTM lệch kỳ năm/bán niên.')
        try:
            if any(date.fromisoformat(f['available_at'])>as_of for f in (annual_field,interim_field)):
                return unavailable
        except (ValueError,TypeError):
            return dict(unavailable,reason='Ngày khả dụng đầu vào TTM không hợp lệ.')
        a,b,c = annual_field.get('value'),interim_field.get('value'),interim_field.get('previous')
        if not all(finite(v) for v in (a,b,c)):
            return dict(unavailable,reason='Đầu vào lợi nhuận TTM thiếu hoặc không hữu hạn.')
        results[key] = dict(value=a+b-c, unit='VND', annual_value=a, current_ytd=b, prior_ytd=c,
            formula='Năm trước + lũy kế hiện tại − lũy kế cùng kỳ năm trước',
            inputs=[dict(annual_field, role='annual',period_begin=f'{year-1}-01-01',period_end=f'{year-1}-12-31'),
                    dict(interim_field, role='current_ytd',period_begin=f'{year}-01-01',period_end=end),
                    dict(interim_field,value=c,source_value=c/interim_field.get('unit_multiplier',1),
                         role='prior_ytd_latest_comparative',period=f'{year-1}-06-30',
                         period_begin=f'{year-1}-01-01',period_end=f'{year-1}-06-30')])
    return dict(available=True,period_begin=f'{year-1}-07-01',period_end=end,scope='consolidated',
                fields=results, comparative_basis='Cột cùng kỳ trong BCTC bán niên mới nhất đã xác minh.',
                note='TTM là số liệu quá khứ ghép từ BCTC năm và bán niên, không nhân đôi bán niên thành dự báo. Cột cùng kỳ lấy từ bản bán niên mới nhất; EPS báo cáo có thể đã điều chỉnh theo cổ phiếu. P/E TTM ở đây dùng vốn hóa theo CP snapshot, không dùng EPS công bố.')


def attach_bank_metrics(financial, ratios, interim, as_of):
    if financial.get('industry_group')!='bank':
        return financial
    metrics = financial['metrics']
    formulas = {'nim':'NIM hợp nhất do ngân hàng công bố; thu nhập lãi thuần / tài sản sinh lãi bình quân, năm hóa',
                'car':'CAR hợp nhất do ngân hàng công bố; vốn tự có / tài sản có rủi ro (RWA)',
                'npl':'(Nợ nhóm 3 + 4 + 5) / cho vay khách hàng gộp hợp nhất × 100'}
    missing = []
    for key,label in [('nim','NIM hợp nhất (ngân hàng công bố)'),('npl','NPL hợp nhất (tính lại thuyết minh)'),('car','CAR hợp nhất (ngân hàng công bố)')]:
        f = (ratios or {}).get('metrics',{}).get(key,{}) if (ratios or {}).get('available') else {}
        value = f.get('value')
        if not finite(value) or f.get('available_at','9999')>as_of.isoformat() or f.get('statement_scope')!='consolidated':
            f={}; value=None; missing.append(key.upper())
        metrics.append(dict(key=key,label=label,value=value,unit='%',period=f.get('period','chưa xác minh'),
            formula=formulas[key],inputs=f.get('inputs',[f]) if f else [],
            previous_value=f.get('previous'), limitation=f.get('limitation'),
            reason=(ratios or {}).get('reason','Chưa có tài liệu cùng phạm vi đủ điều kiện xác minh.') if value is None else None))
    if missing:
        financial['errors'].append('Ngân hàng: chưa xác minh '+', '.join(missing)+' từ tài liệu có kỳ/phạm vi rõ ràng.')
    financial['ttm'] = trailing_profit(financial,interim,as_of)
    return financial
