# SHS: tài chính 2025 và cơ sở chỉ tiêu giá

Cập nhật 11/10/2026 theo PDF người dùng vừa xuất. Adapter `src/data/shs_issuer.py` tự đọc bảng kiểm toán riêng lẻ SHS trong BCTN 2025. [Công bố chính thức](https://www.shs.com.vn/cong-bo-thong-tin/shs-cbtt-bao-cao-thuong-nien-nam-2025) ghi 09/04/2026; văn bản trong PDF ghi 10/04/2026. Dùng ngày muộn hơn, không sử dụng trước ngày đó.

Trang công bố/PDF trực tiếp được cache 24 giờ với URL, thời gian tải và SHA256; kiểm tra hash mỗi lần dùng lại. Bản sao từ danh mục chỉ dùng khi checksum khớp và doanh nghiệp/năm/kiểm toán/đơn vị/phạm vi/hàng bắt buộc trong PDF qua kiểm tra. Danh mục/Parquet không tự trở thành đầu vào định giá. Lần kiểm chứng cuối dùng PDF tải trực tiếp từ máy chủ SHS.

Bộ đọc kiểm tra cột 2025–2024, kể cả PDF hai trang trên một tờ, thứ tự cột, đơn vị VND, tài sản = nợ + vốn và hàng không mơ hồ. Mỗi giá trị có trang PDF/mã hàng/kỳ/nguồn. LNST riêng lẻ là lợi nhuận của chính công ty; không suy NCI cho báo cáo hợp nhất. Adapter này chỉ kiểm chứng bố cục SHS, chưa đọc mọi PDF.

Metadata KBS 2025 ghi 24 tháng vẫn bị loại. Đối chiếu giá trị gắn nhãn năm KBS với PDF không sửa kỳ KBS. Khớp 12 giá trị: tài sản, nợ, vốn, doanh thu, LNST, CFO của hai năm. Chỉ xác nhận giá trị liệt kê; KBS có thể lấy số từ cùng tài liệu gốc, không coi là kiểm toán độc lập thứ hai.

Lỗi thử Yahoo lưu trong `acquisition.json`/`price_attempts`. Nguồn dự phòng thành công thì UI/PDF thông báo nguồn đã dùng; mọi nguồn thất bại thì vẫn hiện lỗi và chặn phân tích. Có Adj Close đầy đủ thì dùng; nếu thiếu, tính biến động/drawdown/MA/độ biến động trên đóng cửa cùng nguồn, ghi chưa xác minh điều chỉnh quyền. Không gọi là tổng lợi nhuận hoặc tổn thất thực nhận. Mẫu lịch sử không khớp vẫn chặn chỉ tiêu. Không ghép chuỗi/tự tạo Adj Close.

SHS 2025: LNST tăng 32,25%; LNTT đã thực hiện giảm 18,19%; chưa thực hiện chiếm 42,89% LNTT. Khuyến nghị **THEO DÕI**, không còn chặn do thiếu 2025. Kịch bản mặc định 18.796 VND/CP so với 11.700 ngày 09/10/2026; chênh lệch giả định không phải lợi suất dự báo. DCF CFO/FCFF sản xuất không áp cho chứng khoán. Thêm luận điểm cho vay, rủi ro chất lượng lợi nhuận và điều kiện xác nhận/bác bỏ; quy tắc chưa backtest.

Mẫu ngành VCK, VCI, MBS, LPS tại 2025; trung vị mỗi chỉ tiêu cần ít nhất hai giá trị. VCK thiếu năm gốc nên thiếu ROE/tăng trưởng. Khi chỉ đủ mẫu năm trước, so cả mã phân tích/peer tại năm chung, ghi độ trễ. P/B mẫu khác kỳ/phạm vi với vốn định giá bị chặn.

112 kiểm thử đạt: kỳ/cột/đơn vị/phạm vi PDF, ngày công bố tương lai, checksum sai, cache khi DNS lỗi, giá trị lệch, cơ sở chuỗi giá, lợi nhuận đã thực hiện, ngành khác năm. Pipeline nguồn thực SHS: khớp 20/20 phiên KBS/Vietcap, `analyzed`, không lỗi thu thập. AppTest dùng kết quả thực, mock pipeline/xuất PDF: không ngoại lệ, năm 2025, THEO DÕI và chỉ tiêu giá nguồn. PDF cuối 14 trang đã render/xem toàn bộ, bỏ trang ngắt thừa.

Minh chứng: `submission/evidence/shs_issuer_upgrade.json`. Kết quả sáu mã tại commit 7634381 là lịch sử; SHS mới thay bản cũ. Adapter này chưa bổ sung F88/QNS. Gemini thật, Cloud và điều chỉnh quyền toàn lịch sử chưa kiểm chứng.
