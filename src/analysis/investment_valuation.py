"""Reference valuation from observed comparables, excluding manual sensitivities."""
from src.analysis.valuation import number


def investment_valuation(financial, market, valuation, benchmark, sotp=None):
    out=dict(available=False,methods=[],comparisons=[],target_price_vnd=None,source_ids=[],
             reason="Chưa có bội số mẫu đủ dữ liệu đồng kỳ hoặc SOTP hợp lệ để định giá chính.",
             methodology="Ưu tiên P/B mẫu cho ngân hàng/chứng khoán, P/E mẫu cho doanh nghiệp phi tài chính; phương pháp còn lại dùng đối chiếu. Không lấy trung bình tùy ý hoặc dùng P/E/P/B nhập tay để khuyến nghị.")
    if not number(valuation.get("shares"),True) or not market or not financial.get("periods"):return out
    if not number(market.get("latest_close_vnd"),True):
        out["reason"]="Giá đóng cửa không dương hoặc không hữu hạn; không tính định giá chính."
        return out
    latest=financial["periods"][0]
    same_basis=benchmark.get("period_end")==latest["period_end"] and benchmark.get("scope")==latest["scope"] and benchmark.get("price_date")==market["latest_date"]
    if not same_basis:
        scope_names={'consolidated':'hợp nhất','separate':'riêng lẻ','parent':'công ty mẹ'}
        out["reason"]=f"BCTC mã phân tích kết thúc {latest['period_end']} ({scope_names.get(latest['scope'],'chưa xác định')}); mẫu định giá kết thúc {benchmark.get('period_end') or 'chưa có'} ({scope_names.get(benchmark.get('scope'),'chưa xác định')}), giá {benchmark.get('price_date') or 'chưa có'}. Chưa đủ mẫu đúng kỳ/phạm vi/ngày giá; không trộn năm để tạo giá mục tiêu."
    price=market["latest_close_vnd"]
    for kind,label,own,base in [
        ("pb","P/B trung vị mẫu đồng kỳ",valuation.get("reference_pb"),valuation.get("book_value_per_share")),
        ("pe","P/E trung vị mẫu đồng kỳ",valuation.get("pe",{}).get("reference_pe"),valuation.get("pe",{}).get("eps"))]:
        middle=benchmark.get("median_"+kind);n=benchmark.get(kind+"_sample_size",0)
        if not same_basis or not number(middle,True) or n<2 or not number(own,True) or not number(base,True):continue
        ids=sorted({i["source_id"] for p in benchmark.get("peers",[]) if number(p.get(kind),True) for i in p.get("inputs",[]) if i.get("source_id")})
        if not ids or len([p for p in benchmark.get("peers",[]) if number(p.get(kind),True)])<2:continue
        out["methods"].append(dict(method=label,key=kind,target_price_vnd=base*middle,multiple=middle,sample_size=n,
                                   difference_pct=(base*middle/price-1)*100,source_ids=ids,
                                   basis="Số liệu năm cuối kỳ quy đổi trên CP snapshot; không phải dự báo/TTM. Không điều chỉnh bội số nếu chưa có luận cứ định lượng."))
        premium=(own/middle-1)*100
        out["comparisons"].append(dict(key=kind,label=kind.upper().replace("P","P/",1),company_value=own,sample_median=middle,
                                      premium_pct=premium,sample_size=n,source_ids=ids,
                                      interpretation=f"Giao dịch {'cao' if premium>=0 else 'thấp'} hơn trung vị mẫu {abs(premium):.2f}%; cần đọc cùng ROE, tăng trưởng, chất lượng lợi nhuận và đòn bẩy. Chênh lệch không tự chứng minh đắt/rẻ."))
    preferred="pb" if financial.get("industry_group") in {"bank","securities"} else "pe"
    chosen=next((m for m in out["methods"] if m["key"]==preferred),next(iter(out["methods"]),None))
    if sotp and sotp.get("usable_in_primary"):
        chosen={"key":"sotp","method":"SOTP từ dữ liệu từng mảng","target_price_vnd":sotp["target_price_vnd"],"difference_pct":(sotp["target_price_vnd"]/price-1)*100,"source_ids":sotp["source_ids"],"basis":sotp["basis"]}
        out["methods"].append(chosen)
    if chosen:
        targets=[m["target_price_vnd"] for m in out["methods"]]
        out.update(available=True,selected_method=chosen["method"],selected_key=chosen["key"],target_price_vnd=chosen["target_price_vnd"],
                   upside_pct=(chosen["target_price_vnd"]/price-1)*100,low_vnd=min(targets),high_vnd=max(targets),
                   source_ids=sorted({s for m in out["methods"] for s in m["source_ids"]}),reason=out["methodology"],
                   selection_reason=("SOTP cộng các mảng không chồng lặp và cầu nối vốn cổ đông đã xác minh." if chosen["key"]=="sotp" else
                       "Chỉ có "+chosen["method"]+" đủ điều kiện; phương pháp ưu tiên theo ngành chưa đủ đầu vào. Cần bổ sung phương pháp đối chiếu." if chosen["key"]!=preferred else
                       "P/B phản ánh hiệu quả sử dụng vốn/tài sản tài chính; P/E mẫu là đối chiếu lợi nhuận." if preferred=="pb" else
                       "P/E mẫu làm tham chiếu lợi nhuận; P/B mẫu đối chiếu mức định giá vốn. Cần kiểm tra tính lặp lại của lợi nhuận."))
        if chosen["key"]!="sotp":out["selection_reason"]+=f" Mẫu có {chosen['sample_size']} doanh nghiệp đủ dữ liệu; giá trị tham chiếu không đại diện toàn ngành."
    return out
