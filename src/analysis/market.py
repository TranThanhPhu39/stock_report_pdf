"""Market statistics with an explicit adjusted or source-close basis."""
import math
import statistics


def analyze_market(rows, quote_check=None):
    if not rows:
        return None
    closes = [row["close"] for row in rows]
    adjusted = [row.get("adjusted_close") for row in rows]
    usable = all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v > 0 for v in adjusted)
    history_ok = quote_check is None or quote_check.get("status")=="matched"
    series = adjusted if usable and history_ok else closes
    # The price chart and moving averages always display provider Close.
    # A separate series may be used for historical return/risk calculations.
    peak, drawdown = series[0], 0
    for value in series:
        peak=max(peak,value);drawdown=min(drawdown,value/peak-1)
    returns = [math.log(series[i]/series[i-1]) for i in range(1,len(series))]
    return {"latest_close_vnd": closes[-1],"source_id":rows[-1].get("source_id"),"first_date":rows[0]["date"],"row_count":len(rows),"latest_date": rows[-1]["date"],"latest_volume": rows[-1]["volume"],
            "ma20_vnd":sum(closes[-20:])/20 if history_ok and len(rows)>=20 else None,
            "ma50_vnd":sum(closes[-50:])/50 if history_ok and len(rows)>=50 else None,
            "return_pct":(series[-1]/series[0]-1)*100 if history_ok else None,
            "max_drawdown_pct":drawdown*100 if history_ok else None,
            "annualized_volatility_pct":statistics.stdev(returns)*math.sqrt(252)*100 if history_ok and len(returns)>1 else None,
            "adjustment_verified":usable and history_ok and all(r.get("adjustment_verified") is True for r in rows),
            "adjusted_series_available":usable,
            "statistics_basis":"provider_adjusted_close" if usable and history_ok else "source_close",
            "return_label":"Biến động giá điều chỉnh theo nguồn" if usable and history_ok else "Biến động đóng cửa nguồn",
            "average_volume_20":sum(r["volume"] for r in rows[-20:])/20 if len(rows)>=20 else None,
            "history_indicators_available":history_ok,
            "chart_prices": closes, "series_basis":"Giá đóng cửa (VND/CP)",
            "chart_note":"Biểu đồ và MA20/MA50 dùng giá đóng cửa (Close) từ nguồn. Giá mới nhất dùng để đối chiếu định giá; không thay bằng Adj Close.",
            "return_note":"Mẫu lịch sử chưa khớp đầy đủ: chỉ vẽ đóng cửa từ nguồn chính, không tính MA, lợi suất, drawdown hoặc biến động năm hóa. Giá mới nhất được kiểm tra riêng cho định giá." if not history_ok else "Biến động, drawdown và độ biến động dùng chuỗi Adj Close do nguồn cung cấp, tách khỏi biểu đồ/MA giá đóng cửa. Chưa đối chiếu độc lập toàn bộ sự kiện điều chỉnh quyền; không phải lợi nhuận thực nhận sau thuế/phí." if usable else "Biến động, drawdown và độ biến động tính trên chuỗi đóng cửa nguồn. Chưa xác minh điều chỉnh cổ tức/chia tách cho toàn lịch sử; sự kiện quyền có thể ảnh hưởng các chỉ tiêu. Đây không phải tổng lợi nhuận đầu tư."}
