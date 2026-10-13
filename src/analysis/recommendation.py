"""Deterministic investment stance, with auditable evidence and explicit gates."""
from __future__ import annotations
from datetime import date
from src.analysis.price_quality import latest_price_matches
from src.analysis.valuation import number


def build_recommendation(result):
    financial=result["financial"];market=result.get("market");valuation=result["valuation"]
    asof=date.fromisoformat(result["request"]["as_of"])
    metrics={m["key"]:m for m in financial.get("metrics",[])}
    def val(key):return metrics.get(key,{}).get("value")
    def refs(*keys):return sorted({i["source_id"] for k in keys for i in metrics.get(k,{}).get("inputs",[]) if i.get("source_id")})
    periods=financial.get("periods",[]);year=periods[0]["year"] if periods else None
    opportunities=[]
    def thesis(title,evidence,implication,catalyst,invalidation,source_ids,period):
        opportunities.append(dict(title=title,evidence=evidence,implication=implication,catalyst=catalyst,
                                  invalidation=invalidation,source_ids=source_ids,period=str(period)))
    growth=val("net_profit_growth")
    if number(growth) and growth>0 and number(val("net_profit"),True):
        thesis("Động lực lợi nhuận",f"LNST {year} tăng {growth:.2f}% so với cùng kỳ.",
               "Kết quả cải thiện là cơ sở theo dõi khả năng duy trì lợi nhuận, chưa chứng minh tăng trưởng tương lai.",
               "BCTC kỳ tiếp theo xác nhận LNST dương và tăng cùng kỳ, sau khi kiểm tra khoản bất thường.",
               "LNST kỳ tiếp theo giảm hoặc tăng chủ yếu do thu nhập không lặp lại.",refs("net_profit_growth","net_profit"),year)
    interim=result.get('interim')
    if financial.get('industry_group')=='bank' and interim and interim.get('valid'):
        interest=interim['fields'].get('net_interest_income');profit=interim['fields'].get('parent_profit')
        if interest and profit and interest['previous']>0 and profit['previous']>0:
            thesis('Cập nhật kết quả bán niên',
                f"Sáu tháng kết thúc {interim['period_end']}: thu nhập lãi thuần {interest['value']/1e9:,.2f} tỷ VND ({(interest['value']/interest['previous']-1)*100:+.2f}%); LNST cổ đông mẹ {profit['value']/1e9:,.2f} tỷ VND ({(profit['value']/profit['previous']-1)*100:+.2f}%) so với cùng kỳ.",
                'Kết quả mới bổ sung bằng chứng kinh doanh; P/E/P/B mẫu đồng kỳ vẫn dùng BCTC năm. TTM, nếu đã xác minh, là tham khảo riêng và không phải định giá dự phóng.',
                'Kiểm tra tăng trưởng thu nhập lãi cùng dự phòng, NPL, NIM và CAR trong BCTC/thuyết minh kỳ tiếp theo.',
                'Tăng trưởng thu nhập lãi/lợi nhuận suy giảm hoặc chi phí tín dụng, chất lượng tài sản xấu đi.',
                sorted({interest['source_id'],profit['source_id']}),interim['period_end'])
    if financial.get("industry_group")=="nonfinancial" and number(val("cash_conversion")) and val("cash_conversion")>=1 and number(val("cfo"),True) and number(val("net_profit"),True):
        thesis("Lợi nhuận được hỗ trợ bởi tiền",f"CFO/LNST {year} = {val('cash_conversion'):.2f} lần; CFO {val('cfo')/1e9:,.2f} tỷ VND.",
               "Dòng tiền hỗ trợ lợi nhuận trong kỳ; cần phân biệt thu hồi vốn lưu động và dòng tiền lặp lại.",
               "Kỳ tiếp theo giữ CFO dương, chuyển đổi tiền tốt mà không tăng mạnh phải thu/tồn kho.",
               "CFO âm hoặc tăng phải thu/tồn kho làm suy yếu chuyển đổi lợi nhuận thành tiền.",refs("cash_conversion","cfo","net_profit"),year)
    if financial.get('industry_group')=='securities' and number(val('lending_revenue_growth')) and val('lending_revenue_growth')>0:
        thesis('Động lực dịch vụ cho vay',f"Lãi cho vay và phải thu {year} tăng {val('lending_revenue_growth'):.2f}%; các khoản cho vay {val('financial_loans')/1e9:,.2f} tỷ VND." if number(val('financial_loans')) else f"Lãi cho vay và phải thu {year} tăng {val('lending_revenue_growth'):.2f}%.",
               'Tăng thu nhập cho vay là động lực kinh doanh; cần đọc cùng chi phí vốn, tài sản bảo đảm và chất lượng các khoản cho vay.',
               'BCTC kỳ tiếp theo xác nhận tăng thu nhập cho vay và kiểm soát chi phí vốn/dự phòng.',
               'Chi phí vốn hoặc dự phòng tăng nhanh, tài sản bảo đảm suy giảm làm giảm hiệu quả cho vay.',refs('lending_revenue_growth','financial_loans'),year)
    for comparison in result.get("industry",{}).get("comparisons",[]):
        if comparison["key"]=="roe" and comparison["sample_size"]>=2 and comparison["company_value"]>comparison["sample_median"]:
            comparison_metrics=result["industry"].get("comparison_financial",financial).get("metrics",[])
            sids=[i["source_id"] for m in comparison_metrics if m["key"]=="roe" for i in m.get("inputs",[]) if i.get("source_id")]+[s["source_id"] for s in result["industry"].get("sources",[])]
            thesis("Hiệu quả vốn trong mẫu ngành",f"ROE {comparison['company_value']:.2f}% so với trung vị {comparison['sample_median']:.2f}%, n={comparison['sample_size']}.",
                   "Hiệu quả vốn cao hơn mẫu cùng kỳ; cần kiểm tra đòn bẩy và khoản bất thường trước khi trả bội số cao hơn.",
                   "Duy trì ROE trên mẫu đồng kỳ khi cập nhật BCTC, không dựa vào tăng đòn bẩy.",
                   "ROE xuống dưới mẫu hoặc chất lượng lợi nhuận suy giảm.",sorted(set(sids)),comparison["period_end"])
    primary=valuation.get("primary",{});components=primary.get("methods",[]) if primary.get("available") else []
    targets=[c["target_price_vnd"] for c in components if number(c.get("target_price_vnd"),True)]
    target=primary.get("target_price_vnd") if targets else None
    price=market.get("latest_close_vnd") if market else None
    spread=(max(targets)/min(targets)-1)*100 if targets else None
    upside=(target/price-1)*100 if number(target,True) and number(price,True) else None
    ids=sorted({i["source_id"] for i in valuation.get("inputs",[]) if i.get("source_id")} | set(primary.get("source_ids",[])))
    if number(upside) and upside>=15:
        thesis("Định giá chính và biên chênh lệch",f"{primary.get('selected_method','Phương pháp chính')}: {target:,.0f} VND/CP, chênh {upside:+.2f}% so với giá {price:,.0f} ngày {market['latest_date']}.",
               f"Đầu vào tài chính năm {year}, cần cập nhật kỳ mới. Có khoảng chênh lệch để nghiên cứu nếu các giả định lợi nhuận, vốn và chi phí vốn giữ được. Không phải lợi suất dự báo.",
               "Xác minh BCTC mới và kiểm tra lại bội số/chi phí vốn trước khi hành động.",
               "Giá trị cập nhật không còn chênh ít nhất 15%, hoặc đầu vào/giả định không còn phù hợp.",ids,market["latest_date"])
    blockers=[]
    if not latest_price_matches(result["quality"]["price_check"],market):blockers.append("Giá sử dụng chưa khớp nguồn độc lập đúng ngày.")
    if not periods:blockers.append("Chưa có kỳ tài chính hợp lệ.")
    elif year<asof.year-1:blockers.append(f"Tài chính mới nhất {year}, cần bổ sung kỳ {asof.year-1} hoặc mới hơn.")
    if result["quality"]["financial_check"].get("status")=="mismatch":blockers.append("Tài chính sai lệch với tài liệu đối chiếu.")
    if market and (asof-date.fromisoformat(market["latest_date"])).days>7:blockers.append("Giá cuối chuỗi cũ hơn 7 ngày; kiểm tra thanh khoản/tình trạng giao dịch.")
    if not number(target,True):blockers.append((primary.get('reason') or "Chưa có phương pháp chính có bội số mẫu đồng kỳ hoặc SOTP đã xác minh.")+" Không dùng giả định nhập tay thay thế.")
    if not number(price,True):blockers.append("Giá đóng cửa dùng để tính chênh lệch không dương hoặc không hữu hạn.")
    weak_profit=number(val("net_profit")) and val("net_profit")<=0
    recent_profit=interim.get('fields',{}).get('parent_profit',{}) if interim and interim.get('valid') else {}
    recent_profit_weak=(number(recent_profit.get('value')) and number(recent_profit.get('previous'),True)
                        and bool(periods) and interim.get('period_end','')>periods[0].get('period_end','')
                        and recent_profit['value']<recent_profit['previous'])
    weak_cash=financial.get("industry_group")=="nonfinancial" and number(val("cfo")) and val("cfo")<=0
    cash_confirmed=financial.get("industry_group")!="nonfinancial" or number(val("cfo"),True)
    financial_check=result["quality"]["financial_check"]
    current_checks=[c for c in financial_check.get("checks",[])
                    if str(c.get("period")) in {str(year),periods[0].get("period_end")} ] if periods else []
    finance_verified=(financial_check.get("status")=="matched_selected_fields"
                      and bool(current_checks) and all(c.get("match") is True for c in current_checks))
    realized_growth=val("realized_profit_growth")
    profit_quality_weak=financial.get("industry_group")=="securities" and number(realized_growth) and realized_growth<0
    independent_note=f"Đối chiếu chỉ tiêu đã chọn của năm {year}; không chứng nhận toàn bộ BCTC." if finance_verified else "Tài chính kỳ đang dùng chưa có đối chiếu độc lập khớp các chỉ tiêu đã chọn; mức tin cậy thấp."
    stance="THEO DÕI";reason="Chưa có biên chênh lệch và chất lượng đầu vào đủ mạnh để đề xuất tích lũy."
    if blockers:
        stance="CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ";reason=" ".join(blockers)
    elif weak_profit or weak_cash or upside<=-15:
        risk_reasons=[]
        if weak_profit:risk_reasons.append(f"LNST {year} không dương ({val('net_profit')/1e9:,.2f} tỷ VND).")
        if weak_cash:risk_reasons.append(f"CFO {year} không dương ({val('cfo')/1e9:,.2f} tỷ VND).")
        if upside<=-15:risk_reasons.append(f"Giá trị tham chiếu chính thấp hơn giá đóng cửa {abs(upside):.2f}%.")
        stance="ƯU TIÊN QUẢN TRỊ RỦI RO";reason=" ".join(risk_reasons)+" Cần xác minh sự phục hồi hoặc cập nhật giả định trước khi tăng tỷ trọng."
    elif recent_profit_weak:
        reason=f"LNST mẹ bán niên kết thúc {interim['period_end']} giảm {(1-recent_profit['value']/recent_profit['previous'])*100:.2f}% so với cùng kỳ. Định giá năm chưa phản ánh đầy đủ cập nhật này; cần xác minh nguyên nhân và cập nhật kỳ mới trước khi tích lũy."
    elif profit_quality_weak:
        share=val("unrealized_profit_share")
        reason=f"LNST {year} tăng {growth:.2f}% nhưng LNTT đã thực hiện giảm {abs(realized_growth):.2f}%. " if number(growth) else f"LNTT đã thực hiện {year} giảm {abs(realized_growth):.2f}%. "
        if number(share):reason+=f"Phần chưa thực hiện chiếm {share:.2f}% LNTT. "
        reason+=f"Chênh lệch định giá chính {upside:+.2f}%; theo dõi khả năng hiện thực hóa lợi nhuận và kiểm tra kỳ mới trước khi tích lũy."
    elif len(targets)>=2 and upside>=15 and number(growth) and growth>0 and finance_verified and cash_confirmed and spread<=60 and min(targets)>=price:
        stance="CÂN NHẮC TÍCH LŨY CÓ ĐIỀU KIỆN";reason="Định giá chính cao hơn giá ít nhất 15%, lợi nhuận tăng, phương pháp đối chiếu cũng không thấp hơn giá và các chỉ tiêu chọn đã được đối chiếu."
    else:
        reason=f"Chênh lệch định giá chính {upside:+.2f}%. "
        if len(targets)<2:reason+="Chỉ có một phương pháp đủ dữ liệu; cần phương pháp đối chiếu trước khi tích lũy. "
        elif spread>60:reason+=f"Các phương pháp đối chiếu phân tán {spread:.2f}%; cần giải thích khác biệt về mô hình kinh doanh/hiệu quả vốn trước khi hành động. "
        elif min(targets)<price:reason+="Một phương pháp đối chiếu thấp hơn giá hiện tại; bằng chứng định giá chưa đồng thuận. "
        elif upside<15:reason+="Biên chênh lệch chưa đạt ngưỡng nghiên cứu 15%. "
        else:reason+="Chưa đủ điều kiện lợi nhuận/dòng tiền để tích lũy. "
        reason+=independent_note
    for item in result.get("research_narrative",{}).get("company_impact",[])[:2]:
        thesis(item["title"],item["evidence"],item["interpretation"],item["monitor"],"Kênh tác động không được xác nhận bởi dữ liệu kỳ mới hoặc môi trường thị trường đổi chiều.",item["source_ids"],item["period"])
    return dict(stance=stance,reason=reason,as_of=asof.isoformat(),horizon="Theo dõi 6-12 tháng; đánh giá lại khi có BCTC mới hoặc sự kiện trọng yếu",
                confidence="Trung bình" if finance_verified and not blockers else "Thấp",confidence_note=independent_note,
                target_price_vnd=target,selected_method=primary.get("selected_method"),valuation_basis=primary.get("reason"),upside_pct=upside,model_low_vnd=min(targets) if targets else None,
                model_high_vnd=max(targets) if targets else None,model_spread_pct=spread,
                entry_ceiling_vnd=min(target/1.15,min(targets)) if stance=="CÂN NHẮC TÍCH LŨY CÓ ĐIỀU KIỆN" else None,
                opportunities=opportunities,blockers=blockers,source_ids=sorted(set(ids+refs("net_profit_growth","net_profit","cfo"))),
                methodology="Định giá chính theo bội số mẫu đồng kỳ hoặc SOTP đủ metadata; giả định nhập tay chỉ dùng độ nhạy. Ngưỡng nghiên cứu: chênh ≥15% xem xét tích lũy; ≤-15% ưu tiên rủi ro; phân tán ≤60%. Một phương pháp có thể làm tham chiếu; tích lũy cần ít nhất hai phương pháp, giá ≤7 ngày, tài chính từ năm trước, LNST tăng, CFO phù hợp ngành, đối chiếu tài chính và mọi phương pháp chính ≥giá. Các ngưỡng là quy tắc đề tài, không phải chuẩn thị trường.",
                conditions=["Kiểm tra BCTC kỳ mới, cổ tức/phát hành và số CP trước khi sử dụng mức tham chiếu.",
                            "Cập nhật kịch bản khi lợi nhuận/dòng tiền suy giảm, chi phí vốn thay đổi hoặc giá không còn biên chênh lệch.",
                            "Đọc toàn văn công bố trọng yếu; tin tiêu đề và kênh vĩ mô có điều kiện chưa xác nhận chất xúc tác."])
