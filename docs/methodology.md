# Phương pháp đã triển khai

## Giá

Dùng Yahoo OHLC (VND/cổ phiếu) và Adj Close riêng. Giá ngày hiện tại theo UTC+7 bị loại. Kiểm tra ngày trùng, giá hữu hạn/dương, high/low, volume nguyên không âm. Đối chiếu tối đa 20 phiên đóng cửa mới nhất với KBS, dung sai 0,1%; các phiên lệch được ghi trong PDF.

Biến động khoảng chọn = (Adj Close cuối / đầu − 1) × 100. Drawdown = min(Adj Close / đỉnh lũy kế − 1) × 100. Biến động năm hóa = std mẫu(lợi suất log ngày) × sqrt(252) × 100. MA20/MA50 tính trên Adj Close nhân hệ số close cuối / Adj Close cuối; chỉ tính khi đủ phiên. Thiếu Adj Close thì không hiển thị return/drawdown/volatility; không tự xác nhận lịch sử điều chỉnh của nguồn.

## Tài chính

Chỉ nhận API KBS bốn kỳ năm riêng biệt với Head ID 1..4; metadata công bố/cập nhật không sau ngày phân tích. Đơn vị tiền gốc là nghìn VND → VND ×1000; EPS là VND/CP giữ nguyên. Hợp nhất/đơn lẻ/công ty mẹ phải nhất quán. Tài sản phải khớp nợ + vốn với dung sai 0,1%.

| Chỉ tiêu | Công thức |
|---|---|
| Tăng trưởng | (Giá trị năm hiện tại / năm trước cùng phạm vi − 1) ×100; kỳ gốc phải dương |
| ROE hợp nhất | LNST hợp nhất / ((VCSH cuối năm + VCSH đầu năm)/2) ×100 |
| Biên gộp / ròng | Lợi nhuận gộp / doanh thu thuần; LNST / doanh thu thuần; ×100 |
| CFO/LNST | Dòng tiền kinh doanh / LNST dương |
| Nợ vay/vốn | (Nợ vay ngắn + dài hạn) / VCSH dương |

Ba tỷ số biên/CFO/nợ vay chỉ áp dụng doanh nghiệp phi tài chính. Chỉ tiêu thiếu, không cùng kỳ hoặc mẫu số không phù hợp là null và có lý do, không phải 0.

PDF hợp nhất soát xét HPG được OCR tự động. Tiền ghi bằng VND; giữ dòng nhận dạng và trang PDF. Kiểm tra assets = liabilities + equity (0,01%) và đối chiếu cột đầu năm với tài chính năm trước. Bán niên kết quả kinh doanh/CFO so với 6 tháng cùng kỳ; bảng cân đối so với đầu năm. Không cộng bán niên với Q2 để tính TTM.

## Kịch bản P/B

BVPS tham chiếu = (VCSH hợp nhất − lợi ích cổ đông không kiểm soát) / số CP hiện tại. P/B tham chiếu = giá đóng cửa / BVPS. Giá trị kịch bản = BVPS × P/B do người dùng giả định; thận trọng/cơ sở/thuận lợi tương ứng 80%/100%/120% giả định cơ sở. Đây là phân tích độ nhạy; giả định vốn cuối năm giữ nguyên trên số CP hiện tại, không phải dự báo giá trị nội tại. Chặn nếu giá không khớp nguồn, số CP/vốn thiếu hoặc dùng ngày quá khứ với số CP hiện tại. Không tính P/E TTM vì API quý chưa có ánh xạ đủ tin cậy.

## Nhận định và đối chiếu

Quy tắc dùng tăng trưởng, CFO/LNST, vị trí so với MA, drawdown và HPG bán niên để trình bày dữ kiện → điều kiện theo dõi. Không áp ngưỡng mua/bán chung. Tin chỉ là danh sách công bố có ngày/liên kết; chưa suy diễn nội dung toàn văn.

Baseline tài chính là tham chiếu đã đọc từ báo cáo thường niên gốc, riêng đúng mã/năm/chỉ tiêu. Sai lệch quá dung sai chặn tài chính/định giá. Không có baseline thì trạng thái chưa đối chiếu độc lập, không tuyên bố khớp. Các phép kiểm tra không chứng nhận toàn bộ số liệu.

## Vĩ mô và ngành

NSO: lấy bản công bố mới nhất không sau ngày phân tích. GDP dùng tăng trưởng lũy kế, CPI dùng bình quân cùng giai đoạn; không tráo tăng trưởng quý/tháng vào chỉ tiêu này. Tín dụng giữ ngày đo riêng và cơ sở cuối năm trước. Bán lẻ thực đã loại yếu tố giá. Chỉ số giá USD theo năm không phải tỷ giá giao ngay.

World Bank: dùng số liệu năm có giá trị và năm nhỏ hơn năm phân tích; ngày cập nhật không được coi là ngày công bố đầu tiên. Lãi suất cho vay mới nhất hiện là 2023, tỷ giá bình quân là 2024, chỉ phục vụ bối cảnh lịch sử. Không suy đoán lãi suất điều hành hiện tại. Bản công bố NSO có thể được sửa; chưa có kho dữ liệu vintage để tái dựng hoàn toàn thông tin quá khứ.

ICB Vietcap chỉ dùng phân loại và sàn HOSE/HNX/UPCOM, bỏ OTC/chỉ số và không sử dụng khuyến nghị/giá mục tiêu của API. Chọn cấp hẹp nhất, mở rộng cấp 3/2 nếu ít hơn hai doanh nghiệp hợp lệ. Kiểm tra cùng ngày cuối kỳ, phạm vi và nhóm báo cáo; loại kỳ sai, thiếu bảng cân đối hoặc không khớp tài sản = nợ + vốn. Chọn tối đa bốn doanh nghiệp có tài sản lớn nhất trong tập hợp lệ. Trung vị mỗi tỷ số cần ít nhất hai giá trị, không gồm mã mục tiêu. Chênh lệch phần trăm được trình bày theo điểm phần trăm; tỷ số lần theo số lần. Mẫu này không phải chỉ số ngành và có thể chứa quan hệ công ty mẹ/con.

ROA = LNST / tài sản bình quân ×100. Ngân hàng: CIR = chi phí hoạt động / (lợi nhuận trước dự phòng + chi phí hoạt động) ×100; cho vay khách hàng gộp / tiền gửi khách hàng là tỷ số phân tích, không đồng nhất LDR theo quy định. Chứng khoán: tỷ trọng doanh thu môi giới và lãi cho vay/phải thu chia doanh thu hoạt động ×100; khoản cho vay tài chính không tự coi là dư nợ margin. Kỳ năm khác 12 tháng hoặc kết thúc sau ngày công bố bị loại, không tự sửa metadata.

Luận điểm tổng hợp mô tả kênh tác động có điều kiện (ví dụ xây dựng → nhu cầu thép), dữ kiện vĩ mô và vị trí doanh nghiệp so với mẫu. Không coi tương quan là quan hệ nhân quả, không phát sinh khuyến nghị mua/bán tự động.

## Bổ sung định giá từ ZIP (09/10/2026)

Phần P/B phía trên là cơ sở phiên bản trước. Hiện có Gordon, P/B trung vị mẫu tự thu thập, P/E lợi nhuận năm quy đổi, DCF FCFF với WACC/equity bridge và bình quân trọng số. Công thức, kiểm tra đầu vào và giới hạn tại [valuation_upgrade.md](valuation_upgrade.md). P/E năm quy đổi không phải P/E TTM. Gemini tùy chọn sử dụng bundle bằng chứng có ngày/kỳ/ngành/nguồn, không tự tạo số liệu.
