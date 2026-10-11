# Báo cáo hai cột, HNX/UPCoM và khuyến nghị (11/10/2026)

Mẫu CFO của người dùng là tài liệu tham khảo bố cục. Nội dung số liệu/khuyến nghị SIP của mẫu không được đưa vào các mã khác.

## Bố cục

Các phần phân tích dùng hai vùng cố định: biểu đồ/bảng tóm tắt bên trái 56 mm, nội dung phân tích bên phải 112 mm, khoảng cách 6 mm. Frame phân tích chỉ nằm bên phải; khi nội dung sang trang, không tràn vào vùng biểu đồ. Từng phần có biểu đồ tương ứng: giá/khối lượng, GDP/CPI năm, so sánh ngành, doanh thu/LNST/CFO, định giá/độ nhạy, số trang BCTN đã tải và mẫu tin truy xuất. Chú giải phương pháp dùng chữ PDF để dễ đọc. Phụ lục công thức và nguồn dùng toàn chiều rộng.

Trang đầu có khuyến nghị, ngày/kỳ, mức tin cậy, kịch bản giá và phạm vi kiểm tra. Phần cơ hội nêu bằng chứng, ý nghĩa có điều kiện, điều kiện xác nhận và điều kiện bác bỏ. Các PDF VNM, SHS, VNZ mới thay mẫu trước; các PDF cũ khác chưa tự đổi chỉ bằng cập nhật code, cần bấm Phân tích lại.

## Lỗi nguồn đã sửa

- Yahoo không có một số mã HNX/UPCoM. KBS đã có giá nhưng code cũ chỉ dùng Yahoo làm đối chiếu, dẫn tới báo thiếu giá và chặn định giá. Thêm adapter Vietcap gap-chart, kiểm tra mã, độ dài mảng, timestamp, OHLC và ngày. Giá gốc VND, không nhân thêm 1.000. Snapshot và tham số POST được lưu để truy vết. Đối chiếu không dùng lại chính nhà cung cấp của chuỗi chính.
- KBS thử trực tiếp cho SHS/VNM: edate=10/10 thiếu phiên 09/10, edate=11/10 có phiên đó. Đệm truy vấn hai ngày, sau đó lọc <= ngày chốt cả ở chuỗi chính và đối chiếu. Không đưa phiên hiện tại/tương lai vào phân tích.
- F88 có ba Head liên tiếp và Value4 trống. Cho phép ba kỳ trong trường hợp này; vẫn loại một/hai Head hoặc Value4 có số không có metadata. Kỳ 24 tháng, công bố/cập nhật sau ngày phân tích, phạm vi hoặc ngày cuối kỳ không khớp vẫn bị loại.
- CFO chứng khoán mã ReportNormID=4735 được bổ sung. Không áp CFO/LNST hay DCF FCFF doanh nghiệp sản xuất cho chứng khoán.
- Giá mẫu định giá ngành cũng thử Vietcap khi Yahoo không truy cập được. Giữ đối chiếu cùng ngày và yêu cầu hai P/B hợp lệ; không thay mẫu thiếu bằng bội số ngành cố định.

Đặc tả adapter được đối chiếu với [mã nguồn Quote của vnstock](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/vci/quote.py), [const Vietcap](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/vci/const.py) và response trực tiếp của Vietcap. Nguồn Parquet tham khảo vn-annual-report-miner vẫn chỉ có HSX/HNX; UPCoM sử dụng tài chính KBS và danh mục BCTN, không tự gán bảng HSX/HNX sang UPCoM.

## Quy tắc khuyến nghị nghiên cứu

Kết luận không cần Gemini. Giá trị tổng hợp là kịch bản dựa trên giả định, không phải dự báo lợi suất/giá mục tiêu được đảm bảo. Theo dõi 6-12 tháng và đánh giá lại khi có BCTC hoặc sự kiện trọng yếu.

| Trạng thái | Điều kiện |
|---|---|
| Chưa đủ cơ sở khuyến nghị | Giá chưa khớp đúng ngày; giá cũ hơn 7 ngày; thiếu kỳ tài chính; kỳ tài chính trước năm liền trước; sai lệch tài chính; hoặc chưa có hai nhóm phương pháp tổng hợp |
| Ưu tiên quản trị rủi ro | Sau kiểm tra dữ liệu: LNST không dương, CFO không dương với phi tài chính, hoặc giá trị tổng hợp thấp hơn giá ít nhất 15% |
| Cân nhắc tích lũy có điều kiện | Chênh lệch >=15%; LNST tăng; CFO dương nếu phi tài chính; các chỉ tiêu chọn đối chiếu khớp; tất cả nhóm mô hình >=giá; max/min-1 <=60% |
| Theo dõi | Đủ đầu vào tổng hợp nhưng chưa đạt điều kiện trên |

Ngưỡng 15%, 60%, 7 ngày và trọng số là quy tắc công khai của đề tài, không phải chuẩn thị trường hay kết quả tối ưu hóa/backtest. Không dùng nhiều biến thể P/B để giả làm hai nhóm mô hình. Mức giá trần tham khảo chỉ hiện khi đủ điều kiện tích lũy: min(giá trị tổng hợp/1,15; mức thấp nhất của các nhóm mô hình). Không tạo stop loss hoặc chất xúc tác từ tiêu đề tin. Đối chiếu tài chính chỉ áp dụng các chỉ tiêu chọn, không chứng nhận toàn bộ BCTC.

## Kiểm chứng và giới hạn

Phần dưới ghi kết quả lịch sử tại commit 7634381. SHS và cách tính chỉ tiêu khi thiếu Adj Close đã được cập nhật tiếp trong [SHS: tài chính 2025](shs_issuer_upgrade.md); không dùng giới hạn cũ bên dưới làm trạng thái SHS hiện tại.

Ngày phân tích 11/10/2026, giá phiên 09/10/2026. Chạy nguồn trực tiếp VNM, SHS, VNZ, PVS, QNS, F88; cả sáu khớp 20/20 phiên trong mẫu đối chiếu. Không chứng nhận toàn thị trường hoặc toàn bộ lịch sử điều chỉnh. KBS/Vietcap không có Adj Close nên chưa tính lợi suất/drawdown/biến động năm hóa; MA được tính trên đóng cửa nguồn khi mẫu đối chiếu khớp.

SHS/F88 vẫn dùng kỳ hợp lệ 2024 do metadata 2025 ghi 24 tháng; không tự sửa thành 12 tháng. QNS thiếu đầu vào cho ít nhất hai nhóm mô hình. F88 thiếu hai peer cùng kỳ nên chưa có trung vị ngành. Các giới hạn này hiện trong giao diện/PDF và hồ sơ phân tích. Báo cáo SHS có CFO chứng khoán âm được trình bày đúng ngành; kịch bản định giá sử dụng 2024 được gắn kỳ và không tạo khuyến nghị tích lũy hiện tại.

101 kiểm thử offline đạt. Giao diện AppTest hiển thị SHS/VNZ từ kết quả nguồn thực, không ngoại lệ; test giao diện mock pipeline, không phải test deploy. Ba PDF mới được render và kiểm tra tất cả trang; kiểm tra ảnh nằm trong cột trái và chữ trong lề. Chi tiết run IDs, giá, giới hạn và SHA256 trong `submission/exchange_report_acceptance.json`. Chưa kiểm chứng API Gemini thật, Streamlit Cloud hoặc mọi mã.
