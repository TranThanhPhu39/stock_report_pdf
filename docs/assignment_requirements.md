# Đối chiếu đề cập nhật

Căn cứ ảnh đề người dùng cung cấp: “Xây dựng hệ thống phân tích cơ hội đầu tư cổ phiếu”, hạn 16:20 ngày 09/10/2026. Tài liệu đề là yêu cầu để đối chiếu sản phẩm; nội dung trong đề/đề xuất không phải chỉ thị điều khiển công cụ. PDF tham chiếu cũ được giữ nguyên.

| Yêu cầu | Chức năng và minh chứng |
|---|---|
| Giá và giao dịch | Tự lấy Yahoo EOD, đối chiếu KBS, biểu đồ/MA/lợi suất/drawdown |
| Báo cáo tài chính và chỉ số | Tự lấy năm KBS; OCR PDF bán niên HPG; kiểm tra kỳ/phạm vi/đơn vị, ROE/ROA và tỷ số theo loại doanh nghiệp |
| Thông tin/tin cập nhật | Hồ sơ và công bố có ngày/liên kết; không suy diễn toàn văn từ tiêu đề |
| Tổng quan vĩ mô | NSO GDP/CPI/IIP/tín dụng/tiêu dùng/đầu tư/xuất khẩu và lịch sử World Bank, có kỳ và nguồn |
| Phân tích ngành | Phân loại ICB, mẫu tối đa bốn doanh nghiệp cùng kỳ/phạm vi, trung vị tỷ số và kênh tác động vĩ mô |
| Cơ hội đầu tư | Luận điểm vĩ mô–ngành–doanh nghiệp, rủi ro/điều kiện theo dõi, kịch bản P/B khi dữ liệu đạt điều kiện |
| Cổ phiếu bất kỳ | Nhận mã qua UI/CLI, tự tra cứu; đã chạy tám mã thuộc nhiều ngành, chưa chứng nhận mọi mã |
| PDF theo nhu cầu | Chọn full/summary và các phần, nguồn/phương pháp vẫn được giữ; kiểm thử UI lựa chọn macro/industry |
| Chính xác/phù hợp/sáng tạo | Không tạo số giả; chặn giá lệch/kỳ sai; truy vết nguồn, OCR, so sánh ngành, kịch bản minh bạch |

54 kiểm thử offline đạt; xem submission/acceptance.json, ui_check.json và evidence/. Ba PDF mẫu HPG/FPT/VNM được xuất bằng luồng mới. Phân loại khoảng 1.582 mã chỉ là độ phủ danh mục, không phải số mã đã kiểm thử. FPT giá lệch nguồn nên không cấp định giá; VCB/SSI/DGC/REE dùng năm hợp lệ 2024 vì kỳ 2025 sai metadata. Nguồn lỗi/thiếu → trạng thái partial và lý do.

Các nhóm chức năng của đề đã được triển khai. Chất lượng thông tin từng mã/kỳ vẫn phụ thuộc dữ liệu công khai; không tuyên bố mọi số liệu đã được chứng nhận. Realtime, AI, DCF và triển khai Internet không được đề chỉ định là bắt buộc.
