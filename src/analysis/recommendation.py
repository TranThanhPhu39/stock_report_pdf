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
    if financial.get("industry_group")=="nonfinancial" and number(val("cash_conversion")) and val("cash_conversion")>=1 and number(val("cfo"),True) and number(val("net_profit"),True):
        thesis("Lợi nhuận được hỗ trợ bởi tiền",f"CFO/LNST {year} = {val('cash_conversion'):.2f} lần; CFO {val('cfo')/1e9:,.2f} tỷ VND.",
               "Dòng tiền hỗ trợ lợi nhuận trong kỳ; cần phân biệt thu hồi vốn lưu động và dòng tiền lặp lại.",
               "Kỳ tiếp theo giữ CFO dương, chuyển đổi tiền tốt mà không tăng mạnh phải thu/tồn kho.",
               "CFO âm hoặc tăng phải thu/tồn kho làm suy yếu chuyển đổi lợi nhuận thành tiền.",refs("cash_conversion","cfo","net_profit"),year)
    for comparison in result.get("industry",{}).get("comparisons",[]):
        if comparison["key"]=="roe" and comparison["sample_size"]>=2 and comparison["company_value"]>comparison["sample_median"]:
            sids=refs("roe")+[s["source_id"] for s in result["industry"].get("sources",[])]
            thesis("Hiệu quả vốn trong mẫu ngành",f"ROE {comparison['company_value']:.2f}% so với trung vị {comparison['sample_median']:.2f}%, n={comparison['sample_size']}.",
                   "Hiệu quả vốn cao hơn mẫu cùng kỳ; cần kiểm tra đòn bẩy và khoản bất thường trước khi trả bội số cao hơn.",
                   "Duy trì ROE trên mẫu đồng kỳ khi cập nhật BCTC, không dựa vào tăng đòn bẩy.",
                   "ROE xuống dưới mẫu hoặc chất lượng lợi nhuận suy giảm.",sorted(set(sids)),year)
    weighted=valuation.get("weighted_average",{});components=weighted.get("components",[]) if weighted.get("available") else []
    targets=[c["target_price_vnd"] for c in components if number(c.get("target_price_vnd"),True)]
    target=weighted.get("target_price_vnd") if len(targets)>=2 else None
    price=market.get("latest_close_vnd") if market else None
    spread=(max(targets)/min(targets)-1)*100 if targets else None
    upside=(target/price-1)*100 if number(target,True) and number(price,True) else None
    ids=sorted({i["source_id"] for i in valuation.get("inputs",[]) if i.get("source_id")} | {i["source_id"] for key in ["gordon","industry","pe","dcf"] for i in valuation.get(key,{}).get("inputs",[]) if i.get("source_id")} | {i["source_id"] for peer in valuation.get("industry",{}).get("peers",[]) for i in peer.get("inputs",[]) if i.get("source_id")})
    if number(upside) and upside>=15:
        thesis("Khoảng chênh lệch định giá giả định",f"Kịch bản tổng hợp {target:,.0f} VND/CP, chênh {upside:+.2f}% so với giá {price:,.0f} ngày {market['latest_date']}.",
               f"Đầu vào tài chính năm {year}, cần cập nhật kỳ mới. Có khoảng chênh lệch để nghiên cứu nếu các giả định lợi nhuận, vốn và chi phí vốn giữ được. Không phải lợi suất dự báo.",
               "Xác minh BCTC mới và kiểm tra lại bội số/chi phí vốn trước khi hành động.",
               "Giá trị cập nhật không còn chênh ít nhất 15%, hoặc đầu vào/giả định không còn phù hợp.",ids,market["latest_date"])
    blockers=[]
    if not latest_price_matches(result["quality"]["price_check"],market):blockers.append("Giá sử dụng chưa khớp nguồn độc lập đúng ngày.")
    if not periods:blockers.append("Chưa có kỳ tài chính hợp lệ.")
    elif year<asof.year-1:blockers.append(f"Tài chính mới nhất {year}, cần bổ sung kỳ {asof.year-1} hoặc mới hơn.")
    if result["quality"]["financial_check"].get("status")=="mismatch":blockers.append("Tài chính sai lệch với tài liệu đối chiếu.")
    if market and (asof-date.fromisoformat(market["latest_date"])).days>7:blockers.append("Giá cuối chuỗi cũ hơn 7 ngày; kiểm tra thanh khoản/tình trạng giao dịch.")
    if not number(target,True):blockers.append("Chưa đủ ít nhất hai nhóm phương pháp định giá để có mức tham chiếu tổng hợp.")
    weak_profit=number(val("net_profit")) and val("net_profit")<=0
    weak_cash=financial.get("industry_group")=="nonfinancial" and number(val("cfo")) and val("cfo")<=0
    cash_confirmed=financial.get("industry_group")!="nonfinancial" or number(val("cfo"),True)
    finance_verified=result["quality"]["financial_check"].get("status")=="matched_selected_fields"
    independent_note="Đối chiếu chỉ tiêu đã chọn; không chứng nhận toàn bộ BCTC." if finance_verified else "Tài chính chưa đối chiếu độc lập; mức tin cậy thấp."
    stance="THEO DÕI";reason="Chưa có biên chênh lệch và chất lượng đầu vào đủ mạnh để đề xuất tích lũy."
    if blockers:
        stance="CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ";reason=" ".join(blockers)
    elif weak_profit or weak_cash or upside<=-15:
        risk_reasons=[]
        if weak_profit:risk_reasons.append(f"LNST {year} không dương ({val('net_profit')/1e9:,.2f} tỷ VND).")
        if weak_cash:risk_reasons.append(f"CFO {year} không dương ({val('cfo')/1e9:,.2f} tỷ VND).")
        if upside<=-15:risk_reasons.append(f"Giá trị kịch bản tổng hợp thấp hơn giá đóng cửa {abs(upside):.2f}%.")
        stance="ƯU TIÊN QUẢN TRỊ RỦI RO";reason=" ".join(risk_reasons)+" Cần xác minh sự phục hồi hoặc cập nhật giả định trước khi tăng tỷ trọng."
    elif upside>=15 and number(growth) and growth>0 and finance_verified and cash_confirmed and spread<=60 and min(targets)>=price:
        stance="CÂN NHẮC TÍCH LŨY CÓ ĐIỀU KIỆN";reason="Chênh lệch kịch bản ít nhất 15%, lợi nhuận tăng, giá không cao hơn mức thấp nhất của các phương pháp và các chỉ tiêu chọn đã được đối chiếu."
    else:
        reason=f"Chênh lệch kịch bản {upside:+.2f}%; cần hoàn tất kiểm tra chất lượng tài chính và mức phân tán mô hình. " + independent_note
    return dict(stance=stance,reason=reason,as_of=asof.isoformat(),horizon="Theo dõi 6-12 tháng; đánh giá lại khi có BCTC mới hoặc sự kiện trọng yếu",
                confidence="Trung bình" if finance_verified and not blockers else "Thấp",confidence_note=independent_note,
                target_price_vnd=target,upside_pct=upside,model_low_vnd=min(targets) if targets else None,
                model_high_vnd=max(targets) if targets else None,model_spread_pct=spread,
                entry_ceiling_vnd=min(target/1.15,min(targets)) if stance=="CÂN NHẮC TÍCH LŨY CÓ ĐIỀU KIỆN" else None,
                opportunities=opportunities,blockers=blockers,source_ids=sorted(set(ids+refs("net_profit_growth","net_profit","cfo"))),
                methodology="Ngưỡng nghiên cứu: chênh ≥15% để xem xét tích lũy; ≤-15% ưu tiên rủi ro; phân tán max/min-1 ≤60%. Cần ≥2 nhóm mô hình, giá ≤7 ngày, tài chính từ năm trước. Tích lũy còn yêu cầu LNST tăng, CFO không âm nếu có, đối chiếu tài chính và mọi mô hình ≥giá. Các ngưỡng là quy tắc của đề tài, không phải chuẩn thị trường.",
                conditions=["Kiểm tra BCTC kỳ mới, cổ tức/phát hành và số CP trước khi sử dụng mức tham chiếu.",
                            "Cập nhật kịch bản khi lợi nhuận/dòng tiền suy giảm, chi phí vốn thay đổi hoặc giá không còn biên chênh lệch.",
                            "Đọc toàn văn công bố trọng yếu; tin tiêu đề và kênh vĩ mô có điều kiện chưa xác nhận chất xúc tác."])
