"""Valuation methods adapted from updated_valuation_files.zip with explicit assumptions."""
import math
from src.analysis.price_quality import latest_price_matches


def number(v, positive=False):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and (not positive or v>0)


def analyze_valuation(financial, market, company, quote_check, as_of, target_pb=1.5,
                      target_pe=12., discount_rate=.115, perpetual_growth=.035,
                      forecast_growth=.07, wacc=.10, tax_rate=.20, industry_benchmark=None,
                      method_weights=None):
    assumptions=dict(target_pb=target_pb,target_pe=target_pe,cost_of_equity=discount_rate,
                     terminal_growth=perpetual_growth,forecast_growth=forecast_growth,wacc=wacc,tax_rate=tax_rate)
    if any(not number(v) for v in assumptions.values()):raise ValueError("Giả định phải là số hữu hạn.")
    if not 0<target_pb<=20 or not 0<target_pe<=100 or not 0<discount_rate<1 or not 0<wacc<1 or not 0<=perpetual_growth<1 or not -1<forecast_growth<1 or not 0<=tax_rate<1:
        raise ValueError("Giả định định giá ngoài phạm vi hợp lệ.")
    weights=method_weights if method_weights is not None else dict(pb=.35,pe=.35,dcf=.30)
    if set(weights)!={"pb","pe","dcf"} or any(not number(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError("Trọng số phải không âm và có tổng dương.")
    val=dict(available=False,reason="",blocked_reasons=[],scenarios=[],pb_methods=[],book_value_per_share=None,
             reference_pb=None,inputs=[],assumptions=assumptions,
             assumption="Kịch bản giả định, không phải khuyến nghị mua/bán. Vốn/lợi nhuận cuối năm quy đổi trên CP snapshot; giả định không đổi vốn, cần xem phát hành/cổ tức sau cuối kỳ.",
             formula="BVPS = vốn mẹ / CP; Gordon P/B = (ROE mẹ - g)/(Ke - g); EPS quy đổi = LNST mẹ năm / CP snapshot; FCFF = CFO + lãi đã trả × (1-thuế) - CAPEX; vốn = PV(FCFF) + tiền - nợ vay - NCI.",
             pe_status="Chưa có bốn quý độc lập để tính P/E TTM.")
    for key in ["gordon","industry","pe","dcf","weighted_average"]:val[key]=dict(available=False)
    reasons=val["blocked_reasons"];shares=company.get("outstanding_shares")
    if not financial.get("periods"):reasons.append("Thiếu kỳ tài chính hợp lệ.")
    if not market:reasons.append("Chưa có chuỗi giá hợp lệ.")
    if not latest_price_matches(quote_check,market):reasons.append("Giá đóng cửa mới nhất chưa khớp nguồn độc lập đúng ngày và giá sử dụng.")
    if not number(shares,True):reasons.append("Thiếu số cổ phiếu lưu hành dương.")
    if company.get("snapshot_at")!=as_of.isoformat():reasons.append("Snapshot số CP khác ngày phân tích; không dùng CP hiện tại cho ngày quá khứ.")
    if market and not number(market.get("latest_close_vnd"),True):reasons.append("Giá đối chiếu không dương/hữu hạn.")
    if reasons:
        val["reason"]=" ".join(reasons)
        for key in ["gordon","industry","pe","dcf","weighted_average"]:val[key]["reason"]=val["reason"]
        return val
    latest=financial["periods"][0];fields=latest["fields"];price=market["latest_close_vnd"]
    val["price_warning"]="" if quote_check.get("status")=="matched" else "Giá đóng cửa mới nhất đã khớp hai nguồn để đối chiếu định giá; mẫu lịch sử chưa khớp đầy đủ. Không xác nhận chuỗi giá hoặc cơ sở điều chỉnh."
    def get(k):return fields.get(k,{}).get("value")
    def refs(keys):return [fields[k] for k in keys if k in fields]
    def parent_book(p):
        f=p["fields"];e=f.get("equity",{}).get("value");n=f.get("non_controlling_equity",{}).get("value")
        if p["scope"] in {"parent","separate"}:return e
        return e-n if number(e) and number(n) else None
    equity=parent_book(latest);components=[]
    val.update(equity_period=str(latest["year"]),shares=shares,shares_snapshot=company["snapshot_at"],price_date=market.get("latest_date"),
               inputs=refs(["equity","non_controlling_equity"])+[dict(source_id=company.get("source_id"),value=shares,unit="shares",period=company["snapshot_at"]),
                       dict(source_id=market.get("source_id"),value=price,unit="VND/share",period=market.get("latest_date")),
                       dict(source_id=quote_check.get("source_id"),value=price,unit="VND/share",period=market.get("latest_date"),role="independently matched closing price")])
    if number(equity,True):
        bv=equity/shares;val.update(book_value_per_share=bv,reference_pb=price/bv)
        val["pb_methods"].append(dict(method="P/B giả định người dùng",multiple=target_pb,target_price_vnd=bv*target_pb,difference_pct=(bv*target_pb/price-1)*100))
        val["scenarios"]=[dict(label=label,target_pb=target_pb*f,reference_price_vnd=bv*target_pb*f,difference_pct=(bv*target_pb*f/price-1)*100) for label,f in [("Thận trọng",.8),("Cơ sở",1),("Thuận lợi",1.2)]]
        prev=next((p for p in financial["periods"][1:] if p["year"]==latest["year"]-1 and p["scope"]==latest["scope"]),None)
        pe=parent_book(prev) if prev else None;profit=get("parent_profit")
        if profit is None and latest["scope"] in {"parent","separate"}:profit=get("net_profit")
        roe=profit/((equity+pe)/2) if number(profit) and number(pe,True) else None
        if roe is not None and roe>perpetual_growth and discount_rate>perpetual_growth:
            pb=(roe-perpetual_growth)/(discount_rate-perpetual_growth);target=bv*pb
            val["gordon"]=dict(available=True,roe_pct=roe*100,cost_of_equity_pct=discount_rate*100,growth_rate_pct=perpetual_growth*100,
                              justified_pb=pb,target_price_vnd=target,difference_pct=(target/price-1)*100,formula="P/B = (ROE cổ đông mẹ - g)/(Ke - g)",
                              explanation="Giả định ROE năm bền vững, g < ROE và g < Ke; không ép bội số vào khoảng tùy ý.",
                              inputs=refs(["parent_profit","equity","non_controlling_equity"])+[v for k,v in prev["fields"].items() if k in {"equity","non_controlling_equity"}])
            val["pb_methods"].append(dict(method="P/B Gordon theo ROE mẹ",multiple=pb,target_price_vnd=target,difference_pct=(target/price-1)*100))
        else:val["gordon"]["reason"]="Thiếu lợi nhuận/vốn mẹ bình quân đồng kỳ, hoặc ROE ≤ g / Ke ≤ g."
        bm=industry_benchmark or {};pb=bm.get("median_pb")
        if bm.get("available") and number(pb,True):
            val["industry"]={**bm,"industry_pb_median":pb,"target_price_vnd":bv*pb,"difference_pct":(bv*pb/price-1)*100}
            val["pb_methods"].append(dict(method="P/B trung vị mẫu ngành",multiple=pb,target_price_vnd=bv*pb,difference_pct=(bv*pb/price-1)*100))
        else:val["industry"]["reason"]=bm.get("reason","Chưa đủ hai P/B đồng kỳ; không dùng số cố định từ ZIP như dữ liệu thị trường.")
        targets=[m["target_price_vnd"] for m in val["pb_methods"][1:]]
        components.append(dict(method="P/B tổng hợp" if targets else "P/B giả định",price=sum(targets)/len(targets) if targets else bv*target_pb,key="pb"))
    else:
        reason="Thiếu vốn cổ đông mẹ: NCI đang null hoặc vốn mẹ không dương; không tự thay null bằng 0."
        reasons.append(reason);val["gordon"]["reason"]=reason;val["industry"]["reason"]=reason
    profit=get("parent_profit")
    if profit is None and latest["scope"] in {"parent","separate"}:profit=get("net_profit")
    if number(profit,True):
        eps=profit/shares;target=eps*target_pe
        val["pe"]=dict(available=True,eps=eps,eps_basis="LNST mẹ năm / CP snapshot: EPS quy đổi giả định, không phải EPS công bố hoặc TTM",
                       reference_pe=price/eps,target_pe=target_pe,base_price_vnd=target,inputs=refs(["parent_profit"]),
                       formula="EPS quy đổi năm = LNST mẹ năm / CP snapshot; giá kịch bản = EPS quy đổi × P/E giả định",
                       scenarios=[dict(label=label,target_pe=target_pe*f,reference_price_vnd=target*f,difference_pct=(target*f/price-1)*100) for label,f in [("Thận trọng",.8),("Cơ sở",1),("Thuận lợi",1.2)]])
        val["pe_status"]=f"Lợi nhuận năm {latest['year']} / CP tại {company['snapshot_at']}; không phải P/E TTM."
        components.append(dict(method="P/E lợi nhuận năm quy đổi",price=target,key="pe"))
    else:val["pe"]["reason"]="Thiếu LNST mẹ dương; không thay bằng LNST hợp nhất khi NCI chưa rõ."
    required=["cfo","capex_cash","interest_paid","cash","short_debt","long_debt","non_controlling_equity"]
    missing=[k for k in required if not number(get(k))]
    if financial.get("industry_group")!="nonfinancial":val["dcf"]["reason"]="Không áp DCF CFO/FCFF của doanh nghiệp sản xuất cho ngân hàng/chứng khoán; cần mô hình vốn hoặc cổ tức riêng."
    elif missing:val["dcf"]["reason"]="Thiếu FCFF/bridge: "+", ".join(missing)+"; không thay CFO thiếu bằng 85% lợi nhuận."
    elif get("capex_cash")>0 or get("interest_paid")>0:val["dcf"]["reason"]="CAPEX/lãi đã trả sai dấu dòng chi."
    elif wacc<=perpetual_growth:val["dcf"]["reason"]="DCF yêu cầu WACC > tăng trưởng dài hạn."
    else:
        base=get("cfo")-get("interest_paid")*(1-tax_rate)+get("capex_cash")
        if base<=0:val["dcf"]["reason"]="FCFF năm gốc không dương; chưa có dự báo phục hồi được chứng minh."
        else:
            flows=[base*(1+forecast_growth)**t for t in range(1,4)]
            terminal=flows[-1]*(1+perpetual_growth)/(wacc-perpetual_growth)
            enterprise=sum(cf/(1+wacc)**t for t,cf in enumerate(flows,1))+terminal/(1+wacc)**3
            debt=get("short_debt")+get("long_debt");ev=enterprise+get("cash")-debt-get("non_controlling_equity")
            val["dcf"]=dict(available=ev>0,reason="Giá trị vốn sau bridge không dương." if ev<=0 else "",cash_flow_base=base,
                            forecast_growth_pct=forecast_growth*100,discount_rate_pct=wacc*100,perpetual_growth_pct=perpetual_growth*100,
                            enterprise_value=enterprise,cash=get("cash"),debt=debt,nci=get("non_controlling_equity"),equity_value=ev,
                            per_share_price_vnd=ev/shares,difference_pct=(ev/shares/price-1)*100,forecast_flows=flows,inputs=refs(required),
                            formula="FCFF chiết khấu WACC 3 năm + terminal; cộng tiền, trừ nợ và NCI. Giả định lãi đã trả nằm trong CFO và lá chắn thuế có hiệu lực. Bridge dùng số cuối kỳ.")
            if ev>0:components.append(dict(method="DCF FCFF + equity bridge",price=ev/shares,key="dcf"))
    eligible=[c for c in components if weights[c["key"]]>0];total=sum(weights[c["key"]] for c in eligible)
    if len(eligible)>=2:
        details=[dict(method=c["method"],target_price_vnd=c["price"],weight_pct=weights[c["key"]]/total*100,contribution_vnd=c["price"]*weights[c["key"]]/total) for c in eligible]
        composite=sum(c["contribution_vnd"] for c in details)
        val["weighted_average"]=dict(available=True,target_price_vnd=composite,difference_pct=(composite/price-1)*100,components=details,
                                     recommendation="Kết quả kịch bản, chưa tự chuyển thành khuyến nghị đầu tư.",
                                     note="Trọng số giả định 35/35/30 hoặc người dùng chỉnh, chuẩn hóa trên phương pháp đủ dữ liệu; các phương pháp dùng chung đầu vào không phải bằng chứng độc lập.")
    else:val["weighted_average"]["reason"]="Cần ít nhất hai phương pháp có trọng số dương; không gọi một phương pháp là bình quân đa phương pháp."
    val["available"]=bool(components);val["reason"]=" ".join(reasons) if reasons else "Đã tính phương pháp đủ đầu vào; xem giới hạn từng phương pháp."
    return val
