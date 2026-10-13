"""Shared decision summary for UI and PDF; show basis beside conclusions."""
from src.analysis.comparison import SCOPE_NAMES
from src.analysis.valuation import number


def decision_summary(result):
    f=result.get('financial',{});periods=f.get('periods',[])
    p=periods[0] if periods else {}
    rec=result.get('recommendation',{});primary=result.get('valuation',{}).get('primary',{})
    methods=primary.get('methods',[]) if primary.get('available') else []
    selected=next((m for m in methods if m.get('key')==primary.get('selected_key')),None)
    ttm=f.get('ttm',{});quarterly=result.get('quarterly',{})
    risks=[r.get('evidence','') for r in result.get('conclusion',{}).get('risk_matrix',[])][:3]
    blockers=list(rec.get('blockers',[]))
    if rec.get('confidence')=='Thấp' and 'chưa' in rec.get('confidence_note','').lower():
        blockers.append(rec['confidence_note'])
    if not ttm.get('available'):blockers.append('TTM đã xác minh: '+ttm.get('reason','Chưa đủ đầu vào cùng kỳ/phạm vi.'))
    prices=[m['target_price_vnd'] for m in methods if number(m.get('target_price_vnd'),True)]
    return dict(method=primary.get('selected_method') or 'Chưa có phương pháp đủ dữ liệu',
                selection_reason=primary.get('selection_reason') or primary.get('reason',''),
                annual_basis=f"{p.get('period_end','Chưa có')} / {SCOPE_NAMES.get(p.get('scope'),'Chưa xác định')}",
                ttm_basis=f"{ttm['period_begin']} đến {ttm['period_end']} / {SCOPE_NAMES.get(ttm.get('scope'),'Chưa xác định')}" if ttm.get('available') else 'Chưa có TTM đã xác minh',
                latest_quarter=quarterly.get('records',[{}])[0].get('period_end') if quarterly.get('records') else None,
                sample_size=selected.get('sample_size') if selected else None,
                low_vnd=min(prices) if prices else None,high_vnd=max(prices) if prices else None,
                spread_pct=rec.get('model_spread_pct'),confidence=rec.get('confidence','Thấp'),
                blockers=list(dict.fromkeys(b for b in blockers if b)),risks=risks,
                conditions=rec.get('conditions',[]),note='Khoảng giá là min-max các phương pháp đủ điều kiện, không phải khoảng xác suất. Giá định giá chính vẫn dùng cơ sở năm/mẫu đồng kỳ; P/E TTM tham khảo riêng.')
