"""Rules produce observations, implications and follow-up conditions, not buy/sell labels."""


def build_conclusion(financial, market, valuation, quote_check, interim=None):
    opportunities, risks = [], []
    metrics={m["key"]:m for m in financial["metrics"]}
    def value(key):return metrics.get(key,{}).get("value")
    year=financial["periods"][0]["year"] if financial["periods"] else None
    if financial.get("industry_group")=="bank":
        profit_growth=value("net_profit_growth")
        if profit_growth is not None:
            target=opportunities if profit_growth>0 else risks
            target.append(f"LNST năm {year} {'tăng' if profit_growth>0 else 'giảm'} {abs(profit_growth):.2f}% so với cùng kỳ; cần đối chiếu thu nhập lãi, chi phí dự phòng và chất lượng tín dụng.")
        for key,label in [("cir","CIR"),("roe","ROE"),("roa","ROA")]:
            if value(key) is not None:
                opportunities.append(f"{label} năm {year}: {value(key):.2f}%; đọc cùng nhóm ngân hàng đồng kỳ và chất lượng tài sản, không tự suy ra cổ phiếu rẻ.")
    elif value("revenue_growth") is not None and value("net_profit_growth") is not None:
        if value("revenue_growth")>0 and value("net_profit_growth")>0:
            opportunities.append(f"Năm {year}, doanh thu tăng {value('revenue_growth'):.1f}% và LNST tăng {value('net_profit_growth'):.1f}%. Kết quả kinh doanh cải thiện; cần theo dõi khả năng duy trì tăng trưởng trong kỳ tiếp theo.")
        elif value("revenue_growth")<0 or value("net_profit_growth")<0:
            risks.append(f"Năm {year}, doanh thu hoặc lợi nhuận giảm so với cùng kỳ. Cần đọc thuyết minh để phân biệt yếu tố chu kỳ và khoản bất thường.")
    if financial.get("industry_group")=="nonfinancial" and value("cfo") is not None:
        if value("cfo")<0:
            risks.append(f"CFO năm {year} âm: hoạt động kinh doanh chưa tạo dòng tiền thuần dương; kiểm tra khoản phải thu, hàng tồn kho và thời điểm thanh toán.")
        elif value("cash_conversion") is not None and value("cash_conversion")>=1:
            opportunities.append(f"CFO/LNST năm {year} là {value('cash_conversion'):.2f} lần: dòng tiền kinh doanh hỗ trợ lợi nhuận trong kỳ; cần kiểm tra tính lặp lại của thay đổi vốn lưu động.")
        elif value("cash_conversion") is not None:
            risks.append(f"CFO/LNST năm {year} là {value('cash_conversion'):.2f} lần, thấp hơn 1; cần theo dõi chuyển đổi lợi nhuận thành tiền.")
    if market and market["ma50_vnd"] is not None:
        if market["latest_close_vnd"]>market["ma20_vnd"] and market["latest_close_vnd"]>market["ma50_vnd"]:
            opportunities.append("Giá cuối chuỗi cao hơn MA20 và MA50, cho thấy xu hướng gần đây tích cực trên chuỗi nguồn; cần đối chiếu thanh khoản và nền tảng kinh doanh.")
        else:
            risks.append("Giá cuối chuỗi chưa đồng thời vượt MA20 và MA50; động lực giá cần được theo dõi thêm.")
    if market and market["max_drawdown_pct"] is not None:
        risks.append(f"Chuỗi giá điều chỉnh có mức sụt giảm lớn nhất {market['max_drawdown_pct']:.1f}% trong giai đoạn chọn; đây là rủi ro biến động đã quan sát, không phải dự báo.")
    if interim and interim.get("valid"):
        fields=interim["fields"];profit=fields["net_profit"];revenue=fields["revenue"]
        if profit["previous"]>0 and revenue["previous"]>0:
            opportunities.append(f"BCTC gốc kỳ kết thúc {interim['period_end']}: doanh thu thuần thay đổi {(revenue['value']/revenue['previous']-1)*100:.1f}%, LNST thay đổi {(profit['value']/profit['previous']-1)*100:.1f}% so với cùng kỳ. Cần kiểm tra đóng góp từ thu nhập tài chính và hoạt động cốt lõi.")
    if quote_check.get("status")!="matched":
        risks.append("Giá chưa được đối chiếu đầy đủ với nguồn độc lập; chưa dùng để đưa kết luận định giá.")
    risks.append("Các tỷ số năm phản ánh kỳ đã công bố, có thể khác tình hình hiện tại. Kịch bản P/B nhạy với giả định và không tự động dẫn đến quyết định mua/bán.")
    if not opportunities:
        opportunities.append("Chưa đủ bằng chứng để kết luận cơ hội nổi bật; cần bổ sung hoặc xác minh dữ liệu.")
    matrix=[]
    if value("net_profit_growth") is not None and value("net_profit_growth")<0:
        matrix.append({"evidence":f"LNST năm {year} giảm {abs(value('net_profit_growth')):.2f}%", "impact":"Áp lực duy trì lợi nhuận", "monitor":"Thu nhập lãi và dự phòng" if financial.get("industry_group")=="bank" else "Sản lượng, biên lợi nhuận và khoản bất thường", "source_ids":[i["source_id"] for i in metrics["net_profit_growth"]["inputs"] if i.get("source_id")]})
    if market and market.get("ma20_vnd") is not None and market["latest_close_vnd"]<market["ma20_vnd"]:
        matrix.append({"evidence":f"Đóng cửa {market['latest_close_vnd']:,.0f} thấp hơn MA20 {market['ma20_vnd']:,.0f}","impact":"Động lực giá ngắn hạn yếu trên chuỗi nguồn","monitor":"Xu hướng giá và thanh khoản; không tự suy ra giá trị doanh nghiệp","source_ids":[quote_check["source_id"]] if quote_check.get("source_id") else []})
    if quote_check.get("status")!="matched":
        matrix.append({"evidence":"Giá chưa khớp đủ phiên nguồn thứ hai","impact":"Không đủ cơ sở đối chiếu định giá","monitor":"Khớp ngày, đơn vị và cơ sở điều chỉnh","source_ids":[quote_check["source_id"]] if quote_check.get("source_id") else []})
    for reason in valuation.get("blocked_reasons",[])[:2]:
        matrix.append({"evidence":reason,"impact":"Một số phương pháp bị chặn","monitor":"Xác minh đầu vào còn thiếu từ tài liệu gốc","source_ids":[]})
    if financial.get("industry_group")=="bank":
        matrix.append({"evidence":"Chưa xác minh NIM, NPL và CAR","impact":"Chưa lượng hóa chất lượng tín dụng/an toàn vốn","monitor":"BCTC và thuyết minh kỳ mới; không suy luận từ tăng trưởng dư nợ","source_ids":[]})
    return {"opportunities":opportunities,"risks":risks,"risk_matrix":matrix,
            "summary":"Đánh giá dựa trên tăng trưởng, dòng tiền, xu hướng giá và giả định định giá; xem từng luận điểm cùng nguồn và giới hạn dữ liệu."}
