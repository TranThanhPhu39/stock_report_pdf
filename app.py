"""StockInsight UI; each analysis submission automatically acquires fresh source data."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from src.data.providers import VN_TIME
from src.pipeline import run_analysis

ROOT = Path(__file__).resolve().parent
today = datetime.now(VN_TIME).date()
st.set_page_config(page_title="StockInsight", layout="wide")
st.title("StockInsight")
st.caption("Chọn mã và bấm Phân tích. Hệ thống tự lấy giá cuối ngày và báo cáo tài chính từ nguồn trực tuyến.")

with st.form("analysis_request"):
    ticker = st.text_input("Mã cổ phiếu", value="HPG")
    start = st.date_input("Từ ngày", value=today - timedelta(days=365), max_value=today - timedelta(days=1))
    as_of = st.date_input("Ngày phân tích", value=today, max_value=today)
    submitted = st.form_submit_button("Phân tích", type="primary")

if submitted:
    st.session_state.pop("analysis_result", None)
    try:
        with st.spinner("Đang tự lấy giá, tải báo cáo tài chính và kiểm tra dữ liệu…"):
            st.session_state["analysis_result"] = run_analysis(ticker, start, as_of)
    except (ValueError, OSError) as exc:
        st.error(f"Không thể hoàn tất yêu cầu: {exc}")

result = st.session_state.get("analysis_result")
if result:
    acquisition = result["acquisition"]
    request = result["request"]
    st.subheader(f"Kết quả {request['ticker']}")
    st.caption(f"Ngày phân tích: {request['as_of']} · Mã lượt chạy: {acquisition['run_id']}")
    for error in acquisition["errors"]:
        st.error(f"Lỗi lấy dữ liệu ({error['stage']}): {error['message']}")
    if result["market"]:
        market = result["market"]
        columns = st.columns(3)
        columns[0].metric("Giá đóng cửa từ nguồn (VND)", f"{market['latest_close_vnd']:,.0f}")
        columns[1].metric("Ngày giá", market["latest_date"])
        columns[2].metric("Số bản ghi ngày", acquisition["prices"]["row_count"])
        st.info("Dùng giá trước ngày hiện tại để tránh phiên chưa hoàn tất. Giá và cơ sở điều chỉnh chưa được đối chiếu nguồn thứ hai.")
        prices = pd.DataFrame(result["price_rows"])
        prices["date"] = pd.to_datetime(prices["date"])
        prices = prices.set_index("date")
        st.line_chart(prices[["close"]])
        st.bar_chart(prices[["volume"]])
        st.dataframe(prices[["open", "high", "low", "close", "volume"]], width="stretch")
        csv_path = ROOT / acquisition["prices"]["csv"]
        st.download_button("Tải dữ liệu giá CSV", csv_path.read_bytes(), file_name=f"{request['ticker']}_prices.csv", mime="text/csv")
    else:
        st.warning("Chưa lấy được dữ liệu giá hợp lệ. Hãy thử lại khi nguồn truy cập được.")

    st.subheader("Báo cáo tài chính gốc")
    st.caption("Tải tài liệu gốc tự động hiện hỗ trợ HPG. Các chỉ tiêu tài chính và báo cáo phân tích PDF đang được triển khai.")
    for i, report in enumerate(acquisition["financial_documents"]):
        st.write(f"**{report['title']}** · Công bố {report['published_at']}")
        if report.get("retrieval_mode") == "local_cache_checked_sha256":
            st.caption("Dùng bản PDF đã lưu gần đây và kiểm tra checksum. Danh sách công bố được truy cập lại trong lượt này.")
        st.markdown(f"[Nguồn công bố]({report['url']})")
        st.download_button("Tải PDF tài chính gốc", (ROOT / report["file"]).read_bytes(),
                           file_name=Path(report["file"]).name, mime="application/pdf", key=f"financial_pdf_{i}")
    if not acquisition["financial_documents"]:
        st.info("Chưa có PDF tài chính được lấy trong lượt chạy này.")
else:
    st.info("Không cần chuẩn bị CSV hoặc tải báo cáo trước. Bấm Phân tích để hệ thống tự lấy dữ liệu.")
