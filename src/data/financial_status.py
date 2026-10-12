"""Distinguish missing periods/fields, rejected metadata and model conditions."""
import re


def financial_status(result):
    financial=result.get("financial",{})
    periods=financial.get("periods",[])
    year=periods[0]["year"] if periods else None
    expected=int(result["request"]["as_of"][:4])-1
    rejected=sorted({int(m.group(1)) for warning in result.get("quality",{}).get("warnings",[])
                     if (m:=re.search(r"loại kỳ (\d{4}), metadata",warning))})
    missing=[m["label"] for m in financial.get("metrics",[]) if m["key"] in {"revenue","net_profit","assets","equity","cfo"} and m.get("value") is None]
    methods=[{"method":label,"reason":data.get("reason","Chưa đủ điều kiện mô hình.")}
             for key,label in [("gordon","Gordon"),("industry","P/B mẫu ngành"),("pe","P/E"),("dcf","DCF")]
             if (data:=result.get("valuation",{}).get(key)) and not data.get("available")]
    messages=[]
    if year is None:messages.append("Chưa có kỳ BCTC đủ metadata và kiểm tra để sử dụng trong phân tích chính.")
    else:messages.append(f"BCTC dùng trong phân tích chính: năm {year}, phạm vi {dict(consolidated='hợp nhất',separate='riêng lẻ',parent='công ty mẹ').get(periods[0]['scope'],periods[0]['scope'])}.")
    if result['request'].get('ticker')=='SSI':messages.append('SSI: bộ đọc hiện xác minh BCTC năm; chưa tích hợp BCTC quý/bán niên hoặc lợi nhuận TTM. Năm 2025 không có nghĩa là báo cáo mới nhất doanh nghiệp đã công bố trong 2026.')
    interim = result.get('interim')
    if interim and interim.get('valid') and interim.get('ticker'):
        messages.append(f"Có cập nhật BCTC hợp nhất bán niên kết thúc {interim['period_end']}. Định giá P/E/P/B mẫu đồng kỳ vẫn dùng năm {year}; chưa tính lợi nhuận TTM hoặc P/B bán niên với mẫu cùng kỳ.")
    if rejected:
        messages.append("Nguồn KBS có kỳ bị loại do metadata đầu/cuối không hợp lệ: "+", ".join(map(str,rejected))+". Có số liệu gắn nhãn năm không đồng nghĩa kỳ đã được xác nhận.")
    if year is not None and year<expected:messages.append(f"Chưa có kỳ {expected} hoặc mới hơn đủ điều kiện sử dụng; không có nghĩa doanh nghiệp chưa công bố BCTC.")
    if missing:messages.append("Thiếu chỉ tiêu phù hợp trong kỳ dùng: "+", ".join(missing)+".")
    return {"latest_valid_year":year,"expected_annual_year":expected,"rejected_kbs_years":rejected,
            "missing_fields":missing,"blocked_methods":methods,"messages":messages,
            "note":"Lợi nhuận âm, FCFF âm hoặc mô hình không phù hợp ngành là điều kiện mô hình; không tự gọi là thiếu toàn bộ BCTC."}
