"""Compare user-selected stocks on a common annual period and dated quotes."""
from src.analysis.financial import analyze_financials
from src.analysis.price_quality import latest_price_matches
from src.analysis.valuation import number


SCOPE_NAMES={'consolidated':'Hợp nhất','separate':'Riêng lẻ','parent':'Công ty mẹ'}
GROUP_NAMES={'bank':'Ngân hàng','securities':'Chứng khoán','nonfinancial':'Phi tài chính','financial':'Tài chính','unknown':'Chưa xác định'}


def compare_results(results,errors=None):
    base=results[0];as_of=base['request']['as_of'];price_date=(base.get('market') or {}).get('latest_date')
    valid=[r for r in results if r.get('financial',{}).get('periods')]
    common=None
    if valid:
        bases=[{(p['period_end'],p['scope']) for p in r['financial']['periods']} for r in valid]
        shared=set.intersection(*bases)
        if shared:common=max(shared,key=lambda b:b[0])
    rows=[];ids=set()
    for r in results:
        f=r.get('financial',{});m=r.get('market') or {};company=r.get('company',{})
        notes=[];metrics={};period=None
        if common:
            period=next((p for p in f.get('periods',[]) if (p['period_end'],p['scope'])==common),None)
        if period:
            records=[p for p in f['periods'] if p['period_end']<=common[0] and p['scope']==common[1]]
            aligned=analyze_financials(records)
            metrics={v['key']:v['value'] for v in aligned['metrics']}
            if period!=f['periods'][0]:notes.append('Đã dùng kỳ cũ hơn để so sánh đồng kỳ; xem báo cáo riêng để đọc kỳ mới nhất.')
        else:notes.append('Chưa có kỳ/phạm vi chung; không ghép tài chính khác năm để so sánh.')
        quote_ok=(r['request']['as_of']==as_of and m.get('latest_date')==price_date and latest_price_matches(r.get('quality',{}).get('price_check',{}),m))
        shares=company.get('outstanding_shares')
        capital=profit=None
        if period:
            fields=period['fields'];equity=fields.get('equity',{}).get('value');nci=fields.get('non_controlling_equity',{}).get('value')
            capital=equity if period['scope'] in {'parent','separate'} else equity-nci if number(equity) and number(nci) else None
            profit=fields.get('parent_profit',{}).get('value')
            if profit is None and period['scope'] in {'parent','separate'}:profit=fields.get('net_profit',{}).get('value')
            ids.update(i['source_id'] for i in fields.values() if i.get('source_id'))
        cap=m.get('latest_close_vnd')*shares if quote_ok and number(shares,True) and company.get('snapshot_at')==as_of else None
        if cap is None:notes.append('Bội số bị ẩn: giá/ngày giá hoặc snapshot số CP chưa đủ điều kiện.')
        ttm=f.get('ttm',{});ttm_field=ttm.get('fields',{}).get('parent_profit',{})
        base_ttm=base.get('financial',{}).get('ttm',{})
        ttm_same=(ttm.get('available') and base_ttm.get('available') and
                  all(ttm.get(k)==base_ttm.get(k) for k in ['period_begin','period_end','scope']))
        pe_ttm=cap/ttm_field['value'] if cap and ttm_same and number(ttm_field.get('value'),True) else None
        ids.update(s['source_id'] for s in r.get('sources',[]) if s.get('source_id'))
        rows.append(dict(ticker=r['request']['ticker'],industry=GROUP_NAMES.get(f.get('industry_group'),'Chưa xác định'),
                         period_end=period['period_end'] if period else None,scope=period['scope'] if period else None,
                         price_date=m.get('latest_date'),price_vnd=m.get('latest_close_vnd') if quote_ok else None,
                         revenue_vnd=metrics.get('revenue'),net_interest_income_vnd=metrics.get('net_interest_income'),
                         net_profit_vnd=metrics.get('net_profit'),profit_growth_pct=metrics.get('net_profit_growth'),
                         roe_pct=metrics.get('roe'),cash_conversion=metrics.get('cash_conversion'),debt_equity=metrics.get('debt_equity'),
                         pe_annual=cap/profit if cap and number(profit,True) else None,
                         pb=cap/capital if cap and number(capital,True) else None,pe_ttm=pe_ttm,
                         ttm_period_end=ttm.get('period_end') if ttm_same else None,
                         notes=notes))
    return dict(available=len(rows)>=2,rows=rows,errors=errors or [],as_of=as_of,price_date=price_date,
                period_end=common[0] if common else None,scope=common[1] if common else None,source_ids=sorted(ids),
                note='So sánh mã tự chọn, không phải mẫu định giá ngành. Chọn kỳ năm/phạm vi chung gần nhất; bội số chỉ dùng giá đã đối chiếu đúng ngày và CP snapshot ngày chốt. P/E TTM chỉ xuất khi TTM đã xác minh cùng khoảng 12 tháng. CFO/LNST, nợ vay/vốn chỉ áp dụng phi tài chính. Không xếp hạng mua/bán từ bảng này.')


def comparison_table(comparison):
    from src.reporting.pdf_exporter import formatted
    return [{'Mã':r['ticker'],'Nhóm':r['industry'],'Kỳ năm':r['period_end'] or 'Chưa đồng kỳ',
             'Phạm vi':SCOPE_NAMES.get(r['scope'],'Chưa xác định'),'Ngày giá':r['price_date'] or 'Chưa có',
             'Giá (VND)':formatted(r['price_vnd']),'LNST (tỷ)':formatted(r['net_profit_vnd']/1e9 if r['net_profit_vnd'] is not None else None),
             'LNST YoY (%)':formatted(r['profit_growth_pct']),'ROE (%)':formatted(r['roe_pct']),
             'P/E năm':formatted(r['pe_annual']),'P/B':formatted(r['pb']),'P/E TTM':formatted(r['pe_ttm']),
             'CFO/LNST':formatted(r['cash_conversion']) if r['industry']=='Phi tài chính' else 'Không áp dụng',
             'Nợ vay/vốn':formatted(r['debt_equity']) if r['industry']=='Phi tài chính' else 'Không áp dụng',
             'Ghi chú':'; '.join(r['notes'])} for r in comparison.get('rows',[])]
